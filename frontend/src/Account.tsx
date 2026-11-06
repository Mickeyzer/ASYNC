import {createContext,useContext,useEffect,useRef,useState} from 'react';
import type {FormEvent,ReactNode} from 'react';
import type {Language} from './types';
import SecuritySettings from './SecuritySettings';
import {currentLanguage,label,localError} from './presentation';
import {Modal,UIIcon} from './UI';

export interface User {id:string;username:string;role:'customer'|'partner'|'reviewer'}
type Panel='login'|'register'|'account'|null;
interface AuthState {user:User|null;loading:boolean;refresh:()=>Promise<void>;panel:Panel;openAuth:(mode?:'login'|'register')=>void;openAccount:()=>void;closePanel:()=>void}
const Auth=createContext<AuthState>({user:null,loading:true,refresh:async()=>{},panel:null,openAuth:()=>{},openAccount:()=>{},closePanel:()=>{}});
export const useAuth=()=>useContext(Auth);

export async function api<T>(path:string,method='GET',body?:unknown):Promise<T>{
  const response=await fetch(path,{method,headers:{'X-Requested-With':'Udyam',...(body!==undefined?{'Content-Type':'application/json'}:{})},body:body===undefined?undefined:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw new Error(localError(typeof result.detail==='string'?result.detail:'Please check the supplied fields and try again.',currentLanguage(),response.status));
  return result;
}

export function AuthProvider({children}:{children:ReactNode}){
  const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true),[panel,setPanel]=useState<Panel>(null);
  async function refresh(){try{setUser((await api<{user:User|null}>('/api/account/me')).user);}finally{setLoading(false);}}
  useEffect(()=>{void refresh().catch(()=>{});},[]);
  return <Auth.Provider value={{user,loading,refresh,panel,openAuth:(mode='register')=>setPanel(mode),openAccount:()=>setPanel(user?'account':'login'),closePanel:()=>setPanel(null)}}>{children}</Auth.Provider>;
}

export function SignIn({language,initialMode='login',onSuccess,idPrefix='account'}:{language:Language;initialMode?:'login'|'register';onSuccess?:(registered:boolean)=>void;idPrefix?:string}){
  const {refresh}=useAuth();const hi=language==='hi';
  const [register,setRegister]=useState(initialMode==='register'),[busy,setBusy]=useState(false),[error,setError]=useState('');
  const [password,setPassword]=useState(''),[confirmation,setConfirmation]=useState(''),[showPassword,setShowPassword]=useState(false);
  const confirmationRef=useRef<HTMLInputElement>(null);
  async function submit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const data=new FormData(event.currentTarget);setError('');
    if(register&&password!==confirmation){setError(hi?'दोनों पासवर्ड एक जैसे होने चाहिए।':'Your passwords do not match. Enter the same password in both fields.');confirmationRef.current?.focus();return;}
    setBusy(true);
    try{await api('/api/account/'+(register?'register':'login'),'POST',{username:data.get('username'),password});await refresh();onSuccess?.(register);}
    catch(e){setError(localError((e as Error).message,language));}finally{setBusy(false);}
  }
  function switchMode(){setRegister(!register);setError('');setPassword('');setConfirmation('');setShowPassword(false);}
  return <section className="auth-form" aria-labelledby={`${idPrefix}-title`}>
    <div className="auth-emblem"><UIIcon name={register?'user':'lock'}/></div>
    <p className="eyebrow">UDYAM DIGITAL</p>
    <h2 id={`${idPrefix}-title`}>{hi?(register?'अपना खाता बनाएँ':'फिर से स्वागत है'):(register?'Your business. One account.':'Welcome back.')}</h2>
    <p className="section-copy">{hi?(register?'दस्तावेज़ जाँच सहेजें और अपना डेमो ऑर्डर एक जगह देखें। ईमेल या फ़ोन नंबर की ज़रूरत नहीं।':'अपने दस्तावेज़ और डेमो ऑर्डर वहीं से जारी रखें जहाँ छोड़े थे।'):(register?'Save document checks and follow your demo order in one place. No email or phone number needed.':'Sign in to pick up your document checks and demo orders.')}</p>
    {error&&<p role="alert" id={`${idPrefix}-error`} className="notice error">{localError(error,language)}</p>}
    <form id={`${idPrefix}-form`} onSubmit={submit} className="auth-fields">
      <label htmlFor={`${idPrefix}-username`}>{hi?'यूज़रनेम':'Username'}</label>
      <input id={`${idPrefix}-username`} name="username" required pattern={'[a-zA-Z0-9][a-zA-Z0-9_.\\-]{2,39}'} minLength={3} maxLength={40} autoComplete="username" autoCapitalize="none" spellCheck={false} placeholder={hi?'जैसे clinic_demo':'e.g. clinic_demo'} aria-describedby={`${idPrefix}-username-help`} onChange={()=>setError('')} disabled={busy}/>
      <small id={`${idPrefix}-username-help`}>{hi?'3–40 अक्षर। अंग्रेज़ी अक्षर, संख्या, बिंदु, अंडरस्कोर या हाइफ़न।':'3–40 characters. Letters, numbers, dots, underscores or hyphens.'}</small>
      <label htmlFor={`${idPrefix}-password`}>{hi?'पासवर्ड':'Password'}</label>
      <div className="password-input"><input id={`${idPrefix}-password`} name="password" type={showPassword?'text':'password'} value={password} onChange={e=>{setPassword(e.target.value);setError('');}} required minLength={12} maxLength={128} autoComplete={register?'new-password':'current-password'} aria-describedby={`${idPrefix}-password-help`} disabled={busy}/><button className="password-reveal" type="button" aria-controls={`${idPrefix}-password`} aria-pressed={showPassword} onClick={()=>setShowPassword(!showPassword)} disabled={busy}>{hi?(showPassword?'छिपाएँ':'दिखाएँ'):(showPassword?'Hide':'Show')}</button></div>
      <small id={`${idPrefix}-password-help`} className={register&&password.length>=12?'field-valid':''}>{register&&password.length>=12&&<UIIcon name="check"/>}{hi?'कम से कम 12 अक्षर। ऐसा पासवर्ड चुनें जिसे याद रख सकें।':'At least 12 characters. A memorable phrase works well.'}</small>
      {register&&<><label htmlFor={`${idPrefix}-confirm-password`}>{hi?'पासवर्ड फिर से लिखें':'Confirm password'}</label><input ref={confirmationRef} id={`${idPrefix}-confirm-password`} name="confirm_password" type={showPassword?'text':'password'} value={confirmation} onChange={e=>{setConfirmation(e.target.value);setError('');}} required minLength={12} maxLength={128} autoComplete="new-password" aria-invalid={Boolean(confirmation&&confirmation!==password)} disabled={busy}/></>}
      <button id={`${idPrefix}-submit`} type="submit" className="button primary wide" disabled={busy}>{busy?(hi?'कृपया रुकें…':'Please wait…'):hi?(register?'खाता बनाएँ':'साइन इन करें'):(register?'Create account':'Sign in')}<UIIcon name="arrow"/></button>
    </form>
    <p className="auth-switch">{hi?(register?'पहले से खाता है?':'यहाँ पहली बार आए हैं?'):(register?'Already have an account?':'New to Udyam Digital?')} <button type="button" className="text-button" onClick={switchMode} disabled={busy}>{hi?(register?'साइन इन करें':'नया खाता बनाएँ'):(register?'Use an existing account':'Create a new account')}</button></p>
    <p className="auth-note"><UIIcon name="shield"/>{hi?'केवल काल्पनिक जानकारी का उपयोग करें। निष्क्रिय खाते 30 दिन बाद और दस्तावेज़ रिकॉर्ड 24 घंटे बाद हटते हैं।':'Use fictional details for this demo. Inactive accounts expire after 30 days; document records after 24 hours.'}</p>
  </section>;
}

