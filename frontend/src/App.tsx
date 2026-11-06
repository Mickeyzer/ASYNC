import { useEffect, useRef, useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { ApiError, post } from './api';
import Onboarding from './Onboarding';
import {AccountBar,useAuth} from './Account';
import Operations from './Operations';
import VoiceInput from './VoiceInput';
import {UIIcon} from './UI';
import {localError} from './presentation';
import { needIcons, translations } from './i18n';
import type { AdvisorReply, BusinessForm, BundleItem, Explanation, Language, LookupReply, Need, Product, Profile, Quote, QuoteLine, Recommendations } from './types';

const initialForm: BusinessForm = {business_type:'', city_tier:'', employees:'', sites:'1', monthly_budget:'', current_internet:'', gstin_claim:'unsure', needs:[]};
type Translate = (key: string) => string;
type Localize = (text: Explanation) => string;
type FormatMoney = (amount: number) => string;

function Icon({need}: {need: Need}) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={needIcons[need]} /></svg>;
}

function Status({product, t}: {product: Product; t: Translate}) {
  const label = product.status === 'conditional' && product.reasons.some(reason=>reason.code==='gstin_unverified') ? 'gstinConditional' : product.status;
  return <span className={`status ${product.status}`}>{t(label)}</span>;
}

function Field({label, help, children}: {label: string; help?: string; children: ReactNode}) {
  return <label><span>{label}</span>{children}{help && <small>{help}</small>}</label>;
}

function ServiceCard({item, why, busy, t, localize, money, onRemove, onQuantity}: {
  item: QuoteLine; why?: Explanation; busy: boolean; t: Translate; localize: Localize; money: FormatMoney;
  onRemove: () => void; onQuantity: (quantity: number) => void;
}) {
  const [quantity, setQuantity] = useState(String(item.quantity));
  useEffect(()=>setQuantity(String(item.quantity)),[item.quantity]);
  function commit() {
    const next = Number(quantity);
    if(next !== item.quantity) onQuantity(next);
    if(!Number.isInteger(next) || next < 1 || next > 10000) setQuantity(String(item.quantity));
  }
  return <article className="service" data-product={item.product_id}>
    <div className="service-top"><div><div className="category">{item.category}</div><h4>{item.name}</h4></div><button type="button" className="remove" data-remove={item.product_id} aria-label={`${t('remove')} ${item.name}`} disabled={busy} onClick={onRemove}>×</button></div>
    <Status product={item} t={t}/>
    {item.reasons.map(reason=><p className="reason" key={reason.code}>{localize(reason)}</p>)}
    <p className="service-description">{why ? localize(why) : item.description}</p>
    <div className="service-bottom"><label className="quantity">{t('quantity')}<input type="number" min="1" max="10000" step="1" value={quantity} disabled={busy} data-quantity={item.product_id} aria-label={`${t('quantityHelp')} ${item.name}`} onChange={event=>setQuantity(event.target.value)} onBlur={commit} onKeyDown={event=>{if(event.key==='Enter') {event.preventDefault();event.currentTarget.blur();}}}/></label><div className="line-price">{money(item.monthly_total)}<small>{t('perMonth')}</small></div></div>
    <div className="service-meta">{money(item.monthly_price)} / {item.unit.replace('per ','')} · {item.contract_months} {t('contract')}<br/>{money(item.setup_fee)} {t('setupPerUnit')}</div>
  </article>;
}

