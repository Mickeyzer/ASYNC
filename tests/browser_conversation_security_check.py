"""Real browser checks for reviewed follow-ups, session controls and Hindi operations."""
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
from backend.models import DiscoveryDraft
from backend.limits import LIMITS

PASSWORD='synthetic-password-123'
NEW_PASSWORD='changed-browser-password-456'


def run():
    previous=(accounts.AUTH,main.STORE,onboarding.STORE,main.discover)
    received=[]
    def controlled_advisor(request):
        received.append(request)
        if request.message=='fail':return {'mode':'guided','draft':None,'message':'Service temporarily unavailable.','message_hi':'सेवा अभी उपलब्ध नहीं है।'}
        draft=(DiscoveryDraft(business_type='clinic',employees=5,sites=1,current_internet='hotspot',needs=['internet','email'],follow_up='What is your monthly budget?') if not request.history else
               DiscoveryDraft(monthly_budget=3000,follow_up='Review the updated answers.'))
        return {'mode':'gemini','draft':draft.model_dump(),'message':'Review the draft.'}
    LIMITS.windows.clear()
    with tempfile.TemporaryDirectory(prefix='udyam-conversation-') as directory:
        directory=Path(directory);accounts.AUTH=Accounts(directory/'accounts.sqlite3')
        main.STORE=onboarding.STORE=OnboardingStore(directory/'onboarding.sqlite3');main.discover=controlled_advisor
        accounts.AUTH.create('reviewer-language',PASSWORD,'reviewer')
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
                page=context.new_page();errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
                page.goto(url);page.locator('.advisor-box > summary').click()
                page.fill('#business-brief','A clinic with five staff needs internet and email');page.check('#advisor-consent');page.click('#ask-advisor')
                expect(page.locator('[name=employees]')).to_have_value('5')
                expect(page.locator('#advisor-conversation')).to_contain_text('What is your monthly budget?')
                expect(page.locator('#ask-advisor')).to_be_disabled()
                page.fill('[name=employees]','7');page.check('#advisor-reviewed');page.fill('#business-brief','3000 per month');page.click('#ask-advisor')
                expect(page.locator('[name=monthly_budget]')).to_have_value('3000')
                expect(page.locator('[name=employees]')).to_have_value('7')
                assert received[-1].reviewed.employees==7 and len(received[-1].history)==2
                page.check('#advisor-reviewed');page.fill('#business-brief','fail');page.click('#ask-advisor')
                expect(page.locator('#advisor-feedback')).to_contain_text('temporarily unavailable')
                expect(page.locator('[name=employees]')).to_have_value('7')
                expect(page.locator('#business-brief')).to_have_value('fail')
                for _ in range(4):
                    page.check('#advisor-reviewed');page.fill('#business-brief','व्यवसाय '*240);page.click('#ask-advisor')
                    expect(page.locator('#advisor-feedback')).to_contain_text('Review the updated answers.')
                assert len(received[-1].history)<=6  # UTF-8 byte bound trims old turns, preserving reviewed facts.
                page.click('#advisor-reset');expect(page.locator('#advisor-conversation')).to_have_count(0)
                expect(page.locator('[name=employees]')).to_have_value('7')

                page.click('#account-toggle');page.get_by_role('button',name='Create a new account',exact=True).click()
                page.fill('#account-form [name=username]','browser-security');page.fill('#account-form [name=password]',PASSWORD)
                page.fill('#account-form [name=confirm_password]',PASSWORD);page.click('#account-submit');expect(page.locator('.account-toast')).to_be_visible();page.click('#account-toggle');page.locator('#security-settings > summary').click();expect(page.locator('#account-security')).to_be_visible()
                other=browser.new_context()
                assert other.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'browser-security','password':PASSWORD}).status==200
                page.get_by_role('button',name='Close account dialog',exact=True).click();page.click('#account-toggle');page.locator('#security-settings > summary').click()
                expect(page.locator('#account-sessions article')).to_have_count(2)
                page.click('#revoke-other-sessions');expect(page.locator('#account-sessions article')).to_have_count(1)
                assert other.request.get(url+'/api/account/me').json()['user'] is None
                assert other.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'browser-security','password':PASSWORD}).status==200
                page.fill('#password-form [name=current_password]',PASSWORD)
                page.fill('#password-form [name=new_password]',NEW_PASSWORD);page.fill('#password-form [name=confirm_password]',NEW_PASSWORD)
                page.click('#change-password');expect(page.locator('#account-security [role=status]')).to_contain_text('Password changed')
                assert other.request.get(url+'/api/account/me').json()['user'] is None
                expect(page.locator('#password-form [name=new_password]')).to_have_value('')
                page.select_option('#account-language','hi')
                expect(page.locator('#account-security [role=status]')).to_contain_text('पासवर्ड बदल दिया')
                page.set_viewport_size({'width':390,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.fill('#password-form [name=current_password]','wrong-synthetic-pass')
                page.fill('#password-form [name=new_password]',PASSWORD);page.fill('#password-form [name=confirm_password]',PASSWORD);page.click('#change-password')
                expect(page.locator('#account-security [role=alert]')).to_contain_text('मौजूदा पासवर्ड गलत')
                expect(page.locator('#account-toggle')).to_contain_text('ग्राहक')
                page.click('#account-sign-out');expect(page.locator('#account-security')).to_have_count(0)

                reviewer=browser.new_context(viewport={'width':390,'height':844});review=reviewer.new_page();review.on('pageerror',lambda error:errors.append(str(error)))
                assert reviewer.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'reviewer-language','password':PASSWORD}).status==200
                review.goto(url);review.select_option('#language','hi');review.click('#open-operations')
                review.locator('#operations-metrics summary').click();review.locator('#channel-status summary').click();review.locator('#business-insights summary').click()
                expect(review.locator('#unique-journey-metrics')).to_contain_text('सहमति वाले रिकॉर्ड')
                expect(review.locator('#channel-status')).to_contain_text('सेटिंग पूरी होने तक बंद')
                expect(review.locator('#business-insights')).to_contain_text('इस ऐप से सुधार का प्रमाण नहीं')
                body=review.locator('#operations-view').inner_text()
                assert 'Retry-inclusive' not in body and 'Current cohort' not in body and 'Historical synthetic' not in body
                assert 'अन्य स्थिति' not in body
                assert review.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                (ROOT/'artifacts').mkdir(exist_ok=True)
                review.evaluate('document.activeElement?.blur();window.scrollTo(0,0)')
                review.screenshot(path=str(ROOT/'artifacts/mobile-hindi-operations.png'),full_page=True)
                assert not errors,errors
                browser.close()
            print(json.dumps({'result':'passed','checks':[
                'follow-up conversation retains reviewed manual corrections','follow-up requires owner review',
                'long Hindi conversation respects UTF-8 request limit',
                'advisor failure preserves answers and retry text','clearing conversation retains editable form',
                'session list and bulk revocation UI','password change rotates other browser sessions',
                'Hindi security errors and role labels','Hindi mobile measurements/channel/evidence',
                'mobile account controls and translated success notice',
                'sign-out removes account security UI'],'unexpected_browser_errors':errors,
                'providers':'Controlled advisor fixture; no live Gemini or WhatsApp calls'},indent=2))
        finally:
            server.should_exit=True;worker.join(10);sock.close()
            accounts.AUTH,main.STORE,onboarding.STORE,main.discover=previous


if __name__=='__main__':run()
