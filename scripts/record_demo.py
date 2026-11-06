"""Captioned, explicitly controlled rehearsal; never presented as a live Gemini demo."""
import importlib.util
import json
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import uvicorn
from PIL import Image,ImageDraw,ImageFont
from playwright.sync_api import expect,sync_playwright
from backend import accounts,kyc,main,onboarding
from backend.accounts import Accounts
from backend.onboarding_store import OnboardingStore
from backend.onboarding_models import KINDS
from backend.limits import LIMITS

OUT=ROOT/'submission'


def run():
    spec=importlib.util.spec_from_file_location('rehearsal_fixtures',ROOT/'tests/browser_onboarding_check.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    documents=module.fixtures()
    original=(accounts.AUTH,main.STORE,onboarding.STORE,kyc.extract_document)
    LIMITS.windows.clear();OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='udyam-rehearsal-') as directory:
        directory=Path(directory);accounts.AUTH=Accounts(directory/'accounts.sqlite3')
        main.STORE=onboarding.STORE=OnboardingStore(directory/'onboarding.sqlite3')
        def extract(content):
            marker=Image.open(__import__('io').BytesIO(content)).getpixel((0,0))[0]
            return documents[KINDS[marker]]
        kyc.extract_document=extract
        accounts.AUTH.create('demo-reviewer','synthetic-demo-password','reviewer')
        partner=accounts.AUTH.create('demo-partner','synthetic-demo-password','partner')
        for index,kind in enumerate(KINDS):
            image=Image.new('RGB',(1100,900),'white');draw=ImageDraw.Draw(image)
            font=ImageFont.load_default(size=23)
            draw.text((24,30),'SYNTHETIC CONTROLLED TEST FIXTURE',fill='black',font=font)
            y=85
            for field,value in documents[kind].model_dump().items():
                if value is not None:
                    # Keep readable address wrapping in the local specimen.
                    import textwrap
                    for line in textwrap.wrap(f'{field}: {value}',75):draw.text((24,y),line,fill='black',font=font);y+=32
            image.putpixel((0,0),(index,0,0));image.save(directory/(kind+'.png'))
        sock=socket.socket();sock.bind(('127.0.0.1',0));url=f'http://127.0.0.1:{sock.getsockname()[1]}'
        server=uvicorn.Server(uvicorn.Config(main.app,log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:raise RuntimeError('Rehearsal server did not start')
                time.sleep(.05)
            with sync_playwright() as pw:
                browser=pw.chromium.launch()
                context=browser.new_context(viewport={'width':1440,'height':1000},record_video_dir=str(directory/'video'),record_video_size={'width':1440,'height':1000})
                headers={'X-Requested-With':'Udyam'}
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                draft={'mode':'gemini','draft':{'business_type':'clinic','employees':5,'sites':1,'monthly_budget':3000,
                    'current_internet':'hotspot','gstin_claim':'yes','needs':['internet','email'],'follow_up':'Review these details before choosing services.'},'message':'Review the draft.'}
                def advisor_fixture(route):
                    reply=json.loads(json.dumps(draft))
                    if not route.request.post_data_json.get('history'):
                        reply['draft']['monthly_budget']=None
                        reply['draft']['follow_up']='What is your monthly budget?'
                    route.fulfill(status=200,content_type='application/json',body=json.dumps(reply))
                page.route('**/api/discover',advisor_fixture)
                def caption(text,delay=1800):
                    page.evaluate('''text=>{let banner=document.getElementById('rehearsal-banner');if(!banner){banner=document.createElement('div');banner.id='rehearsal-banner';document.body.appendChild(banner);Object.assign(banner.style,{position:'fixed',bottom:'0',left:'0',width:'100%',padding:'16px 28px',background:'#172e29',color:'white',font:'18px Arial',zIndex:'99999',boxSizing:'border-box'});}banner.textContent='CONTROLLED REHEARSAL · Synthetic data · '+text;}''',text)
                    page.wait_for_timeout(delay)
                page.goto(url);caption('Advisor and extraction use fixtures. No live Gemini accuracy or activation is claimed.',3000)
                page.click('#create-account');page.fill('#account-username','demo-owner')
                page.fill('#account-password','synthetic-demo-password');page.fill('#account-confirm-password','synthetic-demo-password')
                caption('A visible account entry, clear field guidance and password confirmation.')
                page.click('#account-submit');expect(page.locator('dialog')).to_have_count(0)
                page.click('#account-toggle');page.locator('#security-settings > summary').click();expect(page.locator('#account-security')).to_be_visible()
                caption('Account controls include password changes and individual session revocation.');page.get_by_role('button',name='Close account dialog',exact=True).click()
                page.locator('.advisor-box > summary').click();page.fill('#business-brief','I run a clinic with five staff at one site. We need internet and email.')
                page.check('#advisor-consent');caption('Separate consent; model drafts need owner review.')
                page.click('#ask-advisor');expect(page.locator('[name=employees]')).to_have_value('5')
                page.check('#advisor-reviewed');page.fill('#business-brief','INR 3000 per month');page.click('#ask-advisor')
                expect(page.locator('[name=monthly_budget]')).to_have_value('3000')
                caption('Follow-up updates the draft while retaining reviewed business facts.')
                page.select_option('[name=city_tier]','1');caption('Review the draft and supply the missing city tier.')
                page.click('#recommend-button');expect(page.locator('#quote-summary')).to_contain_text('1,624')
                caption('Catalogue-backed bundle: INR 1,624/month. Backend controls prices and eligibility.',2500)
                page.click('#check-quote');expect(page.locator('#review-view')).to_be_visible();caption('Review quantities, contract lengths and tax assumptions.')
                page.click('#continue-kyc');page.check('#kyc-consent');caption('Account ownership and a separate document-consent notice.')
                page.click('#start-kyc');expect(page.locator('.document-card')).to_have_count(4)
                for kind in KINDS:
                    page.set_input_files('#upload-'+kind,str(directory/(kind+'.png')))
                    expect(page.locator(f'[data-document={kind}] .extracted-fields')).to_be_visible()
                    caption(kind.replace('_',' ')+': controlled extraction; displayed identifiers are masked.',1100)
                page.check('#confirm-documents');page.click('#check-documents');expect(page.locator('#demo-checkout')).to_be_visible()
                caption('Real backend validation compares fixture fields to the mock registries and date rules.',2500)
                page.fill('#handoff-contact','rehearsal@example.invalid');page.check('#followup-consent');page.click('#request-handoff')
                expect(page.locator('#withdraw-handoff')).to_be_visible();caption('Owner explicitly requests help. No message is sent automatically.')
                page.check('#accept-estimate');page.check('#accept-simulation');page.click('#submit-order')
                expect(page.locator('#order-tracker')).to_be_visible();caption('Explicit demo checkout saves one order. No payment or real installation occurs.',2500)
                page.click('#advance-order');expect(page.locator('.order-stages [aria-current=step]')).to_have_text('Installation scheduled')
                caption('Saved tracker replaces status chasing; this transition is simulated.')
                page.click('#advance-order');expect(page.locator('.order-stages [aria-current=step]')).to_have_text('Services activated')
                caption('Demo activation completed. The same record can be reopened after sign-in.')
                context.request.post(url+'/api/account/logout',headers=headers)
                assert context.request.post(url+'/api/account/login',headers=headers,data={'username':'demo-reviewer','password':'synthetic-demo-password'}).status==200
                page.reload();caption('Switching to the separate reviewer role.')
                page.click('#open-operations');page.locator('[data-lead]').first.click();page.locator('#operation-detail select').select_option(partner['id']);page.click('#assign-partner')
                expect(page.locator('#operation-detail')).to_have_count(0);caption('Reviewer assigns the consented task. Partners see assigned summaries only.',2500)
                page.locator('#operations-metrics summary').click();expect(page.locator('#unique-journey-metrics')).to_be_visible()
                caption('Unique active journeys are separate from retry-inclusive counters. This sample is not a pilot result.',3000)
                assert not errors,errors
                page.screenshot(path=str(OUT/'assets/rehearsal-final.png'),full_page=True)
                video=page.video;context.close();video.save_as(OUT/'demo-rehearsal.webm')
                # Verify actual video metadata through Chromium, not wall-clock estimates.
                player='<!doctype html><meta charset="utf-8"><title>Controlled rehearsal</title><h1>Controlled rehearsal: synthetic data and fixture extraction</h1><p>This is not a live-provider accuracy demonstration. Payments and activation are simulated.</p><video controls width="1100" preload="metadata" src="demo-rehearsal.webm"></video>'
                (OUT/'demo-player.html').write_text(player,encoding='utf-8')
                check=browser.new_page();check.goto((OUT/'demo-player.html').as_uri())
                check.wait_for_function('Number.isFinite(document.querySelector("video").duration)')
                duration=check.locator('video').evaluate('(v)=>v.duration')
                assert 0<duration<=180
                browser.close()
                (OUT/'demo-manifest.json').write_text(json.dumps({'type':'controlled_rehearsal','duration_seconds':duration,
                    'provider_calls':0,'extraction':'synthetic controlled fixtures','unexpected_browser_errors':errors,
                    'live_demo_status':'Record a live-provider demo after image/voice validation; this file is explicitly a rehearsal.'},indent=2),encoding='utf-8')
                print(f'Controlled rehearsal recorded and checked: {duration:.1f} seconds, zero provider calls, no unexpected page errors.')
        finally:
            server.should_exit=True;worker.join(timeout=10);sock.close()
            accounts.AUTH,main.STORE,onboarding.STORE,kyc.extract_document=original


if __name__=='__main__':run()
