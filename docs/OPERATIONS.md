# Accounts, partners, voice and local operations

## Run the new build

Stop the old server in its normal terminal with Ctrl+C. In normal PowerShell:

```powershell
cd "C:\Users\ishan\OneDrive\Desktop\ASYNC"
python -m pip install -r requirements.txt
$env:GEMINI_MODEL = "gemini-3.5-flash-lite"
.\run.cmd
```

Keep your existing server-side API-key configuration. Health should report version 0.7.0. No key needs to be pasted into the app.

## Customer account and old records

Click **Create account** in the header, or **Sign in** for an existing account. Registration asks for a synthetic username, a password of at least 12 characters and confirmation. Password visibility, field guidance and a language selector are available inside the dialog. Successful registration returns to your current plan. Click your username/avatar for saved records; expand **Password & sessions** for security controls. Sign-out is available inside the dialog on mobile. Exploring bundles remains anonymous; document checks require a customer account. Account-menu records reopen directly after sign-in, including after a server restart. No localStorage/sessionStorage is used; an HttpOnly SameSite=Strict session cookie lasts at most eight hours. Passwords use Argon2id through the installed cryptography library. Sessions are stored as hashes and revoked on sign-out.

Unclaimed records from the previous version still accept their old recovery code until the original 24-hour expiry. Sign in, choose **Resume a saved check or order**, and supply the record ID and private code to claim one. Once linked, that code cannot grant access to another account. Records already linked to another customer cannot be claimed. Records created under the old consent do not become eligible for document-review access merely by being claimed; start a new consented check when that review is needed.

Accounts expire after 30 days without a credential sign-in; records still expire after 24 hours. Account deletion removes the account, sessions, owned local records and raw cached fields. Aggregate event counts contain no customer IDs and are retained for 30 days. Activity shows the most recent 200 events per record; decision history is capped at 200 entries and further decisions are rejected rather than silently discarding history. This local account system has no email verification, password-reset service or MFA; use a managed identity provider before a real customer pilot.

## Create staff accounts locally

In a second normal terminal at the project directory:

```powershell
python scripts/manage_accounts.py reviewer_demo --role reviewer
python scripts/manage_accounts.py partner_demo --role partner
```

Each command privately prompts for a new password and confirmation. There are no default staff credentials and the public registration API creates customer accounts only. Use separate browser profiles/incognito windows for customer, reviewer and partner sessions.

The account menu now includes **Account security**: change the password using the current password and a repeated new password; inspect session creation/expiry times; revoke one session or sign out all others. A password change atomically invalidates all previous sessions and issues one fresh session. A credential check completed before the change cannot create a new session afterward. Session hashes/tokens are never returned by the session list; IP/browser fingerprints are not collected.

To revoke staff access, run this local operator command against the same runtime store used by the server:

```powershell
python scripts/manage_accounts.py partner-name --disable
```

It disables sign-in and revokes all sessions, including another process's sessions in the same database. Disabled partners disappear from assignment choices. Existing tasks remain available to active reviewers for reassignment. There is no public staff-management endpoint or self-service role escalation; local filesystem access is the operator authority. Already-running requests cannot be recalled. Disabling does not erase decision history.

## Follow-up chat and Hindi

After the first advisor draft, review/edit the guided fields and check **I have reviewed the current answers below** before sending a short follow-up answer. Review is required again after a new draft or a manual edit. Only the latest eight user/question entries and the reviewed structured fields accompany the next consented request. Backend fallback merging retains reviewed fields omitted by the model; explicit corrections remain drafts for review. Nulls are not invented values. A failed request preserves answers and the typed reply. Clear conversation removes the chat context while retaining the editable form; refresh closes its lifetime. Sign-out clears chat context. No conversation is saved in browser storage or server databases.

Hindi now covers account roles, security controls/errors, task states, help priorities, field labels, review actions, channel status, cohort metrics and evidence explanations. Catalogue names/original descriptions and owner-entered content remain as supplied. Browser checks exercise Hindi mobile operations and security failures; they do not establish real microphone/transcription quality.

