'use client';
import {useEffect,useState,FormEvent} from 'react';
import {api} from '../lib/api';

export type AccountAction={purpose:'reset'|'setup'|'verify';token:string};
const errorText=(error:unknown)=>error instanceof Error?error.message:'Request failed';
export function AccountActionPanel({action,onDone}:{action:AccountAction;onDone:()=>void}){
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[done,setDone]=useState(false);
 async function finish(event:FormEvent<HTMLFormElement>){
  event.preventDefault();setError('');
  const data=new FormData(event.currentTarget);
  if(action.purpose!=='verify'&&data.get('password')!==data.get('confirm_password')){setError('Your passwords do not match.');return;}
  setBusy(true);
  try{
   if(action.purpose==='verify')await api('/auth/email/verify','POST',{token:action.token});
   else await api('/auth/password/reset','POST',{token:action.token,purpose:action.purpose,new_password:String(data.get('password'))});
   setDone(true);
  }catch(e){setError(errorText(e))}finally{setBusy(false)}
 }
 return <main className="min-h-screen grid place-items-center p-6"><section className="panel w-full max-w-md">
  <p className="text-emerald-300 mb-7">◈ Agent Meadow</p>
  <h1 className="text-3xl font-semibold">{action.purpose==='verify'?'Verify your email':action.purpose==='setup'?'Set your password':'Reset your password'}</h1>
  {done?<><p role="status" className="my-6 text-emerald-200">{action.purpose==='verify'?'Your email is verified.':'Your password is updated. All previous sessions have ended. Sign in with your new password.'}</p><button className="btn" onClick={onDone}>Continue</button></>:<form onSubmit={finish}>
   {action.purpose==='verify'?<p className="text-slate-400 my-6">Confirm that you want to verify the email address this link was sent to.</p>:<>
    <label htmlFor="action-password">New password</label><input id="action-password" name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required/>
    <label htmlFor="action-confirm">Confirm new password</label><input id="action-confirm" name="confirm_password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required/>
    <p className="text-sm text-slate-400 mt-3">Use at least 12 characters. This private link can be used once.</p>
   </>}
   {error&&<p role="alert" className="text-red-300 mt-4">{error}</p>}
   <button className="btn mt-6 w-full" disabled={busy}>{busy?'Updating…':action.purpose==='verify'?'Verify email':'Save password'}</button>
   <button type="button" className="quiet mt-4 w-full" disabled={busy} onClick={onDone}>Back to workspace</button>
  </form>}
 </section></main>;
}

export function EmailVerificationPanel({verified,onRefresh}:{verified:boolean;onRefresh:()=>Promise<void>}){
 const [available,setAvailable]=useState(false),[busy,setBusy]=useState(false),[notice,setNotice]=useState(''),[error,setError]=useState('');
 useEffect(()=>{const c=new AbortController();api<{available:boolean}>('/auth/email/status','GET',undefined,c.signal).then(r=>setAvailable(r.available)).catch(()=>{});return()=>c.abort()},[]);
 return <section className="panel max-w-xl mb-6"><h2>Email verification</h2><p className="text-slate-400 text-sm my-4">{verified?'Your email is verified.':'Your email has not been verified yet. Existing dashboard access is still available.'}</p>
 {!available&&!verified&&<p className="text-amber-200 text-sm mb-4">Email delivery is unavailable. The owner must configure a delivery provider before verification mail can be sent.</p>}
 {notice&&<p role="status" className="text-emerald-200 my-3">{notice}</p>}{error&&<p role="alert" className="text-red-300 my-3">{error}</p>}
 {!verified&&<button className="btn mr-3" disabled={busy||!available} onClick={async()=>{setBusy(true);setError('');try{const r=await api<{message:string}>('/auth/email/resend','POST');setNotice(r.message)}catch(e){setError(errorText(e))}finally{setBusy(false)}}}>Send verification email</button>}
 <button className="quiet mt-2" disabled={busy} onClick={async()=>{setBusy(true);try{await onRefresh()}catch(e){setError(errorText(e))}finally{setBusy(false)}}}>Refresh verification status</button>
 </section>;
}

