"""Run a disposable two-company fixture through real local embeddings and Ollama."""
from pathlib import Path
from io import BytesIO
import json
import sys
import tempfile
import time
from pypdf import PdfWriter
from pypdf.generic import DecodedStreamObject,DictionaryObject,NameObject

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from fastapi.testclient import TestClient
from server import ai, knowledge
from server.app import create_app

ORIGIN={'Origin':'http://127.0.0.1:5173'}

def text_pdf(text: str) -> bytes:
    writer=PdfWriter();page=writer.add_blank_page(width=612,height=792)
    font=DictionaryObject({NameObject('/Type'):NameObject('/Font'),NameObject('/Subtype'):NameObject('/Type1'),NameObject('/BaseFont'):NameObject('/Helvetica')})
    page[NameObject('/Resources')]=DictionaryObject({NameObject('/Font'):DictionaryObject({NameObject('/F1'):writer._add_object(font)})})
    stream=DecodedStreamObject();stream.set_data(('BT /F1 12 Tf 72 700 Td ('+text+') Tj ET').encode('ascii'))
    page[NameObject('/Contents')]=writer._add_object(stream)
    result=BytesIO();writer.write(result)
    return result.getvalue()

def main():
    if not ai.model_ready(): raise SystemExit('Configured Ollama model is unavailable on loopback.')
    with tempfile.TemporaryDirectory(prefix='h4t-ai-proof-') as folder:
        app=create_app(Path(folder)/'proof.sqlite3')
        clients=[]
        for key,name,source in [
            ('cedar','Cedar Cycles','Cedar Cycles repairs bicycles. Workshop hours are Monday to Friday, 9 AM to 5 PM. A standard bicycle tune-up costs 45 dollars.'),
            ('harbor','Harbor Books','Harbor Books sells books. Store hours are Saturday, 10 AM to 2 PM. A paperback gift card costs 20 dollars.'),
        ]:
            client=TestClient(app)
            registered=client.post('/api/auth/register',headers=ORIGIN,json={'email':key+'@example.test','password':'Synthetic-Local-Proof-Only-2026','name':'Fixture owner','company':name})
            assert registered.status_code==201,registered.text
            account=registered.json()
            filename='verified-facts.pdf' if key=='cedar' else 'verified-facts.txt'
            content=text_pdf(source) if key=='cedar' else source.encode()
            uploaded=client.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':filename,'Content-Type':'application/octet-stream'},content=content)
            assert uploaded.status_code==201,uploaded.text
            sid=uploaded.json()[0]['id']
            published=client.put('/api/company/sources/'+sid,headers=ORIGIN,json={'expected_version':1})
            assert published.status_code==200,published.text
            clients.append((client,account,sid))
        indexed=[]
        while job:=knowledge.next_job(app.state.database):
            started=time.perf_counter()
            outcome=knowledge.process_job(app.state.database,job)
            assert outcome=='ready',f'Indexing returned {outcome}'
            indexed.append(round(time.perf_counter()-started,2))
        assert len(indexed)==2
        a,account_a,_=clients[0]
        b,account_b,_=clients[1]
        a_hits=knowledge.search(app.state.database,account_a['companyId'],'When can I bring in my bike for repair?')
        b_hits=knowledge.search(app.state.database,account_b['companyId'],'When is the bookstore open?')
        assert a_hits and b_hits
        assert all('Harbor Books' not in hit['text'] for hit in a_hits)
        assert all('Cedar Cycles' not in hit['text'] for hit in b_hits)
        visitor=TestClient(app)
        session=visitor.post('/api/visitor/'+account_a['botId']+'/sessions',headers=ORIGIN,json={})
        assert session.status_code==201,session.text
        token=session.json()['token'];cid=session.json()['conversation']['id']
        path='/api/visitor/'+account_a['botId']+'/conversations/'+cid+'/messages'
        started=time.perf_counter()
        answer=visitor.post(path,headers={**ORIGIN,'Authorization':'Bearer '+token},json={'text':'What are your workshop hours?','request_id':'local-proof-hours-001'})
        assert answer.status_code==200,answer.text
        reply=answer.json()['messages'][-1]
        assert reply['role']=='bot' and reply['engine'].startswith('ollama:') and reply['citations'],reply
        assert 'Harbor Books' not in reply['text']
        unknown=visitor.post(path,headers={**ORIGIN,'Authorization':'Bearer '+token},json={'text':'What is your CEO\'s personal phone number?','request_id':'local-proof-unknown-002'})
        assert unknown.status_code==200,unknown.text
        unknown_reply=unknown.json()['messages'][-1]
        assert unknown_reply['engine'] in ('no_evidence','clarification'),unknown_reply
        print(json.dumps({'model':ai.MODEL,'embedding_dimensions':384,'companies':2,'source_types':['PDF','TXT'],'indexed_seconds':indexed,'answer_seconds':round(time.perf_counter()-started,2),'answer':reply['text'],'citation_titles':[c['title'] for c in reply['citations']],'unknown_engine':unknown_reply['engine']},indent=2))

if __name__=='__main__': main()