export function AccountBar({language,onLanguageChange,onOpen,onOperations}:{language:Language;onLanguageChange:(language:Language)=>void;onOpen:(id:string)=>void;onOperations:()=>void}){
  const {user,loading,refresh,panel,openAuth,openAccount,closePanel}=useAuth();const hi=language==='hi';
  const [error,setError]=useState(''),[confirmDelete,setConfirmDelete]=useState(false),[notice,setNotice]=useState<'created'|'signed-in'|null>(null);
  const [records,setRecords]=useState<{session_id:string;status:string;order_reference:string|null}[]>([]),[recordsLoading,setRecordsLoading]=useState(false);
  useEffect(()=>{
    let active=true;setRecords([]);setConfirmDelete(false);setError('');
    if(panel==='account'&&user?.role==='customer'){
      setRecordsLoading(true);void api<{records:typeof records}>('/api/onboarding').then(r=>{if(active)setRecords(r.records);}).catch(e=>{if(active)setError(e.message);}).finally(()=>{if(active)setRecordsLoading(false);});
    }
    return()=>{active=false;};
  },[panel,user?.id]);
  async function logout(){try{await api('/api/account/logout','POST');closePanel();setRecords([]);setNotice(null);await refresh();}catch(e){setError((e as Error).message);}}
  async function remove(){try{await api('/api/account','DELETE');closePanel();setRecords([]);await refresh();}catch(e){setError((e as Error).message);}}
  const dismiss=()=>{closePanel();setError('');};
  const languageControl=<label className="dialog-language"><span className="sr-only">{hi?'भाषा':'Language'}</span><select id="account-language" value={language} onChange={e=>onLanguageChange(e.target.value as Language)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label>;
  return <div className="account-controls">
    <div className={'account-actions '+(user&&user.role!=='customer'?'staff-actions':'')}>
      {user?<><button id="account-toggle" aria-label={hi?`${user.username} का खाता`:`Account for ${user.username}`} className="account-identity" disabled={loading} onClick={openAccount}><span className="avatar">{user.username.slice(0,1).toUpperCase()}</span><span><strong>{user.username}</strong><small>{label(user.role,language)}</small></span><UIIcon name="chevron"/></button>{user.role!=='customer'&&<button className="button secondary" id="open-operations" onClick={onOperations}>{hi?'टीम डैशबोर्ड':'Team dashboard'}</button>}<button className="text-button signout-link" id="sign-out" onClick={logout}>{hi?'साइन आउट':'Sign out'}</button></>:<><button id="account-toggle" type="button" className="button ghost" disabled={loading} onClick={()=>openAuth('login')}>{hi?'साइन इन':'Sign in'}</button><button id="create-account" type="button" className="button primary" disabled={loading} onClick={()=>openAuth('register')}>{hi?'खाता बनाएँ':'Create account'}<UIIcon name="arrow"/></button></>}
    </div>
    {notice&&<div className="account-toast" role="status"><UIIcon name="check"/><span>{hi?(notice==='created'?'खाता तैयार है। अपना व्यवसाय प्लान जारी रखें।':'आप साइन इन हैं। अपना काम जारी रखें।'):(notice==='created'?'Your account is ready. Continue building your plan.':'You’re signed in. Pick up where you left off.')}</span><button className="icon-button" aria-label={hi?'सूचना बंद करें':'Dismiss notification'} onClick={()=>setNotice(null)}><UIIcon name="close"/></button></div>}
    {error&&panel===null&&<div className="account-toast error" role="alert">{localError(error,language)}</div>}
    {(panel==='login'||panel==='register')&&<Modal label={hi?'खाता':'Your account'} onClose={dismiss} closeLabel={hi?'बंद करें':'Close account dialog'}>{languageControl}<SignIn key={panel} language={language} initialMode={panel} onSuccess={registered=>{closePanel();setNotice(registered?'created':'signed-in');}}/></Modal>}
    {panel==='account'&&user&&<Modal label={hi?'आपका खाता':'Your account'} onClose={dismiss} closeLabel={hi?'बंद करें':'Close account dialog'}>
      {languageControl}<section className="account-panel"><p className="eyebrow">{hi?'आपका खाता':'YOUR WORKSPACE'}</p><h2>{hi?'नमस्ते':'Hello'}, {user.username}.</h2><p className="section-copy">{hi?'आपके सहेजे गए दस्तावेज़, ऑर्डर और खाते की सेटिंग।':'Your saved checks, orders and account settings.'}</p>
        {error&&<p role="alert" className="notice error">{localError(error,language)}</p>}
        {user.role==='customer'&&<div className="saved-records"><h3>{hi?'सहेजे गए दस्तावेज़ और ऑर्डर':'Saved checks & orders'}</h3>
          {recordsLoading?<p role="status">{hi?'लोड हो रहा है…':'Loading your records…'}</p>:records.length?records.map(r=><button className="saved-record" key={r.session_id} data-open-record={r.session_id} onClick={()=>{onOpen(r.session_id);closePanel();}}><span className="record-icon"><UIIcon name="file"/></span><span><strong>{r.order_reference||`${hi?'दस्तावेज़ जाँच':'Document check'} · ${r.session_id.slice(0,8)}`}</strong><small>{label(r.status,language)}</small></span><UIIcon name="arrow"/></button>):<div className="empty-records"><UIIcon name="file"/><strong>{hi?'यहाँ से आपकी प्रगति शुरू होगी':'A place for your progress.'}</strong><p>{hi?'दस्तावेज़ जाँच शुरू करने पर वह यहाँ दिखेगी।':'Start a document check and it will appear here. Your record stays available for 24 hours.'}</p><button className="button secondary" onClick={closePanel}>{hi?'मेरा प्लान जारी रखें':'Continue with my plan'}<UIIcon name="arrow"/></button></div>}
        </div>}
        <details className="account-section" id="security-settings"><summary><UIIcon name="lock"/><span>{hi?'पासवर्ड और सत्र':'Password & sessions'}</span><UIIcon name="chevron"/></summary><SecuritySettings key={user.id} language={language}/></details>
        <details className="account-section danger-zone"><summary><span>{hi?'खाता मिटाएँ':'Delete account'}</span><UIIcon name="chevron"/></summary><p>{hi?'आपका खाता और उससे जुड़े स्थानीय रिकॉर्ड मिट जाएँगे।':'This permanently removes your account and its local records.'}</p><label className="consent"><input type="checkbox" checked={confirmDelete} onChange={e=>setConfirmDelete(e.target.checked)}/><span>{hi?'मैं खाता और अपने सभी स्थानीय रिकॉर्ड मिटाना चाहता हूँ।':'Delete my account and all my local records.'}</span></label><button className="button danger" disabled={!confirmDelete} onClick={remove}>{hi?'खाता मिटाएँ':'Delete account'}</button></details>
        <button id="account-sign-out" className="button secondary wide" onClick={logout}>{hi?'साइन आउट':'Sign out'}</button>
      </section>
    </Modal>}
  </div>;
}
