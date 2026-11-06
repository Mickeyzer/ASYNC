"""Registration usability, keyboard access and responsive journey checks in isolated storage."""
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

PASSWORD='synthetic-design-password-123'


def overflow(page):
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.locator('dialog[open]').evaluate_all('(dialogs)=>dialogs.every(d=>d.scrollWidth<=d.clientWidth+1)')


def run():
    previous=(accounts.AUTH,main.STORE,onboarding.STORE);LIMITS.windows.clear()
    with tempfile.TemporaryDirectory(prefix='udyam-design-') as directory:
        directory=Path(directory);accounts.AUTH=Accounts(directory/'accounts.sqlite3')
        main.STORE=onboarding.STORE=OnboardingStore(directory/'onboarding.sqlite3')
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
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                page.goto(url);expect(page.locator('#create-account')).to_be_visible()
                expect(page.locator('#business-form')).to_be_visible()
                ratios=page.evaluate('''()=>{
                  const rgb=value=>(value.match(/[\\d.]+/g)||[]).map(Number);
                  const luminance=values=>values.slice(0,3).map(v=>v/255).map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
                  return ['#recommend-button','.form-grid small','.registration-prompt p>span','.page-footer'].map(selector=>{
                    const element=document.querySelector(selector);let current=element;let background;
                    while(current){const color=rgb(getComputedStyle(current).backgroundColor);if(color.length===3||color[3]>0){background=color;break;}current=current.parentElement;}
                    const a=luminance(rgb(getComputedStyle(element).color)),b=luminance(background||[255,255,255]);return (Math.max(a,b)+.05)/(Math.min(a,b)+.05);
                  });
                }''')
                assert all(ratio>=4.5 for ratio in ratios),ratios
                (ROOT/'artifacts').mkdir(exist_ok=True)
                page.screenshot(path=str(ROOT/'artifacts/redesign-desktop.png'),full_page=True)
                page.fill('[name=employees]','8');page.click('#create-account')
                expect(page.locator('dialog[open]')).to_be_visible()
                expect(page.locator('#account-username')).to_be_focused()
                for _ in range(12):
                    page.keyboard.press('Tab')
                    assert page.evaluate('document.querySelector("dialog[open]").contains(document.activeElement)')
                page.keyboard.press('Escape');expect(page.locator('dialog')).to_have_count(0)
                expect(page.locator('#create-account')).to_be_focused()
                expect(page.locator('[name=employees]')).to_have_value('8')
                page.click('#create-account')
                page.fill('#account-username','invalid username')
                page.fill('#account-password',PASSWORD);page.fill('#account-confirm-password',PASSWORD)
                page.click('#account-submit')
                assert page.locator('#account-username').evaluate('(input)=>!input.validity.valid')
                with accounts.AUTH.connect() as db:assert not db.execute('SELECT 1 FROM users').fetchone()
                page.fill('#account-username','design-owner');page.fill('#account-confirm-password','different-password-456')
                page.click('#account-submit');expect(page.locator('#account-error')).to_contain_text('do not match')
                expect(page.locator('#account-confirm-password')).to_be_focused()
                page.get_by_role('button',name='Show',exact=True).click()
                expect(page.locator('#account-password')).to_have_attribute('type','text')
                page.get_by_role('button',name='Hide',exact=True).click()
                page.fill('#account-confirm-password',PASSWORD)
                # A narrow screen and Hindi must remain usable while the native modal is open.
                page.set_viewport_size({'width':320,'height':740});page.select_option('#account-language','hi');overflow(page)
                page.screenshot(path=str(ROOT/'artifacts/redesign-mobile-registration.png'))
                page.select_option('#account-language','en');page.click('#account-submit')
                expect(page.locator('dialog')).to_have_count(0)
                expect(page.locator('.account-toast')).to_contain_text('account is ready')
                expect(page.locator('[name=employees]')).to_have_value('8')
                overflow(page)
                page.click('#account-toggle');expect(page.locator('.empty-records')).to_contain_text('progress')
                page.locator('#security-settings > summary').click()
                expect(page.locator('#password-form')).to_be_visible();overflow(page)
                page.click('#account-sign-out');expect(page.locator('#create-account')).to_be_visible()
                page.click('#account-toggle');page.fill('#account-username','design-owner');page.fill('#account-password',PASSWORD)
                expect(page.locator('#account-confirm-password')).to_have_count(0)
                page.click('#account-submit');expect(page.locator('dialog')).to_have_count(0)
                # Sign out and register during document onboarding, preserving the selected estimate.
                page.click('#account-toggle');page.click('#account-sign-out')
                page.set_viewport_size({'width':1440,'height':1000})
                page.select_option('[name=business_type]','clinic');page.select_option('[name=city_tier]','1')
                page.fill('[name=employees]','5');page.select_option('[name=current_internet]','hotspot')
                page.check('[name=needs][value=internet]');page.check('[name=needs][value=email]');page.click('#recommend-button')
                expect(page.locator('#quote-summary')).to_contain_text('1,624')
                page.click('#check-quote');page.click('#continue-kyc')
                expect(page.locator('.registration-context')).to_be_visible()
                expect(page.locator('#onboarding-account-confirm-password')).to_be_visible()
                page.fill('#onboarding-account-username','journey-owner');page.click('#create-account')
                assert page.evaluate('''()=>{const ids=[...document.querySelectorAll('[id]')].map(el=>el.id);return ids.length===new Set(ids).size;}''')
                page.keyboard.press('Escape');expect(page.locator('#onboarding-account-username')).to_have_value('journey-owner')
                page.fill('#onboarding-account-username','journey-owner');page.fill('#onboarding-account-password',PASSWORD);page.fill('#onboarding-account-confirm-password',PASSWORD);page.click('#onboarding-account-submit')
                expect(page.locator('#start-kyc')).to_be_visible();expect(page.locator('#start-kyc')).to_be_disabled()
                expect(page.locator('.legacy-recovery')).not_to_have_attribute('open','')
                page.check('#kyc-consent');page.click('#start-kyc')
                expect(page.locator('.document-card')).to_have_count(4)
                page.screenshot(path=str(ROOT/'artifacts/redesign-documents.png'),full_page=True)
                # Dropping multiple files or an unsupported file must not invoke extraction.
                label=page.locator('[data-document=gst_certificate] .upload-label')
                multiple=page.evaluate_handle('''()=>{const data=new DataTransfer();for(let i=0;i<2;i++)data.items.add(new File(['text'],'test.txt',{type:'text/plain'}));return data;}''')
                label.dispatch_event('drop',{'dataTransfer':multiple})
                expect(page.locator('#onboarding-error')).to_contain_text('one image')
                single=page.evaluate_handle('''()=>{const data=new DataTransfer();data.items.add(new File(['text'],'test.txt',{type:'text/plain'}));return data;}''')
                label.dispatch_event('drop',{'dataTransfer':single})
                expect(page.locator('#onboarding-error')).to_contain_text('PNG or JPEG')
                expect(page.locator('[data-document=gst_certificate] .extracted-fields')).to_have_count(0)
                page.set_viewport_size({'width':390,'height':844});page.select_option('#language','hi');overflow(page)
                page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(ROOT/'artifacts/redesign-mobile-documents.png'),full_page=True)
                page.select_option('#language','en');page.locator('#onboarding-view > button').first.click()
                page.click('#open-saved-order');page.click('#find-account-records')
                expect(page.locator('.saved-record')).to_have_count(1)
                page.locator('.saved-record').click();expect(page.locator('.document-card')).to_have_count(4)
                accounts.AUTH.create('design-reviewer',PASSWORD,'reviewer')
                team_context=browser.new_context(viewport={'width':390,'height':844});team=team_context.new_page()
                team.on('pageerror',lambda error:errors.append(str(error)))
                assert team_context.request.post(url+'/api/account/login',headers={'X-Requested-With':'Udyam'},data={'username':'design-reviewer','password':PASSWORD}).status==200
                team.goto(url);team.click('#open-operations')
                team.locator('.staff-navigation').get_by_role('button',name='Journey measurements',exact=True).click()
                expect(team.locator('#operations-metrics')).to_have_attribute('open','')
                team.locator('.staff-navigation').get_by_role('button',name='Channel status',exact=True).click()
                expect(team.locator('#channel-status')).to_have_attribute('open','');overflow(team)
                expect(team.get_by_role('button',name='Account for design-reviewer',exact=True)).to_be_visible()
                assert not errors,errors
                browser.close()
            print(json.dumps({'result':'passed','checks':[
                'prominent account creation with anonymous exploration','modal keyboard focus and Escape return',
                'sampled text and primary controls meet contrast ratio 4.5',
                'invalid usernames rejected before account creation','password mismatch and visibility controls',
                '320px Hindi registration dialog without horizontal overflow','registration preserves entered business details',
                'clear empty-record state and mobile account controls','existing account sign-in without confirmation field',
                'registration during onboarding preserves selected bundle','explicit document consent after registration',
                'header and inline registration have unique accessible field IDs',
                'drag-and-drop rejects multiple or unsupported files','saved-record recovery through account UI',
                'Hindi mobile document layout','authorized staff shortcuts and mobile account naming'],'unexpected_browser_errors':errors,'provider_calls':0},indent=2))
        finally:
            server.should_exit=True;worker.join(10);sock.close();accounts.AUTH,main.STORE,onboarding.STORE=previous


if __name__=='__main__':run()
