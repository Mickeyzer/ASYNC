# Udyam Digital milestone plan

Updated 2026-11-05. This is the implementation roadmap; planned capabilities below are not claims of completed work. The user requested that stretch goals be included before submission. Submission deadline, team capacity, hosting target and external-service access are not yet specified, so this plan sets dependencies and completion checks rather than calendar promises.

## Current position

Frontend overhaul (0.7.0): visible registration/sign-in, accessible account dialogs, inline registration that preserves the chosen estimate, clearer grouped discovery and estimate actions, document upload progress/drag-and-drop, contextual recovery and responsive Hindi/English screens. Existing backend rules are retained. See [FRONTEND.md](FRONTEND.md) and the latest verification report for actual check results.

Implementation update: the account/role and request-limit foundation, partner handoff/review dashboard, operational help ranking, synthetic lead evidence and reviewed Hindi/English browser voice input are now built. Live image/microphone quality remains unverified. Acquisition-time rules failed the held-out ranking comparison, so they are not used for sales prioritization. The WhatsApp contract is tested offline only. Container/CI/backup configuration is prepared; local restore is tested, but the Docker engine was unavailable and hosted CI/deployment have not run. Detailed instructions and limitations: [OPERATIONS.md](OPERATIONS.md). The scope descriptions below remain completion targets, not claims that every milestone gate has passed.

| Milestone | Status | Result |
| --- | --- | --- |
| 1. Advisor, bundles and estimate | Implemented; user confirmed it works | English/Hindi discovery, catalogue rules, editable bundle and server-priced estimate |
| 2. Documents, demo checkout and tracker | Implemented; live image extraction still needs verification | Consented extraction, mock registry/document checks, private recovery and simulated order stages |

Latest actual check counts are recorded in `submission/verification-report.json`. Checks include backend, TypeScript/Vite, isolated core/onboarding/operations browsers, source-package privacy boundaries and submission page/package constraints. Onboarding browser checks use controlled extraction responses. Successful text generation does not establish live image extraction quality. All supplied images decode; live OCR accuracy remains unmeasured.

Previous implementation update (0.6.0): transactional migrations/readiness and unique retained-journey metrics are followed by reviewed multi-turn advisor context, Hindi account/operations messages, password changes, device-session revocation and local staff disabling. WhatsApp now has a signed receiver, encrypted temporary guided state, bilingual consent/corrections/STOP, backend estimates, public web handoff and a separately gated outbound transport. Local checks mock both providers; live receiving/sending remain disabled and unverified. The submission deck, diagram, privacy note, source archive and explicitly controlled rehearsal describe these features. Final live-provider recording, repository publication and external deployment/provider checks remain separate gates.

## 3. Reliable KYC and account access

Build customer sign-in and server-side ownership checks, with separate reviewer and partner permissions. Plan recovery-code migration explicitly: existing records remain private and can be claimed only by an authenticated owner presenting their valid recovery code; an identifier alone cannot claim a record. Partners see assigned leads; reviewers access only their authorized queue.

Verify live image extraction from a network-enabled terminal using synthetic documents. Record field accuracy, unreadable/missing fields, validation outcomes, latency and provider failure categories against independently reviewed student-visible documents. Keep a small unseen subset for checking later changes; do not consult the judges-only pack. Fix the failures found before calling extraction reliable.

Bound provider concurrency and requests per account/source, cap retries and preserve a recoverable flow after timeouts. Maintain consent, masking, retention and deletion when adding accounts. Select a maintained authentication solution during implementation rather than inventing password or token cryptography.

**Complete when:** two customers cannot read, change, claim or delete each other's records; partner/reviewer restrictions pass negative checks; live extraction results and remaining limits are recorded; provider failures and limits produce useful recovery messages. This execution environment cannot perform the live-provider check, so its result must remain explicitly pending until a normal-terminal run supplies evidence.

## 4. Partner dashboard and human review

This includes the back-office stretch goal. Show consented unfinished journeys, the stage reached, reason for stalling, last activity, assigned partner and next action. Capture a contact method only when the owner explicitly requests follow-up; anonymous browsing is not a contactable sales lead. Provide owner-requested handoff, assignment and a recorded resolution. Notifications to real people require an authorized channel and explicit sending scope.

Add a document-review queue with reason codes and a decision history recording actor, time, evidence revision and reason. Reviewers can request replacement evidence and resolve permitted ambiguities under a defined policy. Known inactive registrations, expired required documents and failed eligibility rules cannot be bypassed by a generic approval button. Changed evidence invalidates an earlier decision. Existing raw-field expiry and image non-storage remain in force; expired evidence must be resubmitted unless a separately designed, consented retention change is agreed.

**Complete when:** a stalled owner journey can be handed to an authorized partner, corrected and resumed; unauthorized partners cannot inspect it; document replacement invalidates decisions; every review decision is attributable and known failures still block checkout.

## 5. Explainable lead prioritization and business evidence

This includes the propensity-score stretch goal. Start with an explicit rules-based call-priority score and visible reasons. Describe it as a ranking, not a probability of conversion. Keep eligibility decisions separate: low sales priority never removes customer access or changes service eligibility.

