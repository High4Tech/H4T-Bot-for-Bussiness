"""Local RAG contract: isolation, versioning, evidence, and handoff."""
import json
import secrets
import pytest
from fastapi.testclient import TestClient
from server import ai, knowledge
from server.app import password_hash
from tests.test_product import ORIGIN, PASSWORD, owner, visitor, write

def vectorize(values):
    return [[1.0]+[0.0]*383 for _ in values]

def publish(client, source_id, version=1):
    result=client.put('/api/company/sources/'+source_id,headers=ORIGIN,json={'expected_version':version})
    assert result.status_code==200,result.text
    return next(s for s in result.json() if s['id']==source_id)

def test_two_company_index_update_archive_and_worker_scope(service):
    a,ua=owner(service);b,ub=owner(service,'b')
    for client,filename,text in [(a,'Cedar.txt',b'Cedar support is open Monday to Friday from 9 AM to 5 PM.'),(b,'Harbor.txt',b'Harbor support is open Saturday from 10 AM to 2 PM.')]:
        result=client.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':filename,'Content-Type':'application/octet-stream'},content=text)
        assert result.status_code==201,result.text
        publish(client,result.json()[0]['id'])
    with service.state.database.connect(plane='worker') as conn:
        jobs=[dict(r) for r in conn.execute("SELECT id,company_id,source_id,version FROM ingestion_jobs WHERE status='queued' ORDER BY company_id").fetchall()]
    assert len(jobs)==2
    assert all(knowledge.process_job(service.state.database,job,vectorize)=='ready' for job in jobs)
    a_hits=knowledge.search(service.state.database,ua['companyId'],'support hours',vectorize=vectorize)
    b_hits=knowledge.search(service.state.database,ub['companyId'],'support hours',vectorize=vectorize)
    assert a_hits and b_hits
    assert all('Cedar' in hit['text'] and 'Harbor' not in hit['text'] for hit in a_hits)
    assert all('Harbor' in hit['text'] and 'Cedar' not in hit['text'] for hit in b_hits)
    source_id=a_hits[0]['sourceId']
    draft=a.put('/api/company/sources/'+source_id,headers=ORIGIN,json={'expected_version':2})
    assert draft.status_code==200
    assert knowledge.search(service.state.database,ua['companyId'],'support hours',vectorize=vectorize)==[]
    republished=publish(a,source_id,3)
    assert republished['indexStatus']=='queued'
    job=next(j for j in [knowledge.next_job(service.state.database)] if j and j['company_id']==ua['companyId'])
    assert knowledge.process_job(service.state.database,job,vectorize)=='ready'
    assert all(hit['version']==4 for hit in knowledge.search(service.state.database,ua['companyId'],'support hours',vectorize=vectorize))
    with service.state.database.connect(company=ua['companyId']) as conn:
        versions=[r['version'] for r in conn.execute('SELECT version FROM knowledge_chunks WHERE company_id=? AND source_id=?',(ua['companyId'],source_id)).fetchall()]
    assert versions==[4]
    assert a.delete('/api/company/sources/'+source_id,headers=ORIGIN).status_code==200
    assert knowledge.search(service.state.database,ua['companyId'],'support hours',vectorize=vectorize)==[]

def test_existing_published_source_is_queued_by_migration(service):
    client,account=owner(service)
    uploaded=client.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':'Existing.txt'},content=b'Existing source text.')
    assert uploaded.status_code==201
    source_id=uploaded.json()[0]['id']
    publish(client,source_id)
    with service.state.database.connect(company=account['companyId'],write=True) as conn:
        conn.execute("UPDATE ingestion_jobs SET status='deferred' WHERE company_id=? AND source_id=? AND version=2",(account['companyId'],source_id))
    service.state.database.migrate()
    current=client.get('/api/company/workspace').json()['sources'][0]
    assert current['indexStatus']=='queued'

def test_generation_requires_valid_source_citation_and_rejects_new_numbers(monkeypatch):
    evidence=[{'sourceId':'source-one','version':2,'title':'Hours','url':None,'text':'Support is open from 9 AM to 5 PM.','score':.8}]
    monkeypatch.setattr(ai,'_ollama',lambda messages:({'status':'answered','answer':'Support is open from 9 AM to 5 PM.','citations':[1]},.25))
    response=ai.answer('When is support open?',evidence,'Cedar')
    assert response['engine'].startswith('ollama:') and response['citations'][0]['title']=='Hours'
    monkeypatch.setattr(ai,'_ollama',lambda messages:({'status':'answered','answer':'Support opens at 7 AM.','citations':[1]},.25))
    assert ai.answer('When is support open?',evidence,'Cedar')['engine']=='clarification'
    monkeypatch.setattr(ai,'_ollama',lambda messages:({'status':'answered','answer':'Made up answer.','citations':[99]},.25))
    assert ai.answer('When is support open?',evidence,'Cedar')['engine']=='clarification'
    assert ai.answer('Unknown topic',[],'Cedar')['engine']=='no_evidence'

def test_visitor_ai_citations_idempotency_and_handoff(service,monkeypatch):
    a,ua=owner(service);v,data,path=visitor(service,ua['botId'])
    evidence=[{'sourceId':'synthetic','version':1,'title':'Support hours','url':None,'text':'Support opens at 9 AM.','score':.8}]
    monkeypatch.setattr(knowledge,'search',lambda *args,**kwargs:evidence)
    monkeypatch.setattr(ai,'answer',lambda *args,**kwargs:{'text':'Support opens at 9 AM.','citations':[{'sourceId':'synthetic','version':1,'title':'Support hours','url':None,'snippet':'Support opens at 9 AM.'}],'engine':'ollama:test-local','latency':.1})
    response=write(v,path,data['token'],'When does support open?')
    assert response.status_code==200,response.text
    messages=response.json()['messages']
    assert len(messages)==2 and messages[-1]['citations'][0]['title']=='Support hours'
    assert write(v,path,data['token'],'When does support open?').json()['messages']==messages
    assert write(v,path,data['token'],'Talk to a person',key='handoff-ai-test').json()['status']=='HUMAN_REQUESTED'
    assert a.get('/api/company/billing').json()['aiAnswers']==1
    with service.state.db() as conn:
        conn.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),'ai-operator@example.test','Operator',password_hash(PASSWORD),None,'platform_admin'))
    operator=TestClient(service)
    assert operator.post('/api/auth/login',headers=ORIGIN,json={'email':'ai-operator@example.test','password':PASSWORD}).status_code==200
    metadata=operator.get('/api/platform/companies').json()
    assert metadata[0]['answers']==1
    assert not {'messages','citations','visitor','knowledge'} & metadata[0].keys()
