"""Isolated real browser/API checks. Extraction is controlled; no provider call or user server is used."""

import io
import json
import re
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

import uvicorn
from PIL import Image
from playwright.sync_api import expect, sync_playwright

from backend import kyc, main, onboarding, accounts
from backend.accounts import Accounts
from backend.limits import LIMITS
from backend.onboarding_models import DocumentDraft, KINDS
from backend.onboarding_store import OnboardingStore


def fixtures():
    gst=next(row for row in kyc.GST_REGISTRY.values() if row['status']=='Active' and any(u['enterprise_name']==row['trade_name'] and u['state']==row['state'] for u in kyc.UDYAM_REGISTRY.values()))
    udyam=next(row for row in kyc.UDYAM_REGISTRY.values() if row['enterprise_name']==gst['trade_name'] and row['state']==gst['state'])
    common={'business_name':gst['trade_name'],'legibility':'clear'}
    return {
        'gst_certificate':DocumentDraft(document_type='gst_certificate',**common,gstin=gst['gstin'],legal_name=gst['legal_name'],address=gst['principal_place_of_business'],registration_date=gst['registration_date']),
        'udyam_certificate':DocumentDraft(document_type='udyam_certificate',**common,udyam_number=udyam['udyam_number'],city=udyam['city'],state=udyam['state'],registration_date=udyam['date_of_registration']),
        'signatory_id':DocumentDraft(document_type='signatory_id',**common,signatory_name='Synthetic Tester',id_number='SYN-ID-123456',expiry_date='2028-01-01'),
        'address_proof':DocumentDraft(document_type='address_proof',**common,address=gst['principal_place_of_business'],issue_date='2026-06-26'),
    }


