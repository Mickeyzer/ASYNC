# Teammate checklist: testing, fixes and submission

The job is to validate the existing v0.7.0 application, fix confirmed problems and prepare the final hackathon submission. Work through the priorities below. Record actual outcomes; an automated fixture passing does not prove live Gemini or microphone quality.

## 1. Get a clean, reproducible setup

- [ ] Accept Ishan's invitation to the private [Mickeyzer/ASYNC repository](https://github.com/Mickeyzer/ASYNC).
- [ ] Clone the latest `main` and follow the [README prerequisites and setup](../README.md). Use Python 3.12, Node 22/npm and your own `.env` configuration. No account database or live API key is shared through Git.
- [ ] Confirm a new checkout starts at http://127.0.0.1:8010 and `/api/health` reports 0.7.0. `/api/ready` should report ready; it does not test Gemini.
- [ ] Make a working branch, for example `qa/acceptance`. Record the commit, OS, browser and device used for each test session.
- [ ] Install test dependencies and run the complete local checks:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe scripts/verify_all.py
```

The runner builds the frontend/submission/source package and runs backend plus isolated browser checks. Review `submission/verification-report.json` and the ignored logs in `artifacts/verification/`. The last complete local baseline was **157 backend tests and 77 browser scenario groups**; compare actual results rather than assuming those counts prove the new environment works.

- [ ] Check the latest commit in [GitHub Actions](https://github.com/Mickeyzer/ASYNC/actions). The first push exposed missing Linux native dependencies; commit `396b648` repaired the lockfile without upgrading existing package versions. Judge the latest run, not the original failed run.

## 2. Test every product flow

Create two customer accounts through the UI. In separate browser profiles, use a reviewer and two different partners so positive and negative access tests are possible:

```powershell
.\.venv\Scripts\python.exe scripts/manage_accounts.py reviewer_demo --role reviewer
.\.venv\Scripts\python.exe scripts/manage_accounts.py partner_one --role partner
.\.venv\Scripts\python.exe scripts/manage_accounts.py partner_two --role partner
```

These commands prompt privately for passwords. Customer registration must never grant staff privileges.

| Area | Test | Passing behavior |
| --- | --- | --- |
| Registration | Create account, duplicate/invalid username, short or mismatched passwords, show/hide, existing-user sign-in, wrong password, sign-out | Clear feedback; invalid registration fails; credentials are not displayed or logged; successful creation returns to the current task |
| Registration during a journey | Select a bundle while anonymous, continue to documents, then register/sign in | Selected services and quantities remain; document processing still needs its separate consent |
| Guided discovery | Shop, clinic/office and manufacturer; different team/site counts, tiers, budgets, needs and registration claims | Required/bounded inputs checked; at least one need required; unknown facts are not guessed |
| Advisor | English/Hindi description, missing information, follow-up answer, manual correction, retry/failure and clear conversation | Review required before follow-up; prior reviewed facts retained; failed requests keep editable answers and retry text |
| Service selection | Add/remove products, edit quantities, missing companion service, conditional/ineligible product and low budget | Backend totals/conditions control the result; unmet needs and budget excess visible; ineligible products do not become orderable |
| Price cross-check | Tier-1 clinic, five staff, one location; one P01 fibre and five P16 email units | INR 1,624 monthly, INR 0 setup, INR 1,624 first-month estimate; 12-month terms for those services; taxes excluded |
| Document consent/upload | No consent, four slots, drag/drop, wrong type, multiple files, >5 MB, unreadable image, replacement | No extraction without consent; invalid uploads rejected; progress shown; replacement invalidates prior approval |
| Extraction review | Compare each displayed field with its original image, including missing values and masked identifiers | No invented values; usable correction/retry path; full identifiers are not exposed in the page |
| Document decisions | Missing document/identifier, inactive registration, expiry, old bill, mismatched names/addresses, ambiguous text | Appropriate action/review reason; checkout blocked for unresolved failures; reviewers cannot override hard failures |
| Checkout | Valid evidence, changed declaration, acceptance boxes, repeated submit | Fresh checks and explicit terms/simulation acceptance required; one order reference on repeated submission |
| Tracker/recovery | Refresh, sign out/in, reopen account record, restart backend, wrong legacy recovery code | Saved owned records recover until expiry; wrong/other-owner access denied; simulated stages advance consistently |
| Customer privacy | Second customer tries another record, even with its recovery code; delete record/account | No access to another owner's data; deleted records cannot be reopened |
| Account security | Normal plus incognito sessions; revoke one/others; wrong current password; password change; old password | Revoked sessions fail; password change keeps one fresh session and invalidates all old sessions/password |
| Partner handoff | Request help with separate synthetic-contact consent; assign partner one; inspect with partner two; resolve; withdraw | Only assigned partner sees the consented summary/contact; resolution works; withdrawal removes contact/partner access; no automatic contact message |
| Reviewer workflow | Replacement request, legibility-only review, original-source attestation, stale decision after a document changes | Actor/reason/revision recorded; no expired/stale decision or hard-failure override; inspect original synthetic documents before attesting |
| Staff disabling | Disable a disposable partner account while signed in | Existing sessions stop working; sign-in fails; disabled partner disappears from assignment choices; active reviewer can reassign tasks |
| Metrics/evidence | Repeat a check, create/delete a record, inspect role-restricted metrics, reasons and historical data | Retries differ from unique journeys; denominators reflect retained records; operational priority is not a purchase probability; synthetic history is not product uplift |
| Failure recovery | Missing/unavailable provider, interrupted request, restart and expired raw fields | Honest error/fallback, no guessed fields, no accidental order, preserved recoverable state and re-upload when needed |
| Hindi/mobile/keyboard | English/Hindi; 320/390-pixel mobile, tablet and desktop; Tab/Shift+Tab, Escape, modal language control, long text | No horizontal clipping or lost actions; readable errors; focus stays in dialogs and returns on close; typed path remains usable |

To disable the disposable partner:

```powershell
.\.venv\Scripts\python.exe scripts/manage_accounts.py partner_one --disable
```

Use automated tests for eight-hour sessions, 24-hour records, 30-day accounts, schema guards and races instead of editing a live database or waiting days. If changing tests, use temporary stores. Extracted raw fields expire after 30 minutes or submission; a restart loses raw memory. Dates in document validation use the fixed dataset date **15 July 2026**, not today's calendar.

## 3. Complete the live checks that fixtures cannot establish

### Gemini image extraction

- [ ] Inspect the student-visible synthetic images independently. Never use a judges-only answer pack as expected values.
- [ ] Cover each available applicant group `K01` through `K12`, keeping documents from one applicant together. Missing documents and deliberate defects are valid negative cases; all applicants are not expected to pass.
- [ ] Label visible values before running extraction; record confirmed absence as null, and omit fields not assessed. Do not alter reference labels just to agree with a model response.
- [ ] Start with a small explicit batch, review quota/budget and results, then expand coverage. Use the existing evaluator:

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_kyc.py --prepare
# Independently fill expected values in artifacts/kyc-labels.json first.
.\.venv\Scripts\python.exe scripts/evaluate_kyc.py --labels artifacts/kyc-labels.json --limit 4 --consent
```

