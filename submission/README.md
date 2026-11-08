# Udyam Digital submission

The upload-ready files are in [final/](final/README.md): **Spicers_TIET.pdf** and **Spicers_TIET.pptx**, with seven slides including the cover. The cover names Ishan Bhat and Gaurav Prakash Srivastava and includes clickable [recorded demo](https://youtu.be/VdtKxBKpCHQ) and [source repository](https://github.com/Mickeyzer/ASYNC) links. Each file is checked against the user-reported 20 MB limit. Nothing has been submitted to the competition. See docs/SUBMISSION_SOURCES.md for rules and competitive-analysis sources.

| Artifact | Status |
| --- | --- |
| Udyam_Digital_Business_Case_7_Slides.pptx / .pdf | 7 slides including cover, supplied branding, editable PowerPoint text; source numbers independently checked |
| Architecture.pdf / architecture.svg / architecture-preview.png | Detailed one-page diagram of the implemented web flow, backend authority, browser voice, Gemini boundary and local data retention |
| Privacy_and_Security.pdf | Checked to be one page; describes implemented choices and limits |
| demo-rehearsal.webm / demo-player.html | Captioned controlled rehearsal, under three minutes; zero live-provider calls |
| Udyam_Digital_Source.zip | Clean source/student-data archive for repository preparation; private/runtime material excluded |
| verification-report.json | Actual local check results; external gates separately listed |

The older Udyam_Digital_Business_Case.pptx/.pdf files are superseded ten-slide drafts. Use the files with _7_Slides in the name for the current presentation.

The architecture diagram covers the web flow shown in the recording. It distinguishes browser speech from Gemini, and Gemini drafts/extracted fields from authoritative backend decisions. WhatsApp is omitted from this diagram because live messaging is disabled and outside the recorded flow. Additional staff web tools are mentioned only as a scope note. Regenerate just the SVG, PDF and PNG with `python scripts/architecture_diagram.py`; the full submission builder uses the same renderer.

The final team-recorded video is https://youtu.be/VdtKxBKpCHQ. It is distinct from demo-rehearsal.webm, which uses controlled advisor/extraction fixtures and demonstrates workflow and deterministic backend gates. The supplied video's title is accessible; automated playback inspection is blocked by YouTube's sign-in check. No independent playback, duration or provider-quality result is claimed. The brief's video cap is three minutes. The team reports completing the manual flow and recording. The deck labels rollout targets and scenario savings as proposals rather than achieved results. Synthetic historical observations do not establish product uplift.

The redesigned React frontend adds visible registration, guided account fields, keyboard-accessible dialogs and a clearer document journey. See docs/FRONTEND.md in the source archive. The current draft also covers reviewed follow-up chat, Hindi operations, password/session controls and local staff revocation. WhatsApp guided replies and the outbound adapter are tested with mocked transport, remain disabled by default, and have no live delivery evidence. They require separate account setup; no phone identity bypasses web sign-in. See docs/OPERATIONS.md in the source archive for the exact limits.

Reproduce locally with Python/Node dependencies and Playwright Chromium installed:

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
python scripts/verify_all.py
python scripts/record_demo.py
```

The check runner builds the frontend, PDFs/deck and clean source archive before running backend and isolated browser checks. Raw logs stay in ignored `artifacts/verification/`. `record_demo.py` uses temporary stores and a temporary server; it does not touch a user's running server or call Gemini.

Before actual submission: review the PowerPoint in the intended viewer, check the logged-in submission round and arrange judge access to the private repository and video. The user submits personally and retains confirmation. Hosted CI results are available in the repository's Actions tab; check the run for the latest pushed commit. Docker, broader live extraction/microphone evaluation and production integrations remain separate rollout gates. Account/sandbox setup is needed for live WhatsApp, which is disabled and outside the recorded web flow. Public deployment, real payment and provisioning are not included in the current evidence.

The source archive deliberately contains sources and the two submission text guides, not generated videos/PDFs or private labels. Rebuild the artifacts after extracting it. Keep runtime stores, credentials, downloaded recovery files, independent labels, backups and learning notes out of the public repository.
