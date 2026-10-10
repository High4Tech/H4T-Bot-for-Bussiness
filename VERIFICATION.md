# Local verification — 10 October 2026

## Website-source functionality — 10 October

- The implemented website source fetches **one public HTML or plain-text URL** after the owner publishes it. It does not yet discover a sitemap, follow same-site links, render JavaScript, obey robots.txt, or refresh automatically. Those are required before describing it as a whole-site crawler.
- Added `test_published_website_html_reaches_visitor_answer` to cover saved URL → publication → bounded HTML fetch/cleanup → worker indexing → retrieval → cited visitor answer, with an uploaded TXT source in the same business and a second cited answer from that file. It uses a controlled HTTP response, deterministic vectors, and a stubbed generation result to isolate product wiring. Both SQLite and the project-local PostgreSQL test runs passed: 2 passed, 1 existing Starlette deprecation warning.
- Ran `scripts/smoke-website.py` against the public `https://example.com/` page with the actual website fetcher, saved MiniLM embedding model, isolated temporary SQLite database, and installed Ollama `llama3.2:latest`. It indexed one chunk in 62.41 seconds, answered “What is this domain intended for?” in 31.49 seconds, and cited that URL. These times include cold startup and are a single observation, not a throughput benchmark. No customer website was tested in this run.
- The local PostgreSQL service was started for the test; no production deployment or provider integration was created.

## Earlier checks

## PDF upload diagnosis and workflow pass — 6 October

- Inspected only local upload/processing metadata and response engine labels. The recent upload request returned HTTP 401 after the dashboard session expired. No PDF source exists in the active database; the sole stored source is an older TXT Draft with no index. Three recent bot responses were `no_evidence`. The user's PDF bytes were never saved, so that particular document could not be extracted or answered from.
- The UI now takes an expired owner session back to sign-in with a clear message that the file was not saved. A successful upload shows a direct **Publish & index** action and explains that only Ready sources answer questions. Dashboard and assistant status copy now describe the active local AI engine, and Demo billing shows the real local AI answer count.
- Generated text-based and blank/scanned-style PDFs exercised upload, publication, job processing and retrieval in isolated SQLite and PostgreSQL tests: nine focused AI cases passed with one existing Starlette/TestClient deprecation warning. An image-only PDF reports `pdf_no_extractable_text` so OCR needs are visible.
- A disposable two-company fixture indexed a real generated PDF with local 384-dimensional embeddings and received an Ollama answer citing `verified-facts.pdf`; an unsupported question returned `no_evidence`. PDF indexing took 11.56 seconds including initial model startup and the two visitor requests together took 4.56 seconds. The specific user PDF was not tested because it was not stored.
- Docker CLI exists but its Linux engine was unavailable on this PC during this pass. No container was started and no production hosting cost or model quality was benchmarked.

## Local AI engine pass — 6 October

- Installed the local AI dependencies and saved `sentence-transformers/all-MiniLM-L6-v2` under ignored `.local/models/`; a local encode check returned one normalized 384-dimensional vector. Ollama `llama3.2:latest` was already installed on this PC and answered through its loopback API. No model was trained.
- Added schema version 4 with tenant-scoped source chunks, processing state, citations and generation-turn receipts. The local ingestion worker is separate from the API; the running API health endpoint returned PostgreSQL schema 4, and `/api/engine/status` returned local RAG with embeddings and generation available.
- A disposable two-company fixture used real embeddings to index one source for each business. Cross-company retrieval stayed isolated. A registered visitor asked Cedar Cycles for workshop hours; the local model replied “Monday to Friday, 9 AM to 5 PM” with a source citation. A question for a private CEO phone number returned `no_evidence`. First-source indexing took 14.13 seconds including model startup; the second took 0.09 seconds. The two visitor requests together took 52.53 seconds on this PC. These are observations from a small synthetic fixture, not throughput or quality guarantees.
- The frontend production build and six Node tests passed. The final Python integration suite passed 31 cases across SQLite and PostgreSQL, including the worker-role grant, old-source migration, source-version cleanup and operator aggregate AI-answer count. One Starlette/TestClient deprecation warning remains.
- pgvector is absent from the project-local Windows PostgreSQL runtime, so retrieval currently scores stored vectors in Python with a 5,000-chunk bound. Public website fetching, complex PDFs, multilingual answers, prompt-injection resistance, grounding quality at scale, production retention and browser rendering of the new UI have not been fully validated.

## GO dashboard and local settings pass — 6 October

