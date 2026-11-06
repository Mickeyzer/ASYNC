import {useEffect,useRef} from 'react';
import type {ReactNode} from 'react';
import {createPortal} from 'react-dom';

const paths={
  arrow:'M5 12h14m-6-6 6 6-6 6',check:'m5 12 4 4L19 6',close:'m6 6 12 12M18 6 6 18',
  user:'M20 21v-2a7 7 0 0 0-14 0v2M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z',
  lock:'M5 10h14v11H5zM8 10V6a4 4 0 0 1 8 0v4',file:'M14 2H5v20h14V7zm0 0v5h5M8 12h8M8 16h6',
  grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
  upload:'M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6',chat:'M4 3h16v13H9l-5 5zM8 7h8M8 11h5',
  eye:'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Zm10-3a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z',
  chevron:'m9 5 7 7-7 7',shield:'m12 2 8 3v6c0 5-8 11-8 11S4 16 4 11V5zm-4 9 3 3 5-6',
  plus:'M12 5v14M5 12h14',minus:'M5 12h14',clock:'M12 8v5l3 2M22 12a10 10 0 1 0-20 0 10 10 0 0 0 20 0Z',
};
export function UIIcon({name,className=''}:{name:keyof typeof paths;className?:string}){
  return <svg className={'ui-icon '+className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.65" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[name]}/></svg>;
}

export function Modal({children,label,onClose,closeLabel='Close'}:{children:ReactNode;label:string;onClose:()=>void;closeLabel?:string}){
  const ref=useRef<HTMLDialogElement>(null);
  const callback=useRef(onClose);callback.current=onClose;
  useEffect(()=>{
    const dialog=ref.current!;const previous=document.activeElement as HTMLElement|null;
    const overflow=document.body.style.overflow;document.body.style.overflow='hidden';dialog.showModal();
    dialog.querySelector<HTMLInputElement>('input')?.focus();
    return()=>{dialog.close();document.body.style.overflow=overflow;(previous?.isConnected?previous:document.getElementById('account-toggle'))?.focus();};
  },[]);
  return createPortal(<dialog ref={ref} className="app-dialog" aria-label={label} onCancel={event=>{event.preventDefault();callback.current();}} onKeyDown={event=>{
    if(event.key!=='Tab')return;
    const elements=[...event.currentTarget.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])')].filter(element=>element.getClientRects().length>0);
    const first=elements[0],last=elements[elements.length-1];
    if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
    else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
  }} onClick={event=>{
    if(event.target!==event.currentTarget)return;const rect=event.currentTarget.getBoundingClientRect();
    if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)callback.current();
  }}><button type="button" className="dialog-close icon-button" onClick={onClose} aria-label={closeLabel}><UIIcon name="close"/></button>{children}</dialog>,document.body);
}
