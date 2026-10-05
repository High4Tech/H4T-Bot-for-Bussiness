"""Local database health, lifecycle, private backups and isolated restore checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
import psycopg
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict,make_conninfo

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from server.database import Database
from server.db_security import apply_security
LOCAL=ROOT/'.local';BIN=LOCAL/'postgres-runtime/pgsql/bin'
FLAGS=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0

def pg_tool(command,config,*args,dbname=None):
    params=conninfo_to_dict(config['admin_url'])
    env={**os.environ,'PGHOST':params['host'],'PGPORT':params['port'],'PGUSER':params['user'],'PGPASSWORD':params['password'],'PGDATABASE':dbname or params['dbname']}
    result=subprocess.run([str(BIN/command),*map(str,args)],env=env,creationflags=FLAGS,capture_output=True,text=True,timeout=120)
    if result.returncode: raise RuntimeError(result.stderr)

def backup(config):
    destination=LOCAL/'backups'/f'{int(time.time())}-{secrets.token_hex(4)}'
    destination.mkdir(parents=True)
    pg_tool('pg_dump.exe',config,'-Fc','--no-owner','--no-acl','-f',destination/'database.dump')
    shutil.copytree(LOCAL/'uploads',destination/'uploads',dirs_exist_ok=True)
    manifest={p.relative_to(destination).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.rglob('*') if p.is_file()}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2))
    print('Private database and upload backup created:',destination)
    return destination

def verify_backup(config,destination):
    destination=destination.resolve()
    if not destination.is_relative_to((LOCAL/'backups').resolve()): raise ValueError('Use a backup inside this project local backups directory.')
    manifest=json.loads((destination/'manifest.json').read_text())
    for relative,digest in manifest.items():
        path=(destination/relative).resolve()
        if not path.is_relative_to(destination) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise ValueError('Backup integrity check failed.')
    name='h4t_restore_test_'+secrets.token_hex(8)
    admin=make_conninfo(config['admin_url'],dbname='postgres')
    with psycopg.connect(admin,autocommit=True) as conn: conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    try:
        pg_tool('pg_restore.exe',config,'--exit-on-error','--no-owner','--no-acl','-d',name,destination/'database.dump',dbname=name)
        with psycopg.connect(make_conninfo(config['admin_url'],dbname=name)) as conn:
            apply_security(conn)
            count=conn.execute('SELECT COUNT(*) FROM companies').fetchone()[0]
            files=conn.execute("SELECT file_key,sha256 FROM source_versions WHERE version=1 AND file_key!=''").fetchall()
            for file_key,digest in files:
                path=(destination/'uploads'/file_key).resolve()
                if not path.is_relative_to((destination/'uploads').resolve()) or hashlib.sha256(path.read_bytes()).hexdigest()!=digest: raise ValueError('Restored source file integrity check failed.')
        print(f'Backup restored into an isolated temporary database; {count} company records and {len(files)} source files verified. Running database unchanged.')
    finally:
        assert name.startswith('h4t_restore_test_') and len(name)==33
        with psycopg.connect(admin,autocommit=True) as conn: conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['status','start','stop','backup','verify-backup'])
    parser.add_argument('--backup',type=Path)
    args=parser.parse_args()
    if args.action=='start':
        subprocess.run([sys.executable,str(ROOT/'scripts/setup-database.py')],check=True,creationflags=FLAGS);return
    config=json.loads((LOCAL/'database.json').read_text())
    if args.action=='status':
        print(json.dumps(Database(config=config).health()));return
    if args.action=='stop':
        result=subprocess.run([str(BIN/'pg_ctl.exe'),'stop','-D',str(LOCAL/'pgdata'),'-m','fast','-w'],creationflags=FLAGS,capture_output=True,text=True,timeout=40)
        if result.returncode: raise RuntimeError(result.stderr)
        print('Project-local database stopped.');return
    if args.action=='backup': backup(config);return
    verify_backup(config,args.backup or backup(config))

if __name__=='__main__': main()
