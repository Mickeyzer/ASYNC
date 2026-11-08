# Final demo narration: account, languages, voice and checkout

Target 2:55; the final recording must be at most three minutes. Record actual application/provider results. Keep simulation labels visible. Label processing cuts and their actual elapsed time. DEMO01 documents are separately created synthetic development fixtures, not the organizer's original specimens.

Prepare: clinic, Tier 1, five employees, one site, INR 3,000 budget, hotspot, GSTIN available, internet and email. Start signed out with a fresh synthetic username and keep passwords masked. Open `demo_documents/checkout/` in the file picker. Check microphone permissions before the take.

## 0:00-0:15 | Introduce the journey

Screen: discovery page and the steps in the left column.

> This is Udyam Digital, our digital onboarding solution for Accel Business. It helps small-business owners choose services and complete their onboarding in one place. I'll walk through it using a clinic, from describing its needs to creating a tracked demo order.

## 0:15-0:35 | Create an account

Screen: click Create account, enter a synthetic username, password and confirmation, then register. Keep passwords masked; show the success notification.

> I'll create an account first, so my document checks and orders are saved together. Registration needs a username and password, with confirmation. Owners can explore bundles before registering, but signing in is required before they submit documents.

## 0:35-1:10 | Languages, voice and reviewed answers

Screen: switch to Hindi and back to English before starting voice, since changing language cancels recognition. Open advisor and voice controls; give speech consent and microphone permission. Speak the short example below, stop, review/edit the actual transcript and use it as the description. Separately consent to Gemini drafting, generate answers, review them, and select Tier 1/current internet hotspot if not filled. Keep sites at one and GSTIN available.

Voice example to speak into the microphone; pause narration while saying it:

`I run a clinic with five employees. We need internet and business email, within three thousand rupees monthly.`

> The interface works in English and Hindi. I can type, answer the guided questions, or describe my business by voice. After giving microphone consent, I review the transcript before sending it to Gemini. The advisor drafts answers that I can check and correct before continuing.

## 1:10-1:35 | Backend recommendations and editable pricing

Screen: generate bundle, change email seats to six then restore five, review estimate. Briefly click a completed sidebar step and return if timing permits.

> The backend selects services from the catalogue using those reviewed answers. Here, broadband and five email accounts cost 1,624 rupees monthly. I can adjust quantities or return to earlier steps from the sidebar. Setup is zero, taxes are excluded, and each service has a twelve-month minimum contract.

## 1:35-2:10 | Document consent, extraction and validation

Screen: show document notice and consent. Upload all four DEMO01 images into matching slots, review the actual fields and masked identifiers, then confirm Harmony Dental Care, Joseph Shah and the address printed on the images. Click Check documents and show its result.

> Next, I give separate permission for document processing. I'm using separately created synthetic test documents, labelled DEMO01. Gemini reads the fields, and I review them against the documents. The backend checks registration details, dates and consistency against the mock registries. The app doesn't save the images, and identifiers are masked in the interface.

## 2:10-2:35 | Checkout, saved records and tracker

Screen: once checks actually pass, accept estimate and simulation terms, create demo order and show reference/status. Open Account, then reopen the saved order. Show one simulated stage advance if time permits.

> The checks have passed, so I can accept the estimate and simulation terms, then create the demo order. Here's its reference and current status. It's saved to my account; I can reopen it here and follow its progress. Owners can also request partner help with separate consent.

## 2:35-2:55 | Architecture and limits

Screen: briefly show Architecture.pdf, then finish on the tracker with simulation notice visible.

> React handles the interface, FastAPI runs the backend, and SQLite stores the records. The backend controls recommendations, prices, document checks and order status. Gemini helps with language and extraction. Payment, installation and activation are simulated; a real rollout would need live operator integrations and further validation.

## Recording notes

- Narration pauses while you speak the voice example; that utterance also counts toward the three-minute limit.
- Record an actual transcript and actual extraction/check results. Browser speech support and provider latency vary. Label any processing cuts with actual elapsed time.
- Keep the English/Hindi switch before voice capture. Show separate speech, advisor and document consents; speech permission alone does not authorize a Gemini request.
- Only say the checks passed when the recorded result passes. Keep the DEMO01 source label and simulation labels visible. Do not claim this is a passing K01-K12 set or broad OCR accuracy evidence.
- Partner handoff is mentioned briefly; dashboard, account security and additional metrics can be covered in the deck or presentation Q&A. Do not claim WhatsApp live delivery; it remains disabled.
- Keep credentials, passwords, unrelated tabs and private records off screen. Review the exported video's duration, legibility and audio before uploading.
