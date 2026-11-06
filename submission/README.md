# Udyam Digital submission draft

This folder contains reviewable local deliverables for Enterprise Track A. Draft files are shared in the private repository; nothing has been submitted to the competition. The current deck has seven slides including the cover, following the Unstop listing. Submit PDF and PowerPoint with the registered TeamName_CampusName filename. See docs/SUBMISSION_SOURCES.md for rules and competitive-analysis sources.

| Artifact | Status |
| --- | --- |
| Udyam_Digital_Business_Case_7_Slides.pptx / .pdf | 7 slides including cover, supplied branding, editable PowerPoint text; source numbers independently checked |
| Architecture.pdf / architecture.svg | One-page component/data-flow diagram |
| Privacy_and_Security.pdf | Checked to be one page; describes implemented choices and limits |
| demo-rehearsal.webm / demo-player.html | Captioned controlled rehearsal, under three minutes; zero live-provider calls |
| Udyam_Digital_Source.zip | Clean source/student-data archive for repository preparation; private/runtime material excluded |
| verification-report.json | Actual local check results; external gates separately listed |

The older Udyam_Digital_Business_Case.pptx/.pdf files are superseded ten-slide drafts. Use the files with _7_Slides in the name for the current presentation.

The video explicitly uses controlled advisor/extraction fixtures. It demonstrates the application workflow and real deterministic backend gates, not live Gemini accuracy or production activation. It is a rehearsal. Record the final live-provider demo after image/voice validation, retaining the simulation labels. The deck labels rollout targets and scenario savings as proposals rather than achieved results. Synthetic historical observations do not establish product uplift.

The redesigned React frontend adds visible registration, guided account fields, keyboard-accessible dialogs and a clearer document journey. See docs/FRONTEND.md in the source archive. The current draft also covers reviewed follow-up chat, Hindi operations, password/session controls and local staff revocation. WhatsApp guided replies and the outbound adapter are tested with mocked transport, remain disabled by default, and have no live delivery evidence. They require separate account setup; no phone identity bypasses web sign-in. See docs/OPERATIONS.md in the source archive for the exact limits.

Reproduce locally with Python/Node dependencies and Playwright Chromium installed:

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/verify_all.py
python scripts/record_demo.py
```

The check runner builds the frontend, PDFs/deck and clean source archive before running backend and isolated browser checks. Raw logs stay in ignored `artifacts/verification/`. `record_demo.py` uses temporary stores and a temporary server; it does not touch a user's running server or call Gemini.

Before actual submission: review the PowerPoint in the intended viewer; confirm the template/team requirements with the organizer; validate live extraction and supported microphone/language combinations; record the final <=3-minute demo; publish the reviewed source to the chosen repository and add its URL. Account/sandbox access is needed for live WhatsApp. Docker/hosted-CI checks still need their appropriate environments. Public deployment, real payment and provisioning are not included in the current evidence.

The source archive deliberately contains sources and the two submission text guides, not generated videos/PDFs or private labels. Rebuild the artifacts after extracting it. Keep runtime stores, credentials, downloaded recovery files, independent labels, backups and learning notes out of the public repository.
