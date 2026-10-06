"""Local DB adapter, versioned schema, tenant scopes and metadata-only control plane."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import time
import psycopg
from psycopg.rows import dict_row

APP_ROOT = Path(__file__).resolve().parent.parent
INTEGRITY_ERRORS = (sqlite3.IntegrityError, psycopg.IntegrityError)

BASE_SCHEMA = """
CREATE TABLE IF NOT EXISTS companies(id TEXT PRIMARY KEY, name TEXT NOT NULL, bot_id TEXT UNIQUE NOT NULL, appearance TEXT NOT NULL, created DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, name TEXT NOT NULL, password_hash TEXT NOT NULL, company_id TEXT REFERENCES companies(id), role TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions(hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id), expires DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS channels(company_id TEXT NOT NULL REFERENCES companies(id), channel TEXT NOT NULL, enabled INTEGER NOT NULL, provider_id TEXT NOT NULL, PRIMARY KEY(company_id,channel));
CREATE UNIQUE INDEX IF NOT EXISTS unique_channel_provider ON channels(channel,provider_id) WHERE provider_id != '';
CREATE TABLE IF NOT EXISTS channel_events(id TEXT PRIMARY KEY, company_id TEXT NOT NULL REFERENCES companies(id), channel TEXT NOT NULL, payload TEXT NOT NULL, created DOUBLE PRECISION NOT NULL);
"""
PRODUCT_SCHEMA = """
CREATE TABLE IF NOT EXISTS workspace_preferences(company_id TEXT PRIMARY KEY REFERENCES companies(id),settings TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,updated DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS knowledge_sources(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),name TEXT NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('Website','File')),
 source_url TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'Draft' CHECK(status IN ('Draft','Demo published')),version INTEGER NOT NULL DEFAULT 1 CHECK(version>0),
 deleted_at DOUBLE PRECISION,created DOUBLE PRECISION NOT NULL,updated DOUBLE PRECISION NOT NULL,UNIQUE(id,company_id));
CREATE TABLE IF NOT EXISTS source_versions(
 source_id TEXT NOT NULL,company_id TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL,file_key TEXT NOT NULL DEFAULT '',sha256 TEXT NOT NULL DEFAULT '',bytes INTEGER NOT NULL DEFAULT 0,
 created DOUBLE PRECISION NOT NULL,PRIMARY KEY(source_id,version),FOREIGN KEY(source_id,company_id) REFERENCES knowledge_sources(id,company_id),UNIQUE(source_id,company_id,version));
CREATE TABLE IF NOT EXISTS ingestion_jobs(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL,source_id TEXT NOT NULL,version INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'deferred',created DOUBLE PRECISION NOT NULL,
 updated DOUBLE PRECISION NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',attempts INTEGER NOT NULL DEFAULT 0,
 FOREIGN KEY(source_id,company_id,version) REFERENCES source_versions(source_id,company_id,version),UNIQUE(source_id,version));
CREATE TABLE IF NOT EXISTS knowledge_chunks(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL,source_id TEXT NOT NULL,version INTEGER NOT NULL,ordinal INTEGER NOT NULL,
 content TEXT NOT NULL,embedding TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,
 FOREIGN KEY(source_id,company_id,version) REFERENCES source_versions(source_id,company_id,version),UNIQUE(source_id,version,ordinal));
CREATE TABLE IF NOT EXISTS visitors(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),name TEXT NOT NULL,email TEXT NOT NULL DEFAULT '',consent INTEGER NOT NULL DEFAULT 0,
 created DOUBLE PRECISION NOT NULL,UNIQUE(id,company_id));
CREATE TABLE IF NOT EXISTS conversations(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),visitor_id TEXT NOT NULL,channel TEXT NOT NULL DEFAULT 'web',
 status TEXT NOT NULL DEFAULT 'BOT_ACTIVE' CHECK(status IN ('BOT_ACTIVE','HUMAN_REQUESTED','HUMAN_ASSIGNED','RESOLVED')),assigned_to TEXT REFERENCES users(id),
 version INTEGER NOT NULL DEFAULT 1,created DOUBLE PRECISION NOT NULL,updated DOUBLE PRECISION NOT NULL,
 FOREIGN KEY(visitor_id,company_id) REFERENCES visitors(id,company_id),UNIQUE(id,company_id));
CREATE TABLE IF NOT EXISTS visitor_tokens(
 hash TEXT PRIMARY KEY,company_id TEXT NOT NULL,conversation_id TEXT NOT NULL,visitor_id TEXT NOT NULL,expires DOUBLE PRECISION NOT NULL,
 FOREIGN KEY(conversation_id,company_id) REFERENCES conversations(id,company_id),FOREIGN KEY(visitor_id,company_id) REFERENCES visitors(id,company_id));