1. Customer: open a document-check record, enter a synthetic contact such as `demo@example.invalid`, accept follow-up consent and choose **Request follow-up**. Nothing is messaged automatically.
2. Reviewer: sign in, open **Team dashboard**, open the task, select the partner and choose **Assign partner**.
3. Partner: sign in and open **Team dashboard**. Only assigned, consented leads appear. Add a reason and resolve the follow-up. Partners cannot approve document evidence.
4. Customer: **Refresh check status** shows updates. Withdraw follow-up consent to immediately remove contact and partner access, or delete the record.

Reviewers can inspect ambiguous fields only under the current document-review consent. They can request replacement documents and record reasons. Only a legibility-only ambiguity can be confirmed, with explicit attestation that the original synthetic documents were inspected through an authorized source. Images are not retained, so the dashboard alone cannot establish that attestation. Missing, expired, mismatched or inactive registrations cannot be overridden. Evidence must still be in memory and decisions must match the current revision; otherwise the owner must upload/check again. Do not enter identifiers or personal information in decision reasons.

## Voice

Open the advisor section, expand **Describe your business by voice**, and accept the separate browser speech notice. Choose **Start speaking**, review/edit the transcript, then **Use reviewed transcript as description**. This does not call Gemini or place an order. Accept the separate advisor consent and request a draft afterward. Changing the app language selects en-IN or hi-IN and clears the old transcript/voice consent.