- [ ] Compare successful-field accuracy with end-to-end accuracy, failed-request count and median/p95 latency. A provider timeout is not a correct extraction. Keep private label/result files out of Git.
- [ ] Cross-check an expected failure: K01 has an inactive GSTIN and a blank Udyam number; it should require action. This known manual check is not a live OCR score.
- [ ] Independently validate a live extraction and checkout path using the separately labelled `demo_documents/checkout/DEMO01_*.png` fixtures. All ten supplied Udyam specimens with readable identifiers have registration dates differing from their mock registry entries; K01 has a blank identifier and K05 lacks the certificate. None is an unchanged passing set under the current rules. Original files/rules remain intact. Do not count success on DEMO01 as success on K01-K12 or as broad OCR accuracy evidence. A text-advisor success alone does not establish image extraction quality.

### Real voice and language

- [ ] Use an actual microphone in a supported browser/device; automated tests use simulated speech recognition.
- [ ] Try English, Hindi and mixed-language descriptions, quiet/noisy conditions, team/site counts and budgets. Include potentially confused numbers such as 5/50 and 3,000/30,000.
- [ ] Record the original phrase, transcript mistakes, manual corrections and device/browser. Numbers must be reviewed before they populate confirmed business facts.
- [ ] Deny permission, cancel recording, switch language and try an unsupported device. Typed input must remain usable; voice and Gemini retain separate consents.

## 4. Fix confirmed issues and check reproducibility

