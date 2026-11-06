"""Isolated real browser checks for accounts, assigned operations and reviewed voice."""
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
from playwright.sync_api import expect,sync_playwright
from backend import accounts,main,onboarding
from backend.accounts import Accounts
from backend.onboarding_store import OnboardingStore
from backend.limits import LIMITS

PASSWORD='synthetic-password-123'
PROFILE={'business_type':'clinic','city_tier':1,'employees':5,'sites':1,'monthly_budget':3000,
         'current_internet':'hotspot','gstin_claim':'yes','needs':['internet','email'],'language':'en'}


def run():
    previous=(accounts.AUTH,main.STORE,onboarding.STORE)
    LIMITS.windows.clear()
    with tempfile.TemporaryDirectory(prefix='udyam-operations-') as directory:
        directory=Path(directory)
        accounts.AUTH=Accounts(directory/'accounts.sqlite3')
        main.STORE=onboarding.STORE=OnboardingStore(directory/'onboarding.sqlite3')
        accounts.AUTH.create('reviewer-demo',PASSWORD,'reviewer')
        partner=accounts.AUTH.create('partner-demo',PASSWORD,'partner')
        sock=socket.socket();sock.bind(('127.0.0.1',0));url=f'http://127.0.0.1:{sock.getsockname()[1]}'
        server=uvicorn.Server(uvicorn.Config(main.app,log_level='error',access_log=False))
        worker=threading.Thread(target=server.run,kwargs={'sockets':[sock]},daemon=True);worker.start()
        try:
            deadline=time.monotonic()+10
            while not server.started:
                if time.monotonic()>deadline:raise RuntimeError('Test server did not start')
                time.sleep(.05)
            with sync_playwright() as pw:
                browser=pw.chromium.launch();context=browser.new_context(viewport={'width':1440,'height':1000})
                context.add_init_script('''
                    window.SpeechRecognition=class {
                      start(){window.testSpeechLanguage=this.lang;setTimeout(()=>{
                        if(window.testVoiceDeny){this.onerror?.({error:'not-allowed'});return;}
                        this.onresult?.({resultIndex:0,results:[{0:{transcript:'Clinic with five staff needs internet'},isFinal:true}]});
                        this.onend?.();},30);}
                      stop(){this.onend?.();} abort(){this.onend?.();}
                    };
                ''')
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url);page.click('#account-toggle')
                page.get_by_role('button',name='Create a new account',exact=True).click()
                page.fill('#account-form [name=username]','browser-customer')
                page.fill('#account-form [name=password]',PASSWORD)
                page.fill('#account-form [name=confirm_password]',PASSWORD);page.click('#account-submit')
                expect(page.locator('#account-toggle')).to_contain_text('browser-customer')
                page.locator('.advisor-box > summary').click();page.locator('.voice-box > summary').click()
                expect(page.locator('#start-voice')).to_be_disabled()
                page.check('#voice-consent');page.click('#start-voice')
                expect(page.locator('#voice-transcript')).to_have_value('Clinic with five staff needs internet')
                expect(page.locator('#business-brief')).to_have_value('')
                page.click('#use-transcript')
                expect(page.locator('#business-brief')).to_have_value('Clinic with five staff needs internet')
                assert page.evaluate('window.testSpeechLanguage')=='en-IN'
                page.evaluate('window.testVoiceDeny=true');page.click('#start-voice')
                expect(page.locator('.voice-box')).to_contain_text('permission was denied')
                page.evaluate('window.testVoiceDeny=false');page.click('#start-voice');page.click('#cancel-voice')
                expect(page.locator('#voice-transcript')).to_have_value('')
                page.select_option('#language','hi');page.check('#voice-consent');page.click('#start-voice')
                expect(page.locator('#voice-transcript')).not_to_have_value('')
                assert page.evaluate('window.testSpeechLanguage')=='hi-IN'
                page.select_option('#language','en')
                response=context.request.post(url+'/api/onboarding',headers={'X-Requested-With':'Udyam'},data={'profile':PROFILE,'items':[{'product_id':'P01','quantity':1}],'consent':True})
                assert response.status==200,response.text()
                identifier=response.json()['session_id']
                page.reload();page.click('#account-toggle');page.click('[data-open-record="'+identifier+'"]')
                expect(page.locator('.document-card')).to_have_count(4)
                expect(page.locator('#request-handoff')).to_be_disabled()
                page.fill('#handoff-contact','synthetic@example.invalid');page.check('#followup-consent');page.click('#request-handoff')
                expect(page.locator('#withdraw-handoff')).to_be_visible()

                reviewer=browser.new_context();review=reviewer.new_page();review.on('pageerror',lambda e:errors.append(str(e)))
                assert reviewer.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'reviewer-demo','password':PASSWORD}).status==200
                review.goto(url);review.click('#open-operations');review.click('[data-lead="'+identifier+'"]')
                review.locator('#operation-detail select').select_option(partner['id']);review.click('#assign-partner')
                expect(review.locator('#operation-detail')).to_have_count(0)
                review.click('[data-lead="'+identifier+'"]')
                expect(review.locator('#operation-detail')).to_contain_text('partner_assigned')
                review.locator('#operations-metrics summary').click()
                expect(review.locator('#unique-journey-metrics')).to_contain_text('consented records: 1')
                review.locator('#channel-status summary').click()
                expect(review.locator('#channel-status')).to_contain_text('Disabled until configured')
                review.locator('#business-insights summary').click()
                expect(review.locator('#business-insights')).to_contain_text('not adopt')
                (ROOT/'artifacts').mkdir(exist_ok=True)
                review.screenshot(path=str(ROOT/'artifacts/desktop-partner-dashboard.png'),full_page=True)

                partner_context=browser.new_context(viewport={'width':390,'height':844});team=partner_context.new_page()
                team.on('pageerror',lambda e:errors.append(str(e)))
                assert partner_context.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'partner-demo','password':PASSWORD}).status==200
                team.goto(url);team.click('#open-operations');team.click('[data-lead="'+identifier+'"]')
                expect(team.locator('#operation-detail')).to_contain_text('synthetic@example.invalid')
                expect(team.locator('#request-replacement')).to_have_count(0)
                team.fill('#review-reason','Owner helped using synthetic demo information')
                team.click('#resolve-handoff');expect(team.locator('#operation-detail')).to_have_count(0)
                team.screenshot(path=str(ROOT/'artifacts/mobile-partner-dashboard.png'),full_page=True)
                assert team.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.click('#refresh-check');expect(page.locator('#partner-handoff')).to_contain_text('resolved')
                page.click('#withdraw-handoff');expect(page.locator('#request-handoff')).to_be_visible()
                team.get_by_role('button',name='Refresh queue',exact=True).click()
                expect(team.locator('[data-lead]')).to_have_count(0)
                page.click('#sign-out');expect(page.locator('.registration-gate form')).to_be_visible()
                expect(page.locator('.document-card')).to_have_count(0)

                unsupported=browser.new_context();unsupported.add_init_script('window.SpeechRecognition=undefined;window.webkitSpeechRecognition=undefined;')
                fallback=unsupported.new_page();fallback.goto(url);fallback.locator('.advisor-box > summary').click()
                expect(fallback.locator('.voice-box')).to_contain_text('unavailable')
                expect(fallback.locator('#business-brief')).to_be_enabled()
                assert not errors,errors
                browser.close()
                print(json.dumps({'result':'passed','checks':['customer registration UI','account-linked record recovery','voice consent',
                    'reviewed transcript required','microphone denial fallback','voice cancellation','Hindi speech locale','unsupported browser fallback',
                    'separate follow-up consent','reviewer assignment','partner permissions','follow-up resolution','consent withdrawal',
                    'sign-out clears document UI','mobile dashboard layout','unique active journey metrics','disabled channel status','historical ranking limitations'],'unexpected_browser_errors':errors,
                    'voice':'controlled browser recognition; real microphone/provider quality not established'},indent=2))
        finally:
            server.should_exit=True;worker.join(timeout=10);sock.close()
            accounts.AUTH,main.STORE,onboarding.STORE=previous


if __name__=='__main__':run()
