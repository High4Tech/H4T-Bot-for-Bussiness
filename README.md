# H4T Bot for Business

A standalone, local-first product by High4Tech. React / TypeScript / Vite interface with a loopback FastAPI product service. This stage implements the website, visitor widget, single-assistant customer workspace, local authentication and channel setup. AI generation and ingestion remain deferred at the user’s explicit request.

The agency repository is separate. This repository contains no agency auth assumptions, private transcripts, supplied font binaries, credentials or local database. Synced ChatGPT project references remain read-only outside the app.

## Run locally

Prerequisites: Node.js 20+ and Python 3.12+. From the repository directory:

```powershell
npm.cmd ci
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r server/requirements-lock.txt
```

Use two terminals, with this directory as their working folder:

```powershell
.venv/Scripts/python.exe -m uvicorn server.app:app --host 127.0.0.1 --port 8871
```

```powershell
npm.cmd run dev
```

Open http://127.0.0.1:5173/. The frontend proxies `/api` to the local service. Both bind to loopback. API settings and accounts persist in ignored `.local/h4t.sqlite3`. No hosted database, auth provider, AI API or cloud provisioning is needed. For a build preview, run `npm.cmd run build` followed by `npm.cmd run preview` while the API remains running.

## Typography and motion

PP Neue Montreal is used for headings and the product website; Helvetica Neue for workspace and widget text. Supplied font binaries are installed locally and excluded from Git because the ZIPs contain no redistribution license. A fresh checkout uses Helvetica / Arial fallbacks. Import your licensed archives:

```powershell
./scripts/import-fonts.ps1 -NeueMontrealZip "path/to/pp-neue-montreal-cufonfonts.zip" -HelveticaNeueZip "path/to/helvetica-neue-5.zip"
```

The script extracts only six known font filenames, never ZIP paths or executable files. Phosphor icons and Lenis are installed packages, served locally. Lenis is confined to the product website; smoothing and decorative animation are disabled with reduced-motion preferences. No runtime CDN, remote font, image, analytics or inference dependency is included.

## Surfaces

- `/`: product website with original High4Tech branding and supplied fonts.
- `/signup`, `/login`: local account registration and sign-in.
- `/dashboard`: protected owner workspace with one business assistant. Overview, Assistant, Inbox, Knowledge, Appearance, Channels and Demo billing. Legacy `#/bots` and `#/install` links open Assistant and Channels.
- `/widget?company=<public-assistant-id>`: public branding from the local API, then a scripted chat preview. No owner account is required to view the widget.
- `/demo-host.html?company=<public-assistant-id>`: loopback sample website with the isolated iframe widget.
- `/widget?company=high4tech` and `company=cedar`: synthetic reference themes, independent of real account data.
- `/platform`: protected, metadata-only operator view. Customer accounts are denied. The operator has no customer membership.

Registration creates exactly one assistant per business. There is no create-bot flow or list of assistants. Branding settings save through the authenticated API and are shared by that assistant’s website installations. Knowledge, source publication and chat replies remain simulations; uploaded file contents are not read or indexed.

## Local authentication and privacy

Passwords use salted scrypt hashes. Sessions use random tokens, hashed server storage and HTTP-only, SameSite Strict cookies with eight-hour expiry. Logout revokes the server session. Owner APIs derive company membership from the session instead of trusting a client-supplied company ID. Writes require a trusted local Origin; requests and auth attempts are bounded. Hostnames are restricted to loopback (plus the test harness host).

The HTTP cookie intentionally has `Secure=false` for local HTTP. This is a development service, not a production security or deployment claim. Email delivery, verification, password reset, team invitations, durable chat, quotas, retention policy and production PostgreSQL are deferred.

The operator endpoint returns only an explicit metadata allowlist. No conversations, visitor profiles, source contents, brand uploads, webhook payloads or impersonation endpoints are available to the operator. To create an operator yourself, explicitly run:

```powershell
.venv/Scripts/python.exe -m server.manage create-platform-admin --email "your-operator-address"
```

The command prompts for a password without echoing it. Ordinary sign-up cannot request the operator role. No shared default operator password is provided.

Registered-workspace preview messages stay in memory in their current tab and are never broadcast. Try handoff in the dashboard’s widget preview, close it, take over in Inbox, reply, then reopen the widget. A separate embedded tab does not deliver chats to the owner inbox yet. Only the two synthetic reference fixtures use BroadcastChannel; their synchronization excludes every registered workspace. Use sample visitor contact details only.

## Channels: implemented scope