Analyze the 5,000 supplied synthetic leads to select initial segments and bundles and to support the business case. If adding a learned probability model, compare it with the simple ranking on a held-out split before choosing it. Use only information available at the stated contact/decision time. Later funnel outcomes, activation dates, purchased bundles and churn must not leak into predictors. Report small-sample limits and historical associations without claiming causal improvement or real-world uplift.

Instrument minimal stage events, with purpose and retention documented, to measure journey completion, time to quote, document-check completion/time, handoff rate and provider failure rate. Distinguish local demo observations, synthetic historical baselines and proposed pilot targets. Do not invent acquisition cost savings from demo events.

**Complete when:** the dashboard ranks leads with intelligible reasons; the analysis is reproducible; predictors are reviewed for leakage; evaluation states its baseline and limitations; business-case claims link to measured or clearly labelled assumed values.

## 6. Voice and language experience

This includes the voice stretch goal. Add explicit microphone consent and Hindi/English voice input to the existing advisor. Show an editable transcript and require owner confirmation before using it as business facts. Keep guided and typed input available after denied permission, poor transcription or unsupported devices. Voice output is a later enhancement if the input journey is reliable.

Choose browser or provider speech tools after checking actual language/device support and privacy behavior. Document where audio is processed and retained; do not assume browser speech is offline. Test Hindi/English speech, mixed-language phrases, business quantities, noisy input, cancellation and error recovery. Never accept a quote, verify identity or submit an order on an unconfirmed transcript.

**Complete when:** voice can populate a reviewed draft on the supported test devices, and microphone/transcription failures leave a usable typed journey. Measured language coverage and limitations are documented.

## 7. WhatsApp channel, gated by account access

The brief allows voice or WhatsApp. Voice is the committed channel stretch in this roadmap; WhatsApp is included as an additional extension whose live completion depends on approved account/sandbox access and sufficient time. Prepare the channel adapter contract and test it with clearly labelled fixtures first. Use the same backend rules and owner-confirmation steps, validate webhook signatures, handle duplicate events and bind channel identity securely before exposing a saved record.

Keep document uploads and sensitive actions in the authenticated web flow initially. Define channel consent and message retention. Choose the provider and verify its current setup requirements before integration. Credentials, external account configuration and real outbound messages require the appropriate user authorization. Without access, report the adapter as locally tested and the live channel as pending; never present a fixture as a live integration.

**Complete when:** a supported sandbox conversation produces a reviewed web handoff, duplicate events are harmless, webhook authentication is checked and cross-customer access is blocked. If account access is unavailable, preserve this as a documented follow-on and proceed with the working voice stretch.

## 8. Deployment readiness and final quality checks

Implement deployment controls alongside earlier milestones; finish their verification here. Prepare a reproducible container/build, automated meaningful checks, health checks, database migrations, secret configuration, safe diagnostics and rollback instructions. Choose managed database/auth/storage services only when the hosting target is known; require encrypted transport/storage before real customer data. Test restore on synthetic data and ensure retention/deletion behavior includes backups and connected services in its documented limits.

Measure end-to-end duration and bounded concurrent use, verify mobile Hindi/English and interrupted journeys, and rehearse one clean success and one exception/handoff. Keep real payments, address availability and provisioning explicitly simulated. Automated request checks are not a production security certification.

**Complete when:** a clean setup can reproduce the journey, role/retention checks pass in the intended deployment configuration, restart/recovery and rollback are demonstrated, and the known-limits list matches the application. Preparing configuration does not publish a site or authorize infrastructure spending; deployment approval comes after the concrete configuration is reviewable.

## 9. Submission and judging

Prepare the code repository, architecture/data-flow diagram, business case of at most 10 slides, one-page privacy/security note and video of at most 3 minutes. Cover target segments, bundle value, partner role, rollout, risks and 3-5 business metrics with clearly labelled targets. Show the required advisor-to-tracker flow first, then the most useful stretch behavior. Rehearse from a clean setup and verify every submitted claim, link and file. Publishing/submitting is a separate external action.

**Complete when:** someone can reproduce the documented demo and the deliverables meet the brief's limits. Practice explanations of decisions, measured results, failures and simulated integrations before judging.

## After submission: controlled pilot

Invite a small tester group using synthetic data first, evaluate abandonment/errors and update priorities from observations. Real documents, government verification, payments and telecom activation require authorized providers, operational support, security review and appropriate data arrangements before use. Production readiness is established by those controls and operating evidence, not by the feature count.

## Recommended priorities

1. Preserve the working advisor-to-order journey while adding each stretch goal. Access controls precede dashboard exposure.
2. Prioritize partner handoff and measured extraction quality: they resolve actual incomplete journeys and demonstrate business value.
3. Start lead ranking with transparent rules; add a model only if its held-out performance justifies the extra complexity.
4. Build voice before pursuing a second external messaging channel. If time becomes limited, retain milestones 3-5, the tested core and required deliverables first; voice follows and WhatsApp stays access-gated.
5. Measure results early, not only when writing slides. Separate observed results, synthetic-data analysis and projected improvements.

This update authorizes the roadmap changes, not an unrequested deployment, service purchase or external message. No future milestone is marked implemented by adding it to this plan.
