import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { BundleItem, Language, Profile, Quote } from './types';
import {SignIn,useAuth} from './Account';
import {label,localError} from './presentation';
import {UIIcon} from './UI';

type Kind = 'gst_certificate' | 'udyam_certificate' | 'signatory_id' | 'address_proof';
const kinds: Kind[] = ['gst_certificate','udyam_certificate','signatory_id','address_proof'];
interface DocumentInfo {kind: Kind; legibility: string; masked_identifier: string | null; fields: Record<string,string|null> | null}
interface Issue {code:string; document:Kind; message:string; message_hi:string; severity:string}
interface Order {reference:string; status:'accepted'|'installation_scheduled'|'activated'; expected_date:string; reference_date:string; schedule:{product_id:string;name:string;install_days:number;expected_date:string}[]}
interface RecordView {session_id:string; expires_at:number; status:string; quote:Quote; documents:Partial<Record<Kind,DocumentInfo>>; extraction_available:boolean; kyc:{status:string;issues:Issue[];reference_date:string}|null; order:Order|null; events:{name:string;at:number}[]; access_code?:string;handoff?:{reason:string;status:string}|null}

const words: Record<Language,Record<string,string>> = {
  en: {
    title:'Add your business documents.', intro:'Use only the supplied fictional documents for this demo. Keep all four documents from the same applicant together.',
    consentTitle:'Before you upload', consentText:'With your permission, document images go to Gemini to read the fields and the local app compares them with the supplied mock GSTIN and Udyam registries. Images are not saved by this app. Extracted fields stay in server memory for up to 30 minutes, or until you submit the demo order. Masked check summaries, consent, estimate and order events are kept locally for 24 hours. You can delete this record at any time. Google handles submitted data under your API account settings; deleting the local record does not delete provider records.',
    consent:'I agree to document extraction with Gemini, mock checks and the stated local retention.', start:'Start document checks', back:'← Return to estimate / discovery', loading:'Working…',
    gst_certificate:'GST certificate', udyam_certificate:'Udyam certificate', signatory_id:'Signatory ID', address_proof:'Address proof', upload:'Upload and extract', replace:'Replace image', formats:'PNG or JPEG, up to 5 MB. Files are processed one at a time.',
    missing:'Not uploaded', extracted:'Fields extracted; review them below.', noFields:'Extracted fields expired or the server restarted. Upload again if checks have not passed.', noGuess:'Extraction failed. No document fields have been guessed. Retry with a clear image.',
    declaration:'Review the extracted details', business_name:'Business / trade name', business_address:'Business address', signatory_name:'Signatory name', legal_name:'Legal name', address:'Address', city:'City', state:'State', registration_date:'Registration date', issue_date:'Bill date', expiry_date:'Valid until', gstin:'GSTIN (masked)', udyam_number:'Udyam number (masked)', id_number:'ID number (masked)',
    confirmed:'I reviewed the extracted fields against the documents and confirm these business details.', check:'Check documents', reference:'All document date checks use the dataset date: 15 July 2026. Address proof must be no older than 90 days.',
    documents_pending:'Documents pending', action_required:'Action required', needs_review:'Manual review required', checks_passed:'Demo document checks passed', order_created:'Demo order created',
    unresolved:'Replace missing, invalid or inconsistent documents and run the checks again. You can request help below. An authorized reviewer can confirm legibility after checking originals; other failed requirements still need correction.',
    checked:'Mock registry and document consistency checks passed. These checks do not establish real identity, ownership or signatory authority.',
    checkout:'Review and create your demo order', monthly:'Monthly services', setup:'One-time setup', first:'First month estimate', tax:'Taxes are not calculated or included.', contract:'month minimum contract', quantity:'Qty',
    accept:'I accept the displayed estimate and per-service contract terms for this demo.', simulationConsent:'I understand this is a simulation: no payment, real service-availability check, installation or activation occurs.', submit:'Create demo order',
    tracker:'Your demo order', accepted:'Order accepted', installation_scheduled:'Installation scheduled', activated:'Services activated', simulated:'SIMULATION · No real services are purchased or activated.', eta:'Expected activation in the demo calendar', days:'days from 15 July 2026', advance:'Simulate next stage', refresh:'Refresh status', timeline:'Order activity',
    consent_recorded:'Consent recorded', document_received:'Document received', document_replaced:'Document received / replaced', order_accepted:'Demo order accepted',
    access:'Save your access details', accessHelp:'Download this private access code to reopen the record after a refresh or server restart. Anyone with the code can view, advance or delete this demo record. No browser storage is used.', save:'Download access details', resume:'Resume a saved check or order', session:'Record ID', code:'Private access code', open:'Open record', expires:'Local record expires',
    deleteConsent:'Delete this local record and withdraw consent for further processing.', delete:'Delete record', deleted:'The local record and any retained extracted fields have been deleted.',
    network:'The request could not be completed. Check the server connection and retry.', invalidFile:'Choose a PNG or JPEG no larger than 5 MB.',
  },
  hi: {
    title:'आपके दस्तावेज़ों की जाँच।', intro:'इस डेमो में केवल दिए गए काल्पनिक दस्तावेज़ उपयोग करें। चारों दस्तावेज़ एक ही आवेदक के हों।',
    consentTitle:'अपलोड करने से पहले', consentText:'आपकी अनुमति से दस्तावेज़ों की छवियाँ Gemini को जानकारी पढ़ने के लिए भेजी जाएँगी। स्थानीय ऐप नमूना GSTIN और उद्यम रजिस्ट्री से तुलना करेगा। ऐप छवियाँ सहेजता नहीं है। निकाली गई जानकारी सर्वर की मेमोरी में अधिकतम 30 मिनट या डेमो ऑर्डर जमा होने तक रहती है। छिपे पहचान नंबरों वाले जाँच सारांश, सहमति, अनुमान और ऑर्डर गतिविधि स्थानीय रूप से 24 घंटे रखे जाते हैं। आप रिकॉर्ड मिटा सकते हैं। Google की डेटा प्रक्रिया आपके API खाते की सेटिंग पर निर्भर है; स्थानीय रिकॉर्ड मिटाने से Google के रिकॉर्ड नहीं मिटते।',
    consent:'मैं Gemini से जानकारी पढ़ने, नमूना जाँच और बताई गई स्थानीय संग्रह अवधि के लिए सहमत हूँ।', start:'दस्तावेज़ जाँच शुरू करें', back:'← अनुमान / जानकारी पर लौटें', loading:'काम जारी है…',
    gst_certificate:'GST प्रमाणपत्र', udyam_certificate:'उद्यम प्रमाणपत्र', signatory_id:'हस्ताक्षरकर्ता पहचान पत्र', address_proof:'पते का प्रमाण', upload:'अपलोड करके जानकारी पढ़ें', replace:'छवि बदलें', formats:'PNG या JPEG, अधिकतम 5 MB। एक समय पर एक फ़ाइल।',
    missing:'अपलोड नहीं हुआ', extracted:'जानकारी पढ़ी गई; नीचे जाँचें।', noFields:'जानकारी की अवधि समाप्त है या सर्वर फिर शुरू हुआ। जाँच सफल नहीं हुई हो तो दोबारा अपलोड करें।', noGuess:'जानकारी पढ़ना असफल रहा। कोई अनुमानित जानकारी नहीं भरी गई। साफ़ छवि से फिर प्रयास करें।',
    declaration:'निकाली गई जानकारी की समीक्षा करें', business_name:'व्यवसाय / व्यापार का नाम', business_address:'व्यवसाय का पता', signatory_name:'हस्ताक्षरकर्ता का नाम', legal_name:'कानूनी नाम', address:'पता', city:'शहर', state:'राज्य', registration_date:'पंजीकरण की तारीख', issue_date:'बिल की तारीख', expiry_date:'वैधता की अंतिम तारीख', gstin:'GSTIN (छिपा हुआ)', udyam_number:'उद्यम नंबर (छिपा हुआ)', id_number:'पहचान नंबर (छिपा हुआ)',
    confirmed:'मैंने निकाली गई जानकारी दस्तावेज़ों से मिलाई है और व्यवसाय की जानकारी की पुष्टि करता/करती हूँ।', check:'दस्तावेज़ जाँचें', reference:'सभी तारीखों की जाँच डेटासेट की 15 जुलाई 2026 तारीख के अनुसार है। पते का प्रमाण 90 दिन से पुराना नहीं होना चाहिए।',
    documents_pending:'दस्तावेज़ बाकी हैं', action_required:'सुधार आवश्यक', needs_review:'मानवीय समीक्षा आवश्यक', checks_passed:'डेमो दस्तावेज़ जाँच सफल', order_created:'डेमो ऑर्डर बना',
    unresolved:'गायब, गलत या असंगत दस्तावेज़ बदलकर फिर जाँचें। नीचे सहायता माँग सकते हैं। अधिकृत समीक्षक मूल दस्तावेज़ देखकर पाठ की स्पष्टता की पुष्टि कर सकता है; अन्य असफल शर्तों में सुधार आवश्यक है।',
    checked:'नमूना रजिस्ट्री और दस्तावेज़ मिलान सफल है। यह वास्तविक पहचान, स्वामित्व या हस्ताक्षर अधिकार का प्रमाण नहीं है।',
    checkout:'अनुमान देखकर डेमो ऑर्डर बनाएँ', monthly:'मासिक सेवाएँ', setup:'एक बार का सेटअप', first:'पहले महीने का अनुमान', tax:'करों की गणना नहीं हुई है और वे शामिल नहीं हैं।', contract:'महीने का न्यूनतम अनुबंध', quantity:'मात्रा',
    accept:'मैं इस डेमो के लिए दिखाए गए अनुमान और हर सेवा की अनुबंध शर्तों से सहमत हूँ।', simulationConsent:'मैं समझता/समझती हूँ कि यह सिमुलेशन है: कोई भुगतान, वास्तविक उपलब्धता जाँच, स्थापना या सक्रियण नहीं होगा।', submit:'डेमो ऑर्डर बनाएँ',
    tracker:'आपका डेमो ऑर्डर', accepted:'ऑर्डर स्वीकार हुआ', installation_scheduled:'स्थापना तय हुई', activated:'सेवाएँ सक्रिय हुईं', simulated:'सिमुलेशन · कोई वास्तविक सेवा खरीदी या सक्रिय नहीं की जाती।', eta:'डेमो कैलेंडर में अपेक्षित सक्रियण', days:'दिन, 15 जुलाई 2026 से', advance:'अगला चरण सिमुलेट करें', refresh:'स्थिति फिर देखें', timeline:'ऑर्डर गतिविधि',
    consent_recorded:'सहमति दर्ज हुई', document_received:'दस्तावेज़ मिला', document_replaced:'दस्तावेज़ मिला / बदला गया', order_accepted:'डेमो ऑर्डर स्वीकार हुआ',
    access:'अपनी पहुँच की जानकारी सहेजें', accessHelp:'पेज रीफ़्रेश या सर्वर फिर शुरू होने के बाद रिकॉर्ड खोलने के लिए निजी कोड डाउनलोड करें। जिसके पास कोड होगा वह डेमो रिकॉर्ड देख, आगे बढ़ा या मिटा सकता है। ब्राउज़र में जानकारी संग्रहित नहीं होती।', save:'पहुँच की जानकारी डाउनलोड करें', resume:'सहेजी गई जाँच या ऑर्डर खोलें', session:'रिकॉर्ड ID', code:'निजी पहुँच कोड', open:'रिकॉर्ड खोलें', expires:'स्थानीय रिकॉर्ड समाप्त होगा',
    deleteConsent:'यह स्थानीय रिकॉर्ड मिटाएँ और आगे की प्रक्रिया की सहमति वापस लें।', delete:'रिकॉर्ड मिटाएँ', deleted:'स्थानीय रिकॉर्ड और मेमोरी में बची निकाली गई जानकारी मिटा दी गई है।',
    network:'अनुरोध पूरा नहीं हुआ। सर्वर कनेक्शन जाँचकर फिर प्रयास करें।', invalidFile:'अधिकतम 5 MB की PNG या JPEG चुनें।',
  },
};

