"""Isolated real-network website → index → visitor-answer smoke test.

Usage: .venv/Scripts/python.exe scripts/smoke-website.py URL QUESTION
Creates only a temporary SQLite database. Does not modify customer data.
"""
import argparse
import json
from pathlib import Path
import secrets
import sys
from tempfile import TemporaryDirectory
import time

from fastapi.testclient import TestClient

sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from server.app import create_app
from server.knowledge import next_job, process_job

ORIGIN={'Origin':'http://127.0.0.1:5173'}

def checked(response):
    if response.status_code >= 400:
        raise RuntimeError(f'HTTP {response.status_code}: {response.text[:300]}')
    return response.json()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url',help='Public HTML page URL')
    parser.add_argument('question',help='Question answerable from that page')
    args=parser.parse_args()
    with TemporaryDirectory(prefix='h4t-website-smoke-') as directory:
        app=create_app(Path(directory)/'smoke.sqlite3')
        owner=TestClient(app)
        account=checked(owner.post('/api/auth/register',headers=ORIGIN,json={
            'email':'smoke-'+secrets.token_hex(6)+'@example.test',
            'password':secrets.token_urlsafe(24),'name':'Smoke tester','company':'Website smoke test',
        }))
        source=checked(owner.post('/api/company/sources',headers=ORIGIN,json={
            'name':'Public website page','kind':'Website','url':args.url,
        }))[0]
        published=checked(owner.put('/api/company/sources/'+source['id'],headers=ORIGIN,
                                    json={'expected_version':source['version']}))
        source=next(item for item in published if item['id']==source['id'])
        start=time.perf_counter()
        job=next_job(app.state.database)
        if not job: raise RuntimeError('No ingestion job was queued')
        job_status=process_job(app.state.database,job)
        index_seconds=round(time.perf_counter()-start,2)
        source=next(item for item in checked(owner.get('/api/company/workspace'))['sources'] if item['id']==source['id'])
        if job_status!='ready': raise RuntimeError(f'Indexing failed: {source["indexError"] or job_status}')
        visitor=TestClient(app)
        session=checked(visitor.post(f'/api/visitor/{account["botId"]}/sessions',headers=ORIGIN,json={
            'name':'Smoke visitor',
        }))
        start=time.perf_counter()
        result=checked(visitor.post(f'/api/visitor/{account["botId"]}/conversations/{session["conversation"]["id"]}/messages',
                                    headers={**ORIGIN,'Authorization':'Bearer '+session['token']},json={
            'text':args.question,'request_id':secrets.token_hex(12),
        }))
        answer_seconds=round(time.perf_counter()-start,2)
        reply=result['messages'][-1]
        print(json.dumps({
            'url':args.url,'indexStatus':source['indexStatus'],'chunks':source['chunks'],
            'indexSeconds':index_seconds,'answerSeconds':answer_seconds,
            'engine':reply['engine'],'answer':reply['text'],
            'citations':[{'title':citation['title'],'url':citation['url']} for citation in reply['citations']],
        },indent=2))

if __name__=='__main__': main()
