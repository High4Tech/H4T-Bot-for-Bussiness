# H4T Bot implementation boundaries

- This is a standalone High4Tech product. Do not push to or copy the agency repository.
- One assistant per company, shared branding and future knowledge across channels. Do not add a bot marketplace/list or create-bot flow.
- Keep runtime services on loopback. No cloud provisioning unless explicitly requested.
- Local auth and saved appearance/channel settings are real. Chat, handoff, knowledge publication, billing and metrics are previews. Preserve their notices; never claim an AI engine, model training or live provider connection without evidence.
- Owner APIs must derive company membership from the session. The operator may receive only allowlisted account and aggregate metadata, never conversations, profiles, uploads, webhook payloads or impersonation access.
- Registered preview conversations must stay out of fixture BroadcastChannel synchronization.
- Keep supplied font binaries, `.local`, `.venv`, credentials and reference exports out of Git. Use bundled icons/assets without runtime CDNs.
- Run the TypeScript/build check, Node tests and scoped Python API tests after relevant changes. The explicit pytest configuration prevents collecting unrelated user directories.
- In the original ChatGPT workspace, `../sources` is synced read-only reference material. AI-ENGINE-DECISION.md and NEXT-CHAT-CONTEXT.md supersede H4T-Bot-Plan.md. Future AI uses grounded company RAG, local replaceable inference, and PostgreSQL/pgvector. SQLite is the current local product adapter.
