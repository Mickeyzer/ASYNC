import {useEffect,useState} from 'react';
import type {FormEvent} from 'react';
import {api,useAuth} from './Account';
import type {Language} from './types';
import {localError} from './presentation';

interface Session {id:string;created_at:number;expires_at:number;current:boolean}
export default function SecuritySettings({language}:{language:Language}){
  const hi=language==='hi';const {refresh}=useAuth();
  const [sessions,setSessions]=useState<Session[]>([]),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(false);
  async function load(){setSessions((await api<{sessions:Session[]}>('/api/account/sessions')).sessions);}
  useEffect(()=>{void load().catch(e=>setError(e.message));},[]);
  async function revoke(id?:string){setBusy(true);setError('');setNotice(false);try{await api('/api/account/sessions'+(id?'/'+id:''),'DELETE');await refresh();await load();}catch(e){setError((e as Error).message);}finally{setBusy(false);}}
  async function change(event:FormEvent<HTMLFormElement>){
    event.preventDefault();const form=event.currentTarget;const data=new FormData(form);setError('');setNotice(false);
    if(data.get('new_password')!==data.get('confirm_password')){setError(hi?'नए पासवर्ड मेल नहीं खाते।':'New passwords do not match.');return;}
    setBusy(true);try{await api('/api/account/password','POST',{current_password:data.get('current_password'),new_password:data.get('new_password')});form.reset();await load();setNotice(true);}catch(e){setError((e as Error).message);}finally{setBusy(false);}
  }
  const date=(value:number)=>value?new Date(value*1000).toLocaleString(hi?'hi-IN':'en-IN'):(hi?'पुराना सत्र':'Older session');
  return <section id="account-security"><h3>{hi?'खाते की सुरक्षा':'Account security'}</h3>{error&&<p role="alert">{localError(error,language)}</p>}{notice&&<p role="status">{hi?'पासवर्ड बदल दिया गया। अन्य सभी सत्र बंद कर दिए गए हैं।':'Password changed. All other sessions have been signed out.'}</p>}
    <form id="password-form" onSubmit={change} className="form-grid"><label>{hi?'मौजूदा पासवर्ड':'Current password'}<input name="current_password" type="password" required minLength={12} maxLength={128} autoComplete="current-password" disabled={busy}/></label><label>{hi?'नया पासवर्ड (कम से कम 12 अक्षर)':'New password (at least 12 characters)'}<input name="new_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" disabled={busy}/></label><label>{hi?'नया पासवर्ड दोहराएँ':'Repeat new password'}<input name="confirm_password" type="password" required minLength={12} maxLength={128} autoComplete="new-password" disabled={busy}/></label><button id="change-password" className="button secondary" disabled={busy}>{hi?'पासवर्ड बदलें':'Change password'}</button></form>
    <h4>{hi?'सक्रिय सत्र':'Active sessions'}</h4><p className="quiet">{hi?'सत्र 8 घंटे में समाप्त होते हैं। पहचान के लिए बनाई गई तारीख देखें। IP या ब्राउज़र का विवरण संग्रहित नहीं किया जाता।':'Sessions expire after eight hours. Use the creation time to identify a session; IP addresses and browser details are not stored.'}</p><div id="account-sessions">{sessions.map(s=><article key={s.id} data-session={s.id}><p>{s.current?(hi?'यह सत्र':'This session'):(hi?'अन्य सत्र':'Other session')} · {hi?'शुरू':'Created'}: {date(s.created_at)} · {hi?'समाप्ति':'Expires'}: {date(s.expires_at)}</p><button className="text-button" disabled={busy} onClick={()=>revoke(s.id)}>{hi?'सत्र बंद करें':'Revoke session'}</button></article>)}</div><button id="revoke-other-sessions" className="button secondary" disabled={busy||sessions.length<2} onClick={()=>revoke()}>{hi?'अन्य सभी सत्र बंद करें':'Sign out all other sessions'}</button>
  </section>;
}
