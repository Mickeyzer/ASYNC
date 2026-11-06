import {useEffect,useState} from 'react';
import {api,useAuth} from './Account';
import {label,localError} from './presentation';
import type {Language} from './types';

interface Lead {session_id:string;revision:number;status:string;business_type:string;monthly_total:number;contact?:string;assigned_to?:string;next_action:string;priority:{score:number;reasons:string[]};handoff:{status:string;reason:string}|null;kyc?:{status:string;issues:{code:string;message:string;message_hi?:string}[]};reviews?:{action:string;reason:string;actor:string;at:number}[];documents?:Record<string,{fields:Record<string,string|null>|null}>}
interface Insights {leads:number;activated:number;activation_rate:number;ranking_decision:string;segments:{segment:string;leads:number;activation_rate:number;median_monthly_bundle_inr:number}[]}
interface Journeys {counts:Record<string,number>;durations:Record<string,{samples:number;median_seconds:number|null;p95_seconds:number|null}>;active_cohort_order_rate:number|null;scope:string;definitions:string}
interface Channel {inbound_configured:boolean;outbound_enabled:boolean;description:string}
export default function Operations({language,onExit}:{language:Language;onExit:()=>void}){
  const {user}=useAuth();const hi=language==='hi';const l=(value:string)=>label(value,language);
  const [leads,setLeads]=useState<Lead[]>([]),[selected,setSelected]=useState<Lead|null>(null),[partners,setPartners]=useState<{id:string;username:string}[]>([]),[partner,setPartner]=useState(''),[reason,setReason]=useState(''),[original,setOriginal]=useState(false),[error,setError]=useState(''),[busy,setBusy]=useState(false),[counts,setCounts]=useState<{day:string;event:string;count:number}[]>([]);
  const [insights,setInsights]=useState<Insights|null>(null),[journeys,setJourneys]=useState<Journeys|null>(null),[channel,setChannel]=useState<Channel|null>(null);
  const fail=(e:unknown)=>setError(localError((e as Error).message,language));
  async function refresh(){
    setLeads((await api<{leads:Lead[]}>('/api/operations/leads')).leads);
    if(user?.role==='reviewer'){
      setPartners((await api<{partners:typeof partners}>('/api/operations/partners')).partners);
      const metrics=await api<{counts:typeof counts;journeys:Journeys}>('/api/operations/metrics/summary');
      setCounts(metrics.counts);setJourneys(metrics.journeys);
      setInsights(await api<Insights>('/api/operations/insights/summary'));setChannel(await api<Channel>('/api/operations/channel-status'));
    }
  }
  useEffect(()=>{void refresh().catch(fail);},[user?.id]);
  async function choose(id:string){setBusy(true);setError('');try{setSelected(await api<Lead>('/api/operations/'+id));setOriginal(false);setReason('');setPartner('');}catch(e){fail(e);}finally{setBusy(false);}}
  async function act(action:string){
    if(!selected)return;setBusy(true);setError('');
    try{await api('/api/operations/'+selected.session_id+(action==='assign'?'/assign':'/decision'),'POST',action==='assign'?{partner_id:partner,expected_revision:selected.revision}:{action,expected_revision:selected.revision,reason,original_checked:original||null});setSelected(null);await refresh();}catch(e){fail(e);}finally{setBusy(false);}
  }
  return <section id="operations-view">
    <button className="text-button" onClick={onExit}>{hi?'वापस जाएँ':'Return to discovery'}</button>
    <h1>{hi?'पार्टनर और समीक्षा डैशबोर्ड':'Partner and review dashboard'}</h1>
    <p className="quiet">{hi?'प्राथमिकता मदद की ज़रूरत दिखाती है। पार्टनर को केवल सौंपे गए और अनुमति वाले काम दिखते हैं। सभी ऑर्डर डेमो हैं।':'Priority reflects the need for help, not a probability of purchase. Partners see assigned, consented leads only. All orders remain simulated.'}</p>
    {error&&<div className="notice error" role="alert">{localError(error,language)}</div>}
    <button className="button secondary" disabled={busy} onClick={()=>void refresh().catch(fail)}>{hi?'फिर लोड करें':'Refresh queue'}</button>
    <div className="operations-grid"><div>
      {!leads.length&&<p>{hi?'अभी कोई अधिकृत कार्य नहीं है।':'No authorized tasks in your queue.'}</p>}
      {leads.map(lead=><article className="service" key={lead.session_id}>
        <h3>{l(lead.business_type)} · {l(lead.status)}</h3><p>{l(lead.next_action)}</p>
        <p>{hi?'प्राथमिकता':'Priority'}: {lead.priority.score} · {lead.priority.reasons.map(l).join(' · ')}</p>
        <button className="button secondary" data-lead={lead.session_id} disabled={busy} onClick={()=>choose(lead.session_id)}>{hi?'खोलें':'Open task'}</button>
      </article>)}
    </div>
    {selected&&<article className="account-box" id="operation-detail">
      <h3>{selected.session_id.slice(0,8)} · {l(selected.status)}</h3>
      {selected.contact&&<p>{hi?'अनुमत संपर्क':'Consented contact'}: {selected.contact}</p>}
      <p>{l(selected.next_action)}</p>
      {selected.kyc?.issues.map((i,n)=><p key={n}>{hi?i.message_hi||'दस्तावेज़ की जानकारी जाँचें।':`${i.code}: ${i.message}`}</p>)}
      {selected.documents&&<details><summary>{hi?'छिपे पहचान नंबरों वाली जानकारी':'Masked extraction summaries'}</summary>
        {Object.entries(selected.documents).map(([kind,doc])=><div key={kind}><strong>{l(kind)}</strong>
          {doc.fields?Object.entries(doc.fields).filter(([,v])=>v).map(([k,v])=><p key={k}>{l(k)}: {v}</p>):<p>{hi?'जानकारी समाप्त हो गई; नए दस्तावेज़ माँगें।':'Fields expired; request replacement.'}</p>}
        </div>)}
      </details>}
      {user?.role==='reviewer'&&selected.handoff&&<div className="form-grid"><label>{hi?'पार्टनर':'Partner'}<select value={partner} onChange={e=>setPartner(e.target.value)}><option value="">{hi?'पार्टनर चुनें':'Select partner'}</option>{partners.map(p=><option key={p.id} value={p.id}>{p.username}</option>)}</select></label><button id="assign-partner" className="button secondary" disabled={busy||!partner} onClick={()=>act('assign')}>{hi?'कार्य सौंपें':'Assign partner'}</button></div>}
      <label>{hi?'निर्णय का कारण; नाम, पते और पहचान नंबर न लिखें':'Decision reason; omit names, addresses and identifiers'}<textarea id="review-reason" value={reason} minLength={10} maxLength={300} onChange={e=>setReason(e.target.value)}/></label>
      <div className="action-row">{user?.role==='reviewer'&&<button id="request-replacement" className="button secondary" disabled={busy||reason.length<10} onClick={()=>act('request_replacement')}>{hi?'नए दस्तावेज़ माँगें':'Request replacement'}</button>}{selected.handoff&&<button id="resolve-handoff" className="button secondary" disabled={busy||reason.length<10} onClick={()=>act('resolve_handoff')}>{hi?'सहायता पूर्ण':'Resolve follow-up'}</button>}</div>
      {user?.role==='reviewer'&&selected.kyc?.issues.length!==0&&selected.kyc?.issues.every(i=>i.code==='unclear_document')&&<>
        <p className="quiet">{hi?'तस्वीरें सुरक्षित नहीं रखी जातीं। अधिकृत स्रोत से मूल काल्पनिक दस्तावेज़ देखने के बाद ही पठनीयता की पुष्टि करें। गायब, पुराने, असंगत या अयोग्य प्रमाण की अनदेखी नहीं की जा सकती।':'Images are not retained. Confirm legibility only after inspecting the original synthetic documents through an authorized source. This cannot override missing, expired, inconsistent or ineligible evidence.'}</p>
        <label className="consent"><input id="original-checked" type="checkbox" checked={original} onChange={e=>setOriginal(e.target.checked)}/>{hi?'मैंने मूल दस्तावेज़ों से हर निकाले गए उत्तर का मिलान किया है।':'I compared the original documents with every extracted field.'}</label>
        <button id="confirm-legibility" className="button secondary" disabled={busy||!original||reason.length<10} onClick={()=>act('confirm_legibility')}>{hi?'केवल पठनीयता की पुष्टि करें':'Confirm legibility only'}</button>
      </>}
      {selected.reviews?.map((r,i)=><p key={i}>{hi?l(r.action):r.action} · {r.reason} · {new Date(r.at*1000).toLocaleString(hi?'hi-IN':'en-IN')}</p>)}
    </article>}</div>
    {user?.role==='reviewer'&&<details id="operations-metrics"><summary>{hi?'स्थानीय यात्रा के आँकड़े':'Local journey measurements'}</summary>
      {journeys&&<section id="unique-journey-metrics"><h3>{hi?'वर्तमान सहमति वाले रिकॉर्ड':'Currently retained consented records'}</h3>
        <p>{hi?'अधिकतम 24 घंटे तक रखे गए अलग-अलग रिकॉर्ड। मिटे या समाप्त रिकॉर्ड शामिल नहीं हैं। यह बिक्री से सक्रियण की दर नहीं है।':journeys.scope}</p>
        <p>{hi?'हर चरण पहली बार पूरा होने पर गिना जाता है। दोबारा जाँच अलग ग्राहक नहीं है। बाद में प्रमाण बदल सकता है। पुराने रिकॉर्ड के अज्ञात समय का अनुमान नहीं लगाया जाता।':journeys.definitions}</p>
        {Object.entries(journeys.counts).map(([name,count])=><p key={name}>{l(name)}: <strong>{count}</strong></p>)}
        <p>{hi?'वर्तमान रिकॉर्ड की डेमो ऑर्डर दर':'Current cohort demo-order rate'}: {journeys.active_cohort_order_rate===null?(hi?'कोई रिकॉर्ड नहीं':'No records'):(journeys.active_cohort_order_rate*100).toFixed(1)+'%'}</p>
        {Object.entries(journeys.durations).map(([name,d])=><p key={name}>{l(name)}: {hi?'मध्यिका':'median'} {d.median_seconds??'—'} {hi?'सेकंड':'s'} · {hi?'95वाँ प्रतिशतक':'p95'} {d.p95_seconds??'—'} {hi?'सेकंड':'s'} · {d.samples} {hi?'मापे गए रिकॉर्ड':'measured records'}</p>)}
      </section>}
      <h3>{hi?'दोहराए गए प्रयासों सहित घटनाएँ':'Retry-inclusive event counts'}</h3><p>{hi?'कुल घटनाएँ 30 दिन रहती हैं। बार-बार जाँच को नए ग्राहक या बिक्री में बदलाव न मानें।':'Aggregate counts retained for 30 days. Repeated checks are events, not unique customers or conversion rates.'}</p>
      {counts.map(r=><p key={r.day+r.event}>{r.day} · {hi?l(r.event):r.event}: {r.count}</p>)}
    </details>}
    {channel&&<details id="channel-status"><summary>{hi?'WhatsApp इंटीग्रेशन की स्थिति':'WhatsApp integration status'}</summary>
      <p>{channel.inbound_configured?(hi?'संदेश प्राप्त करने की सेटिंग मौजूद है':'Inbound configuration present'):(hi?'सेटिंग पूरी होने तक बंद है':'Disabled until configured')}</p>
      <p>{hi?(channel.outbound_enabled?'जवाब भेजना चालू है; लाइव डिलीवरी अभी सत्यापित नहीं है।':'जवाब भेजना बंद है। अनुमति, भाषा और निर्देशित प्रश्नों का प्रवाह उपलब्ध है। लाइव डिलीवरी सत्यापित नहीं है।'):channel.description}</p>
    </details>}
    {insights&&<details id="business-insights"><summary>{hi?'कृत्रिम लीड डेटा का विश्लेषण':'Synthetic lead-data evidence'}</summary>
      <p>{insights.activated} / {insights.leads} {hi?'सक्रिय':'activated'} ({(insights.activation_rate*100).toFixed(2)}%). {hi?'ये पुराने कृत्रिम आँकड़े हैं, इस ऐप से सुधार का प्रमाण नहीं।':'Historical synthetic observations, not product uplift.'}</p>
      {insights.segments.map(s=><p key={s.segment}>{hi?l(s.segment):s.segment}: {s.leads} {hi?'लीड':'leads'} · {(s.activation_rate*100).toFixed(2)}% {hi?'सक्रिय':'activated'} · INR {s.median_monthly_bundle_inr}/{hi?'माह, सक्रिय बंडल की मध्यिका':'month median activated bundle'}</p>)}
      <p>{hi?'बिक्री का अनुमान लगाने वाली रैंकिंग नहीं अपनाई गई: होल्डआउट पर सबसे ऊपर के समूह ने आधार दर से बेहतर प्रदर्शन नहीं किया।':insights.ranking_decision}</p>
    </details>}
  </section>;
}
