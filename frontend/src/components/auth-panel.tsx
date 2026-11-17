'use client';
import {useEffect,useState,FormEvent} from 'react';
import {api} from '../lib/api';
type Props={busy:boolean;error:string;submit:(path:string,data:Record<string,string>)=>void};
export default function AuthPanel({busy,error,submit}:Props){
  const [forgot,setForgot]=useState(false),[mailAvailable,setMailAvailable]=useState(false),[sending,setSending]=useState(false),[notice,setNotice]=useState(''),[mailError,setMailError]=useState('');
  useEffect(()=>{const c=new AbortController();api<{available:boolean}>('/auth/email/status','GET',undefined,c.signal).then(r=>setMailAvailable(r.available)).catch(()=>{});return()=>c.abort()},[]);
  useEffect(()=>{
    // Retired owner links must not restore signup or leave old codes in history.
    const clearSetupLink=()=>{
      if(new URLSearchParams(window.location.hash.slice(1)).has('owner-setup'))
        window.history.replaceState(null,'',window.location.pathname+window.location.search);
    };
    clearSetupLink();window.addEventListener('hashchange',clearSetupLink);
    return ()=>window.removeEventListener('hashchange',clearSetupLink);
  },[]);
  async function onSubmit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();
    const fields=new FormData(event.currentTarget);
    if(forgot){
      setSending(true);setMailError('');setNotice('');
      try{const r=await api<{message:string}>('/auth/password/forgot','POST',{email:String(fields.get('email'))});setNotice(r.message)}
      catch(e){setMailError(e instanceof Error?e.message:'Request failed')}
      finally{setSending(false)}
      return;
    }
    submit('/auth/login',{email:String(fields.get('email')),password:String(fields.get('password'))});
  }
  return <main className="min-h-screen grid place-items-center p-6"><section className="panel w-full max-w-md">
    <div className="text-emerald-300 text-xl mb-8">◈ Agent Meadow</div>
    <h1 className="text-3xl font-semibold">{forgot?'Recover your account':'Welcome back.'}</h1>
    <p className="text-slate-400 mt-3 mb-7">{forgot?'Request a private password reset link for your existing account.':'Sign in to your agent workspace.'}</p>
    <form onSubmit={onSubmit}>
      <label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="username" required maxLength={254}/>
      {!forgot&&<><label htmlFor="password">Password</label><input id="password" name="password" type="password" minLength={12} maxLength={128} autoComplete="current-password" required/></>}
      {forgot&&!mailAvailable&&<p className="text-amber-200 text-sm mt-4">Email delivery is unavailable. Contact the owner below for help; no recovery email has been sent.</p>}
      {(forgot?mailError:error)&&<p role="alert" className="text-red-300 mt-4">{forgot?mailError:error}</p>}
      {notice&&<p role="status" className="text-emerald-200 mt-4">{notice}</p>}
      <button disabled={busy||sending||forgot&&!mailAvailable} className="btn w-full mt-6">{forgot?(sending?'Requesting…':'Request password reset'):(busy?'Signing in…':'Sign in →')}</button>
    </form>
    <button type="button" className="quiet w-full mt-4" disabled={busy||sending} onClick={()=>{setForgot(!forgot);setNotice('');setMailError('')}}>{forgot?'Back to sign in':'Forgot password?'}</button>
    <div className="border-t border-slate-700 mt-6 pt-6 text-center">
      <p className="text-sm text-slate-400 mb-3">Accounts are provided by the platform owner. Email to request access for your business.</p>
      <a className="quiet inline-block" href="mailto:tmcwilliams2010@outlook.com?subject=Agent%20Meadow%20account%20request">Request access by email</a>
      <p className="text-sm text-slate-400 mt-3 break-all">tmcwilliams2010@outlook.com</p>
    </div>
  </section></main>;
}
