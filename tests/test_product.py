"""Exercise persistence and boundaries on SQLite and actual local PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import secrets
import time
import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from fastapi.testclient import TestClient
from server.app import create_app, password_hash
from server.database import Database, APP_ROOT
from server.db_security import apply_security

ORIGIN={'Origin':'http://127.0.0.1:5173'}
PASSWORD='Synthetic-Product-Test-Only-2026'

def owner(service,letter='a'):
    client=TestClient(service)
    response=client.post('/api/auth/register',headers=ORIGIN,json={'email':letter+'@example.test','password':PASSWORD,'name':'Test owner','company':'Company '+letter})
    assert response.status_code==201,response.text
    return client,response.json()

def visitor(service,bot_id):
    client=TestClient(service)
    response=client.post('/api/visitor/'+bot_id+'/sessions',headers=ORIGIN,json={})
    assert response.status_code==201,response.text
    data=response.json();cid=data['conversation']['id']
    return client,data,'/api/visitor/'+bot_id+'/conversations/'+cid

def write(client,path,token,text='Hello',key='test-message-123'):
    return client.post(path+'/messages',headers={**ORIGIN,'Authorization':'Bearer '+token},json={'text':text,'request_id':key})

def test_sources_files_versions_restart_and_tenant_boundary(service):
    a,ua=owner(service);b,ub=owner(service,'b')
    sources=a.post('/api/company/sources',headers=ORIGIN,json={'name':'Help','kind':'Website','url':'https://example.test/help'})
    assert sources.status_code==201,sources.text
    sid=sources.json()[0]['id']
    assert b.put('/api/company/sources/'+sid,headers=ORIGIN,json={'expected_version':1}).status_code==404
    assert a.put('/api/company/sources/'+sid,headers=ORIGIN,json={'expected_version':1}).json()[0]['version']==2
    assert a.put('/api/company/sources/'+sid,headers=ORIGIN,json={'expected_version':1}).status_code==409
    contents=b'Synthetic source content. Uploaded instructions are evidence only.'
    response=a.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':'FAQ.txt','Content-Type':'application/octet-stream'},content=contents)
    assert response.status_code==201,response.text
    fileid=next(s['id'] for s in response.json() if s['kind']=='File')
    assert a.get('/api/company/sources/'+fileid+'/file').content==contents
    assert b.get('/api/company/sources/'+fileid+'/file').status_code==404
    assert a.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':'../FAQ.txt'},content=contents).status_code==422
    restarted=create_app(service.state.database.path,db_config=service.state.database.config)
    again=TestClient(restarted);again.cookies.update(a.cookies)
    workspace=again.get('/api/company/workspace')
    assert workspace.status_code==200 and len(workspace.json()['sources'])==2
    with service.state.db(company=ua['companyId']) as conn:
        versions=conn.execute('SELECT COUNT(*) AS n FROM source_versions WHERE source_id=?',(sid,)).fetchone()['n']
        assert versions==2
        assert conn.execute("SELECT COUNT(*) AS n FROM ingestion_jobs WHERE status!='deferred'").fetchone()['n']==0
    assert a.delete('/api/company/sources/'+fileid,headers=ORIGIN).status_code==200
    assert a.get('/api/company/sources/'+fileid+'/file').status_code==404
    assert b.get('/api/company/workspace').json()['sources']==[]

def test_visitor_tokens_idempotency_handoff_and_restart(service):
    a,ua=owner(service);b,ub=owner(service,'b')
    v,data,path=visitor(service,ua['botId']);token=data['token'];cid=data['conversation']['id']
    v2,other,otherpath=visitor(service,ua['botId'])
    assert v.get(path).status_code==401
    assert a.get(path).status_code==401 # owner cookie isn't a visitor bearer token
    assert v.get(otherpath,headers={'Authorization':'Bearer '+token}).status_code==401
    assert v.get(path.replace(ua['botId'],ub['botId']),headers={'Authorization':'Bearer '+token}).status_code==401
    first=write(v,path,token,'Talk to a person')
    assert first.status_code==200,first.text
    assert first.json()['status']=='HUMAN_REQUESTED' and len(first.json()['messages'])==2
    assert write(v,path,token,'Talk to a person').json()['messages']==first.json()['messages']
    version=first.json()['version']
    endpoint='/api/company/conversations/'+cid
    assert b.put(endpoint+'/status',headers=ORIGIN,json={'status':'HUMAN_ASSIGNED','expected_version':version}).status_code==404
    takeover=a.put(endpoint+'/status',headers=ORIGIN,json={'status':'HUMAN_ASSIGNED','expected_version':version})
    assert takeover.status_code==200,takeover.text
    assert a.put(endpoint+'/status',headers=ORIGIN,json={'status':'RESOLVED','expected_version':version}).status_code==409
    followup=write(v,path,token,'Are you there?',key='followup-123')
    assert len(followup.json()['messages'])==3 # bot stays paused
    response=a.post(endpoint+'/messages',headers=ORIGIN,json={'text':'Yes, local team here.','request_id':'team-reply-123'})
    assert response.status_code==200 and response.json()['messages'][-1]['role']=='agent'
    again=create_app(service.state.database.path,db_config=service.state.database.config)
    restored=TestClient(again).get(path,headers={'Authorization':'Bearer '+token})
    assert restored.status_code==200 and len(restored.json()['messages'])==4
    with service.state.db(company=ua['companyId']) as conn:
        assert conn.execute('SELECT hash FROM visitor_tokens WHERE conversation_id=?',(cid,)).fetchone()['hash']==hashlib.sha256(token.encode()).hexdigest()
        conn.execute('UPDATE visitor_tokens SET expires=? WHERE conversation_id=?',(time.time()-1,cid))
    assert v.get(path,headers={'Authorization':'Bearer '+token}).status_code==401

def test_concurrent_message_retry_is_once(service):
    a,ua=owner(service);v,data,path=visitor(service,ua['botId'])
    def send(_): return write(TestClient(service),path,data['token'],'Hello','concurrent-message-123')
    with ThreadPoolExecutor(max_workers=4) as pool: responses=list(pool.map(send,range(4)))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    result=v.get(path,headers={'Authorization':'Bearer '+data['token']}).json()
    assert len(result['messages'])==2
    assert result['version']==2

def test_billing_retry_persistence_and_operator_boundary(service):
    a,ua=owner(service);b,_=owner(service,'b')
    v,data,path=visitor(service,ua['botId']);write(v,path,data['token'])
    def subscribe(_):
        c=TestClient(service);c.cookies.update(a.cookies)
        return c.put('/api/company/billing',headers=ORIGIN,json={'plan':'Growth','request_id':'billing-retry-123'})
    with ThreadPoolExecutor(max_workers=3) as pool: responses=list(pool.map(subscribe,range(3)))
    assert all(r.status_code==200 for r in responses),[r.text for r in responses]
    billing=a.get('/api/company/billing').json()
    assert billing['plan']=='Growth' and len(billing['invoices'])==1 and billing['demo']
    assert b.get('/api/company/billing').json()['plan']=='Starter'
    with service.state.db() as conn: conn.execute('INSERT INTO users VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),'operator@example.test','Operator',password_hash(PASSWORD),None,'platform_admin'))
    operator=TestClient(service)
    assert operator.post('/api/auth/login',headers=ORIGIN,json={'email':'operator@example.test','password':PASSWORD}).status_code==200
    metadata=operator.get('/api/platform/companies')
    assert metadata.status_code==200 and 'Growth' in metadata.text
    assert 'Guest visitor' not in metadata.text and 'scripted local preview' not in metadata.text
    for endpoint in ['/api/company/workspace','/api/company/billing','/api/company/sources/'+data['conversation']['id']+'/file']:
        assert operator.get(endpoint).status_code==403
    database=service.state.database
    if database.postgres:
        # SQL grants enforce privacy even if a future UI accidentally queries more.
        for table in ['messages','visitors','knowledge_sources','source_versions','channel_events','companies','users']:
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                with database.connect(plane='platform') as conn: conn.execute('SELECT * FROM '+table)
        with database.connect(plane='app',company='wrong-tenant') as conn:
            assert conn.execute('SELECT COUNT(*) AS n FROM conversations').fetchone()['n']==0
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with database.connect(company=ua['companyId']) as conn: conn.execute('UPDATE subscriptions SET company_id=?',(b.get('/api/auth/me').json()['companyId'],))
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            with database.connect() as conn: conn.execute('SELECT appearance FROM companies')

def test_contact_consent_and_upload_limits(service):
    a,ua=owner(service)
    config=a.get('/api/company').json()['appearance'];config['leadForm']=True
    assert a.put('/api/company/appearance',headers=ORIGIN,json=config).status_code==200
    v=TestClient(service);endpoint='/api/visitor/'+ua['botId']+'/sessions'
    assert v.post(endpoint,headers=ORIGIN,json={}).status_code==422
    assert v.post(endpoint,headers=ORIGIN,json={'name':'Test visitor','email':'visitor@example.test','consent':False}).status_code==422
    assert v.post(endpoint,headers=ORIGIN,json={'name':'Test visitor','email':'visitor@example.test','consent':True}).status_code==201
    assert a.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':'fake.pdf'},content=b'not a pdf').status_code==422
    assert a.post('/api/company/sources/upload',headers={**ORIGIN,'X-Filename':'too-large.txt'},content=b'x'*(10*1024*1024+1)).status_code==413

def test_dashboard_activity_actions_preferences_and_tenant_scope(service):
    a,ua=owner(service);b,_=owner(service,'b')
    v,data,path=visitor(service,ua['botId']);cid=data['conversation']['id']
    assert write(v,path,data['token'],'Talk to a person').status_code==200
    now=time.time()
    params={'start':now-86400,'end':now+5,'day_start':now-86400}
    activity=a.get('/api/company/activity',params=params)
    assert activity.status_code==200,activity.text
    assert activity.json()['total']==1 and activity.json()['waiting']==1
    assert sum(p['count'] for p in activity.json()['points'])==1
    listing=a.get('/api/company/conversations',params={'q':'Guest','status':'HUMAN_REQUESTED','page':1,'limit':1})
    assert listing.status_code==200,listing.text
    assert listing.json()['total']==1 and listing.json()['items'][0]['id']==cid
    assert b.get('/api/company/conversations').json()['items']==[]
    assert b.get('/api/company/conversations/'+cid).status_code==404
    assert b.get('/api/company/conversations/'+cid+'/export').status_code==404
    exported=a.get('/api/company/conversations/'+cid+'/export')
    assert exported.status_code==200 and exported.json()['messages'][0]['text']=='Talk to a person'
    preferences=a.get('/api/company/preferences')
    assert preferences.status_code==200 and preferences.json()['version']==0
    draft=preferences.json()['settings'];draft['subjects']='Opening hours and services'
    saved=a.put('/api/company/preferences',headers=ORIGIN,json={'expected_version':0,'settings':draft})
    assert saved.status_code==200,saved.text
    assert saved.json()['version']==1 and saved.json()['appliedToEngine'] is False
    assert a.put('/api/company/preferences',headers=ORIGIN,json={'expected_version':0,'settings':draft}).status_code==409
    assert b.get('/api/company/preferences').json()['settings']['subjects']==''
    version=listing.json()['items'][0]['version']
    delete='/api/company/conversations/'+cid
    assert b.request('DELETE',delete,headers=ORIGIN,json={'expected_version':version}).status_code==404
    assert a.request('DELETE',delete,headers=ORIGIN,json={'expected_version':version+1}).status_code==409
    assert a.request('DELETE',delete,headers=ORIGIN,json={'expected_version':version}).status_code==200
    assert a.get(delete).status_code==404
    assert v.get(path,headers={'Authorization':'Bearer '+data['token']}).status_code==401