- Inspected GO light Home `3008:17100`, Chats `3008:17205`, chat detail `3008:17431`, Knowledge `3008:18714`, Settings `3008:18910`, Users `3008:18814`, Pricing `3008:19779`, and their child controls before coding. The resulting dashboard uses the High4Tech brand, a GO-style sidebar, cards, activity line, table and split chat layout. Calls and unsupported controls remain hidden. No pixel-exact visual match is claimed.
- The owner API now serves counts and hourly chat-start data, searched/paginated conversation summaries, details, JSON export and version-checked deletion. Settings and team entries persist as drafts. This does not turn on AI behavior or team sign-in.
- Migrated the local PostgreSQL database to schema version 3 with a tenant-scoped preferences table and refreshed grants. Restarted the local API. Its health endpoint reported PostgreSQL schema 3; the new protected preferences route returned 401 without a session instead of the old 404.
- `npm run build` passed after the final UI changes; six Node tests passed. All 24 Python tests passed against SQLite and the local PostgreSQL test database, including new activity, actions, preferences and tenant-boundary cases. One existing Starlette/TestClient deprecation warning remains.
- The local preview was left running. Fresh browser visual inspection was not performed for this pass, so rendering and interaction alignment remain to be checked in the browser.

## Visual refinement and service checks — 6 October

- Inspected exact Figma contexts and screenshots before implementation: Untitled `NU1SlgUvw6zmalvW1Qhj6K` button `3287:427323`; GO `dxZUj3AlKSm8II2xgIvFwY` sidebar `3040:36753` and widget Home `2923:8335`. Reused the original High4Tech assets, supplied local typography and bundled Phosphor icons. No exact frame match is claimed.
- Added the branded single-assistant welcome page and setup links; refined shared controls, spacing, dark-mode tokens, widget and empty states. Widget primary actions now follow the business accent color, and business logos use contain sizing. Added responsive layout rules, an Escape dismissal and a mobile navigation scrim; their fresh visual behavior has not been browser-verified.
- Replaced the fixed sample activity chart with local-day counts from saved timestamps in the 50 most recent conversations. The scope is stated in the interface.
- TypeScript and the Vite production build passed (90 modules). All six Node tests and all 22 Python tests passed. The Python suite exercised SQLite and actual PostgreSQL and emitted one existing Starlette HTTPX TestClient deprecation warning. Initial test setup attempts failed on temporary-directory permissions; the successful suite used a fresh project-local temporary directory with pytest cache disabled.
- Restarted the project-local services using the documented startup helper. The running Vite proxy returned healthy PostgreSQL, schema version 2, and `ai: deferred`. The existing synthetic owner could sign in; saved sources, conversations and Demo invoices were present after restart. Saved conversation timestamps were returned for the chart. Unauthenticated workspace access returned 401 and customer access to the operator endpoint returned 403.
- The original branding assets and all six supplied local font endpoints returned valid files; font payloads had OpenType headers.
- Created a fresh private database/upload backup and verified its hashes and isolated restore: one company and one source file passed verification. The running database was unchanged.
- Fresh browser inspection was rejected by the browser tool URL policy before navigation. No alternate browser or automation workaround was used. Desktop/mobile rendering, interactions, dark mode and visual alignment for this refinement therefore remain unverified in a browser; the older screenshots below are not evidence for this revision.

## Previous verification — 5 October 2026

Executed on the user’s Windows PC, in the standalone H4T Bot workspace. This covers the premium interface baseline and the subsequent PostgreSQL persistence revision; it does not claim a deployed product or active AI engine.

## PostgreSQL revision: checks actually completed

- Installed official PostgreSQL 17.11 binaries inside the project, initialized `h4t_bot`, and bound it to `127.0.0.1:55432`. No cloud or global Windows database service was created. Docker Desktop's engine did not become available; the app uses the portable direct runtime.
- Preserved the original SQLite file, created a backup, and imported eight existing account/settings/session rows. The existing synthetic preview owner signed in successfully through Vite's real `/api` proxy.
- Database inspection confirmed 18 base tables, schema version 2 and 15 tables with forced row-level security. pgvector is absent and explicitly deferred.
- The TypeScript and final Vite production build passed (88 modules). All six existing Node tests passed.
- Six original API tests and five product tests run against both SQLite and actual PostgreSQL. All 22 Python cases passed, with one existing Starlette HTTPX TestClient deprecation warning. Product checks cover persisted sources/files/revisions, stale updates, tenant and visitor-token isolation, consent, file limits, restart behavior, handoff, paused replies, concurrent idempotency, Demo invoices and SQL-level operator restrictions.
- Through the running local proxy, a synthetic private upload, visitor handoff, owner takeover, team reply and Growth Demo plan were saved. PostgreSQL was stopped and restarted; the authenticated workspace, original file bytes, visitor token and team reply still worked. This verifies API delivery across independent clients, not a fresh browser rendering check.
- Created a private PostgreSQL dump and upload backup, checked hashes, restored it into an isolated temporary database, reapplied grants, and verified one company and one source file. The running database was not overwritten. Zero temporary test databases remained after cleanup.
- All six supplied local font endpoints still returned valid OpenType files.
- The documented local startup helper ran successfully and reused the existing loopback API and preview.

## Earlier interface checks actually run

