"""Create a project-local PostgreSQL cluster, migrate SQLite, and restrict runtime roles."""
import json
import os
from pathlib import Path
import secrets
import sqlite3
import subprocess
import sys
import time
import tempfile
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from server.database import Database
from server.db_security import apply_security

LOCAL=ROOT/'.local'
BIN=LOCAL/'postgres-runtime/pgsql/bin'
DATA=LOCAL/'pgdata'
CONFIG=LOCAL/'database.json'
BOOTSTRAP=LOCAL/'pg-bootstrap.json'
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def run(*arguments):
    # Windows database children can inherit pipe handles; file-backed output avoids
    # waiting for EOF from a server that should keep running after pg_ctl exits.
    with tempfile.TemporaryFile() as output:
        result=subprocess.run([str(BIN/arguments[0]),*map(str,arguments[1:])],cwd=ROOT,creationflags=FLAGS,stdout=output,stderr=output,timeout=120)
        output.seek(0); message=output.read().decode('utf-8',errors='replace')
    if result.returncode: raise RuntimeError(message)
    return message.strip()

def main():
    LOCAL.mkdir(exist_ok=True)
    if not (BIN/'initdb.exe').exists(): raise SystemExit('Run scripts/download-postgres.py first.')
    bootstrap=json.loads(BOOTSTRAP.read_text()) if BOOTSTRAP.exists() else {'password':secrets.token_urlsafe(32),'port':55432}
    if not BOOTSTRAP.exists(): BOOTSTRAP.write_text(json.dumps(bootstrap))
    if not (DATA/'PG_VERSION').exists():
        pwfile=LOCAL/'init-password.tmp'
        try:
            pwfile.write_text(bootstrap['password'])
            run('initdb.exe','-D',DATA,'-U','h4t_bootstrap','--pwfile',pwfile,'--auth-host=scram-sha-256','--auth-local=scram-sha-256','--encoding=UTF8')
        finally: pwfile.unlink(missing_ok=True)
    status=subprocess.run([str(BIN/'pg_ctl.exe'),'status','-D',str(DATA)],creationflags=FLAGS,capture_output=True)
    if status.returncode:
        run('pg_ctl.exe','start','-D',DATA,'-l',LOCAL/'postgres.log','-o',f"-h 127.0.0.1 -p {bootstrap['port']}",'-w','-t','30')
    admin=make_conninfo(host='127.0.0.1',port=bootstrap['port'],dbname='postgres',user='h4t_bootstrap',password=bootstrap['password'])
    config=json.loads(CONFIG.read_text()) if CONFIG.exists() else {'engine':'postgresql'}
    with psycopg.connect(admin,autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname='h4t_bot'").fetchone(): conn.execute('CREATE DATABASE h4t_bot')
        for plane in ['auth','app','ingest','platform','worker']:
            role='h4t_'+plane
            if plane+'_url' not in config:
                password=secrets.token_urlsafe(32)
                if conn.execute('SELECT 1 FROM pg_roles WHERE rolname=%s',(role,)).fetchone():
                    raise RuntimeError('An existing database role needs its original local config; refusing to reset credentials.')
                conn.execute(sql.SQL('CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS').format(sql.Identifier(role),sql.Literal(password)))
                config[plane+'_url']=make_conninfo(host='127.0.0.1',port=bootstrap['port'],dbname='h4t_bot',user=role,password=password)
        config['admin_url']=make_conninfo(admin,dbname='h4t_bot')
    database=Database(config=config)
    database.migrate()
    old=LOCAL/'h4t.sqlite3'
    imported=0
    if old.exists() and not config.get('sqliteMigrated'):
        backup=LOCAL/f'sqlite-before-postgres-{int(time.time())}.sqlite3'
        with sqlite3.connect(old) as source, sqlite3.connect(backup) as target: source.backup(target)
        with sqlite3.connect(backup) as source, psycopg.connect(config['admin_url']) as target:
            # Ordered to satisfy foreign keys. No data is copied outside this PC.
            tables=['companies','users','sessions','channels','channel_events','workspace_preferences','knowledge_sources','source_versions','ingestion_jobs','knowledge_chunks','visitors','conversations','visitor_tokens','messages','message_requests','ai_turns','subscriptions','demo_invoices','usage_events','audit_events']
            for table in tables:
                if not source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone(): continue
                rows=source.execute('SELECT * FROM '+table).fetchall()
                for row in rows:
                    cursor=target.execute(sql.SQL('INSERT INTO {} VALUES({}) ON CONFLICT DO NOTHING').format(sql.Identifier(table),sql.SQL(',').join(sql.Placeholder() for _ in row)),row)
                    imported+=cursor.rowcount
        config['sqliteMigrated']=True
        database.migrate() # seed subscriptions for imported owners
    with psycopg.connect(config['admin_url']) as conn:
        apply_security(conn)
    temporary=CONFIG.with_suffix('.tmp')
    temporary.write_text(json.dumps(config,indent=2)); temporary.replace(CONFIG)
    print(f'PostgreSQL running on 127.0.0.1:{bootstrap["port"]}; database h4t_bot; schema v4; imported {imported} rows. Customer RLS and operator metadata grants applied.')

if __name__=='__main__': main()