export default function Onboarding({language, initial, initialRecord, onExit, onStage}: {
  language:Language; initialRecord?:string;initial:{profile:Profile;items:BundleItem[]}|null; onExit:()=>void; onStage:(stage:number)=>void;
}) {
  const {user,loading,openAccount}=useAuth();
  const [followConsent,setFollowConsent]=useState(false),[contact,setContact]=useState(''),[helpReason,setHelpReason]=useState('documents');
  const [record,setRecord]=useState<RecordView|null>(null);
  const [access,setAccess]=useState('');
  const [resumeId,setResumeId]=useState('');
  const [resumeCode,setResumeCode]=useState('');
  const [consent,setConsent]=useState(false);
  const [busy,setBusy]=useState(false);
  const [uploading,setUploading]=useState<Kind|null>(null),[dragging,setDragging]=useState<Kind|null>(null);
  const [error,setError]=useState('');
  const [deleted,setDeleted]=useState(false);
  const [declaration,setDeclaration]=useState({business_name:'',business_address:'',signatory_name:''});
  const [confirmed,setConfirmed]=useState(false);
  const [accept,setAccept]=useState(false);
  const [simulate,setSimulate]=useState(false);
  const [deleteConsent,setDeleteConsent]=useState(false);
  const title=useRef<HTMLHeadingElement>(null);
  const errorBox=useRef<HTMLDivElement>(null);
  const t=(key:string)=>words[language][key]|| (language==='hi'?label(key,language):words.en[key]||key);
  const reviewNotice=language==='hi'?'दस्तावेज़ आपके खाते से जुड़े रहेंगे। अधिकृत समीक्षक अस्पष्ट दस्तावेज़ों की जानकारी जाँच सकता है; पार्टनर को केवल आपकी अलग सहमति पर यात्रा का सारांश और संपर्क दिखेगा। निजी नंबर न लिखें।':'Records belong to your account. Authorized reviewers may inspect ambiguous document fields. Partners receive only a journey summary and contact after your separate follow-up consent. Local aggregate event counts are kept for 30 days without customer IDs or document values.';
  const money=(n:number)=>new Intl.NumberFormat(language==='hi'?'hi-IN':'en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(n);
  useEffect(()=>{onStage(record?.order?5:4);window.scrollTo({top:0,behavior:'instant'});title.current?.focus({preventScroll:true});},[record?.session_id,record?.order?.status,onStage]);
  useEffect(()=>{if(error) errorBox.current?.focus();},[error]);
  useEffect(()=>{if(initialRecord&&user)void perform(()=>request('/api/onboarding/'+initialRecord));},[initialRecord,user?.id]);

  async function request(path:string, method='GET', body?:unknown, key=access):Promise<RecordView> {
    const headers:Record<string,string>={'X-Requested-With':'Udyam'};
    if(key) headers['X-Order-Key']=key;
    if(body instanceof File) headers['Content-Type']=body.type;
    else if(body!==undefined) headers['Content-Type']='application/json';
    const response=await fetch(path,{method,headers,body:body instanceof File?body:body===undefined?undefined:JSON.stringify(body)});
    const result=await response.json();
    if(!response.ok) throw new Error(localError(typeof result.detail==='string'?result.detail:(language==='hi'?result.detail?.message_hi:result.detail?.message)||result.detail?.message||t('network'),language,response.status));
    return result;
  }
  async function perform(work:()=>Promise<RecordView>) {
    setBusy(true);setError('');
    try {const next=await work();setRecord(next);return next;}
    catch(e) {setError(e instanceof Error?e.message:t('network'));return null;}
    finally {setBusy(false);}
  }
  async function start() {
    if(!consent||!initial) return;
    const next=await perform(()=>request('/api/onboarding','POST',{...initial,consent:true}));
    if(next?.access_code) setAccess(next.access_code);
  }
  async function resume(event:FormEvent) {
    event.preventDefault();
    if(!/^[a-f0-9]{32}$/.test(resumeId.trim())) {setError(t('session')+': '+t('network'));return;}
    const key=resumeCode.trim();
    const next=await perform(()=>request('/api/onboarding/'+resumeId.trim()+'/claim','POST',{access_code:key}));
    if(next) {setAccess(key);setResumeCode('');}
  }
  async function upload(kind:Kind,file:File) {
    if(!record) return;
    if(!['image/png','image/jpeg'].includes(file.type)||file.size>5*1024*1024) {setError(t('invalidFile'));return;}
    setUploading(kind);setConfirmed(false);setAccept(false);setSimulate(false);
    const next=await perform(()=>request(`/api/onboarding/${record.session_id}/documents/${kind}`,'POST',file));
    setUploading(null);
    const fields=next?.documents[kind]?.fields;
    if(fields) setDeclaration(old=>({
      business_name:old.business_name||fields.business_name||'',
      business_address:old.business_address||fields.address||'',
      signatory_name:old.signatory_name||fields.signatory_name||'',
    }));
  }
  async function check(event:FormEvent) {
    event.preventDefault();if(!record||!confirmed) return;
    setAccept(false);setSimulate(false);
    await perform(()=>request(`/api/onboarding/${record.session_id}/check`,'POST',{...declaration,confirmed:true}));
  }
  function saveAccess() {
    if(!record) return;
    const text=`Udyam Digital demo - private access\nRecord ID: ${record.session_id}\nAccess code: ${access}\nExpires: ${new Date(record.expires_at*1000).toISOString()}\nOpen the local app and choose Resume a saved check or order. Keep this file private.\n`;
    const url=URL.createObjectURL(new Blob([text],{type:'text/plain;charset=utf-8'}));
    const a=document.createElement('a');a.href=url;a.download='udyam-private-access.txt';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  async function forget() {
    if(!record||!deleteConsent) return;
    setBusy(true);setError('');
    try {await request(`/api/onboarding/${record.session_id}`,'DELETE');setRecord(null);setAccess('');setDeclaration({business_name:'',business_address:'',signatory_name:''});setDeleted(true);}
    catch(e) {setError(e instanceof Error?e.message:t('network'));}
    finally {setBusy(false);}
  }
  const totals=record&&<div className="quote-breakdown">{[['monthly',record.quote.monthly_total],['setup',record.quote.setup_total],['first',record.quote.first_month_estimate]].map(([label,n])=><div className="quote-row" key={label}><span>{t(String(label))}</span><strong>{money(Number(n))}</strong></div>)}<p className="quiet">{t('tax')}</p></div>;
  if(loading)return <p role="status">{t('loading')}</p>;
  if(!user)return <><button className="text-button" onClick={onExit}>{t('back')}</button><div className="registration-gate"><div className="registration-context"><UIIcon name="file"/><p>{language==='hi'?'आपका चुना हुआ बंडल तैयार है। दस्तावेज़ सुरक्षित रखने और अपना डेमो ऑर्डर देखने के लिए खाता बनाएँ।':'Your selected bundle is ready. Create an account to save document checks and follow your demo order.'}</p></div><SignIn language={language} initialMode="register" idPrefix="onboarding-account"/></div></>;
  if(user.role!=='customer')return <p>{language==='hi'?'दस्तावेज़ जमा करने के लिए ग्राहक खाते से साइन इन करें।':'Sign in with a customer account to submit documents. Staff tasks are in the team dashboard.'}</p>;
  return <section id="onboarding-view">
    <button className="text-button" type="button" onClick={onExit} disabled={busy}>{t('back')}</button>
    <div id="onboarding-error" ref={errorBox} className="notice error" role="alert" tabIndex={-1} hidden={!error}>{localError(error,language)}</div>
    <div className="section-heading"><div><span className="eyebrow">{language==='hi'?(record?.order?'चरण 05 / स्थिति':'चरण 04 / दस्तावेज़'):(record?.order?'STEP 05 / TRACK':'STEP 04 / DOCUMENTS')}</span><h1 ref={title} tabIndex={-1}>{t(record?.order?'tracker':'title')}</h1></div></div>
    {deleted?<div className="notice success" role="status">{t('deleted')}</div>:!record?<>
      {initial&&<div className="onboarding-consent"><h3>{t('consentTitle')}</h3><p>{t('intro')}</p>
        <ul className="consent-points"><li><UIIcon name="file"/><span>{language==='hi'?'चार दस्तावेज़ों से व्यवसाय की जानकारी पढ़ी जाएगी और दिए गए डेमो रजिस्टर से मिलाई जाएगी।':'We’ll read the four documents with Gemini and compare the details with the supplied demo registries.'}</span></li><li><UIIcon name="clock"/><span>{language==='hi'?'तस्वीरें सुरक्षित नहीं रखी जातीं। पढ़ी गई जानकारी 30 मिनट या ऑर्डर भेजने तक और सहेजे गए रिकॉर्ड 24 घंटे तक रहते हैं।':'Images are not saved. Extracted details expire after 30 minutes or order submission; saved records expire after 24 hours.'}</span></li><li><UIIcon name="shield"/><span>{language==='hi'?'अनुमति वाले समीक्षक अस्पष्ट जानकारी जाँच सकते हैं। Google के डेटा नियम अलग हैं। पार्टनर संपर्क के लिए अलग अनुमति ली जाएगी।':'Authorized reviewers can check ambiguous fields. Google’s data terms apply separately. Partner contact needs your separate permission.'}</span></li></ul>
        <details className="consent-details"><summary>{language==='hi'?'डेटा उपयोग की पूरी जानकारी':'Read the full data-use notice'}</summary><p>{t('consentText')}</p><p>{reviewNotice}</p></details>
        <label className="consent"><input id="kyc-consent" type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)} disabled={busy}/><span>{t('consent')}</span></label><button id="start-kyc" className="button primary" type="button" disabled={!consent||busy} onClick={start}>{t(busy?'loading':'start')}<UIIcon name="arrow"/></button></div>}
      {!initial&&<div className="resume-intro"><h3>{language==='hi'?'अपना सहेजा हुआ काम ढूँढें':'Pick up where you left off.'}</h3><p className="quiet">{language==='hi'?'आपके दस्तावेज़ और ऑर्डर आपके खाते में उपलब्ध हैं।':'Your account keeps your saved checks and orders together.'}</p><button id="find-account-records" className="button primary" onClick={openAccount}>{language==='hi'?'मेरे सहेजे हुए रिकॉर्ड':'View my saved records'}<UIIcon name="arrow"/></button></div>}
      <details className="legacy-recovery"><summary>{language==='hi'?'पुराना रिकवरी कोड है?':'Have an older recovery code?'}</summary><form className="resume-form form-grid" onSubmit={resume}><h3>{t('resume')}</h3><label><span>{t('session')}</span><input id="resume-id" value={resumeId} onChange={e=>setResumeId(e.target.value)} required maxLength={32} disabled={busy}/></label><label><span>{t('code')}</span><input id="resume-code" type="password" value={resumeCode} onChange={e=>setResumeCode(e.target.value)} required maxLength={100} autoComplete="off" disabled={busy}/></label><button id="resume-record" className="button secondary" disabled={busy}>{t(busy?'loading':'open')}</button></form></details>
    </>:<>
      <details className="access-box"><summary>{t('access')}</summary><p className="quiet">{language==='hi'?'यह रिकॉर्ड आपके खाते से जुड़ा है। साइन इन करके खाता मेनू से इसे फिर खोलें।':'This record belongs to your account. Sign in and use the Account menu to reopen it. Older unclaimed records require the private recovery code to link them to your account.'}</p><p className="quiet">{t('expires')}: {new Date(record.expires_at*1000).toLocaleString(language==='hi'?'hi-IN':'en-IN')}</p>{access&&<button id="save-access" className="button secondary" onClick={saveAccess}>{t('save')}</button>}</details>
      {!record.order?<>
        <button id="refresh-check" className="button secondary" disabled={busy} onClick={()=>perform(()=>request(`/api/onboarding/${record.session_id}`))}>{language==='hi'?'जाँच की स्थिति फिर देखें':'Refresh check status'}</button>
        <div className="notice info"><strong>{t(record.status)}</strong><p>{t('reference')}</p></div>
        <div className="document-progress"><h3>{language==='hi'?'अपने चार दस्तावेज़ जोड़ें':'Add your four documents'}</h3><span>{Object.keys(record.documents).length} / 4 {language==='hi'?'जुड़ गए':'added'}</span></div>
        <div className="document-grid">{kinds.map(kind=>{
          const doc=record.documents[kind];
          return <article key={kind} className="document-card" data-document={kind} aria-busy={uploading===kind}><h3>{t(kind)}</h3><p className="quiet">{uploading===kind?(language==='hi'?'दस्तावेज़ पढ़ा जा रहा है…':'Reading your document…'):t(doc?'extracted':'missing')}</p>
            <label className={'upload-label '+(dragging===kind?'dragging':'')} onDragOver={e=>{e.preventDefault();if(!busy)setDragging(kind);}} onDragLeave={()=>setDragging(null)} onDrop={e=>{e.preventDefault();setDragging(null);if(busy)return;const files=e.dataTransfer.files;if(files.length!==1){setError(language==='hi'?'एक बार में एक तस्वीर चुनें।':'Choose one image at a time.');return;}void upload(kind,files[0]);}}>
              <UIIcon name="upload"/><span><strong>{t(doc?'replace':'upload')}</strong><small>{language==='hi'?'तस्वीर खींचकर यहाँ छोड़ें या क्लिक करें · PNG / JPEG · 5 MB':'Drop an image here or browse · PNG / JPEG · 5 MB'}</small></span><input className="sr-only" id={'upload-'+kind} type="file" accept="image/png,image/jpeg" disabled={busy} aria-label={`${t(doc?'replace':'upload')}: ${t(kind)}`} onChange={e=>{const file=e.target.files?.[0];e.target.value='';if(file) void upload(kind,file);}}/>
            </label>
            {doc?.fields?<dl className="extracted-fields">{Object.entries(doc.fields).filter(([key,value])=>value&& !['document_type','legibility'].includes(key)).map(([key,value])=><div key={key}><dt>{t(key)}</dt><dd>{value}</dd></div>)}</dl>:doc&&<p className="quiet">{t('noFields')}</p>}
          </article>;
        })}</div><p className="quiet">{t('formats')}</p>{busy&&<p role="status">{t('loading')}</p>}
        {record.kyc&&<div id="kyc-result" className={'notice '+(record.kyc.status==='checks_passed'?'success':'warning')} role="status"><strong>{t(record.kyc.status)}</strong>{record.kyc.status==='checks_passed'?<p>{t('checked')}</p>:<><p>{t('unresolved')}</p><ul>{record.kyc.issues.map((issue,i)=><li key={i}><strong>{t(issue.document)}:</strong> {language==='hi'?issue.message_hi:issue.message}</li>)}</ul></>}</div>}
        {Object.values(record.documents).some(doc=>doc?.fields)?<form id="document-confirmation" onSubmit={check}><h3>{t('declaration')}</h3><div className="form-grid">{(['business_name','business_address','signatory_name'] as const).map(key=><label key={key}><span>{t(key)}</span><input name={key} value={declaration[key]} minLength={key==='business_address'?5:2} maxLength={key==='business_address'?600:300} required disabled={busy} onChange={e=>{setDeclaration({...declaration,[key]:e.target.value});setConfirmed(false);setAccept(false);setSimulate(false);setRecord({...record,kyc:null,status:'documents_pending'});}}/></label>)}</div><label className="consent"><input id="confirm-documents" type="checkbox" checked={confirmed} disabled={busy} onChange={e=>setConfirmed(e.target.checked)}/><span>{t('confirmed')}</span></label><button id="check-documents" className="button primary" disabled={busy||!confirmed}>{t(busy?'loading':'check')}</button></form>:<div className="document-next"><UIIcon name="check"/><div><h3>{language==='hi'?'अगला कदम: निकाली गई जानकारी जाँचें':'Next: review the extracted details'}</h3><p>{language==='hi'?'पहली तस्वीर अपलोड करने के बाद आपकी जानकारी यहाँ दिखेगी।':'Your details will appear here after you upload your first document.'}</p></div></div>}
        {record.kyc?.status==='checks_passed'&&<section id="demo-checkout" className="checkout-box"><h3>{t('checkout')}</h3>{record.quote.items.map(item=><div className="service" key={item.product_id}><strong>{item.name}</strong><p className="quiet">{t('quantity')}: {item.quantity} · {item.contract_months} {t('contract')}</p><div className="quote-row"><span>{t('monthly')}</span><strong>{money(item.monthly_total)}</strong></div><div className="quote-row"><span>{t('setup')}</span><strong>{money(item.setup_total)}</strong></div></div>)}{totals}<label className="consent"><input id="accept-estimate" type="checkbox" checked={accept} disabled={busy} onChange={e=>setAccept(e.target.checked)}/><span>{t('accept')}</span></label><label className="consent"><input id="accept-simulation" type="checkbox" checked={simulate} disabled={busy} onChange={e=>setSimulate(e.target.checked)}/><span>{t('simulationConsent')}</span></label><button id="submit-order" className="button primary" disabled={busy||!accept||!simulate} onClick={()=>perform(()=>request(`/api/onboarding/${record.session_id}/submit`,'POST',{accept_estimate:true,acknowledge_simulation:true}))}>{t(busy?'loading':'submit')}</button></section>}
      </>:<section id="order-tracker"><div className="notice info"><strong>{t('simulated')}</strong></div><h3>{record.order.reference}</h3><ol className="order-stages">{(['accepted','installation_scheduled','activated'] as const).map(stage=><li key={stage} aria-current={record.order?.status===stage?'step':undefined}>{t(stage)}</li>)}</ol><p><strong>{t(record.order.status)}</strong></p><p className="quiet">{t('eta')}: {record.order.expected_date}</p>{record.order.schedule.map(item=><div className="quote-row" key={item.product_id}><span>{item.name}</span><span>{item.install_days} {t('days')}</span></div>)}{totals}<div className="action-row"><button id="refresh-order" className="button secondary" disabled={busy} onClick={()=>perform(()=>request(`/api/onboarding/${record.session_id}`))}>{t('refresh')}</button>{record.order.status!=='activated'&&<button id="advance-order" className="button secondary" disabled={busy} onClick={()=>perform(()=>request(`/api/onboarding/${record.session_id}/advance`,'POST',{expected_status:record.order?.status}))}>{t(busy?'loading':'advance')}</button>}</div><h3>{t('timeline')}</h3><ol className="order-events">{record.events.map((event,i)=><li key={i}><span>{t(event.name)}</span><time>{new Date(event.at*1000).toLocaleString(language==='hi'?'hi-IN':'en-IN')}</time></li>)}</ol></section>}
      <section className="account-box" id="partner-handoff"><h3>{language==='hi'?'टीम की सहायता लें':'Ask the team for help'}</h3><p className="quiet">{language==='hi'?'केवल काल्पनिक संपर्क दें। सहमति पर टीम और नियुक्त पार्टनर संपर्क तथा इस यात्रा का सारांश देख सकेंगे। जानकारी रिकॉर्ड की अवधि तक रहेगी।':'Use a synthetic contact only. With your consent, the review team and assigned partner can see this contact and journey summary for follow-up, until this record expires. No message is sent automatically.'}</p>{record.handoff?<><p role="status">{t(record.handoff.status)} · {t(record.handoff.reason)}</p><button className="button secondary" id="withdraw-handoff" disabled={busy} onClick={()=>perform(()=>request(`/api/onboarding/${record.session_id}/handoff`,'DELETE'))}>{language==='hi'?'संपर्क की सहमति वापस लें':'Withdraw follow-up consent'}</button></>:<form onSubmit={e=>{e.preventDefault();if(followConsent)void perform(()=>request(`/api/onboarding/${record.session_id}/handoff`,'POST',{consent:true,contact,reason:helpReason}));}} className="form-grid"><label>{language==='hi'?'काल्पनिक संपर्क':'Synthetic contact'}<input id="handoff-contact" required minLength={3} maxLength={120} value={contact} onChange={e=>setContact(e.target.value)} disabled={busy}/></label><label>{language==='hi'?'सहायता का विषय':'Help with'}<select value={helpReason} onChange={e=>setHelpReason(e.target.value)}>{['documents','bundle','installation','other'].map(r=><option key={r} value={r}>{t(r)}</option>)}</select></label><label className="consent"><input id="followup-consent" type="checkbox" checked={followConsent} onChange={e=>setFollowConsent(e.target.checked)}/><span>{language==='hi'?'मैं संपर्क साझा करने और सहायता के लिए सहमत हूँ।':'I consent to sharing my contact and summary for follow-up.'}</span></label><button id="request-handoff" className="button secondary" disabled={busy||!followConsent}>{language==='hi'?'सहायता माँगें':'Request follow-up'}</button></form>}</section>
      <div className="delete-record"><label className="consent"><input id="delete-consent" type="checkbox" checked={deleteConsent} disabled={busy} onChange={e=>setDeleteConsent(e.target.checked)}/><span>{t('deleteConsent')}</span></label><button id="delete-record" className="text-button" disabled={busy||!deleteConsent} onClick={forget}>{t('delete')}</button></div>
    </>}
  </section>;
}