export default function App() {
  const {user,openAuth}=useAuth();
  const [operations,setOperations]=useState(false);
  const [requestedSection,setRequestedSection]=useState('');
  const [savedRecord,setSavedRecord]=useState('');
  const [language, setLanguage] = useState<Language>('en');
  const [form, setForm] = useState<BusinessForm>(initialForm);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [recommendations, setRecommendations] = useState<Recommendations | null>(null);
  const [quote, setQuote] = useState<Quote | null>(null);
  const [items, setItems] = useState<BundleItem[]>([]);
  const [token, setToken] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [reviewed, setReviewed] = useState(false);
  const [reviewBlocked, setReviewBlocked] = useState(false);
  const [reviewBusy, setReviewBusy] = useState(false);
  const [planStep, setPlanStep] = useState(1);
  const [onboarding, setOnboarding] = useState<'new'|'resume'|null>(null);
  const [onboardingStep, setOnboardingStep] = useState(4);
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [showDocuments, setShowDocuments] = useState(false);
  const [onboardingBusy, setOnboardingBusy] = useState(false);
  const [search, setSearch] = useState('');
  const [gstin, setGstin] = useState('');
  const [lookupConsent, setLookupConsent] = useState(false);
  const [lookup, setLookup] = useState<LookupReply | null>(null);
  const [brief, setBrief] = useState('');
  const [advisorConsent, setAdvisorConsent] = useState(false);
  const [advisorBusy, setAdvisorBusy] = useState(false);
  const [advisorReply, setAdvisorReply] = useState<AdvisorReply | null>(null);
  const [conversation,setConversation]=useState<{role:'user'|'assistant';text:string}[]>([]);
  const [factsReviewed,setFactsReviewed]=useState(false);
  const advisorEpoch=useRef(0);
  const epoch = useRef(0);
  const operation = useRef<AbortController | null>(null);
  const heading = useRef<HTMLHeadingElement>(null);
  const focusJourney = useRef(false);
  const reviewNotice = useRef<HTMLDivElement>(null);
  const reviewRequirements = useRef<HTMLDivElement>(null);
  const errorNotice = useRef<HTMLDivElement>(null);
  const t: Translate = key=>translations[language][key] ?? translations.en[key] ?? key;
  const localize: Localize = value=>language==='hi' ? value.message_hi || value.message : value.message;
  const money: FormatMoney = value=>new Intl.NumberFormat(language==='hi'?'hi-IN':'en-IN',{style:'currency',currency:'INR',maximumFractionDigits:0}).format(value);
  const step = showOnboarding ? showDocuments ? 4 : onboardingStep : planStep;
  const staffView=operations&&user&&user.role!=='customer';
  function revealSection(id:string){setRequestedSection(id);}
  useEffect(()=>{
    if(!staffView||!requestedSection) return;
    function openSection(){
      const node=document.getElementById(requestedSection);
      if(!node) return false;
      if(node instanceof HTMLDetailsElement) node.open=true;
      node.scrollIntoView({behavior:'instant',block:'start'});
      node.querySelector<HTMLElement>('summary')?.focus({preventScroll:true});
      setRequestedSection('');return true;
    }
    if(openSection()) return;
    const observer=new MutationObserver(()=>{if(openSection()) observer.disconnect();});
    observer.observe(document.getElementById('main')!,{childList:true,subtree:true});
    return ()=>observer.disconnect();
  },[requestedSection,staffView]);

  useEffect(()=>{document.documentElement.lang=language;advisorEpoch.current++;setAdvisorBusy(false);},[language]);
  useEffect(()=>{advisorEpoch.current++;setAdvisorBusy(false);setAdvisorReply(null);setConversation([]);setBrief('');setFactsReviewed(false);},[user?.id]);
  useEffect(()=>{document.body.classList.toggle('results-mode',Boolean(profile)); return ()=>document.body.classList.remove('results-mode');},[profile]);
  useEffect(()=>{
    if(showOnboarding||staffView||!focusJourney.current) return;
    focusJourney.current=false;
    window.scrollTo({top:0,behavior:'instant'});
    const target=planStep===1?document.getElementById('discovery-title'):planStep===2?heading.current:reviewNotice.current;
    target?.focus({preventScroll:true});
  },[planStep,showOnboarding,staffView]);
  useEffect(()=>{if(reviewBlocked) reviewRequirements.current?.focus();},[reviewBlocked]);
  useEffect(()=>{if(error) errorNotice.current?.focus();},[error]);
  useEffect(()=>()=>operation.current?.abort(),[]);

  function clearDocumentJourney() {
    setOnboarding(null);setSavedRecord('');setShowOnboarding(false);setShowDocuments(false);setOnboardingStep(4);setOnboardingBusy(false);
  }
  function invalidatePlan() {
    clearDocumentJourney();setProfile(null);setRecommendations(null);setQuote(null);setToken(null);setLookup(null);setItems([]);setReviewed(false);setReviewBlocked(false);setError('');
  }
  function update<K extends keyof BusinessForm>(key: K, value: BusinessForm[K]) { if(profile) invalidatePlan();setForm(previous=>({...previous,[key]:value}));setFactsReviewed(false); }
  function canVisitStep(target:number) {
    if(target===1) return true;
    if(target===2) return Boolean(profile);
    if(target===3) return Boolean(profile&&reviewed&&quote?.catalogue_checks_pass);
    if(target===4) return onboarding!==null;
    return target===5&&onboarding!==null&&onboardingStep===5;
  }
  function visitStep(target:number) {
    if(busy||advisorBusy||onboardingBusy||!canVisitStep(target)||target===step) return;
    setError('');setReviewBlocked(false);
    if(target<=3) {focusJourney.current=true;setShowOnboarding(false);setPlanStep(target);}
    else {setShowDocuments(target===4&&onboardingStep===5);setShowOnboarding(true);}
  }
  function openOnboarding(mode:'new'|'resume', recordId='') {
    setSavedRecord(recordId);setOnboarding(mode);setShowDocuments(false);setShowOnboarding(true);setOperations(false);
  }
  function begin() { operation.current?.abort(); operation.current=new AbortController(); setBusy(true); setReviewBlocked(false); setError(''); return {id:++epoch.current,signal:operation.current.signal}; }
  function handleError(exception: unknown) {
    if(exception instanceof DOMException && exception.name==='AbortError') return;
    if(exception instanceof ApiError && exception.status===409 && /verif/i.test(exception.originalMessage)) {setToken(null);setLookup(null);setError(t('verificationError'));}
    else setError(exception instanceof ApiError ? exception.message : t('unavailable'));
  }

  async function recommend(event: FormEvent) {
    event.preventDefault();
    if(!form.needs.length) {setError(t('needRequired'));return;}
    if(!form.business_type || !form.city_tier || !form.current_internet) return;
    const details: Profile={business_type:form.business_type,city_tier:Number(form.city_tier) as 1|2,employees:Number(form.employees),sites:Number(form.sites),monthly_budget:Number(form.monthly_budget||0),current_internet:form.current_internet,gstin_claim:form.gstin_claim,needs:form.needs,language};
    if(profile&&JSON.stringify({...profile,language})===JSON.stringify(details)) {focusJourney.current=true;setPlanStep(2);return;}
    const {id,signal}=begin();
    try {
      const result=await post<Recommendations>('/api/recommend',{profile:details},signal);
      if(id!==epoch.current) return;
      focusJourney.current=true;clearDocumentJourney();setPlanStep(2);setProfile(details);setRecommendations(result);setQuote(result.quote);setItems(result.quote?.items.map(({product_id,quantity})=>({product_id,quantity}))||[]);setToken(null);setLookup(null);setGstin('');setLookupConsent(false);setReviewed(false);setSearch('');
    } catch(exception) {if(id===epoch.current) handleError(exception);}
    finally {if(id===epoch.current) setBusy(false);}
  }

  async function refresh(nextItems: BundleItem[]) {
    if(!profile) return;
    clearDocumentJourney();
    setItems(nextItems);setReviewed(false);
    const {id,signal}=begin();
    try {
      const result=nextItems.length ? await post<Quote>('/api/quote',{profile:{...profile,language},items:nextItems,verification_token:token},signal) : null;
      if(id===epoch.current) setQuote(result);
    } catch(exception) {if(id===epoch.current) {setQuote(null);handleError(exception);}}
    finally {if(id===epoch.current) setBusy(false);}
  }

  async function verify(event: FormEvent) {
    event.preventDefault();if(!profile||!lookupConsent) return;
    clearDocumentJourney();
    const {id,signal}=begin();setReviewed(false);
    try {
      const evidence=await post<LookupReply>('/api/gstin/verify',{gstin:gstin.trim().toUpperCase(),consent:true},signal);
      if(id!==epoch.current) return;
      setGstin('');setToken(evidence.verification_token);setLookup(evidence);
      const refreshed=await post<Recommendations>('/api/recommend',{profile:{...profile,language},verification_token:evidence.verification_token},signal);
      const result=items.length ? await post<Quote>('/api/quote',{profile:{...profile,language},items,verification_token:evidence.verification_token},signal) : null;
      if(id===epoch.current) {setRecommendations(refreshed);setQuote(result);}
    } catch(exception) {if(id===epoch.current) {setQuote(null);handleError(exception);}}
    finally {if(id===epoch.current) setBusy(false);}
  }

  async function review() {
    if(!profile||!quote) return;
    if(!quote.catalogue_checks_pass) {setReviewBlocked(true);reviewRequirements.current?.focus();return;}
    const {id,signal}=begin();
    setReviewBusy(true);
    try {
      const result=await post<{quote:Quote}>('/api/quote/check',{profile:{...profile,language},items,verification_token:token},signal);
      if(id===epoch.current) {focusJourney.current=true;setQuote(result.quote);setReviewed(true);setPlanStep(3);}
    } catch(exception) {if(id===epoch.current) {setReviewed(false);handleError(exception);}}
    finally {if(id===epoch.current) {setBusy(false);setReviewBusy(false);}}
  }

  async function askAdvisor() {
    if(!advisorConsent) {setError(t('consentRequired'));return;}
    if(!brief.trim()) {setError(t('briefRequired'));return;}
    if(conversation.length&&!factsReviewed) return;
    const turnId=++advisorEpoch.current;
    const message=brief.trim();
    const reviewed=conversation.length?{business_type:form.business_type||null,employees:form.employees?Number(form.employees):null,sites:form.sites?Number(form.sites):null,monthly_budget:form.monthly_budget?Number(form.monthly_budget):null,current_internet:form.current_internet||null,gstin_claim:form.gstin_claim,needs:form.needs,follow_up:''}:null;
    setAdvisorBusy(true);setError('');setAdvisorReply(null);
    try {
      const history=conversation.slice(-8);
      const body={message,language,consent:true,history,reviewed};
      while(history.length&&new TextEncoder().encode(JSON.stringify(body)).length>18000)history.splice(0,2);
      const result=await post<AdvisorReply>('/api/discover',body);
      if(turnId!==advisorEpoch.current) return;
      setAdvisorReply(result);
      const draft=result.draft;
      if(draft) {invalidatePlan();setForm(previous=>({...previous,
        business_type:draft.business_type??previous.business_type,
        employees:draft.employees===null?previous.employees:String(draft.employees),
        sites:draft.sites===null?previous.sites:String(draft.sites),
        monthly_budget:draft.monthly_budget===null?previous.monthly_budget:String(draft.monthly_budget),
        current_internet:draft.current_internet??previous.current_internet,
        gstin_claim:draft.gstin_claim??previous.gstin_claim,
        needs:draft.needs.length?draft.needs:previous.needs,
      }));}
      if(draft){setConversation(previous=>[...previous,{role:'user',text:message},{role:'assistant',text:draft.follow_up}].slice(-8) as typeof conversation);setBrief('');setFactsReviewed(false);}
    } catch {if(turnId===advisorEpoch.current)setAdvisorReply({mode:'guided',draft:null,message:translations.en.unavailable,message_hi:translations.hi.unavailable,reason:'server_unreachable',retryable:true});}
    finally {if(turnId===advisorEpoch.current)setAdvisorBusy(false);}
  }

  function download() {
    if(!quote) return;
    const lines=[t('exportTitle'),t('fictional'),'',t('pricingNote'),t('allStatuses'),''];
    quote.items.forEach(item=>lines.push(`${item.name} × ${item.quantity}`,`${money(item.monthly_total)} ${t('perMonth')} | ${money(item.setup_total)} ${t('setupFees')} | ${item.contract_months} ${t('contract')}`,`${t(item.status)}: ${item.reasons.map(localize).join(' ')}`,''));
    lines.push(`${t('monthly')}: ${money(quote.monthly_total)}`,`${t('setupFees')}: ${money(quote.setup_total)}`,`${t('firstMonth')}: ${money(quote.first_month_estimate)}`,'',t('estimateLimit'));
    const url=URL.createObjectURL(new Blob(['\uFEFF'+lines.join('\n')],{type:'text/plain;charset=utf-8'}));
    const anchor=document.createElement('a');anchor.href=url;anchor.download='udyam-demo-estimate.txt';anchor.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }

  return <>
    <a className="skip" href="#main">{language==='hi'?'मुख्य सामग्री पर जाएँ':'Skip to content'}</a>
    <header className="topbar">
      <a className="brand" href="#main" aria-label="Accel Business home"><span className="brand-mark">a</span><span className="brand-wordmark">accel<span>BUSINESS</span></span></a>
      <span className="product-name">Udyam Digital</span>
      <div className="topbar-right"><span className="prototype">{language==='hi'?'डेमो वर्कस्पेस':'Demo workspace'}</span><label className="language-label"><span className="sr-only">{t('language')}</span><select id="language" aria-label={t('language')} value={language} onChange={event=>setLanguage(event.target.value as Language)}><option value="en">English</option><option value="hi">हिन्दी</option></select></label>
        <AccountBar language={language} onLanguageChange={setLanguage} onOpen={id=>openOnboarding('resume',id)} onOperations={()=>setOperations(true)}/>
      </div>
    </header>
    <main id="main" className="workspace">
      <aside className="intro" aria-label={language==='hi'?'आपकी यात्रा':'Your journey'}>
        <div className="rail-heading"><UIIcon name="grid"/><span>{staffView?(language==='hi'?'टीम वर्कस्पेस':'Team workspace'):(language==='hi'?'आपका बिज़नेस प्लान':'Your business plan')}</span></div>
        <p className="rail-caption">{language==='hi'?'एक समय में एक आसान कदम।':'One clear step at a time.'}</p>
        {staffView?<nav className="staff-navigation" aria-label={language==='hi'?'टीम के हिस्से':'Team sections'}><button onClick={()=>revealSection('operations-view')}><UIIcon name="file"/>{language==='hi'?'कार्य सूची':'Task queue'}</button>{user.role==='reviewer'&&<><button onClick={()=>revealSection('operations-metrics')}><UIIcon name="clock"/>{language==='hi'?'यात्रा के आँकड़े':'Journey measurements'}</button><button onClick={()=>revealSection('business-insights')}><UIIcon name="grid"/>{language==='hi'?'व्यवसाय विश्लेषण':'Business evidence'}</button><button onClick={()=>revealSection('channel-status')}><UIIcon name="chat"/>{language==='hi'?'चैनल की स्थिति':'Channel status'}</button></>}</nav>:<ol className="steps" aria-label={language==='hi'?'आपकी प्रगति':'Your progress'}>{(['discover','tailor','review','documents','track'] as const).map((name,i)=><li key={name} id={`step${i+1}`} className={step===i+1?'active':step>i+1?'complete':''} aria-current={step===i+1?'step':undefined}><button className="step-link" type="button" disabled={i+1===step||busy||advisorBusy||onboardingBusy||!canVisitStep(i+1)} onClick={()=>visitStep(i+1)} aria-label={t(name)}><span>{step>i+1?<UIIcon name="check"/>:i+1}</span><div><strong>{t(name)}</strong><small>{t(name+'Sub')}</small></div></button></li>)}</ol>}
        <div className="rail-note"><UIIcon name="shield"/><strong>{language==='hi'?'पहले अपना प्लान देखें।':'Explore at your own pace.'}</strong><p>{t('privacyShort')}</p></div>
        <div className="rail-footer"><span className="environment-dot"/>{language==='hi'?'काल्पनिक डेटा वाला डेमो':'Synthetic data · Demo only'}</div>
      </aside>
      <section className="content">
        <div className="content-topline"><p className="breadcrumb">{language==='hi'?'व्यवसाय सेवाएँ':'Business services'}<span>/</span>{operations?(language==='hi'?'टीम वर्कस्पेस':'Team workspace'):showOnboarding?(language==='hi'?'दस्तावेज़ और ऑर्डर':'Checks & orders'):(language==='hi'?'नया प्लान':'New plan')}</p>
          {!showOnboarding&&!operations&&<button id="open-saved-order" className="text-button resume-link" type="button" disabled={busy||advisorBusy} onClick={()=>openOnboarding('resume')}><UIIcon name="clock"/>{language==='hi'?'सहेजा हुआ काम जारी रखें':'Resume saved progress'}</button>}
        </div>
        <div id="error" ref={errorNotice} tabIndex={-1} className="notice error" role="alert" hidden={!error}>{localError(error,language)}</div>
        {onboarding&&<div hidden={!showOnboarding||Boolean(staffView)}><Onboarding key={(user?.id||'anonymous')+':'+savedRecord} language={language} initialRecord={savedRecord} initial={onboarding==='new'&&profile?{profile:{...profile,language},items}:null} active={showOnboarding&&!staffView} showDocuments={showDocuments} onBusyChange={setOnboardingBusy} onStage={setOnboardingStep}/></div>}
        {staffView?<Operations key={user.id} language={language} onExit={()=>setOperations(false)}/>:showOnboarding ? null : planStep===1||!profile ? <section id="discovery-view" aria-labelledby="discovery-title">
          <div className="section-heading"><div><span className="eyebrow">{t('stepOne')}</span><h1 id="discovery-title" tabIndex={-1}>{language==='hi'?'आपके काम के लिए सही सेवाएँ।':'A better way to connect your business.'}</h1></div></div><p className="section-copy">{language==='hi'?'अपने व्यवसाय के बारे में बताएँ। सेवाएँ चुनें, कीमतें देखें और तैयार होने पर आगे बढ़ें।':'Tell us a little about your business. Explore the services, see the costs, and take the next step when you’re ready.'}</p>
          {!user&&<div className="registration-prompt"><UIIcon name="user"/><p><strong>{language==='hi'?'एक जगह से अपनी प्रगति देखें।':'Keep your next steps in one place.'}</strong><span>{language==='hi'?'खाता बनाएँ और दस्तावेज़ जाँच व डेमो ऑर्डर सहेजें। अभी सेवाएँ देखना भी जारी रख सकते हैं।':'Create an account to save document checks and track your demo order. You can explore first.'}</span></p><button className="text-button" onClick={()=>openAuth('register')}>{language==='hi'?'खाता बनाएँ':'Create account'}<UIIcon name="arrow"/></button></div>}
          <div className="method-label"><span>{language==='hi'?'आसान सवालों से शुरू करें':'Start with a few details'}</span><span>{language==='hi'?'या सलाहकार की मदद लें':'or get a little help'}</span></div>
          <details className="advisor-box"><summary><span className="advisor-icon"><UIIcon name="chat"/></span><div><strong>{t('advisorTitle')}</strong><span>{t('advisorSub')}</span></div><span className="plus" aria-hidden="true">+</span></summary><div className="advisor-body">
            {conversation.length>0&&<><ol id="advisor-conversation" aria-label={language==='hi'?'सलाहकार से बातचीत':'Advisor conversation'}>{conversation.map((turn,index)=><li key={index}><strong>{turn.role==='user'?(language==='hi'?'आप':'You'):(language==='hi'?'सलाहकार':'Advisor')}: </strong>{turn.text}</li>)}</ol><p className="quiet">{language==='hi'?'बातचीत केवल इस खुले पृष्ठ में रहती है। नीचे उत्तर जाँचें, फिर अगला जवाब भेजें।':'Conversation stays in this open page only. Review the answers below before sending your next reply.'}</p><label className="consent"><input id="advisor-reviewed" type="checkbox" checked={factsReviewed} disabled={advisorBusy} onChange={e=>setFactsReviewed(e.target.checked)}/><span>{language==='hi'?'मैंने नीचे दिए मौजूदा उत्तर जाँच लिए हैं।':'I have reviewed the current answers below.'}</span></label><button id="advisor-reset" className="text-button" disabled={advisorBusy} onClick={()=>{advisorEpoch.current++;setConversation([]);setAdvisorReply(null);setFactsReviewed(false);setBrief('');}}>{language==='hi'?'बातचीत मिटाएँ':'Clear conversation'}</button></>}
            <p className="quiet">{language==='hi'?'हर अनुमति वाले अनुरोध में आपका नया जवाब, हाल की बातचीत और जाँचे गए व्यावसायिक उत्तर Gemini को भेजे जाते हैं। बातचीत पृष्ठ बंद होने तक रहती है।':'Each consented request sends your new answer, recent conversation and reviewed business facts to Gemini. Conversation lasts only while this page stays open.'}</p>
            <label htmlFor="business-brief">{t('briefLabel')}</label><textarea id="business-brief" rows={3} maxLength={2000} value={brief} disabled={advisorBusy||busy} onChange={event=>setBrief(event.target.value)} placeholder={language==='hi'?'मेरा एक क्लिनिक है जिसमें 5 कर्मचारी हैं। मुझे इंटरनेट और ईमेल चाहिए।':'I run a clinic with 5 employees at one location. We need internet and business email, within ₹3,000 a month.'}/>
            <VoiceInput language={language} disabled={advisorBusy||busy} onConfirm={text=>setBrief(text)}/>
            <label className="consent"><input id="advisor-consent" type="checkbox" checked={advisorConsent} disabled={advisorBusy} onChange={event=>setAdvisorConsent(event.target.checked)}/><span>{t('advisorConsent')}</span></label>
            <button className="button secondary" id="ask-advisor" type="button" disabled={advisorBusy||busy||Boolean(conversation.length&&!factsReviewed)} onClick={askAdvisor}>{advisorBusy?t('drafting'):conversation.length?(language==='hi'?'जवाब भेजें और मसौदा अपडेट करें':'Send reply and update draft'):t('draftAnswers')}</button>
            <p id="advisor-feedback" className="feedback" aria-live="polite">{advisorBusy ? t('drafting') : advisorReply?.draft ? `${t('advisorReview')} ${advisorReply.draft.follow_up}` : advisorReply ? language==='hi' ? advisorReply.message_hi||advisorReply.message : advisorReply.message : ''}</p>
            {advisorReply?.mode==='guided' && <p className="quiet">{t('advisorUnavailable')}</p>}
          </div></details>
          <form id="business-form" onSubmit={recommend}>
            <div className="form-section"><div className="form-section-title"><span>01</span><div><h3>{t('basics')}</h3><p>{language==='hi'?'इससे सेवाओं और मात्रा का सुझाव मिलेगा।':'So we can suggest the right services and quantities.'}</p></div></div><div className="form-grid">
              <Field label={t('businessType')}><select name="business_type" value={form.business_type} required disabled={busy||advisorBusy} onChange={event=>update('business_type',event.target.value as BusinessForm['business_type'])}><option value="">{t('selectType')}</option>{['shop','office','clinic','restaurant','manufacturing','other'].map(type=><option key={type} value={type}>{t(type)}</option>)}</select></Field>
              <Field label={t('cityTier')} help={t('tierHelp')}><select name="city_tier" value={form.city_tier} required disabled={busy||advisorBusy} onChange={event=>update('city_tier',event.target.value as BusinessForm['city_tier'])}><option value="">{t('selectTier')}</option><option value="1">{t('tier1')}</option><option value="2">{t('tier2')}</option></select></Field>
              <Field label={t('employees')} help={t('employeeHelp')}><input name="employees" type="number" min={1} max={10000} step={1} placeholder="5" value={form.employees} required disabled={busy||advisorBusy} onChange={event=>update('employees',event.target.value)}/></Field>
              <Field label={t('sites')}><input name="sites" type="number" min={1} max={1000} step={1} value={form.sites} required disabled={busy||advisorBusy} onChange={event=>update('sites',event.target.value)}/></Field>
            </div></div>
            <div className="form-section"><div className="form-section-title"><span>02</span><div><h3>{t('setup')}</h3><p>{language==='hi'?'आपके मौजूदा कनेक्शन और बजट के हिसाब से।':'A starting point that fits how you work today.'}</p></div></div><div className="form-grid">
              <Field label={t('currentInternet')}><select name="current_internet" value={form.current_internet} required disabled={busy||advisorBusy} onChange={event=>update('current_internet',event.target.value as BusinessForm['current_internet'])}><option value="">{t('selectSetup')}</option>{[['none','none'],['hotspot','hotspot'],['broadband','broadband'],['leased_line','leasedLine']].map(([value,label])=><option key={value} value={value}>{t(label)}</option>)}</select></Field>
              <Field label={t('budget')} help={t('budgetHelp')}><input name="monthly_budget" type="number" min={0} max={10000000} step={1} placeholder="3000" value={form.monthly_budget} disabled={busy||advisorBusy} onChange={event=>update('monthly_budget',event.target.value)}/></Field>
            </div><fieldset className="registration" disabled={busy||advisorBusy}><legend>{t('gstinQuestion')}</legend><div className="radio-options">{(['yes','no','unsure'] as const).map(value=><label key={value}><input type="radio" name="gstin_claim" value={value} checked={form.gstin_claim===value} onChange={()=>update('gstin_claim',value)}/><span>{t(value)}</span></label>)}</div><small>{t('gstinHelp')}</small></fieldset></div>
            <div className="form-section"><div className="form-section-title"><span>03</span><div><h3>{t('needsTitle')}</h3><p>{t('needsHelp')}</p></div></div><div id="needs" className="needs-grid">{(Object.keys(needIcons) as Need[]).map(need=><label className="need" key={need}><Icon need={need}/><span>{t(need)}</span><input type="checkbox" name="needs" value={need} checked={form.needs.includes(need)} disabled={busy||advisorBusy} onChange={event=>update('needs',event.target.checked?[...form.needs,need]:form.needs.filter(item=>item!==need))}/></label>)}</div></div>
            <div className="form-footer"><p>{t('formFooter')}</p><button className="button primary" id="recommend-button" type="submit" disabled={busy||advisorBusy}><span>{busy?t('waiting'):t('seeBundle')}</span><UIIcon name="arrow"/></button></div>
          </form>
        </section> : planStep===3 && reviewed && quote ? <section id="review-view" aria-labelledby="review-title">
          <div id="review-result" ref={reviewNotice} tabIndex={-1}>
            <div className="section-heading"><div><span className="eyebrow">{t('stepThree')}</span><h1 id="review-title">{t('checked')}</h1></div></div>
            <div className="notice success" role="status"><p>{t('checkedNote')}</p></div>
          </div>
          <h3>{t('yourServices')}</h3>
          {quote.items.map(item=><article className="service" key={item.product_id}>
            <h4>{item.name}</h4><p className="quiet">{t('quantity')}: {item.quantity} · {item.contract_months} {t('contract')}</p>
            <div className="quote-row"><span>{t('monthly')}</span><strong>{money(item.monthly_total)}</strong></div>
            <div className="quote-row"><span>{t('setupFees')}</span><strong>{money(item.setup_total)}</strong></div>
          </article>)}
          <div className="quote-breakdown" id="review-totals">{[['monthly',quote.monthly_total],['setupFees',quote.setup_total],['firstMonth',quote.first_month_estimate]].map(([label,amount])=><div className="quote-row" key={label}><span>{t(String(label))}</span><strong>{money(Number(amount))}</strong></div>)}</div>
          <p className="quiet">{t('taxNote')}</p><p className="quiet">{t('pricingNote')}</p>
          <button id="continue-kyc" className="button primary" type="button" onClick={()=>openOnboarding('new')}>{t('continueKyc')}</button>
          <button id="download-quote" className="button secondary" type="button" onClick={download}>{t('download')}</button>
          <p className="quote-footnote">{t('estimateLimit')}</p>
        </section> : <section id="bundle-view" aria-labelledby="bundle-title">
          <div className="section-heading"><div><span className="eyebrow">{t('stepTwo')}</span><h1 id="bundle-title" ref={heading} tabIndex={-1}>{t('bundleTitle')}</h1></div></div>
          <p id="profile-summary" className="section-copy">{t('profileSummary').replace('{type}',t(profile.business_type)).replace('{team}',String(profile.employees)).replace('{sites}',String(profile.sites)).replace('{tier}',String(profile.city_tier))}</p>
          <div className="notice info"><strong>{t('demoPricing')}</strong><p>{t('pricingNote')}</p></div>
          <div id="unmet-needs" className="notice warning" hidden={!recommendations?.unmet_needs.length}><strong>{t('unmetTitle')}</strong>{recommendations?.unmet_needs.map(item=><p key={item.need}>{t('unmetNote')} {t(item.need)}. {item.reasons.map(localize).join(' ')}</p>)}</div>
          <div className="bundle-layout"><div className="bundle-main">
            <div className="subheading"><h3>{t('yourServices')}</h3><span id="selection-count" className="quiet">{items.length} {t('services')}</span></div><p className="quiet" id="sizing-note">{language==='hi'?recommendations?.sizing_note_hi:recommendations?.sizing_note}</p>
            <div id="selected-products" aria-live="polite">{quote?.items.length ? quote.items.map(item=><ServiceCard key={item.product_id} item={item} why={recommendations?.explanations[item.product_id]} busy={busy} t={t} localize={localize} money={money} onRemove={()=>refresh(items.filter(selected=>selected.product_id!==item.product_id))} onQuantity={quantity=>{if(!Number.isInteger(quantity)||quantity<1||quantity>10000) {setError(t('invalidQuantity'));return;}void refresh(items.map(selected=>selected.product_id===item.product_id?{...selected,quantity}:selected));}}/>) : items.length ? <div className="empty"><p>{t('refreshFailed')}</p><button className="button secondary" data-retry type="button" disabled={busy} onClick={()=>refresh(items)}>{t('retry')}</button></div> : <div className="empty">{t('empty')}</div>}</div>
            <details className="catalogue-drawer"><summary><span>{t('browseCatalogue')}</span><span aria-hidden="true">+</span></summary><label className="catalogue-search"><span className="sr-only">{t('searchProducts')}</span><input type="search" id="catalogue-search" placeholder={t('searchProducts')} value={search} onChange={event=>setSearch(event.target.value)}/></label><div id="catalogue-products">
              {recommendations?.catalogue.filter(product=>(product.name+' '+product.description+' '+product.category).toLowerCase().includes(search.toLowerCase())).map(product=>{
                const selected=items.some(item=>item.product_id===product.product_id);
                return <article className="catalogue-item" key={product.product_id}><h4>{product.name}</h4><Status product={product} t={t}/><p>{product.description}</p>{product.reasons.map(reason=><p key={reason.code}>{localize(reason)}</p>)}{Boolean(product.requires_one_of.length)&&<p>{language==='hi'?'इसी बंडल में संगत कनेक्शन आवश्यक है।':'Requires a compatible connection in the same bundle.'}</p>}<div className="catalogue-item-footer"><span>{money(product.monthly_price)} <small>{product.unit}</small></span><button type="button" className="button secondary" data-add={product.product_id} disabled={busy||selected||product.status==='ineligible'} onClick={()=>refresh([...items,{product_id:product.product_id,quantity:1}])}>{t(selected?'added':product.status==='ineligible'?'blocked':'add')}</button></div></article>;
              })}
              {recommendations?.catalogue.every(product=>!(product.name+' '+product.description+' '+product.category).toLowerCase().includes(search.toLowerCase()))&&<p className="quiet">{t('noSearch')}</p>}
            </div></details>
            <details className="verification-box"><summary>{t('verifyTitle')}</summary><p className="quiet">{t('verifyHelp')}</p><form id="verification-form" onSubmit={verify}><label htmlFor="gstin-input">{t('gstinLabel')}</label><input id="gstin-input" name="gstin" minLength={15} maxLength={15} autoComplete="off" spellCheck={false} value={gstin} onChange={event=>setGstin(event.target.value)} required disabled={busy}/><label className="consent"><input id="lookup-consent" type="checkbox" checked={lookupConsent} onChange={event=>setLookupConsent(event.target.checked)} required disabled={busy}/><span>{t('lookupConsent')}</span></label><button className="button secondary" id="verify-button" type="submit" disabled={busy}>{t('verify')}</button></form><p id="verification-feedback" aria-live="polite" className="feedback">{lookup&&`${lookup.masked_gstin} · ${t('verifyStatus')}: ${t(lookup.status)}`}</p></details>
          </div><aside className="quote-panel" aria-labelledby="quote-title"><div className="quote-kicker">{t('yourEstimate')}</div><h3 id="quote-title">{t('oneMonthlyView')}</h3>
            <div id="quote-summary" aria-live="polite">{busy?<p className="quote-state">{t('changes')}</p>:!quote?<p className="quote-state">{t(items.length?'refreshFailed':'emptyQuote')}</p>:<>
              <div className="quote-amount">{money(quote.monthly_total)} <small>{t('perMonth')}</small></div><div className="tax-note">{t('taxNote')}</div><div className="quote-breakdown">{[['monthly',quote.monthly_total],['setupFees',quote.setup_total],['firstMonth',quote.first_month_estimate]].map(([label,amount])=><div className="quote-row" key={label}><span>{t(String(label))}</span><strong>{money(Number(amount))}</strong></div>)}</div>{quote.budget_provided&&<p className="quote-budget">{quote.over_budget_by?`${t('aboveBudget')} ${money(quote.over_budget_by)}`:t('withinBudget')}</p>}<p className="quote-state">{t(quote.status+'Note')}</p>
            </>}</div>
            <button id="check-quote" className="button primary wide" type="button" disabled={busy||!quote} onClick={review}>{t(reviewBusy?'checkingQuote':'checkQuote')}</button>
            {reviewBlocked&&quote&&<div id="review-requirements" ref={reviewRequirements} className="notice warning" role="alert" tabIndex={-1}><strong>{t('reviewRequirements')}</strong><ul>{quote.items.filter(item=>item.status!=='eligible').map(item=><li key={item.product_id}>{item.name}: {item.reasons.map(localize).join(' ')}</li>)}</ul></div>}
            {reviewBlocked&&quote?.status==='conditional'&&quote.items.every(item=>item.reasons.every(reason=>['gstin_unverified','dependency_conditional'].includes(reason.code)))&&<button id="conditional-kyc" className="button secondary wide" type="button" onClick={()=>openOnboarding('new')}>{t('continueKyc')}</button>}
            <button id="download-quote" className="text-button wide" type="button" disabled={busy||!quote} onClick={download}>{t('download')}</button><p className="quote-footnote">{t('estimateLimit')}</p>
          </aside></div>
        </section>}
        <footer className="page-footer"><span>{t('fictional')}</span><details><summary>{t('privacy')}</summary><p>{t('privacyDetails')}</p></details></footer>
      </section>
    </main>
  </>;
}