type ManagedUser={id:string;email:string;role:string;business_id:string|null;business_role:string;disabled:boolean;email_verified:boolean;last_delivery:{purpose:string;status:string;at:string}|null};
export function AdminAccounts({businessId,currentUserId,onBusinessCreated,onBusinessChanged}:{businessId:string;currentUserId:string;onBusinessCreated:(id:string)=>Promise<void>;onBusinessChanged:()=>Promise<void>}){
 const [users,setUsers]=useState<ManagedUser[]>([]),[mail,setMail]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState('');
 const path='/users'+(businessId?'?business_id='+encodeURIComponent(businessId):'');
 async function refresh(){setUsers(await api<ManagedUser[]>(path))}
 useEffect(()=>{const c=new AbortController();Promise.all([api<ManagedUser[]>(path,'GET',undefined,c.signal),api<{available:boolean}>('/auth/email/status','GET',undefined,c.signal)]).then(([u,m])=>{setUsers(u);setMail(m.available)}).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort()},[path]);
 async function run(work:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await work()}catch(e){setError(errorText(e))}finally{setBusy(false)}}
 const roles=<><option value="viewer">Viewer · read dashboard</option><option value="responder">Responder · handle handoffs</option><option value="manager">Manager · onboarding and handoffs</option></>;
 return <div className="space-y-6">
  {error&&<p role="alert" className="text-red-300">{error}</p>}{notice&&<p role="status" className="text-emerald-200">{notice}</p>}
  <div className="grid lg:grid-cols-2 gap-6">
   <form className="panel" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(async()=>{const b=await api<{id:string}>('/businesses','POST',{name:String(f.get('name'))});await onBusinessCreated(b.id)})}}><h2>Create business</h2><label htmlFor="new-business-name">Business name</label><input id="new-business-name" name="name" maxLength={120} required/><button className="btn mt-5" disabled={busy}>Create business</button></form>
   <form className="panel" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(async()=>{await api('/businesses/'+businessId,'PUT',{name:String(f.get('name'))});await onBusinessChanged();setNotice('Business name updated.')})}}><h2>Rename selected business</h2><label htmlFor="rename-business">New business name</label><input id="rename-business" name="name" maxLength={120} required/><button className="btn mt-5" disabled={busy||!businessId}>Save business name</button></form>
   <form className="panel" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(async()=>{const r=await api<{delivery:string}>('/users/invite','POST',{email:String(f.get('email')),business_id:businessId,business_role:String(f.get('business_role'))});await refresh();setNotice(r.delivery==='sent'?'Account created; setup email accepted by the provider.':'Account created but delivery failed. Use Send setup email below to retry.')})}}>
    <h2>Invite an approved client</h2><p className="text-sm text-slate-400 mt-3">The client sets their own password through a private, expiring email link.</p>
    {!mail&&<p className="text-amber-200 text-sm mt-3">Email delivery is off. Invitations are unavailable; the manual account option remains available.</p>}
    <label htmlFor="invite-email">Invitation email</label><input id="invite-email" name="email" type="email" maxLength={254} required/>
    <label htmlFor="invite-role">Business role</label><select id="invite-role" name="business_role">{roles}</select>
    <button className="btn mt-5" disabled={busy||!businessId||!mail}>Create account and email setup link</button>
   </form>
   <form className="panel" onSubmit={e=>{e.preventDefault();const f=new FormData(e.currentTarget);run(async()=>{await api('/users','POST',{email:String(f.get('email')),password:String(f.get('password')),business_id:businessId,business_role:String(f.get('business_role'))});await refresh();setNotice('Client account created. Share the temporary password securely and ask the client to change it in Account security.')})}}>
    <h2>Manual client account</h2><p className="text-sm text-slate-400 mt-3">For owner-approved access while email is unavailable. This does not verify the client’s email.</p>
    <label htmlFor="manual-email">Client email</label><input id="manual-email" name="email" type="email" maxLength={254} required/>
    <label htmlFor="manual-password">Temporary password · share securely</label><input id="manual-password" name="password" type="password" autoComplete="new-password" minLength={12} maxLength={128} required/>
    <label htmlFor="manual-role">Business role</label><select id="manual-role" name="business_role">{roles}</select>
    <button className="btn mt-5" disabled={busy||!businessId}>Create client account</button>
   </form>
  </div>
  <section className="panel"><h2>Account access</h2><p className="text-sm text-slate-400 mt-3 mb-5">Roles apply only to the account’s business. Choose Manager for a client who should complete onboarding. The final active owner cannot be disabled.</p>
   <button className="quiet mb-5" disabled={busy} onClick={()=>run(refresh)}>Refresh accounts</button>
   <div className="space-y-5">{users.map(u=><div key={u.id} className="border-t border-slate-700 pt-5"><p className="break-all">{u.email}</p><p className="text-sm text-slate-400 mt-2">{u.disabled?'Disabled':'Active'} · {u.email_verified?'Email verified':'Email unverified'} · {u.role==='admin'?'Platform administrator':u.business_role}</p>
    {u.last_delivery&&<small className="block mt-2">Last {u.last_delivery.purpose} email: {u.last_delivery.status}</small>}
    <div className="flex flex-wrap gap-3 mt-3">
     {u.role==='client'&&<select aria-label={'Business role for '+u.email} className="!w-auto max-w-full" value={u.business_role} disabled={busy} onChange={e=>{const role=e.target.value;run(async()=>{await api('/businesses/'+u.business_id+'/members/'+u.id,'PUT',{role});await refresh();setNotice('Business role updated.')})}}>{roles}</select>}
     <button className="quiet" disabled={busy||!mail||u.disabled} onClick={()=>run(async()=>{const r=await api<{message:string}>('/users/'+u.id+'/setup','POST');setNotice(r.message);await refresh()})}>Send setup email</button>
     {u.id!==currentUserId&&<button className="quiet" disabled={busy} onClick={()=>run(async()=>{await api('/users/'+u.id+'/status','PUT',{disabled:!u.disabled});await refresh();setNotice(u.disabled?'Account enabled.':'Account disabled and its sessions revoked.')})}>{u.disabled?'Enable account':'Disable account'}</button>}
    </div>
   </div>)}{!users.length&&<p className="text-slate-400">No accounts in this business yet.</p>}</div>
  </section>
 </div>;
}
