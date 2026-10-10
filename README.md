# H4T Bot for Business

A standalone, local-first product by High4Tech. React / TypeScript / Vite interface with a loopback FastAPI product service, tenant-scoped knowledge ingestion, local embeddings and Ollama-backed visitor answers.

The agency repository is separate. This repository contains no agency auth assumptions, private transcripts, supplied font binaries, credentials or local database. Synced ChatGPT project references remain read-only outside the app.

## Run locally

Prerequisites: Node.js 20+ and Python 3.12+. From the repository directory:

```powershell
npm.cmd ci
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r server/requirements-lock.txt
.venv/Scripts/python.exe -m pip install -r server/requirements-ai.txt
```

Create the project-local PostgreSQL database first (Windows, official EnterpriseDB binaries):

```powershell
.venv/Scripts/python.exe scripts/download-postgres.py
.venv/Scripts/python.exe scripts/setup-database.py
.venv/Scripts/python.exe scripts/download-embedding.py
```

Install [Ollama](https://ollama.com/download) locally and pull the configured generation model (`ollama pull llama3.2`). The model must be running or available through Ollama's loopback API. Start the ingestion worker with `./scripts/start-local.ps1`, or separately with `.venv/Scripts/python.exe -m server.worker`. Model binaries, uploads and database files remain ignored under `.local/`. The embedding download is a one-time setup step; normal inference uses only the local saved model.

Then start the local services with `./scripts/start-local.ps1`, or use two terminals with this directory as their working folder:

```powershell
.venv/Scripts/python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8871
```

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173/. The frontend proxies `/api` to the local service. Both bind to loopback. App records persist in project-local PostgreSQL on `127.0.0.1:55432`, database `h4t_bot`. Uploads, credentials, backups and runtime files stay in ignored `.local/`. The original SQLite database is preserved as a migration backup. See [DATABASE.md](DATABASE.md) for schema, permissions and backup commands. No hosted database, auth provider, AI API or cloud provisioning is needed. For a build preview, run `npm.cmd run build` followed by `npm.cmd run preview` while the API remains running.

If another local app already uses port 5173, start only this frontend with `npm.cmd run dev -- --port 5174 --strictPort` and open http://127.0.0.1:5174/. The API accepts either exact loopback preview origin; it does not accept arbitrary origins.

## Typography and motion

PP Neue Montreal is used for headings and the product website; Helvetica Neue for workspace and widget text. Supplied font binaries are installed locally and excluded from Git because the ZIPs contain no redistribution license. A fresh checkout uses Helvetica / Arial fallbacks. Import your licensed archives:

```powershell
./scripts/import-fonts.ps1 -NeueMontrealZip "path/to/pp-neue-montreal-cufonfonts.zip" -HelveticaNeueZip "path/to/helvetica-neue-5.zip"
```

The script extracts only six known font filenames, never ZIP paths or executable files. Phosphor icons and Lenis are installed packages, served locally. Lenis is confined to the product website; smoothing and decorative animation are disabled with reduced-motion preferences. No runtime CDN, remote font, image, analytics or inference dependency is included.

## Surfaces

The customer dashboard adapts the inspected GO light-screen layout with a 280px sidebar, three summary cards, a period-filtered activity graph, searchable conversation table, pagination and a three-column chat detail. Its totals and chart are queried from the local database rather than the 50-row workspace snapshot. The registered widget uses customer-specific branding and published business knowledge. Shared controls follow the inspected Untitled library geometry.

- `/`: product website with original High4Tech branding and bundled shadcn typography.
- `/signup`, `/login`: local account registration and sign-in.
- `/dashboard`: protected owner workspace with one business assistant. Dashboard, Chat record, Knowledge, Integrations, Users, Settings, Appearance and Demo Pricing. Legacy `#/bots` and `#/install` links open Assistant and Integrations.
- `/widget?company=<public-assistant-id>`: public branding and locally generated, cited answers from that business's ready sources. No owner account is required to view the widget.
- `/demo-host.html?company=<public-assistant-id>`: loopback sample website with the isolated iframe widget.
- `/widget?company=high4tech` and `company=cedar`: synthetic reference themes, independent of real account data.
- `/platform`: protected, metadata-only operator view. Customer accounts are denied. The operator has no customer membership.

Registration creates exactly one assistant per business. There is no create-bot flow or list of assistants. Branding settings save through the authenticated API and are shared by that assistant’s website installations. Website source records, privately stored files, version history, visitor sessions, conversations, handoffs and Demo billing persist. Publishing a source queues bounded text extraction and indexing. Only ready, currently published source versions can support an answer. Source publication still has the legacy database label “Demo published”; billing alone is simulated.

To answer from a PDF: sign in, open **Knowledge**, choose a text-based PDF under 10 MB, select **Publish & index**, and wait for **Ready**. Then ask a question in **Try in browser**. An upload saved as Draft is private storage, not answerable knowledge. If the session expires during upload, the file is not saved and must be selected again after sign-in. Scanned/image-only PDFs currently need OCR; the index shows a specific failure instead of claiming Ready.

## Local authentication and privacy

Passwords use salted scrypt hashes. Sessions use random tokens, hashed server storage and HTTP-only, SameSite Strict cookies with eight-hour expiry. Logout revokes the server session. Owner APIs derive company membership from the session instead of trusting a client-supplied company ID. Writes require a trusted local Origin; requests and auth attempts are bounded. Hostnames are restricted to loopback (plus the test harness host).

The HTTP cookie intentionally has `Secure=false` for local HTTP. This is a development service, not a production security or deployment claim. Email delivery, verification, password reset, team invitations, production retention and deployment are deferred. Local limits bound files, sources, conversation creation and message volume; these are development limits, not sold plan allowances.

The operator endpoint returns only an explicit metadata allowlist. No conversations, visitor profiles, source contents, brand uploads, webhook payloads or impersonation endpoints are available to the operator. To create an operator yourself, explicitly run:

```powershell
.venv/Scripts/python.exe -m server.manage create-platform-admin --email "your-operator-address"
```

The command prompts for a password without echoing it. Ordinary sign-up cannot request the operator role. No shared default operator password is provided.

Registered visitor chats use hashed, expiring bearer tokens and are saved in PostgreSQL. A visitor can read only their own conversation. The owner Chat record and widget poll the local API; takeover pauses assistant replies and team messages are delivered across tabs. Owner actions include viewing, exporting and deleting a conversation with version checks. Settings and team entries are saved drafts: they do not yet affect AI behavior, create accounts or send invitations. Synthetic reference fixtures still use BroadcastChannel and never include registered workspace data. Use sample visitor details during development.

## Channels: implemented scope

| Channel | Local implementation | Remaining work |
| --- | --- | --- |
| Website | Rebrandable iframe loader, public appearance endpoint, local sample site | Verified public hosts and deployment |
| WordPress | Same widget snippet and a local-only installable PHP plugin | Testing in an actual WordPress installation; public hosting |
| Shopify | Theme snippet instructions using the same assistant ID | Shopify theme/store validation; app OAuth and public hosting |
| WhatsApp | Saved business phone-number routing, verification handshake, signed inbound webhook receiver | Meta credentials, reachable HTTPS callback, outbound delivery and AI replies |
| Facebook Messenger | Saved Page routing and the same verified inbound transport | Meta credentials, reachable HTTPS callback, outbound delivery and AI replies |

Setup is labeled “saved” rather than “connected.” Saving installation metadata does not verify that a website or social account is live. Voice, real payment checkout and custom-domain controls remain hidden. Billing amounts, checkout and invoices are Demo.

Set `H4T_META_APP_SECRET` and `H4T_META_VERIFY_TOKEN` in the API process environment when preparing webhook tests. `.env.example` describes these variables; the server does not automatically load `.env`. Never put provider secrets in browser fields. The receiver checks HMAC SHA-256 over raw bytes, verifies the challenge, maps an enabled provider ID to its company and suppresses identical retransmitted envelopes. Payloads stay in the ignored local database; the owner event endpoint returns receipt metadata only. Missing credentials return unavailable. The local service cannot receive Meta’s public callbacks without future HTTPS hosting; no tunnel or cloud service is created.

The widget loader accepts loopback websites only, validates frame messages against the exact origin and frame, and sends only public appearance and close events to the host. Public installation still requires public host origin policy and production retention enforcement.

## Engine direction

The engine runs a bounded local worker over TXT, PDF, DOCX, CSV and public website text. It splits each source into chunks, embeds them with `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions), and stores the vectors with tenant and source-version keys in PostgreSQL. Retrieval combines semantic similarity, token overlap and bounded typo matching. Ollama's loopback API generates an answer from retrieved passages and returns source citations. Missing or conflicting facts trigger clarification; a visitor can request human handoff. Knowledge text is treated as evidence, never instructions. A failed worker job is visible in Knowledge and can be retried.

The project-local Windows PostgreSQL installation currently lacks pgvector. The local prototype uses PostgreSQL storage and bounded application-side vector and lexical scoring; a full-text index is present for later database-side retrieval. pgvector-backed nearest-neighbor search remains a scaling step. The current Llama 3.2 model is a prototype choice whose [license](https://ollama.com/library/llama3.2) needs review before commercial launch. This is RAG indexing, not weight training; company-specific fine-tuning remains a separate, evaluated future decision. No claim of perfect grounding or multilingual quality is made.

The cost-conscious deployment path reuses the current FastAPI, PostgreSQL, Sentence Transformers and Ollama components. A later Docker Compose package can use the official [pgvector PostgreSQL image](https://github.com/pgvector/pgvector#docker) and keep the API/worker/inference adapters separate; this PC's Docker daemon was not running during the PDF fix, so no container deployment is claimed. [Qwen3 4B on Ollama](https://ollama.com/library/qwen3:4b) is an Apache-2.0 licensed candidate to benchmark against the installed 3B model before any switch. Container images and model weights may be free to use under their licenses, but an always-on production server, storage, backups and support still have costs. The current local stack is already functional without Docker.

## Interface system

The current interface uses [shadcn/ui](https://ui.shadcn.com/) components with Tailwind CSS, the Nova preset, bundled Geist type, Lucide icons and the shadcn chart component (Recharts). `components.json` records the local registry configuration. Product layout CSS in `src/app.css` uses the library's color and radius tokens; the only brand accent is High4Tech orange `#F97328` alongside white and black. The original High4Tech logo and mascot remain local assets. The former custom visual stylesheets and Phosphor/Lenis packages were removed. No runtime CDN is used.

The company dashboard, visitor widget, local auth, product page and metadata-only operator surface share this theme. Business widget appearance can still use each customer's saved accent color and assets. Historical design exploration is recorded in `VERIFICATION.md`; it is not the current UI specification.
## Validation

```powershell
npm.cmd run build
npm.cmd test
.venv/Scripts/python.exe -m pytest -c pytest.ini tests -q
```

See VERIFICATION.md for evidence actually collected and limitations. Reference materials and local proof screenshots are excluded from the published repository.

## Upstream references

- [shadcn/ui](https://ui.shadcn.com/), local component source and theme.
- [Lucide](https://lucide.dev/), bundled interface icons.
- [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/).
- [Meta’s WhatsApp webhook reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/), verification and signature checking.