Browser speech support and language quality vary; the browser may send audio to its own provider. The app does not record audio and cannot control provider retention. Permission denial, recognition failure and unsupported browsers leave typed input available. Automated checks use controlled recognition; a real microphone, supported devices and Hindi/mixed-language accuracy still need live checks. See [MDN SpeechRecognition](https://developer.mozilla.org/en-US/docs/Web/API/SpeechRecognition).

## Evidence and measurement

```powershell
python scripts/analyze_leads.py
python scripts/evaluate_kyc.py --prepare
```

The first writes [synthetic business evidence](BUSINESS_EVIDENCE.md). The acquisition heuristic did not beat its held-out baseline and is not adopted for sales prioritization. The dashboard instead orders work by explicit help requests, document problems and nearing expiry, with visible reasons and no probability claim. The reviewer dashboard exposes aggregate observations and historical segment evidence.

The second creates blank private labels in `artifacts/kyc-labels.json` without provider calls. Read the student-visible original images and populate `expected` fields independently. Use strings for visible field values and null for confirmed absence; leave unassessed fields out. Keep an unseen subset for checking later prompt changes. Never use the judges-only pack. From your network-enabled terminal, explicitly authorize a bounded live run:

```powershell
python scripts/evaluate_kyc.py --labels artifacts/kyc-labels.json --limit 4 --consent
```

This sends up to four labelled synthetic images, one attempt each. It records per-field match booleans and elapsed time in `artifacts/kyc-evaluation.json`, without printing extracted values. Labels themselves can contain synthetic identifiers; do not publish them. Failed requests are reported separately from field accuracy. This assesses extraction, not identity/authenticity or KYC decision accuracy; document validation has separate automated tests.

A private `artifacts/kyc-reference-labels.json` was also prepared in this workspace by directly reading the four student-visible K01 images. The Udyam number is visibly blank; its GSTIN maps to an inactive registry entry. Passing those manually read fields into the backend correctly returns `action_required` with `missing_udyam_number` and `gstin_inactive`. This is a manual validation cross-check, not an OCR result. If using that file for a live run, substitute it in `--labels` above; it is intentionally excluded from the source archive and public submission. No judges-only answer key was consulted.

Local request limits: 300 mutations/minute per direct source IP, 10 login/register/password-change attempts/minute per source, 20 provider requests/minute per source and 12 per account (or anonymous session subject), with at most two concurrent provider calls. These controls assume a single worker and direct loopback clients; a future proxy deployment needs an explicitly trusted proxy strategy and shared limits.

## WhatsApp status

`backend/whatsapp.py` implements a signed receiver at `/api/integrations/whatsapp/webhook`, plus reviewer-only channel status. Both receiving and sending are disabled by default. GET verifies the token/mode and a bounded numeric challenge. POST validates exact-body signatures, receiving phone-number ID and bounded messages, and transactionally deduplicates message IDs for 24 hours. In inbound-only mode it retains replay hashes only. Receiving an event never establishes web-account ownership or changes an order.

Server-only settings are listed blank in `.env.example`: `UDYAM_WHATSAPP_ENABLED`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_PUBLIC_URL`. Enabling requires all settings, a 24+ character ASCII verification token, the matching receiving-account ID and a public HTTPS web-handoff URL without credentials/query/fragment. Do not put credentials into frontend fields or logs. Meta's verification protocol uses the verification token in a query string, so also disable/sanitize reverse-proxy logs for that endpoint. The normal cookie-CSRF header is bypassed only for this signed receiver; signature verification remains mandatory.

The reply adapter and deterministic guided conversation are implemented and tested with mocked transport. They are **not live-enabled or live-verified**. `UDYAM_WHATSAPP_OUTBOUND_ENABLED=1` additionally requires a server-only `WHATSAPP_ACCESS_TOKEN`, explicit supported `WHATSAPP_GRAPH_VERSION` and valid Fernet `WHATSAPP_STATE_KEY`. Generate the key privately using a password/secret-management tool; never put it in source, a browser, a screenshot or a command argument. Preserve it separately from encrypted database backups. Restore clears temporary channel state and queued replies to avoid replaying old sends; fresh channel consent is required. Changing the key makes existing channel state unreadable; preserve the old key until records expire or are deliberately cleared. Configure approved sandbox recipients/permissions and HTTPS in the provider console before a separately authorized live test. No real messages were sent during implementation.

Flow: an initial message receives a bilingual notice; START consents; choose English/Hindi; answer business type, city tier, employees, locations, budget, current internet, GSTIN claim and needs. The bot validates numeric choices without guessing, shows a summary and accepts EDIT 1 through EDIT 8 corrections. CONFIRM calls the same deterministic recommendation/quote code and returns a labelled estimate plus the public web link. HELP provides web support. STOP deletes local answers and queued recipient/content payloads, then sends one acknowledgement. RESTART requests consent again. No document/media extraction, Gemini call, account linking, private order lookup or checkout takes place on WhatsApp. The web handoff deliberately requires re-entering reviewed answers and signing in.

Structured answers are Fernet-encrypted for 30 idle minutes. Recipient/reply payloads are encrypted for at most ten minutes; sender lookup uses keyed hashes. Incoming raw text is not stored. Acknowledgement follows committed queueing; sending runs after the HTTP response. A reply is queued only for an inbound timestamp at most ten minutes old (within Meta's 24-hour service window); future timestamps over one minute ahead are rejected for replies. Limits: five messages per enabled batch, 40 turns per conversation, 1,000 concurrent states and 200 queued replies/day. Unknown text receives the current guided question; media is not downloaded.

Delivery reserves each queued message before network I/O, uses a fixed Meta origin/explicit API version and no redirects, proxies or automatic retries. Accepted/failed/unknown send states are separate from actual delivery; provider acceptance does not prove handset delivery. Timeouts or a crash after reservation never trigger a blind resend. Still-pending work can be dispatched by a subsequent valid webhook until expiry; there is no autonomous durable worker or retry administration. STOP cannot recall an in-flight or provider-accepted message. Keep the switches off until live account approval and review; dashboard configuration presence never claims live verification. References: [Meta's message collection](https://www.postman.com/meta/whatsapp-business-platform/folder/o48mro7/messages), [WhatsApp messaging policy](https://whatsappbusiness.com/policy/), [official SDK text schema](https://whatsapp.github.io/WhatsApp-Nodejs-SDK/api-reference/messages/text/).

## Readiness, schemas and journey measurements

`/api/health` checks liveness/version only; `/api/ready` actually opens both stores, validates/migrates supported schemas and prunes expired records. Readiness does not call Gemini or certify external availability. Startup runs these storage checks before serving. Cleanup retries storage failures with a fixed safe warning. Schema versions are explicit (accounts 2, onboarding 1); legacy versions migrate transactionally, while unknown future versions or wrong-store databases fail without silently resetting their version. Do not point both store settings at the same file. Independent record mutations use SQLite write transactions, so two store instances cannot both claim an unowned record. Raw extraction cache still requires one worker. SQLite references: [transactions](https://www.sqlite.org/lang_transaction.html), [user_version](https://www.sqlite.org/pragma.html#pragma_user_version).

Reviewer metrics now separate retry-inclusive 30-day counters from unique currently retained consented journeys. The latter show first occurrence of four extracted documents, check attempts, checks passed, help requests and demo orders, with median/p95 durations from document consent. Deleted/expired records leave this maximum-24-hour cohort. A passed-ever count can include subsequently replaced evidence; it does not imply current checkout approval. Historical records without stage markers are not assigned guessed times. These are not acquisition conversion or measured cost savings.

The extraction evaluator reports accuracy conditional on successfully assessed fields separately from end-to-end accuracy over all selected labelled fields. Failed requests lower end-to-end accuracy rather than disappearing from its denominator. It also records successful-document count and median/p95 request time, rejects duplicate/invalid labels before sending any request and defaults to four images per explicit run.

## Submission rehearsal and repeatable cross-checks

```powershell
python scripts/verify_all.py
python scripts/record_demo.py
```

The first rebuilds frontend and submission artifacts/source package, runs backend and isolated browser checks, and writes actual outcomes to `submission/verification-report.json`. The second produces a captioned, controlled rehearsal under three minutes using temporary synthetic stores and fixtures, with no provider calls. The native-text PowerPoint/PDF uses the supplied branding; a separate privacy PDF is checked to fit one page. See `submission/README.md` for review gates. The source ZIP deliberately excludes credentials, runtime records, backups, learning notes and caches; publishing the reviewed repository is a separate action.

## Containers, backup and rollback

Dockerfile and Compose prepare a non-root, single-worker local container, a private named volume, read-only root filesystem and loopback-only port. Start Docker Desktop before building; these image builds need package-network access:

```powershell
docker compose config --quiet
docker compose build
docker compose up -d
docker compose logs --tail 30
```

Configuration validation passed locally, but Docker's engine was unavailable, so image build/runtime are unverified. The CI workflow is authored and its constituent local checks run; it has not run on GitHub. No deployment or infrastructure spending occurred. Configure HTTPS, secure cookies (`UDYAM_SECURE_COOKIES=1`), allowed hosts, proxy-origin handling, encrypted managed storage, shared sessions/limits and operational monitoring before public exposure. Do not treat the local container as a public deployment template.

For local backups, stop the server first. These commands create a private snapshot and restore into an empty directory; they never overwrite existing runtime databases:

```powershell
python scripts/backup_runtime.py backup --directory artifacts/private-backup --server-stopped
python scripts/backup_runtime.py restore --directory artifacts/private-backup --runtime artifacts/restored-runtime --server-stopped
```

Restore clears sessions and prunes expired records/accounts. Extracted raw fields cannot be restored because they were never written to disk. Protect backup folders, keep them out of Git and folder sharing, and delete them under an explicit retention policy; deleting an app record cannot erase a separate backup. Restore behavior was tested on temporary synthetic databases. For rollback, stop the new version, retain a private snapshot, restore compatible code and databases together in a separate empty runtime directory, and verify health/access before resuming. Never restore over a running server. Cross-version/production rollback still requires a tested migration strategy.

Implementation references: [cryptography Argon2id PHC APIs](https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#argon2id). Persistent schema initialization is additive; incompatible future schemas need explicit migrations. Payment, service availability and activation remain simulated.
