"""Durable tenant-scoped product data and local assistant conversation routes."""
import hashlib
import hmac
import json
import re
import secrets
import time
from collections import defaultdict, deque
from urllib.parse import urlparse, unquote, quote
from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from server import ai, knowledge

class SourceInput(BaseModel):
    name: str = Field(min_length=1, max_length=240)
    kind: str = Field(pattern='^Website$')
    url: str = Field(max_length=2000)

class VersionInput(BaseModel):
    expected_version: int = Field(ge=1)

class StatusInput(VersionInput):
    status: str = Field(pattern='^(BOT_ACTIVE|HUMAN_REQUESTED|HUMAN_ASSIGNED|RESOLVED)$')

class MessageInput(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=8, max_length=80, pattern='^[a-zA-Z0-9_-]+$')

class VisitorInput(BaseModel):
    name: str = Field(default='Guest visitor', min_length=1, max_length=80)
    email: str = Field(default='', max_length=150)
    consent: bool = False

class PlanInput(BaseModel):
    plan: str = Field(pattern='^(Starter|Growth|Business)$')
    request_id: str = Field(min_length=8, max_length=80, pattern='^[a-zA-Z0-9_-]+$')

TRANSITIONS = {'BOT_ACTIVE':['HUMAN_REQUESTED','HUMAN_ASSIGNED','RESOLVED'], 'HUMAN_REQUESTED':['HUMAN_ASSIGNED','RESOLVED'], 'HUMAN_ASSIGNED':['BOT_ACTIVE','RESOLVED'], 'RESOLVED':['BOT_ACTIVE']}

