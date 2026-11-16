'use client';
import {useEffect,FormEvent} from 'react';
type Props={busy:boolean;error:string;submit:(path:string,data:Record<string,string>)=>void};
export default function AuthPanel({busy,error,submit}:Props){
  useEffect(()=>{
    // Retired owner links must not restore signup or leave old codes in history.
    const clearSetupLink=()=>{
      if(new URLSearchParams(window.location.hash.slice(1)).has('owner-setup'))
        window.history.replaceState(null,'',window.location.pathname+window.location.search);
    };
    clearSetupLink();window.addEventListener('hashchange',clearSetupLink);
    return ()=>window.removeEventListener('hashchange',clearSetupLink);
  },[]);
  function onSubmit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();
    const fields=new FormData(event.currentTarget);
    submit('/auth/login',{email:String(fields.get('email')),password:String(fields.get('password'))});
  }
  return <main className="min-h-screen grid place-items-center p-6"><section className="panel w-full max-w-md">
    <div className="text-emerald-300 text-xl mb-8">◈ Agent Meadow</div>
    <h1 className="text-3xl font-semibold">Welcome back.</h1>
    <p className="text-slate-400 mt-3 mb-7">Sign in to your agent workspace.</p>
    <form onSubmit={onSubmit}>
      <label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="username" required maxLength={254}/>
      <label htmlFor="password">Password</label><input id="password" name="password" type="password" minLength={12} maxLength={128} autoComplete="current-password" required/>
      {error&&<p role="alert" className="text-red-300 mt-4">{error}</p>}
      <button disabled={busy} className="btn w-full mt-6">{busy?'Signing in…':'Sign in →'}</button>
    </form>
    <div className="border-t border-slate-700 mt-6 pt-6 text-center">
      <p className="text-sm text-slate-400 mb-3">Accounts are provided by the platform owner. Email to request access for your business.</p>
      <a className="quiet inline-block" href="mailto:tmcwilliams2010@outlook.com?subject=Agent%20Meadow%20account%20request">Request access by email</a>
      <p className="text-sm text-slate-400 mt-3 break-all">tmcwilliams2010@outlook.com</p>
    </div>
  </section></main>;
}