def run():
    documents=fixtures()
    calls=[]
    def controlled_extract(content):
        marker=Image.open(io.BytesIO(content)).getpixel((0,0))[0]
        calls.append(marker)
        if marker==9:
            return documents['udyam_certificate'].model_copy(update={'udyam_number':None})
        return documents[KINDS[marker]]

    original_extract=kyc.extract_document
    original_store=onboarding.STORE
    original_main_store=main.STORE
    original_auth=accounts.AUTH
    LIMITS.windows.clear()
    kyc.extract_document=controlled_extract
    with tempfile.TemporaryDirectory(prefix='udyam-browser-') as directory:
        directory=Path(directory)
        store=OnboardingStore(directory/'test.sqlite3')
        accounts.AUTH=Accounts(directory/'accounts.sqlite3')
        onboarding.STORE=main.STORE=store
        for marker in [0,1,2,3,9]:
            Image.new('RGB',(20,20),(marker,0,0)).save(directory/f'fixture-{marker}.png')
        sock=socket.socket()
        sock.bind(('127.0.0.1',0))
        url=f'http://127.0.0.1:{sock.getsockname()[1]}'
        server=uvicorn.Server(uvicorn.Config(main.app,log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True)
        worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:
                    raise RuntimeError('Test server did not start')
                time.sleep(.05)
            with sync_playwright() as playwright:
                browser=playwright.chromium.launch()
                page=browser.new_page(viewport={'width':1440,'height':1080})
                response=page.request.post(url+'/api/account/register',headers={'X-Requested-With':'Udyam'},data={'username':'browser-owner','password':'synthetic-password-123'})
                assert response.status==200
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url)
                page.select_option('[name=business_type]','clinic')
                page.select_option('[name=city_tier]','1')
                page.fill('[name=employees]','5')
                page.select_option('[name=current_internet]','hotspot')
                page.check('[name=needs][value=internet]')
                page.check('[name=needs][value=email]')
                page.click('#recommend-button')
                page.click('#check-quote')
                page.click('#continue-kyc')
                expect(page.locator('#start-kyc')).to_be_disabled()
                assert not calls
                page.check('#kyc-consent')
                page.click('#start-kyc')
                expect(page.locator('.document-card')).to_have_count(4)
                page.locator('.access-box > summary').click()
                with page.expect_download() as download:
                    page.click('#save-access')
                private=directory/'access.txt'
                download.value.save_as(private)
                text=private.read_text()
                identifier=re.search(r'Record ID: (\w+)',text)[1]
                code=re.search(r'Access code: (\S+)',text)[1]
                for index,kind in enumerate(KINDS):
                    marker=9 if kind=='udyam_certificate' else index
                    page.set_input_files('#upload-'+kind,str(directory/f'fixture-{marker}.png'))
                    expect(page.locator(f'[data-document={kind}] .extracted-fields')).to_be_visible()
                    expect(page.locator('#upload-'+kind)).to_be_enabled()
                assert documents['gst_certificate'].gstin not in page.locator('body').inner_text()
                assert documents['signatory_id'].id_number not in page.locator('body').inner_text()
                expect(page.locator('[name=business_name]')).to_have_value(documents['gst_certificate'].business_name)
                page.check('#confirm-documents')
                page.click('#check-documents')
                expect(page.locator('#kyc-result')).to_contain_text('Action required')
                expect(page.locator('#demo-checkout')).to_have_count(0)
                page.set_input_files('#upload-udyam_certificate',str(directory/'fixture-1.png'))
                expect(page.locator('[data-document=udyam_certificate] .extracted-fields')).to_contain_text('****')
                expect(page.locator('#upload-udyam_certificate')).to_be_enabled()
                page.check('#confirm-documents')
                page.click('#check-documents')
                expect(page.locator('#demo-checkout')).to_be_visible()
                expect(page.locator('#submit-order')).to_be_disabled()
                # Editing reviewed declarations must hide checkout until checks run again.
                page.fill('[name=signatory_name]','Another Person')
                expect(page.locator('#demo-checkout')).to_have_count(0)
                page.check('#confirm-documents')
                page.click('#check-documents')
                expect(page.locator('#kyc-result')).to_contain_text('Manual review required')
                page.fill('[name=signatory_name]','Synthetic Tester')
                page.check('#confirm-documents')
                page.click('#check-documents')
                expect(page.locator('#demo-checkout')).to_be_visible()
                (ROOT/'artifacts').mkdir(exist_ok=True)
                page.screenshot(path=str(ROOT/'artifacts'/'desktop-kyc-checkout.png'),full_page=True)
                page.check('#accept-estimate')
                expect(page.locator('#submit-order')).to_be_disabled()
                page.check('#accept-simulation')
                page.click('#submit-order')
                expect(page.locator('#order-tracker')).to_be_visible()
                expect(page.locator('#step5')).to_have_attribute('aria-current','step')
                expect(page.locator('#order-tracker')).to_contain_text('SIMULATION')
                assert not store.drafts(identifier)
                # New store instance simulates losing all process memory on restart.
                onboarding.STORE=main.STORE=OnboardingStore(store.path)
                page.reload()
                page.click('#open-saved-order')
                page.locator('.legacy-recovery > summary').click()
                page.fill('#resume-id',identifier)
                page.fill('#resume-code','incorrect-code')
                page.click('#resume-record')
                expect(page.locator('#onboarding-error')).to_be_visible()
                page.fill('#resume-code',code)
                page.click('#resume-record')
                expect(page.locator('#order-tracker')).to_be_visible()
                page.click('#advance-order')
                expect(page.locator('.order-stages [aria-current=step]')).to_have_text('Installation scheduled')
                page.click('#advance-order')
                expect(page.locator('.order-stages [aria-current=step]')).to_have_text('Services activated')
                expect(page.locator('#advance-order')).to_have_count(0)
                page.set_viewport_size({'width':390,'height':844})
                page.select_option('#language','hi')
                expect(page.locator('.order-stages [aria-current=step]')).to_have_text('सेवाएँ सक्रिय हुईं')
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                page.screenshot(path=str(ROOT/'artifacts'/'mobile-order-tracker.png'),full_page=True)
                page.check('#delete-consent')
                page.click('#delete-record')
                expect(page.locator('#order-tracker')).to_have_count(0)
                assert page.request.get(url+'/api/onboarding/'+identifier,headers={'X-Order-Key':code}).status==404
                assert not errors,errors
                browser.close()
                print(json.dumps({'result':'passed','provider_calls':'controlled test extraction only','extractions':len(calls),
                                  'checks':['consent gate','four image uploads','masked identifiers','missing Udyam correction','mismatch blocks checkout','declaration edits invalidate UI approval','explicit checkout consent','persistent order recovery','wrong access code denied','simulated status transitions','Hindi mobile tracker','record deletion'],
                                  'unexpected_browser_errors':errors},indent=2))
        finally:
            server.should_exit=True
            worker.join(timeout=10)
            sock.close()
            kyc.extract_document=original_extract
            onboarding.STORE=original_store
            main.STORE=original_main_store
            accounts.AUTH=original_auth


if __name__=='__main__':
    run()
