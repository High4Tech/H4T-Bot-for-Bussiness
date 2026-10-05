from pathlib import Path
import json
import secrets
import pytest
import psycopg
from psycopg import sql
from psycopg.conninfo import make_conninfo
from server.app import create_app
from server.database import Database, APP_ROOT
from server.db_security import apply_security

@pytest.fixture(params=['sqlite','postgresql'])
def service(request,tmp_path):
    if request.param=='sqlite':
        yield create_app(tmp_path/'test.sqlite3');return
    path=APP_ROOT/'.local/database.json'
    if not path.exists(): pytest.skip('Local PostgreSQL configuration is absent')
    original=json.loads(path.read_text())
    name='h4t_test_'+secrets.token_hex(8)
    admin=make_conninfo(original['admin_url'],dbname='postgres')
    with psycopg.connect(admin,autocommit=True) as conn: conn.execute(sql.SQL('CREATE DATABASE {}').format(sql.Identifier(name)))
    config={**original,**{key:make_conninfo(value,dbname=name) for key,value in original.items() if key.endswith('_url')}}
    try:
        database=Database(tmp_path/'test.sqlite3',config=config);database.migrate()
        with psycopg.connect(config['admin_url']) as conn: apply_security(conn)
        yield create_app(tmp_path/'test.sqlite3',db_config=config)
    finally:
        assert name.startswith('h4t_test_') and len(name)==25
        with psycopg.connect(admin,autocommit=True) as conn: conn.execute(sql.SQL('DROP DATABASE {} WITH (FORCE)').format(sql.Identifier(name)))
