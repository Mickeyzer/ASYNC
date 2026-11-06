"""Render separate synthetic checkout fixtures without changing supplied documents."""
import hashlib
import html
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.kyc import GST_REGISTRY,UDYAM_REGISTRY,validate_documents
from backend.onboarding_models import DocumentDraft,ConfirmDocuments

OUT=ROOT/'demo_documents/checkout'


def build(destination=OUT):
    gst=next(row for row in GST_REGISTRY.values() if row['trade_name']=='Harmony Dental Care' and row['state']=='West Bengal' and row['status']=='Active')
    udyam=next(row for row in UDYAM_REGISTRY.values() if row['enterprise_name']==gst['trade_name'] and row['state']==gst['state'])
    business=gst['trade_name'];address=gst['principal_place_of_business'];signatory='Joseph Shah'
    common={'legibility':'clear','business_name':business}
    drafts={
        'gst_certificate':DocumentDraft(document_type='gst_certificate',**common,gstin=gst['gstin'],legal_name=gst['legal_name'],address=address,registration_date=gst['registration_date']),
        'udyam_certificate':DocumentDraft(document_type='udyam_certificate',**common,udyam_number=udyam['udyam_number'],city=udyam['city'],state=udyam['state'],registration_date=udyam['date_of_registration']),
        'signatory_id':DocumentDraft(document_type='signatory_id',**common,signatory_name=signatory,id_number='SYN-ID-816907',expiry_date='2028-09-10'),
        'address_proof':DocumentDraft(document_type='address_proof',**common,address=address,issue_date='2026-06-26'),
    }
    declaration=ConfirmDocuments(business_name=business,business_address=address,signatory_name=signatory,confirmed=True)
    decision=validate_documents(drafts,declaration)
    if decision['status']!='checks_passed':
        raise ValueError('Demo fixture does not pass the current rules; no images were written.')
    titles={'gst_certificate':'GST Registration Certificate','udyam_certificate':'Udyam Registration Certificate','signatory_id':'Authorised Signatory ID','address_proof':'Electricity Bill / Address Proof'}
    labels={'gstin':'GSTIN','legal_name':'Legal name','business_name':'Business / trade name','address':'Business address','registration_date':'Date of registration','udyam_number':'Udyam registration number','city':'City','state':'State','signatory_name':'Signatory name','id_number':'ID number','expiry_date':'Valid until','issue_date':'Bill date'}
    style='''*{box-sizing:border-box}body{margin:0;padding:44px;background:#fff;font:22px/1.5 Arial,sans-serif;color:#20252e}.document{border:2px solid #cfd5de;min-height:1060px;padding:36px}.fixture{font-size:18px;letter-spacing:1px;font-weight:bold;color:#ad1930;border-bottom:2px solid #ad1930;padding-bottom:16px}h1{font-size:32px;line-height:1.3;margin:25px 0 12px}p{font-size:18px;color:#596675}dl{margin:35px 0}dl>div{display:grid;grid-template-columns:300px 1fr;gap:25px;border-bottom:1px solid #e2e5ea;padding:17px 0}dt{font-weight:bold}dd{margin:0;overflow-wrap:anywhere}footer{font-size:17px;color:#ad1930;border-top:2px solid #ad1930;padding-top:18px;margin-top:40px}'''
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    files=[]
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        try:
            page=browser.new_page(viewport={'width':1200,'height':1200},device_scale_factor=1)
            for kind,draft in drafts.items():
                fields={key:value for key,value in draft.model_dump().items() if value is not None and key not in ('document_type','legibility')}
                rows=''.join('<div><dt>'+html.escape(labels[key])+'</dt><dd>'+html.escape(value)+'</dd></div>' for key,value in fields.items())
                page.set_content('<!doctype html><html lang="en"><meta charset="utf-8"><style>'+style+'</style><body><main class="document"><div class="fixture">DEVELOPMENT TEST FIXTURE / DEMO01 / SYNTHETIC DATA</div><h1>'+titles[kind]+'</h1><p>Separate sample created for prototype testing. Not an organizer-supplied K01-K12 document.</p><dl>'+rows+'</dl><footer>NOT A REAL DOCUMENT. Fictional business, person and identifiers.<br>For mock extraction and checkout testing only. No identity or authority is established.</footer></main></body></html>')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                filename='DEMO01_'+kind+'.png'
                page.screenshot(path=str(destination/filename),full_page=True)
                files.append({'file':filename,'expected':draft.model_dump(exclude_none=True),'sha256':hashlib.sha256((destination/filename).read_bytes()).hexdigest()})
        finally:
            browser.close()
    manifest={'type':'separate_synthetic_development_fixtures','source':'Supplied fictional mock registries; not the original specimen image pack.','provider_calls':0,'live_extraction_status':'Not tested; upload normally through the application to test your configured provider.','expected_validation':decision['status'],'declaration':declaration.model_dump(),'reference_date':decision['reference_date'],'documents':files}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (destination/'README.md').write_text('''# Successful checkout development sample

These four DEMO01 images are separately created synthetic development fixtures. They are not organizer-supplied K01-K12 specimens or real identity documents. The supplied specimen files, registries and application validation rules are unchanged.

All four images describe Harmony Dental Care / Joseph Shah. Registration values match the supplied active mock registries; bill and ID dates are valid on the required 15 July 2026 demo calendar. The manifest records the expected fields, image hashes and declaration. Generation makes no provider calls. A deterministic check passes, but live Gemini extraction has not been measured for these images.

1. Start a new plan: clinic, Tier 1, five staff, one site, internet and email, budget INR 3,000, GSTIN available, current internet hotspot. The starter estimate is INR 1,624 monthly, zero setup, taxes excluded, with 12-month service contracts.
2. Review the estimate, sign in and consent to document extraction.
3. Upload the four DEMO01 PNG files into their matching document slots, one at a time. This uses the normal extraction adapter and validation gates.
4. Compare extracted values to the images. Confirm business Harmony Dental Care; signatory Joseph Shah; address Shop/Unit 199, Station Road, Kolkata, West Bengal - 347550. The Udyam fixture date is 2022-09-27.
5. Confirm your review and click Check documents. Accurate complete extraction should produce Demo document checks passed. If an extraction is wrong or unclear, investigate it rather than assuming this outcome.
6. Accept the estimate and simulation terms, then Create demo order. The saved tracker should show Order accepted; Simulate next stage advances installation and activation without real provisioning or payment.

Label these as separate synthetic fixtures if shown in a recording. Do not describe a successful run with these files as a pass on the supplied K01-K12 pack or as proof of production OCR accuracy.
''',encoding='utf-8')
    print('Prepared four separate DEMO01 PNG fixtures. Deterministic document checks pass; zero provider calls. Live extraction remains to be tested.')
    return manifest


if __name__=='__main__':build()