- TypeScript and the final Vite production build passed (88 modules).
- Six Node tests passed: unavailable facts, simulated handoff, status transitions, metadata projection, independent synthetic themes and fixture synchronization.
- Six scoped Python API tests passed after the database connection cleanup. They cover registration, password/session hashing, HTTP-only / SameSite cookie flags, revocation, sign-in, Origin and Host rejection, unauthenticated access, two-company appearance isolation, public appearance allowlisting, operator restriction, channel provider conflicts, webhook challenge/signatures/routing, identical-envelope duplicate suppression, malformed envelope handling, auth throttling and body-size limits.
- The Python test run emitted one Starlette deprecation warning about the supported legacy HTTPX TestClient integration. No test failed.
- The local font import script ran successfully against both supplied ZIPs. All six font endpoints returned HTTP 200, `font/otf`, and valid OpenType `OTTO` headers.
- The frontend’s `/api/health` proxy returned the local API’s healthy status and `ai: deferred`.

The initial unscoped Python test attempt stalled while discovering the unrelated home-directory project. That helper was interrupted; a repository-specific pytest.ini and explicit `-c pytest.ini` scoped the successful runs. Do not interpret the stalled attempt as a pass.

## Browser checks from the earlier interface baseline (before database wiring)

- Product website rendered the original High4Tech branding, supplied font-family styles, bundled Phosphor icons and animated conversation cards.
- Synthetic local account sign-in opened its protected workspace. Logout returned to the sign-in page.
- Navigation displayed one assistant and Channels, with no company selector or multiple-bot list.
- Channels showed Website, WhatsApp, Messenger, WordPress and Shopify setup cards.
- Synthetic WhatsApp setup saved successfully and visibly retained the “live delivery not verified” notice. The synthetic routing was then disabled and cleared.
- Saved welcome copy survived a full reload and appeared in a separate public embedded widget using the same assistant ID.
- The widget was loaded by the iframe script on the local sample website and answered a demo question with an explicit deferred-engine explanation.
- In the dashboard widget preview, requesting a person populated the same-tab inbox. Taking over paused the demo assistant, and the team reply appeared after reopening the widget.
- The revised appearance editor was inspected in dark mode; fields, text and navigation were readable.
- A customer account opening `/platform` saw “Platform access is restricted.” The server operator allowlist and customer-API denial were verified separately by the Python tests.

Proof screenshots are local only: `preview/premium-website.png` and `preview/premium-channels.png`. Their files, font binaries and local runtime data are ignored by Git.

## Limits

The current in-app browser did not apply the requested 390 × 844 viewport override: DOM inspection still reported 1280 pixels. This revision was inspected at desktop width; a fresh mobile visual check remains outstanding. The override was reset. A previous interface baseline was checked on mobile, but that is not evidence for this revised layout.

WordPress plugin execution, a Shopify store/theme, Meta’s live handshake, social outbound delivery, social OAuth/app review, email delivery and public hosting were not tested. The Meta tests use signed synthetic payloads, not live customer traffic. No provider credentials were installed and no tunnel or cloud service was provisioned.

At the time of the previous interface pass, no AI model, embeddings, pgvector extension, ingestion, training, benchmarks, social outbound delivery, production host policy, real payments, retention jobs or exhaustive accessibility/device coverage had been implemented or verified. The local AI engine changes and their checks are recorded above. Sample visitor and source records used for verification remain only in ignored development or disposable test databases.

The attempted current browser inspection was rejected by the browser tool URL security policy before navigation. No workaround was attempted. The new database-connected screen behavior has build/API verification, but no fresh visual browser check is claimed.

The platform UI imports no customer store. The operator SQL-role and tenant row-security restrictions are tested locally. Production security and deployment review remain separate work. No pixel-exact match to every Figma frame is claimed.
# shadcn/ui visual system — 10 October 2026

- Installed the official shadcn/ui Nova preset for the existing Vite app, plus local Card, Button, Input, Badge, Table, Tabs, Alert Dialog and Chart components. Replaced legacy visual stylesheets, Phosphor icons and Lenis with one shadcn-token-based theme, bundled Geist/Lucide, and the original High4Tech assets. The dashboard chart now uses shadcn's ChartContainer and Recharts.
- Updated the High4Tech preview assistant accent from its former saved purple value to `#F97328` through the local Appearance screen; the save confirmation appeared. Customer widgets remain rebrandable through their own appearance settings.
- Built the production frontend successfully; all six Node product tests passed. The scoped API suite passed 12 tests against its local SQLite/PostgreSQL fixtures after routing pytest's temporary files into `.local`; an initial sandbox run failed only because pytest could not create its default temporary directory.
- Inspected the running local dashboard, Knowledge, product website and widget in the in-app browser. The activity period Tabs switched from 12 months to 7 days, and light/dark Appearance rendering was visually checked. The preview remains local on `127.0.0.1:5174`.
- A follow-up pass moved native selects, text areas, inputs, checkboxes, labels and remaining action buttons onto shadcn components, and placed the dashboard shell under the shadcn Sidebar provider. The Settings and Integrations pages were then visually checked in the running preview; a narrow Integrations guide caused by an unbreakable embed snippet was fixed.
