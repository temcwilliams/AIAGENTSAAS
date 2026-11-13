'use client';
import {useEffect,useState} from 'react';
type InstallPrompt = Event & {prompt:()=>Promise<void>;userChoice:Promise<{outcome:string}>};
export default function Pwa(){
  const [prompt,setPrompt]=useState<InstallPrompt|null>(null);
  const [standalone,setStandalone]=useState(true);
  const [help,setHelp]=useState(false);
  useEffect(()=>{
    const media=window.matchMedia('(display-mode: standalone)');
    const update=()=>setStandalone(media.matches || Boolean((navigator as Navigator & {standalone?:boolean}).standalone));
    const install=(e:Event)=>{e.preventDefault();setPrompt(e as InstallPrompt)};
    const installed=()=>{setStandalone(true);setPrompt(null);setHelp(false)};
    update();media.addEventListener('change',update);
    window.addEventListener('beforeinstallprompt',install);window.addEventListener('appinstalled',installed);
    if(process.env.NODE_ENV==='production' && 'serviceWorker' in navigator && window.isSecureContext){
      navigator.serviceWorker.register('/sw.js',{scope:'/',updateViaCache:'none'}).catch(()=>{/* Browser installation remains optional. */});
    }
    return ()=>{media.removeEventListener('change',update);window.removeEventListener('beforeinstallprompt',install);window.removeEventListener('appinstalled',installed)};
  },[]);
  if(standalone)return null;
  return <aside className="fixed bottom-4 right-4 z-50 max-w-sm rounded-xl border border-slate-700 bg-slate-900 p-3 shadow-xl" aria-label="Install Agent Studio">
    {help&&<div className="text-sm text-slate-300 mb-3"><p>On iPhone or iPad: open in Safari, tap Share, then Add to Home Screen.</p><p className="mt-2">On Android or desktop: use your browser’s Install app menu. Installation availability depends on the browser.</p><button className="quiet mt-3" onClick={()=>setHelp(false)}>Close instructions</button></div>}
    <button className="quiet text-sm" onClick={async()=>{if(!prompt){setHelp(!help);return;}await prompt.prompt();await prompt.userChoice;setPrompt(null)}}>Install app ↗</button>
  </aside>;
}