- [ ] File reproducible issues and fix the highest-impact failures first: unauthorized data access, incorrect prices/order approvals, duplicate orders, unusable registration or blocked core journeys. Then fix extraction/error handling and mobile/language defects. Cosmetic changes come after blockers.
- [ ] Use small branches/PRs with steps, before/after behavior and relevant checks. Do not weaken a failing eligibility, consent or privacy test simply to make the suite green.
- [ ] Run the affected checks after each fix, then the full runner before handing back a submission candidate. Check the current GitHub Actions result after pushing.
- [ ] Verify a fresh clone on another machine. Document any environment-specific setup missing from the README.
- [ ] If Docker Desktop is available, stop the normal server to free port 8010, then verify build, startup, readiness, the app flow, persistence and clean shutdown:

```powershell
docker compose config --quiet
docker compose build
docker compose up -d
docker compose logs --tail 30
# Test the application, including /api/ready, then:
docker compose down
```

- [ ] Verify backup/restore on disposable synthetic data, using [operations instructions](OPERATIONS.md). Stop the server first; restore into an empty directory. Sessions and queued channel state must not be resurrected. Keep backups private.

Docker runtime and live provider/device quality need actual operating evidence. A local prototype is not production-ready merely because all listed features exist. Keep real payments, government verification, availability and telecom activation outside this hackathon demo unless separately designed and authorized.

## 5. WhatsApp is conditional work

Voice already provides the main additional channel. Test live WhatsApp only when the team has an approved account/sandbox, required credentials, recipient authorization and an agreed live-test scope. Otherwise report the adapter as tested offline and leave its switches off.

When approved, follow [WhatsApp operations](OPERATIONS.md#whatsapp-status): verify signed ingress/receiver, START consent, both languages, valid/invalid answers, EDIT, CONFIRM estimate, HELP, RESTART, STOP, duplicate events, timeout/no-blind-resend, expiry and public web handoff. Confirm handset delivery separately from provider acceptance. Phone identity must never reveal private records or permit checkout; those remain authenticated web actions.

## 6. Finish the submission materials

- [ ] Review the supplied hackathon brief/template for team details, deadline, required links and file formats; do not infer the deadline from the synthetic dataset date.
- [ ] Update the business-case deck after confirmed fixes/evaluation. Keep it at **7 slides including the cover**, following the Unstop listing, with competitive analysis, reproducible synthetic baselines and clearly labelled proposed targets. No unsupported conversion/CAC uplift or production claims.
- [ ] Check architecture/data flow, partner role, privacy/retention, consent, simulations and limitations against the actual final code. Keep the privacy/security PDF to **one page**.
- [ ] Record the final **three-minute maximum** demonstration: registration/discovery, a reviewed estimate, genuine document extraction/checks, simulated checkout/tracker and a brief exception/handoff. Show only tested optional channels.
- [ ] The existing `demo-rehearsal.webm` is explicitly controlled fixtures, not a live-provider result. A final recording should distinguish live requests, any fixtures, cuts and elapsed processing times honestly.
- [ ] Add the private repository URL and required reviewer access according to the organizers' instructions. Confirm it can be cloned by the intended reviewer; do not make the repository public without the team's decision.
- [ ] Rebuild/review final artifacts, reopen the PowerPoint/PDF/video in their intended viewers, and prepare one clean submission folder without keys, runtime stores, private labels, backups or caches.
- [ ] Have both teammates review the final package before the actual submission. Preparation does not itself mean the project has been submitted.

## What to return to Ishan

1. A pass/fail/blocked matrix for every feature row, with commit, machine/browser, expected/actual behavior and evidence.
2. A prioritized bug list and fix PRs, with retest results; record remaining limitations separately from defects.
3. Live extraction evaluation and microphone/language observations, including errors and latency; keep raw private labels/results locally.
4. Reproducibility evidence: fresh setup, latest CI, Docker/restore result or an explicit blocker.
5. Final reviewed deck, architecture, one-page privacy note, <=3-minute video, repository link and a submission-ready folder.

Use this bug-report format; omit passwords, API keys, recovery codes and raw private fields:

```text
Feature / test ID:
Commit / OS / browser / device:
Steps and synthetic applicant filename(s):
Expected:
Actual:
Pass / fail / blocked:
Impact / severity:
Sanitized screenshot or safe error category / elapsed time:
Fix PR / retest result:
```

Acceptance: clean setup works, the latest automated checks pass, the core success and expected-failure journeys are demonstrated, no unresolved access/pricing/approval blocker remains, and every live/submission claim has supporting evidence. Missing external access is reported as blocked, never as passed.