CREATE TABLE IF NOT EXISTS messages(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL,conversation_id TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('visitor','bot','agent')),text TEXT NOT NULL,
 sequence INTEGER NOT NULL,created DOUBLE PRECISION NOT NULL,FOREIGN KEY(conversation_id,company_id) REFERENCES conversations(id,company_id),UNIQUE(conversation_id,sequence));
CREATE TABLE IF NOT EXISTS message_requests(
 company_id TEXT NOT NULL,conversation_id TEXT NOT NULL,request_id TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,
 PRIMARY KEY(conversation_id,request_id),FOREIGN KEY(conversation_id,company_id) REFERENCES conversations(id,company_id));
CREATE TABLE IF NOT EXISTS ai_turns(
 company_id TEXT NOT NULL,conversation_id TEXT NOT NULL,request_id TEXT NOT NULL,status TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,
 PRIMARY KEY(conversation_id,request_id),FOREIGN KEY(conversation_id,company_id) REFERENCES conversations(id,company_id));
CREATE TABLE IF NOT EXISTS subscriptions(
 company_id TEXT PRIMARY KEY REFERENCES companies(id),plan TEXT NOT NULL DEFAULT 'Starter' CHECK(plan IN ('Starter','Growth','Business')),updated DOUBLE PRECISION NOT NULL);
CREATE TABLE IF NOT EXISTS demo_invoices(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),plan TEXT NOT NULL,cents INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'Demo — no payment',
 request_id TEXT NOT NULL,created DOUBLE PRECISION NOT NULL,UNIQUE(company_id,request_id));
CREATE TABLE IF NOT EXISTS usage_events(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),kind TEXT NOT NULL,value INTEGER NOT NULL DEFAULT 1,dedupe_key TEXT NOT NULL,
 created DOUBLE PRECISION NOT NULL,UNIQUE(company_id,kind,dedupe_key));
CREATE TABLE IF NOT EXISTS audit_events(
 id TEXT PRIMARY KEY,company_id TEXT NOT NULL REFERENCES companies(id),actor_id TEXT,action TEXT NOT NULL,entity_id TEXT NOT NULL,created DOUBLE PRECISION NOT NULL);
CREATE INDEX IF NOT EXISTS sources_company ON knowledge_sources(company_id,deleted_at);
CREATE INDEX IF NOT EXISTS conversations_company_updated ON conversations(company_id,updated);
CREATE INDEX IF NOT EXISTS messages_conversation ON messages(company_id,conversation_id,sequence);
CREATE INDEX IF NOT EXISTS chunks_tenant_source ON knowledge_chunks(company_id,source_id,version);
CREATE INDEX IF NOT EXISTS jobs_pending ON ingestion_jobs(status,created);
CREATE INDEX IF NOT EXISTS visitor_token_expiry ON visitor_tokens(expires);
CREATE INDEX IF NOT EXISTS sessions_expiry ON sessions(expires);
CREATE INDEX IF NOT EXISTS usage_company_created ON usage_events(company_id,created);
CREATE VIEW IF NOT EXISTS platform_company_metadata AS
 SELECT c.id,c.name,c.bot_id,c.created,COALESCE(s.plan,'Starter') AS plan,1 AS bots,CAST((SELECT COUNT(*) FROM usage_events u WHERE u.company_id=c.id AND u.kind='local_ai_answer') AS INTEGER) AS answers,
 (SELECT COUNT(*) FROM conversations v WHERE v.company_id=c.id) AS conversations,
 (SELECT COUNT(*) FROM messages m WHERE m.company_id=c.id) AS messages,
 (SELECT COALESCE(SUM(bytes),0) FROM source_versions sv WHERE sv.company_id=c.id AND sv.version=1) AS storage_bytes
 FROM companies c LEFT JOIN subscriptions s ON s.company_id=c.id;
