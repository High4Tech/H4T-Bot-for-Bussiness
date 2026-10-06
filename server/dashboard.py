"""Owner-only dashboard queries and saved configuration drafts. No inference."""
import json
import secrets
import time
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

class Hours(BaseModel):
    enabled: bool = True
    start: str = Field(default='09:00', pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    end: str = Field(default='17:00', pattern=r'^([01]\d|2[0-3]):[0-5]\d$')

class TeamDraft(BaseModel):
    id: str = Field(min_length=1,max_length=80)
    name: str = Field(min_length=1,max_length=80)
    email: str = Field(max_length=150,pattern=r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
    role: Literal['Admin','Editor','Agent'] = 'Agent'

class Preferences(BaseModel):
    subjects: str = Field(default='',max_length=500)
    description: str = Field(default='',max_length=2000)
    hours: list[Hours] = Field(default_factory=lambda:[Hours(enabled=i<5) for i in range(7)],min_length=7,max_length=7)
    timezone: str = Field(default='Asia/Karachi',max_length=80)
    outsideMessage: str = Field(default='Our team will reply during business hours.',max_length=500)
    language: Literal['English','Urdu','Arabic'] = 'English'
    fallbackLanguage: Literal['English','Urdu','Arabic'] = 'English'
    autoLanguage: bool = False
    tone: Literal['Professional','Friendly','Concise'] = 'Professional'
    responseLength: Literal['Short','Medium','Detailed'] = 'Medium'
    typing: bool = True
    avatar: bool = True
    handoff: bool = True
    team: list[TeamDraft] = Field(default_factory=list,max_length=10)

class SavePreferences(BaseModel):
    expected_version: int = Field(ge=0)
    settings: Preferences

class DeleteConversation(BaseModel):
    expected_version: int = Field(ge=1)

def install_dashboard_routes(app, database, company_user, conversation):
    @app.get('/api/company/preferences')
    def preferences(user=Depends(company_user)):
        with database.connect(company=user['company_id']) as conn:
            row=conn.execute('SELECT settings,version FROM workspace_preferences WHERE company_id=?',(user['company_id'],)).fetchone()
        return {'settings':json.loads(row['settings']) if row else Preferences().model_dump(),'version':row['version'] if row else 0,'appliedToEngine':False}

    @app.put('/api/company/preferences')
    def save_preferences(data:SavePreferences,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            conn.execute(database.locked('SELECT id FROM companies WHERE id=?'),(company,)).fetchone()
            row=conn.execute('SELECT version FROM workspace_preferences WHERE company_id=?',(company,)).fetchone()
            version=row['version'] if row else 0
            if data.expected_version!=version: raise HTTPException(409,'Settings changed. Reload before saving.')
            value=data.settings.model_dump()
            conn.execute('INSERT INTO workspace_preferences VALUES(?,?,?,?) ON CONFLICT(company_id) DO UPDATE SET settings=excluded.settings,version=excluded.version,updated=excluded.updated',(company,json.dumps(value),version+1,time.time()))
        return {'settings':value,'version':version+1,'appliedToEngine':False}

    @app.get('/api/company/activity')
    def activity(start:float=Query(ge=0),end:float=Query(ge=0),day_start:float=Query(ge=0),status:str='',user=Depends(company_user)):
        if end<=start or end-start>367*86400: raise HTTPException(422,'Choose a period of up to 366 days.')
        if status and status not in ['BOT_ACTIVE','HUMAN_REQUESTED','HUMAN_ASSIGNED','RESOLVED']: raise HTTPException(422,'Invalid status.')
        company=user['company_id']
        with database.connect(company=company) as conn:
            totals=conn.execute("SELECT COUNT(*) AS total,SUM(CASE WHEN created>=? AND created<? THEN 1 ELSE 0 END) AS today,SUM(CASE WHEN status='HUMAN_REQUESTED' THEN 1 ELSE 0 END) AS waiting FROM conversations WHERE company_id=?",(day_start,day_start+86400,company)).fetchone()
            query='SELECT FLOOR(created/3600)*3600 AS timestamp,COUNT(*) AS count FROM conversations WHERE company_id=? AND created>=? AND created<?'
            values=[company,start,end]
            if status: query+=' AND status=?';values.append(status)
            points=conn.execute(query+' GROUP BY FLOOR(created/3600) ORDER BY timestamp',values).fetchall()
        return {'total':totals['total'],'today':totals['today'] or 0,'waiting':totals['waiting'] or 0,'points':[dict(p) for p in points]}

    @app.get('/api/company/conversations')
    def conversations(q:str=Query(default='',max_length=150),status:str='',since:float=0,page:int=Query(default=1,ge=1),limit:int=Query(default=7,ge=1,le=50),sort:Literal['updated','name','status']='updated',direction:Literal['asc','desc']='desc',user=Depends(company_user)):
        company=user['company_id'];where='c.company_id=? AND c.created>=?';params=[company,since]
        if status: where+=' AND c.status=?';params.append(status)
        if q: where+=' AND (LOWER(v.name) LIKE ? OR LOWER(v.email) LIKE ?)';params.extend(['%'+q.lower()+'%']*2)
        base=' FROM conversations c JOIN visitors v ON v.id=c.visitor_id AND v.company_id=c.company_id WHERE '+where
        with database.connect(company=company) as conn:
            total=conn.execute('SELECT COUNT(*) AS count'+base,params).fetchone()['count']
            column={'updated':'c.updated','name':'v.name','status':'c.status'}[sort]
            rows=conn.execute("SELECT c.id,c.status,c.version,c.channel,c.created,c.updated,v.name,v.email,(SELECT text FROM messages m WHERE m.company_id=c.company_id AND m.conversation_id=c.id ORDER BY sequence DESC LIMIT 1) AS latest"+base+' ORDER BY '+column+' '+direction+',c.id LIMIT ? OFFSET ?',params+[limit,(page-1)*limit]).fetchall()
        return {'items':[dict(r) for r in rows],'total':total,'page':page,'limit':limit}

    @app.get('/api/company/conversations/{cid}')
    def detail(cid:str,user=Depends(company_user)):
        with database.connect(company=user['company_id']) as conn: return conversation(conn,user['company_id'],cid)

    @app.get('/api/company/conversations/{cid}/export')
    def export(cid:str,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company) as conn:
            value=conversation(conn,company,cid)
            value['messages']=[dict(r) for r in conn.execute('SELECT role,text,sequence,created FROM messages WHERE conversation_id=? AND company_id=? ORDER BY sequence',(cid,company)).fetchall()]
        return value

    @app.delete('/api/company/conversations/{cid}')
    def delete(cid:str,data:DeleteConversation,user=Depends(company_user)):
        company=user['company_id']
        with database.connect(company=company,write=True) as conn:
            row=conn.execute(database.locked('SELECT visitor_id,version FROM conversations WHERE id=? AND company_id=?'),(cid,company)).fetchone()
            if not row: raise HTTPException(404,'Conversation not found.')
            if row['version']!=data.expected_version: raise HTTPException(409,'Conversation changed. Refresh before deleting.')
            for table in ['ai_turns','message_requests','visitor_tokens','messages']:
                conn.execute('DELETE FROM '+table+' WHERE company_id=? AND conversation_id=?',(company,cid))
            conn.execute('DELETE FROM conversations WHERE company_id=? AND id=?',(company,cid))
            remaining=conn.execute('SELECT COUNT(*) AS n FROM conversations WHERE company_id=? AND visitor_id=?',(company,row['visitor_id'])).fetchone()['n']
            if not remaining: conn.execute('DELETE FROM visitors WHERE company_id=? AND id=?',(company,row['visitor_id']))
            conn.execute('INSERT INTO audit_events VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),company,user['id'],'conversation.deleted',cid,time.time()))
        return {'deleted':True}