| Channel | Local implementation | Remaining work |
| --- | --- | --- |
| Website | Rebrandable iframe loader, public appearance endpoint, local sample site | Verified public hosts, visitor sessions, server chat and deployment |
| WordPress | Same widget snippet and a local-only installable PHP plugin | Testing in an actual WordPress installation; public hosting |
| Shopify | Theme snippet instructions using the same assistant ID | Shopify theme/store validation; app OAuth and public hosting |
| WhatsApp | Saved business phone-number routing, verification handshake, signed inbound webhook receiver | Meta credentials, reachable HTTPS callback, outbound delivery and AI replies |
| Facebook Messenger | Saved Page routing and the same verified inbound transport | Meta credentials, reachable HTTPS callback, outbound delivery and AI replies |

Setup is labeled “saved” rather than “connected.” Saving installation metadata does not verify that a website or social account is live. Voice, real payment checkout and custom-domain controls remain hidden. Billing amounts, checkout and invoices are Demo.

Set `H4T_META_APP_SECRET` and `H4T_META_VERIFY_TOKEN` in the API process environment when preparing webhook tests. `.env.example` describes these variables; the server does not automatically load `.env`. Never put provider secrets in browser fields. The receiver checks HMAC SHA-256 over raw bytes, verifies the challenge, maps an enabled provider ID to its company and suppresses identical retransmitted envelopes. Payloads stay in the ignored local database; the owner event endpoint returns receipt metadata only. Missing credentials return unavailable. The local service cannot receive Meta’s public callbacks without future HTTPS hosting; no tunnel or cloud service is created.

The widget loader accepts loopback websites only, validates frame messages against the exact origin and frame, and sends only public appearance and close events to the host. Public installation still requires server origin policy, visitor tokens, quotas and production retention enforcement.

## Engine direction

The original AI-ENGINE-DECISION.md and NEXT-CHAT-CONTEXT.md supersede the older runtime recommendation. Their architecture remains: FastAPI services, bounded ingestion worker, Sentence Transformers embeddings, PostgreSQL/pgvector hybrid retrieval and replaceable Ollama inference. SQLite here is a local product-development adapter. No model was downloaded, trained, benchmarked or served. RAG indexing must not be called weight training; company-specific fine-tuning is a later evaluated decision.

Answers must eventually be grounded in each business’s published sources, with clarification or handoff for missing/conflicting facts. Knowledge uploads are evidence, never instructions. The current replies explicitly state that generation and retrieval are deferred.

## Figma provenance

Library: https://www.figma.com/design/NU1SlgUvw6zmalvW1Qhj6K/

Linked node 18:1951 returned an unavailable-selection error. The actual Buttons page 1:1183 and Inputs page 85:1269 were inspected instead, then high-fidelity secondary button 3287:427323 and input 3531:402962 contexts. Shared controls adapt their 8px corners, 40px height, 14px labels, spacing and border/shadow hierarchy to local CSS and the supplied typography.

Product layout reference: https://www.figma.com/design/dxZUj3AlKSm8II2xgIvFwY/

Exact inspected child contexts before implementation:
- Widget set 2923:8293, including Home 2923:8335, Information 2923:8378, Chat 2923:8542, typing 2923:8582 and answered 2923:8610.
- Dashboard 2913:7816 was sparse; inspected sidebar 3040:36753, metric 2913:7844, chart 2913:7860 and cell 2913:7868 separately.
- Inbox metadata 2953:15870; high-fidelity header 2956:8691 and message 2959:10480.
- Knowledge metadata 2913:7930; high-fidelity website card 2913:7937 and upload card 2913:7943.

Original High4Tech favicon, wordmark and mascots were copied from approved sources. The original exported Figma icons remain local references; runtime icons now use bundled Phosphor React components. Reference screenshots are not runtime assets. No remote fonts/images/inference calls are used.

H4T adapts the GO hierarchy to #F97328, white-led UI and a single business assistant. Installation, platform and billing are new shared-component layouts; no pixel-exact Figma match is claimed.

## Validation

```powershell
npm.cmd run build
npm.cmd test
.venv/Scripts/python.exe -m pytest -c pytest.ini tests/test_api.py -q
```

See VERIFICATION.md for evidence actually collected and limitations. Reference materials and local proof screenshots are excluded from the published repository.

## Upstream references

- [Phosphor React](https://github.com/phosphor-icons/react), MIT icon library.
- [Lenis](https://github.com/darkroomengineering/lenis), MIT scrolling library.
- [FastAPI security documentation](https://fastapi.tiangolo.com/tutorial/security/).
- [Meta’s WhatsApp webhook reference](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/webhooks/start/), verification and signature checking.
