import {useEffect,useRef,useState} from 'react';
import type {Language} from './types';

interface RecognitionResult {isFinal:boolean;[index:number]:{transcript:string}}
interface RecognitionEvent {resultIndex:number;results:{length:number;[index:number]:RecognitionResult}}
interface Recognition {lang:string;continuous:boolean;interimResults:boolean;maxAlternatives:number;onresult:((e:RecognitionEvent)=>void)|null;onerror:((e:{error:string})=>void)|null;onend:(()=>void)|null;start:()=>void;stop:()=>void;abort:()=>void}
type SpeechWindow=Window&{SpeechRecognition?:new()=>Recognition;webkitSpeechRecognition?:new()=>Recognition};

export default function VoiceInput({language,disabled,onConfirm}:{language:Language;disabled:boolean;onConfirm:(text:string)=>void}){
  const hi=language==='hi';const [consent,setConsent]=useState(false),[listening,setListening]=useState(false),[transcript,setTranscript]=useState(''),[message,setMessage]=useState('');
  const recognition=useRef<Recognition|null>(null),version=useRef(0);
  const Speech=(window as SpeechWindow).SpeechRecognition||(window as SpeechWindow).webkitSpeechRecognition;
  function cancel(){version.current++;recognition.current?.abort();recognition.current=null;setListening(false);}
  useEffect(()=>()=>{version.current++;recognition.current?.abort();},[]);
  useEffect(()=>{cancel();setTranscript('');setConsent(false);},[language]);
  useEffect(()=>{if(disabled)cancel();},[disabled]);
  function start(){
    if(!Speech||!consent||disabled)return;
    cancel();const generation=version.current;const current=new Speech();recognition.current=current;
    current.lang=hi?'hi-IN':'en-IN';current.continuous=false;current.interimResults=true;current.maxAlternatives=1;
    current.onresult=e=>{if(version.current!==generation)return;const parts=[];for(let i=0;i<e.results.length;i++)parts.push(e.results[i][0].transcript);setTranscript(parts.join(' ').slice(0,2000));};
    current.onerror=e=>{if(version.current!==generation)return;setListening(false);setMessage(e.error==='not-allowed'?(hi?'माइक्रोफ़ोन की अनुमति नहीं मिली। आप लिख सकते हैं।':'Microphone permission was denied. You can type instead.'):(hi?'आवाज़ पढ़ी नहीं जा सकी। फिर प्रयास करें या लिखें।':'Speech could not be transcribed. Retry or type your description.'));};
    current.onend=()=>{if(version.current===generation)setListening(false);};
    setTranscript('');setMessage('');setListening(true);
    try{current.start();}catch{setListening(false);setMessage(hi?'आवाज़ शुरू नहीं हुई। कृपया लिखें।':'Voice could not start. Please type your description.');}
  }
  return <details className="voice-box"><summary id="voice-title">{hi?'अपना व्यवसाय बोलकर बताएँ':'Describe your business by voice'}</summary><div className="voice-content">{!Speech?<p className="quiet">{hi?'इस ब्राउज़र में आवाज़ उपलब्ध नहीं है। नीचे लिखें।':'Voice recognition is unavailable in this browser. Type below.'}</p>:<><p className="quiet">{hi?'आवाज़ आपके ब्राउज़र की सेवा द्वारा संसाधित हो सकती है। उसकी संग्रह नीति लागू होगी। ऐप ऑडियो सहेजता नहीं है। Gemini को भेजने से पहले पाठ जाँचें और अलग सहमति दें।':'Your browser may send audio to its speech provider; that provider’s retention terms apply. This app does not store audio. Review the transcript before using it, then separately consent to Gemini drafting.'}</p><label className="consent"><input id="voice-consent" type="checkbox" checked={consent} disabled={disabled} onChange={e=>{setConsent(e.target.checked);if(!e.target.checked)cancel();}}/><span>{hi?'मैं ब्राउज़र की आवाज़ सेवा उपयोग करने के लिए सहमत हूँ।':'I consent to using my browser’s speech service.'}</span></label><div className="action-row"><button id="start-voice" className="button secondary" type="button" disabled={!consent||disabled||listening} onClick={start}>{hi?'बोलना शुरू करें':'Start speaking'}</button>{listening&&<button id="stop-voice" className="button secondary" type="button" onClick={()=>recognition.current?.stop()}>{hi?'रोकें और समीक्षा करें':'Stop and review'}</button>}<button id="cancel-voice" className="text-button" type="button" disabled={disabled} onClick={()=>{cancel();setTranscript('');}}>{hi?'आवाज़ रद्द करें':'Cancel voice'}</button></div>{listening&&<p role="status">{hi?'सुन रहे हैं…':'Listening…'}</p>}{message&&<p role="status">{message}</p>}<label htmlFor="voice-transcript">{hi?'पाठ जाँचें और सुधारें':'Review and edit transcript'}</label><textarea id="voice-transcript" value={transcript} maxLength={2000} disabled={disabled||listening} onChange={e=>setTranscript(e.target.value)}/><button id="use-transcript" className="button secondary" type="button" disabled={disabled||listening||transcript.trim().length<3} onClick={()=>{onConfirm(transcript.trim());setMessage(hi?'पाठ विवरण में जोड़ा गया। जाँचकर ड्राफ्ट बनाएँ।':'Transcript copied to your description. Review it before drafting.');}}>{hi?'यह पाठ विवरण में उपयोग करें':'Use reviewed transcript as description'}</button></>}</div></details>;
}
