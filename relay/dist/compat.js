'use strict';
// Browser capabilities, not OS names, determine available features.
const storage=(()=>{
  const memory=new Map();let persistent=true;
  try{localStorage.setItem('relay-storage-probe','1');localStorage.removeItem('relay-storage-probe')}catch{persistent=false}
  return {get persistent(){return persistent},getItem(key){if(persistent){try{return localStorage.getItem(key)}catch{persistent=false}}return memory.get(key)??null},setItem(key,value){memory.set(key,String(value));if(persistent){try{localStorage.setItem(key,value)}catch{persistent=false;throw Error('Device storage unavailable')}}}};
})();
function chatId(){if(globalThis.crypto?.randomUUID)return crypto.randomUUID();if(globalThis.crypto?.getRandomValues){const bytes=crypto.getRandomValues(new Uint8Array(16));return Array.from(bytes,b=>b.toString(16).padStart(2,'0')).join('')}return Date.now().toString(36)+'-'+Math.random().toString(36).slice(2)}
async function timedFetch(url,options={},timeout=15000,consume){
  const abort=new AbortController();const parent=options.signal;const cancel=()=>abort.abort();if(parent?.aborted)cancel();else parent?.addEventListener('abort',cancel,{once:true});let expired=false;const timer=setTimeout(()=>{expired=true;cancel()},timeout);
  try{const response=await fetch(url,{...options,signal:abort.signal});return consume?await consume(response):response}catch(error){if(expired&&!parent?.aborted)throw Error('Server connection timed out. Check its address and network access.');throw error}finally{clearTimeout(timer);/* Keep parent cancellation wired while its response body streams. */}
}
const dialogFocus=new WeakMap();
function openDialog(dialog){
  if(typeof stopVoiceForNavigation==='function')stopVoiceForNavigation();
  if(typeof setSidebar==='function')setSidebar(false);
  if(typeof document!=='undefined'){
    dialogFocus.set(dialog,document.activeElement);
    document.querySelectorAll('dialog[open]').forEach(other=>{if(other!==dialog&&other.tagName==='DIALOG')closeDialog(other)});
  }
  if(dialog.open)return;dialog.scrollTop=0;
  if(typeof dialog.showModal==='function')dialog.showModal();else{dialog.setAttribute('open','');dialog.setAttribute('aria-modal','true')}
  dialog.scrollTop=0;dialog.querySelector?.('.dialog-head button')?.focus?.({preventScroll:true});
}
function closeDialog(dialog){
  if(typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open');
  dialogFocus.get(dialog)?.focus?.();dialogFocus.delete(dialog);
}
