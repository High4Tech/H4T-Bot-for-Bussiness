# Local verification — 5 October 2026

Executed on the user’s Windows PC, in the standalone H4T Bot workspace. This describes the premium, single-assistant revision; it does not claim a deployed product or active AI engine.

## Automated checks actually run

- TypeScript and the final Vite production build passed (88 modules).
- Six Node tests passed: unavailable facts, simulated handoff, status transitions, metadata projection, independent synthetic themes and fixture synchronization.
- Six scoped Python API tests passed after the database connection cleanup. They cover registration, password/session hashing, HTTP-only / SameSite cookie flags, revocation, sign-in, Origin and Host rejection, unauthenticated access, two-company appearance isolation, public appearance allowlisting, operator restriction, channel provider conflicts, webhook challenge/signatures/routing, identical-envelope duplicate suppression, malformed envelope handling, auth throttling and body-size limits.
- The Python test run emitted one Starlette deprecation warning about the supported legacy HTTPX TestClient integration. No test failed.
- The local font import script ran successfully against both supplied ZIPs. All six font endpoints returned HTTP 200, `font/otf`, and valid OpenType `OTTO` headers.
- The frontend’s `/api/health` proxy returned the local API’s healthy status and `ai: deferred`.

The initial unscoped Python test attempt stalled while discovering the unrelated home-directory project. That helper was interrupted; a repository-specific pytest.ini and explicit `-c pytest.ini` scoped the successful runs. Do not interpret the stalled attempt as a pass.

## Browser checks actually performed on this revision

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

No AI model, embeddings, ingestion, PostgreSQL, training, benchmarks, durable visitor sessions, cross-tab registered inbox delivery, production host policy, quotas, real payments, retention or exhaustive accessibility/device coverage are implemented or verified. Registered chat/source/billing previews remain in memory; real account and appearance/channel settings are local API-backed. A synthetic preview owner was created only in the ignored local database for browser verification, then signed out; its data is not included in Git.

The platform UI imports no customer store. Production privacy and security still require the future service/database architecture and deployment review. No pixel-exact match to every Figma frame is claimed.
