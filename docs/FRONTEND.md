# Frontend and registration

The React/TypeScript interface uses a consistent application workspace: a compact header, a progress rail, grouped business questions, a service-selection area with an itemized estimate, and a focused document journey. The visual system uses a neutral surface, clear typography, restrained red actions, readable supporting text and shared controls. Fonts and icons are local; no remote font service or new UI dependency is required.

## Account creation

The header has a visible **Create account** button and a separate **Sign in** action. Exploring services remains anonymous. Registration asks for a username, a password of at least 12 characters and password confirmation. Guidance appears beside the fields; password visibility is optional. Invalid usernames and mismatched passwords are caught before submission. Backend authentication remains authoritative.

Successful registration closes the dialog and confirms that the account is ready. The selected bundle and entered business details remain in place. Starting document checks while signed out presents registration directly, with a sign-in alternative for existing customers. The header and inline forms use distinct accessible IDs.

The account dialog groups saved checks/orders separately from password/session controls and account deletion. Sign-out is available inside the dialog on mobile. A language selector remains available while a modal is open. Keyboard focus stays inside the dialog, Escape closes it, and focus returns to its trigger or the account button. Native modal behavior prevents interacting with the background.

## Discovery and service selection

Business details, current setup and selected needs have distinct sections. The optional advisor can draft the same editable fields. Voice is an expandable option beside typed input, with its separate consent and reviewed transcript. Neither the redesign nor registration changes eligibility, price calculations or verification requirements.

The estimate groups monthly costs, setup fees, first-month totals, contracts and unmet conditions. **Continue to document checks** is the primary action after reviewing an estimate; downloading it remains secondary. Staff have section shortcuts for their queue and authorized measurement/evidence/channel panels.

The progress rail is the journey navigation. Click an available step to return to it; keyboard users can Tab to its button and press Enter or Space. Dedicated journey back buttons are removed. Future steps remain disabled until their requirements are met. Returning without edits preserves the customized bundle, reviewed estimate, uploaded fields and draft declarations. Editing business details or the bundle invalidates later checks and requires a new document-consent flow. Existing saved orders remain unchanged. After submission, the Documents step shows a read-only masked summary, and Track reopens the same order. On mobile, the same navigation appears above the content. Staff shortcuts also wait for asynchronously loaded panels before opening them.

## Documents and recovery

Before uploads, concise statements explain provider processing, retention and authorized review, with the full notice available before consent. Four upload slots accept browse or drag-and-drop, display reading progress, and count added documents. Unsupported/multiple files are rejected. The extracted-detail confirmation form appears after the first extraction. Missing or invalid evidence still blocks submission.

Saved checks are easiest to reopen from the account dialog. Private recovery-code entry is kept under **Have an older recovery code?** rather than competing with a new document journey. Retention and simulation rules remain unchanged.

## Reproduce visual and interaction checks

```powershell
npm.cmd run build --prefix frontend
python tests/browser_design_check.py
```

This uses a temporary local server and temporary databases, makes no live provider calls and produces screenshots in ignored `artifacts/`. It checks registration errors, password visibility, keyboard/modal behavior, state preservation, account recovery, upload rejection and a 320-pixel Hindi layout. The complete runner is `python scripts/verify_all.py`; it includes the existing discovery, document, voice, security and staff checks. Automated checks and inspected screenshots do not replace live microphone/extraction testing or a full accessibility audit.
