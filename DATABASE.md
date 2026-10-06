# Local product database

PostgreSQL 17.11 runs only on `127.0.0.1:55432`, database `h4t_bot`. The Windows binaries come from EnterpriseDB's official distribution and live under `.local/postgres-runtime/`. This is a local development setup, with no Windows service, global PATH modification, cloud database, container or automatic startup task.

## What is stored

| Records | Purpose |
| --- | --- |
| companies, users, sessions | One assistant per company, branding, salted password hashes, expiring hashed login tokens |
| channels, channel_events | Saved installation/routing settings and signed inbound envelope receipts |
| workspace_preferences | Tenant-scoped business hours, language, behavior and proposed team directory drafts; these are not applied to AI or team authentication |
| knowledge_sources, source_versions, ingestion_jobs, knowledge_chunks | Published source versions, bounded processing jobs, text chunks and local 384-dimensional embeddings |
| visitors, visitor_tokens | Contact consent and hashed eight-hour conversation access tokens |
| conversations, messages, message_requests, ai_turns | Saved transcripts, citations, handoff state, ordered messages and idempotent generation turns |
| subscriptions, demo_invoices | Demo plan changes and idempotent simulated invoices; no payment processing |
| usage_events, audit_events | Activity counters and opaque action/entity metadata, without copying transcript content |
| schema_migrations | Applied schema version, currently 4 |

File bytes are stored under `.local/uploads/` using random opaque filenames. Their original names, size and SHA-256 are recorded in source versions. Downloads require the owning customer session and return attachments. Publishing a source creates a queued job for the local worker; only ready chunks from the current published version can answer visitors. Draft and archived sources are excluded immediately. Indexing updates knowledge, never model weights.

## Database permissions

The API chooses a separate SQL role for each access plane:

- `h4t_auth`: authentication records, hashed visitor tokens, allowlisted company metadata and public widget appearance; registration can insert initial company/settings records.
- `h4t_app`: customer records under forced row-level security. Each transaction sets the session-derived company ID. Requests cannot choose another tenant. Visitor endpoints additionally validate a bearer token tied to the exact assistant and conversation.
- `h4t_ingest`: channel routing and signed-envelope insertion, with no grant to read envelope payloads.
- `h4t_worker`: queued job metadata only. The worker processes one job through the app role scoped to its recorded company ID.
- `h4t_platform`: only the aggregate `platform_company_metadata` view. No grant on conversations, visitor profiles, knowledge, brand uploads, authentication records or webhook payloads.

The bootstrap owner is used only by setup, migrations, backup and isolated test tools. Its credentials and all runtime role credentials stay in `.local/database.json` and `.local/pg-bootstrap.json`; never publish either. This is a development privacy boundary, not a claim that the PC/database owner cannot inspect local files.

## Start and check

```powershell
.venv/Scripts/python.exe scripts/database-tools.py start
.venv/Scripts/python.exe scripts/database-tools.py status
./scripts/start-local.ps1
```

The setup command is repeatable. On first setup it creates a SQLite backup, copies existing account/settings rows, seeds Demo subscriptions, and applies the PostgreSQL grants/policies before writing the active configuration. The original `.local/h4t.sqlite3` remains intact. The old database is not an active replica after migration.

Use `scripts/database-tools.py stop` to stop only this project cluster. Services can be run separately using the commands in README.md. No services are provisioned outside this PC. A fresh checkout must download the binaries and initialize its own ignored local configuration; credentials and database files are excluded from Git.

## Backup and restore verification

```powershell
.venv/Scripts/python.exe scripts/database-tools.py backup
.venv/Scripts/python.exe scripts/database-tools.py verify-backup
# Check a specific backup:
.venv/Scripts/python.exe scripts/database-tools.py verify-backup --backup ".local/backups/<backup-folder>"
```

Backups contain a PostgreSQL custom-format dump, private upload files and integrity hashes in `.local/backups/`. Keep these private. Verification checks hashes, restores into an isolated temporary database, reapplies SQL permissions, verifies referenced upload content, and removes only that temporary verification database. It never replaces the running app database. There is deliberately no command that blindly overwrites the active database.

## Development limits and concurrency

Limits are enforced server-side: 100 active sources, 100 MB total stored source bytes per company, 10 MB per file, 500 new conversations per company per day, 1,000 messages per conversation, plus per-client/session request throttling. Limits are fixed local development safeguards; proposed plan allowances are not yet production billing quotas.

PostgreSQL row locks serialize conversation writes, handoff transitions and Demo billing retries. Expected revisions reject stale handoff/source updates. Source and visitor-creation quota checks serialize on the company row. Composite foreign keys prevent messages, visitors and source revisions from belonging to different tenants. Retry receipts suppress repeated messages and Demo invoice creation.

SQLite remains a scoped API-test fallback, using foreign keys and serialized write transactions. It does not provide PostgreSQL's SQL-role privacy enforcement. The running app uses PostgreSQL, verified by `/api/health`.

## Engine limits and remaining work

The local worker accepts TXT, CSV, text-based PDF, DOCX and public HTML/plain-text URLs. Scanned/image-only PDFs report `pdf_no_extractable_text` until local OCR is added. Limits are 10 MB per uploaded file, 1 MB per fetched page, 50 PDF pages, 60,000 extracted characters, 100 chunks per source and 5,000 chunks per company. The worker does not crawl a whole website. Failed jobs expose an error code and can be retried; stale running jobs are retried by the single local worker after three minutes. Retrieval scores at most 5,000 current published chunks in the API process, which is suitable for local development, not a production scale benchmark.

pgvector is not installed in the bundled Windows PostgreSQL runtime. Embeddings are stored as validated 384-dimensional JSON vectors and scored with bounded Python cosine/lexical matching. Database-side vector search, fine-tuning, social outbound delivery, production host policy, payment processing, retention/deletion jobs and email-based account recovery remain later work. Scripted greetings and local model answers have distinct usage categories; only successful Ollama answers count as AI answers.

Official references: [EnterpriseDB Windows binaries](https://www.enterprisedb.com/download-postgresql-binaries), [PostgreSQL row security](https://www.postgresql.org/docs/current/ddl-rowsecurity.html), [psycopg bound parameters](https://www.psycopg.org/psycopg3/docs/basic/params.html), [pgvector](https://github.com/pgvector/pgvector). The download tool records a computed SHA-256 and verifies ZIP integrity; it does not claim validation against an official published checksum.