def install_product_routes(app, database, company_user):
    attempts = defaultdict(deque)
    def throttle(key, limit, seconds):
        now=time.time(); q=attempts[key]
        while q and q[0]<now-seconds: q.popleft()
        if len(q)>=limit: raise HTTPException(429, 'Too many preview requests. Please try later.')
        q.append(now)
        if len(attempts)>2000:
            for k in list(attempts):
                if not attempts[k] or attempts[k][-1]<now-3600: attempts.pop(k, None)

    def audit(conn, company, action, entity, actor=None):
        conn.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?)', (secrets.token_hex(16),company,actor,action,entity,time.time()))

    def usage(conn, company, kind, key):
        conn.execute('INSERT INTO usage_events VALUES(?,?,?,?,?,?) ON CONFLICT(company_id,kind,dedupe_key) DO NOTHING', (secrets.token_hex(16),company,kind,1,key,time.time()))

    def conversation(conn, company, cid):
        row=conn.execute('SELECT c.*,v.name,v.email FROM conversations c JOIN visitors v ON v.id=c.visitor_id AND v.company_id=c.company_id WHERE c.id=? AND c.company_id=?', (cid,company)).fetchone()
        if not row: raise HTTPException(404,'Conversation not found.')
        messages=conn.execute('SELECT id,role,text,sequence,created,citations,engine FROM messages WHERE company_id=? AND conversation_id=? ORDER BY sequence DESC LIMIT 200',(company,cid)).fetchall()
        items=[{**dict(m),'citations':json.loads(m['citations'])} for m in reversed(messages)]
        return dict(id=row['id'],company=company,name=row['name'],email=row['email'],status=row['status'],version=row['version'],channel=row['channel'],created=row['created'],updated=row['updated'],messages=items)

    def list_sources(conn, company):
        return [dict(r) for r in conn.execute("SELECT k.id,k.name,k.kind,k.status,k.version,k.source_url AS url,k.created,COALESCE(j.status,'deferred') AS \"indexStatus\",COALESCE(j.error,'') AS \"indexError\",(SELECT COUNT(*) FROM knowledge_chunks c WHERE c.company_id=k.company_id AND c.source_id=k.id AND c.version=k.version) AS chunks FROM knowledge_sources k LEFT JOIN ingestion_jobs j ON j.company_id=k.company_id AND j.source_id=k.id AND j.version=k.version WHERE k.company_id=? AND k.deleted_at IS NULL ORDER BY k.created DESC",(company,)).fetchall()]

    from server.dashboard import install_dashboard_routes
    install_dashboard_routes(app,database,company_user,conversation)

    def billing(conn, company):
        sub=conn.execute('SELECT plan FROM subscriptions WHERE company_id=?',(company,)).fetchone()
        invoices=[dict(r) for r in conn.execute('SELECT id,plan,cents,status,created FROM demo_invoices WHERE company_id=? ORDER BY created DESC LIMIT 30',(company,)).fetchall()]
        answers=conn.execute("SELECT COUNT(*) AS count FROM usage_events WHERE company_id=? AND kind='local_ai_answer'",(company,)).fetchone()['count']
        return {'plan':sub['plan'] if sub else 'Starter','invoices':invoices,'demo':True,'aiAnswers':answers}

    def source_version(conn, row):
        previous=conn.execute('SELECT file_key,sha256,bytes FROM source_versions WHERE source_id=? AND company_id=? ORDER BY version DESC LIMIT 1',(row['id'],row['company_id'])).fetchone()
        conn.execute('INSERT INTO source_versions VALUES(?,?,?,?,?,?,?,?)',(row['id'],row['company_id'],row['version'],row['status'],previous['file_key'] if previous else '',previous['sha256'] if previous else '',previous['bytes'] if previous else 0,time.time()))
        conn.execute('INSERT INTO ingestion_jobs(id,company_id,source_id,version,status,created,updated) VALUES(?,?,?,?,?,?,?)',(secrets.token_hex(16),row['company_id'],row['id'],row['version'],'queued' if row['status']=='Demo published' else 'deferred',time.time(),time.time()))

    @app.get('/api/company/workspace')
    def workspace(user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company) as conn:
            appearance=conn.execute('SELECT appearance FROM companies WHERE id=?',(company,)).fetchone()
            ids=conn.execute('SELECT id FROM conversations WHERE company_id=? ORDER BY updated DESC LIMIT 50',(company,)).fetchall()
            return {'appearance':json.loads(appearance['appearance']),'sources':list_sources(conn,company),'conversations':[conversation(conn,company,r['id']) for r in ids],'billing':billing(conn,company),'mode':'local-rag' if (knowledge.MODEL_DIR/'modules.json').exists() else 'knowledge-setup','database':database.health()}

    @app.post('/api/company/sources',status_code=201)
    def create_source(data:SourceInput,user=Depends(company_user)):
        parsed=urlparse(data.url)
        if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username or parsed.password: raise HTTPException(422,'Enter a valid public website URL without credentials.')
        if not data.name.strip(): raise HTTPException(422,'Source name is required.')
        company=user['company_id']; sid=secrets.token_hex(16); now=time.time()
        with database.connect(company=company,write=True) as conn:
            conn.execute(database.locked('SELECT id FROM companies WHERE id=?'),(company,)).fetchone()
            if conn.execute('SELECT COUNT(*) AS count FROM knowledge_sources WHERE company_id=? AND deleted_at IS NULL',(company,)).fetchone()['count']>=100: raise HTTPException(409,'Local source limit reached (100).')
            conn.execute('INSERT INTO knowledge_sources VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,company,data.name.strip(),'Website',data.url,'Draft',1,None,now,now))
            source_version(conn,dict(id=sid,company_id=company,version=1,status='Draft'))
            audit(conn,company,'source.created',sid,user['id'])
            return list_sources(conn,company)

    @app.post('/api/company/sources/upload',status_code=201)
    async def upload_source(request:Request,user=Depends(company_user)):
        name=unquote(request.headers.get('x-filename',''))
        if len(name)>240 or not name or any(c in name for c in ('/','\\','\r','\n','\x00')): raise HTTPException(422,'Invalid filename.')
        extension=name.rsplit('.',1)[-1].lower()
        if extension not in ('txt','csv','pdf','docx'): raise HTTPException(422,'Use TXT, CSV, PDF or DOCX.')
        content=await request.body()
        if not content or len(content)>10*1024*1024: raise HTTPException(413,'Choose a nonempty file under 10 MB.')
        if extension=='pdf' and not content.startswith(b'%PDF'): raise HTTPException(422,'Invalid PDF file.')
        if extension=='docx' and not content.startswith(b'PK'): raise HTTPException(422,'Invalid DOCX file.')
        company=user['company_id']; sid=secrets.token_hex(16); now=time.time(); target=database.upload_root/(sid+'.bin')
        try:
            with database.connect(company=company,write=True) as conn:
                conn.execute(database.locked('SELECT id FROM companies WHERE id=?'),(company,)).fetchone()
                count=conn.execute('SELECT COUNT(*) AS count FROM knowledge_sources WHERE company_id=? AND deleted_at IS NULL',(company,)).fetchone()['count']
                size=conn.execute('SELECT COALESCE(SUM(bytes),0) AS bytes FROM source_versions WHERE company_id=? AND version=1',(company,)).fetchone()['bytes']
                if count>=100 or size+len(content)>100*1024*1024: raise HTTPException(409,'Local storage limit reached (100 sources / 100 MB).')
                target.write_bytes(content)
                conn.execute('INSERT INTO knowledge_sources VALUES(?,?,?,?,?,?,?,?,?,?)',(sid,company,name,'File','','Draft',1,None,now,now))
                conn.execute('INSERT INTO source_versions VALUES(?,?,?,?,?,?,?,?)',(sid,company,1,'Draft',target.name,hashlib.sha256(content).hexdigest(),len(content),now))
                conn.execute('INSERT INTO ingestion_jobs(id,company_id,source_id,version,status,created,updated) VALUES(?,?,?,?,?,?,?)',(secrets.token_hex(16),company,sid,1,'deferred',now,now))
                audit(conn,company,'file.stored',sid,user['id'])
                return list_sources(conn,company)
        except Exception:
            if target.exists(): target.unlink() # only this newly generated file, never a user pathname
            raise

    @app.get('/api/company/sources/{sid}/file')
    def download_source(sid:str,user=Depends(company_user)):
        with database.connect(company=user['company_id']) as conn:
            row=conn.execute("SELECT k.name,s.file_key FROM knowledge_sources k JOIN source_versions s ON s.source_id=k.id AND s.company_id=k.company_id AND s.version=k.version WHERE k.id=? AND k.company_id=? AND k.deleted_at IS NULL AND k.kind='File'",(sid,user['company_id'])).fetchone()
        if not row: raise HTTPException(404,'File not found.')
        path=(database.upload_root/row['file_key']).resolve()
        if not path.is_relative_to(database.upload_root.resolve()) or not path.is_file(): raise HTTPException(404,'File not found.')
        return FileResponse(path,media_type='application/octet-stream',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(row['name'])})

    @app.put('/api/company/sources/{sid}')
    def toggle_source(sid:str,data:VersionInput,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT * FROM knowledge_sources WHERE id=? AND company_id=? AND deleted_at IS NULL'),(sid,company)).fetchone()
            if not row: raise HTTPException(404,'Source not found.')
            if row['version']!=data.expected_version: raise HTTPException(409,'This source changed. Refresh and try again.')
            status='Draft' if row['status']=='Demo published' else 'Demo published'; version=row['version']+1
            conn.execute('UPDATE knowledge_sources SET status=?,version=?,updated=? WHERE id=? AND company_id=?',(status,version,time.time(),sid,company))
            source_version(conn,dict(id=sid,company_id=company,version=version,status=status))
            audit(conn,company,'source.publication_changed',sid,user['id'])
            return list_sources(conn,company)

    @app.post('/api/company/sources/{sid}/process')
    def process_source(sid:str,data:VersionInput,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            source=conn.execute(database.locked('SELECT version,status FROM knowledge_sources WHERE id=? AND company_id=? AND deleted_at IS NULL'),(sid,company)).fetchone()
            if not source: raise HTTPException(404,'Source not found.')
            if source['version']!=data.expected_version: raise HTTPException(409,'This source changed. Refresh and try again.')
            if source['status']!='Demo published': raise HTTPException(409,'Publish this source before processing it.')
            conn.execute("UPDATE ingestion_jobs SET status='queued',error='',updated=? WHERE source_id=? AND company_id=? AND version=? AND status IN ('deferred','failed','ready','obsolete')",(time.time(),sid,company,source['version']))
            return list_sources(conn,company)

    @app.delete('/api/company/sources/{sid}')
    def remove_source(sid:str,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            result=conn.execute('UPDATE knowledge_sources SET deleted_at=?,updated=? WHERE id=? AND company_id=? AND deleted_at IS NULL',(time.time(),time.time(),sid,company))
            if result.rowcount!=1: raise HTTPException(404,'Source not found.')
            audit(conn,company,'source.archived',sid,user['id'])
            return list_sources(conn,company)

    def identity(request,bot_id,cid):
        token=request.headers.get('authorization','')
        if not token.startswith('Bearer ') or len(token)>200: raise HTTPException(401,'Visitor session is required.')
        with database.connect() as conn:
            row=conn.execute('SELECT t.* FROM visitor_tokens t JOIN companies c ON c.id=t.company_id WHERE t.hash=? AND t.conversation_id=? AND c.bot_id=? AND t.expires>?',(hashlib.sha256(token[7:].encode()).hexdigest(),cid,bot_id,time.time())).fetchone()
        if not row: raise HTTPException(401,'Visitor session has expired or is not authorized.')
        return dict(row)

    @app.post('/api/visitor/{bot_id}/sessions',status_code=201)
    def visitor_session(bot_id:str,data:VisitorInput,request:Request):
        throttle(('sessions',request.client.host if request.client else 'local'),30,3600)
        with database.connect() as conn:
            row=conn.execute('SELECT c.id,p.appearance FROM companies c JOIN public_assistant_appearance p ON p.bot_id=c.bot_id WHERE c.bot_id=?',(bot_id,)).fetchone()
        if not row: raise HTTPException(404,'Assistant not found.')
        appearance=json.loads(row['appearance'])
        if data.email and (not data.consent or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data.email)): raise HTTPException(422,'A valid email and contact consent are required.')
        if appearance['leadForm'] and (not data.email or not data.consent or not data.name.strip()): raise HTTPException(422,'Complete the introduction and consent first.')
        company=row['id']; vid=secrets.token_hex(16); cid=secrets.token_hex(16); token=secrets.token_urlsafe(32); now=time.time()
        with database.connect(company=company,write=True) as conn:
            conn.execute(database.locked('SELECT id FROM companies WHERE id=?'),(company,)).fetchone()
            if conn.execute('SELECT COUNT(*) AS count FROM conversations WHERE company_id=? AND created>?',(company,now-86400)).fetchone()['count']>=500: raise HTTPException(429,'Local preview conversation limit reached.')
            conn.execute('INSERT INTO visitors VALUES(?,?,?,?,?,?)',(vid,company,data.name.strip() or 'Guest visitor',data.email.lower(),int(data.consent),now))
            conn.execute('INSERT INTO conversations VALUES(?,?,?,?,?,?,?,?,?)',(cid,company,vid,'web','BOT_ACTIVE',None,1,now,now))
            conn.execute('INSERT INTO visitor_tokens VALUES(?,?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),company,cid,vid,now+8*3600))
            audit(conn,company,'conversation.created',cid)
            return {'token':token,'conversation':conversation(conn,company,cid),'expires':now+8*3600}

    @app.get('/api/visitor/{bot_id}/conversations/{cid}')
    def visitor_conversation(bot_id:str,cid:str,request:Request):
        visitor=identity(request,bot_id,cid)
        with database.connect(company=visitor['company_id'],write=True) as conn:
            recover_stale_turn(conn,visitor['company_id'],cid)
            return conversation(conn,visitor['company_id'],cid)

    def append_message(conn,company,cid,role,text,citations=None,engine='local-rule'):
        sequence=conn.execute('SELECT COALESCE(MAX(sequence),0)+1 AS next FROM messages WHERE company_id=? AND conversation_id=?',(company,cid)).fetchone()['next']
        if sequence>1000: raise HTTPException(409,'Local conversation message limit reached.')
        mid=secrets.token_hex(16)
        conn.execute('INSERT INTO messages(id,company_id,conversation_id,role,text,sequence,created,citations,engine) VALUES(?,?,?,?,?,?,?,?,?)',(mid,company,cid,role,text,sequence,time.time(),json.dumps(citations or []),engine))
        usage(conn,company,'local_ai_answer' if role=='bot' and engine.startswith('ollama:') else ('scripted_message' if role=='bot' else role+'_message'),mid)

    def recover_stale_turn(conn,company,cid):
        pending=conn.execute("SELECT request_id,created FROM ai_turns WHERE company_id=? AND conversation_id=? AND status='pending'",(company,cid)).fetchone()
        if pending and pending['created'] < time.time()-150:
            row=conn.execute(database.locked('SELECT status FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            if row and row['status']=='BOT_ACTIVE':
                append_message(conn,company,cid,'bot',ai.UNAVAILABLE,engine='unavailable')
                conn.execute('UPDATE conversations SET version=version+1,updated=? WHERE id=? AND company_id=?',(time.time(),cid,company))
            conn.execute("UPDATE ai_turns SET status='failed' WHERE company_id=? AND conversation_id=? AND request_id=?",(company,cid,pending['request_id']))

    @app.post('/api/visitor/{bot_id}/conversations/{cid}/messages')
    def visitor_message(bot_id:str,cid:str,data:MessageInput,request:Request):
        visitor=identity(request,bot_id,cid); company=visitor['company_id']; throttle(('messages',visitor['hash']),30,60)
        if not data.text.strip(): raise HTTPException(422,'Message is empty.')
        needs_ai=False; previous=''; question=data.text.strip()
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT * FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            recover_stale_turn(conn,company,cid)
            if conn.execute('SELECT 1 FROM message_requests WHERE conversation_id=? AND company_id=? AND request_id=?',(cid,company,data.request_id)).fetchone(): return conversation(conn,company,cid)
            if row['status']=='RESOLVED': raise HTTPException(409,'This conversation is resolved. Start a new conversation.')
            if row['status']=='BOT_ACTIVE' and conn.execute("SELECT 1 FROM ai_turns WHERE company_id=? AND conversation_id=? AND status='pending'",(company,cid)).fetchone():
                raise HTTPException(409,'The assistant is still answering. Please wait a moment.')
            prior=conn.execute("SELECT text FROM messages WHERE company_id=? AND conversation_id=? AND role='visitor' ORDER BY sequence DESC LIMIT 1",(company,cid)).fetchone()
            previous=prior['text'] if prior else ''
            append_message(conn,company,cid,'visitor',question)
            status=row['status']
            if status=='BOT_ACTIVE':
                if re.search(r'\b(person|human|agent|handoff|representative)\b',question,re.I):
                    append_message(conn,company,cid,'bot','I have saved your request for a person. The assistant is paused while your team takes over.')
                    status='HUMAN_REQUESTED'
                elif re.fullmatch(r'(hi|hello|hey|thanks|thank you)[! .]*',question,re.I):
                    append_message(conn,company,cid,'bot','Hello! Ask me about this business, or choose “Talk to a person” if you need the team.')
                else:
                    conn.execute('INSERT INTO ai_turns VALUES(?,?,?,?,?)',(company,cid,data.request_id,'pending',time.time()))
                    needs_ai=True
            conn.execute('UPDATE conversations SET status=?,version=version+1,updated=? WHERE id=? AND company_id=?',(status,time.time(),cid,company))
            conn.execute('INSERT INTO message_requests VALUES(?,?,?,?)',(company,cid,data.request_id,time.time()))
            if not needs_ai: return conversation(conn,company,cid)
        try:
            evidence=knowledge.search(database,company,question,previous)
            with database.connect(company=company) as conn:
                business=conn.execute('SELECT name FROM companies WHERE id=?',(company,)).fetchone()['name']
            result=ai.answer(question,evidence,business,previous)
        except Exception:
            result={'text':ai.UNAVAILABLE,'citations':[],'engine':'unavailable','latency':0}
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT status FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            turn=conn.execute("SELECT status FROM ai_turns WHERE company_id=? AND conversation_id=? AND request_id=?",(company,cid,data.request_id)).fetchone()
            if turn and turn['status']=='pending':
                if row and row['status']=='BOT_ACTIVE':
                    append_message(conn,company,cid,'bot',result['text'],result['citations'],result['engine'])
                    conn.execute('UPDATE conversations SET version=version+1,updated=? WHERE id=? AND company_id=?',(time.time(),cid,company))
                conn.execute("UPDATE ai_turns SET status=? WHERE company_id=? AND conversation_id=? AND request_id=?",('failed' if result['engine']=='unavailable' else 'complete',company,cid,data.request_id))
            return conversation(conn,company,cid)

    @app.put('/api/company/conversations/{cid}/status')
    def update_status(cid:str,data:StatusInput,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT * FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            if not row: raise HTTPException(404,'Conversation not found.')
            if row['version']!=data.expected_version: raise HTTPException(409,'Conversation changed. Refresh and try again.')
            if data.status not in TRANSITIONS[row['status']]: raise HTTPException(409,'This handoff transition is not allowed.')
            conn.execute('UPDATE conversations SET status=?,assigned_to=?,version=version+1,updated=? WHERE id=? AND company_id=?',(data.status,user['id'] if data.status=='HUMAN_ASSIGNED' else None,time.time(),cid,company))
            audit(conn,company,'conversation.'+data.status.lower(),cid,user['id'])
            return conversation(conn,company,cid)

    @app.post('/api/company/conversations/{cid}/messages')
    def team_message(cid:str,data:MessageInput,user=Depends(company_user)):
        company=user['company_id']
        if not data.text.strip(): raise HTTPException(422,'Message is empty.')
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT * FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            if not row: raise HTTPException(404,'Conversation not found.')
            if conn.execute('SELECT 1 FROM message_requests WHERE conversation_id=? AND company_id=? AND request_id=?',(cid,company,data.request_id)).fetchone(): return conversation(conn,company,cid)
            if row['status']!='HUMAN_ASSIGNED' or row['assigned_to']!=user['id']: raise HTTPException(409,'Take over this conversation before replying.')
            append_message(conn,company,cid,'agent',data.text.strip())
            conn.execute('UPDATE conversations SET version=version+1,updated=? WHERE id=? AND company_id=?',(time.time(),cid,company))
            conn.execute('INSERT INTO message_requests VALUES(?,?,?,?)',(company,cid,data.request_id,time.time()))
            return conversation(conn,company,cid)

    @app.get('/api/company/billing')
    def read_billing(user=Depends(company_user)):
        with database.connect(company=user['company_id']) as conn: return billing(conn,user['company_id'])

    @app.put('/api/company/billing')
    def update_billing(data:PlanInput,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            conn.execute(database.locked('SELECT company_id FROM subscriptions WHERE company_id=?'),(company,)).fetchone()
            existing=conn.execute('SELECT 1 FROM demo_invoices WHERE company_id=? AND request_id=?',(company,data.request_id)).fetchone()
            if not existing:
                conn.execute('INSERT INTO subscriptions VALUES(?,?,?) ON CONFLICT(company_id) DO UPDATE SET plan=excluded.plan,updated=excluded.updated',(company,data.plan,time.time()))
                invoice=secrets.token_hex(16)
                conn.execute('INSERT INTO demo_invoices VALUES(?,?,?,?,?,?,?)',(invoice,company,data.plan,{'Starter':1900,'Growth':4900,'Business':14900}[data.plan],'Demo — no payment',data.request_id,time.time()))
                audit(conn,company,'subscription.demo_changed',invoice,user['id'])
            return billing(conn,company)