CREATE VIEW IF NOT EXISTS public_assistant_appearance AS SELECT bot_id,appearance FROM companies;
"""
PRIVATE_TABLES = ['workspace_preferences','knowledge_sources','source_versions','ingestion_jobs','knowledge_chunks','visitors','conversations','visitor_tokens','messages','message_requests','ai_turns','subscriptions','demo_invoices','usage_events','audit_events','channel_events']

class PgConnection:
    def __init__(self, connection): self.connection = connection
    def execute(self, sql, parameters=()):
        return self.connection.execute(sql.replace('?', '%s'), parameters or None)
    def executescript(self, sql):
        self.connection.execute(sql.replace('CREATE VIEW IF NOT EXISTS', 'CREATE OR REPLACE VIEW'), prepare=False)

class Database:
    def __init__(self, path=None, config=None):
        config_path = APP_ROOT / '.local/database.json'
        self.config = config or (json.loads(config_path.read_text()) if path is None and config_path.exists() else {})
        self.postgres = self.config.get('engine') == 'postgresql'
        self.path = Path(path or os.environ.get('H4T_DATABASE_PATH', APP_ROOT / '.local/h4t.sqlite3'))
        self.upload_root = (self.path.parent if path else APP_ROOT / '.local') / 'uploads'
        self.upload_root.mkdir(parents=True, exist_ok=True)
        if not self.postgres: self.migrate()

    @contextmanager
    def connect(self, plane='auth', company=None, write=False):
        if self.postgres:
            if company is not None and plane == 'auth': plane = 'app'
            with psycopg.connect(self.config[plane+'_url'], row_factory=dict_row, connect_timeout=5) as connection:
                connection.execute("SELECT set_config('h4t.company_id',%s,true)", (company or '',))
                yield PgConnection(connection)
        else:
            connection = sqlite3.connect(self.path, timeout=10)
            connection.row_factory = sqlite3.Row
            connection.execute('PRAGMA foreign_keys=ON')
            connection.execute('PRAGMA busy_timeout=10000')
            try:
                with connection:
                    if write: connection.execute('BEGIN IMMEDIATE')
                    yield connection
            finally: connection.close()

    def locked(self, sql): return sql + (' FOR UPDATE' if self.postgres else '')

    def migrate(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        plane = 'admin' if self.postgres else 'auth'
        with self.connect(plane) as connection:
            if not self.postgres: connection.execute('PRAGMA journal_mode=WAL')
            connection.executescript(BASE_SCHEMA + PRODUCT_SCHEMA + "CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY,applied DOUBLE PRECISION NOT NULL);")
            if self.postgres:
                connection.execute('ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS updated DOUBLE PRECISION NOT NULL DEFAULT 0')
                connection.execute("ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS error TEXT NOT NULL DEFAULT ''")
                connection.execute('ALTER TABLE ingestion_jobs ADD COLUMN IF NOT EXISTS attempts INTEGER NOT NULL DEFAULT 0')
                connection.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS citations TEXT NOT NULL DEFAULT '[]'")
                connection.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS engine TEXT NOT NULL DEFAULT 'scripted'")
                connection.execute("CREATE INDEX IF NOT EXISTS chunks_search ON knowledge_chunks USING GIN (to_tsvector('simple',content))")
            else:
                jobs_columns={row['name'] for row in connection.execute('PRAGMA table_info(ingestion_jobs)').fetchall()}
                if 'updated' not in jobs_columns: connection.execute('ALTER TABLE ingestion_jobs ADD COLUMN updated DOUBLE PRECISION NOT NULL DEFAULT 0')
                if 'error' not in jobs_columns: connection.execute("ALTER TABLE ingestion_jobs ADD COLUMN error TEXT NOT NULL DEFAULT ''")
                if 'attempts' not in jobs_columns: connection.execute('ALTER TABLE ingestion_jobs ADD COLUMN attempts INTEGER NOT NULL DEFAULT 0')
                columns={row['name'] for row in connection.execute('PRAGMA table_info(messages)').fetchall()}
                if 'citations' not in columns: connection.execute("ALTER TABLE messages ADD COLUMN citations TEXT NOT NULL DEFAULT '[]'")
                if 'engine' not in columns: connection.execute("ALTER TABLE messages ADD COLUMN engine TEXT NOT NULL DEFAULT 'scripted'")
            connection.execute("UPDATE ingestion_jobs SET status='queued',updated=? WHERE status='deferred' AND EXISTS (SELECT 1 FROM knowledge_sources s WHERE s.id=ingestion_jobs.source_id AND s.company_id=ingestion_jobs.company_id AND s.version=ingestion_jobs.version AND s.status='Demo published' AND s.deleted_at IS NULL)",(time.time(),))
            connection.execute("INSERT INTO schema_migrations VALUES(2,?) ON CONFLICT(version) DO NOTHING", (time.time(),))
            connection.execute("INSERT INTO schema_migrations VALUES(3,?) ON CONFLICT(version) DO NOTHING", (time.time(),))
            connection.execute("INSERT INTO schema_migrations VALUES(4,?) ON CONFLICT(version) DO NOTHING", (time.time(),))
            connection.execute("INSERT INTO subscriptions(company_id,plan,updated) SELECT id,'Starter',? FROM companies WHERE 1=1 ON CONFLICT(company_id) DO NOTHING", (time.time(),))

    def health(self):
        with self.connect() as connection:
            row = connection.execute('SELECT MAX(version) AS version FROM schema_migrations').fetchone()
        return {'engine':'postgresql' if self.postgres else 'sqlite','schemaVersion':row['version'],'status':'ok'}
