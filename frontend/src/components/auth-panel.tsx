'use client';
import {useEffect,useState,FormEvent} from 'react';
type Props={busy:boolean;error:string;submit:(path:string,data:Record<string,string>)=>void;clearError:()=>void};
export default function AuthPanel({busy,error,submit,clearError}:Props){
  const [signup,setSignup]=useState(false),[setupToken,setSetupToken]=useState(''),[confirmError,setConfirmError]=useState(''),[ownerLink,setOwnerLink]=useState(false);
  useEffect(()=>{
    const params=new URLSearchParams(window.location.hash.slice(1));
    const token=params.get('owner-setup');
    if(token){setOwnerLink(true);setSetupToken(token);setSignup(true);window.history.replaceState(null,'',window.location.pathname+window.location.search);}
  },[]);
  function changeMode(){setSignup(!signup);setConfirmError('');clearError()}
  function onSubmit(event:FormEvent<HTMLFormElement>){
    event.preventDefault();setConfirmError('');
    const fields=new FormData(event.currentTarget);
    const password=String(fields.get('password'));
    if(signup&&password!==fields.get('confirm_password')){setConfirmError('Your passwords do not match.');return;}
    const data:Record<string,string>={email:String(fields.get('email')),password};
    if(signup){data.business_name=String(fields.get('business_name'));if(setupToken)data.setup_token=setupToken;}
    submit(signup?'/auth/register':'/auth/login',data);
  }
  return <main className="min-h-screen grid place-items-center p-6"><section className="panel w-full max-w-md">
    <div className="text-emerald-300 text-xl mb-8">◈ Agent Studio</div>
    <h1 className="text-3xl font-semibold">{signup?'Create your account.':'Welcome back.'}</h1>
    <p className="text-slate-400 mt-3 mb-7">{signup?(setupToken?'Set up your platform owner account.':'Get your own business workspace in minutes.'):'Sign in to your agent workspace.'}</p>
    <form onSubmit={onSubmit}>
      {signup&&<><label htmlFor="business-name">Business name</label><input id="business-name" name="business_name" autoComplete="organization" required minLength={1} maxLength={120}/></>}
      <label htmlFor="email">Email address</label><input id="email" name="email" type="email" autoComplete="username" required maxLength={254}/>
      <label htmlFor="password">Password</label><input id="password" name="password" type="password" minLength={12} maxLength={128} autoComplete={signup?'new-password':'current-password'} required/>
      {signup&&<><small className="block mt-2">Use at least 12 characters.</small><label htmlFor="confirm-password">Confirm password</label><input id="confirm-password" name="confirm_password" type="password" autoComplete="new-password" required minLength={12} maxLength={128}/></>}
      {(confirmError||error)&&<p role="alert" className="text-red-300 mt-4">{confirmError||error}</p>}
      <button disabled={busy} className="btn w-full mt-6">{busy?(signup?'Creating account…':'Signing in…'):(signup?'Create account':'Sign in →')}</button>
    </form>
    <div className="border-t border-slate-700 mt-6 pt-6 text-center"><p className="text-sm text-slate-400 mb-3">{signup?'Already have an account?':'New to Agent Studio?'}</p><button type="button" disabled={busy} className="quiet w-full" onClick={changeMode}>{signup?'Back to sign in':'Create account'}</button></div>
    {signup&&!ownerLink&&<details className="mt-5 text-sm text-slate-400"><summary className="cursor-pointer">Have an owner setup code?</summary><label htmlFor="owner-code">Owner setup code</label><input id="owner-code" type="password" autoComplete="off" maxLength={256} value={setupToken} onChange={event=>setSetupToken(event.target.value)}/></details>}
  </section></main>;
}
