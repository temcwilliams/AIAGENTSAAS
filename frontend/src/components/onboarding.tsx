'use client';
import {useEffect,useState} from 'react';
import {api} from '../lib/api';
type Profile={business_name:string;description:string;contact_name:string;contact_email:string;phone:string;website:string;services:string;faqs:string;hours:string;handoff_preferences:string;template:string};
type Draft={business_id:string;version:number;status:string;profile:Profile;reviewer_notes:string;agent_id:string|null;published_at:string|null;template_version:number};
const blank:Profile={business_name:'',description:'',contact_name:'',contact_email:'',phone:'',website:'',services:'',faqs:'',hours:'',handoff_preferences:'',template:'reception'};
const labels:Record<string,string>={draft:'Draft',submitted:'Submitted for review',changes_requested:'Changes requested',approved:'Approved',published:'Published to workspace'};
export default function Onboarding({businessId,role,onPublished}:{businessId:string;role:string;onPublished:()=>Promise<void>}){
 const [draft,setDraft]=useState<Draft|null>(null),[profile,setProfile]=useState<Profile>(blank),[step,setStep]=useState(0),[busy,setBusy]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[notes,setNotes]=useState(''),[model,setModel]=useState('qwen2.5:1.5b'),[enabled,setEnabled]=useState(true),[preview,setPreview]=useState<{knowledge:string;system_prompt:string}|null>(null);
 const base='/businesses/'+businessId+'/onboarding';
 const canManage=role==='admin'||role==='manager';
 const editable=canManage&&draft&&!['submitted','approved'].includes(draft.status);
 const dirty=!!draft&&JSON.stringify(profile)!==JSON.stringify({...blank,...draft.profile});
 function accept(d:Draft){setDraft(d);setProfile({...blank,...d.profile});setNotes(d.reviewer_notes||'');setPreview(null)}
 useEffect(()=>{const c=new AbortController();if(businessId)api<Draft>(base,'GET',undefined,c.signal).then(accept).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>c.abort()},[base,businessId]);
 async function run(work:()=>Promise<void>){setBusy(true);setError('');setNotice('');try{await work()}catch(e){setError(e instanceof Error?e.message:'Request failed')}finally{setBusy(false)}}
 async function save(){const d=await api<Draft>(base,'PUT',{expected_version:draft?.version??0,profile});accept(d);return d}
 function field(key:keyof Profile,label:string,max:number,multiline=false,type='text'){
  const props={id:'setup-'+key,value:profile[key],maxLength:max,readOnly:!editable,onChange:(e:React.ChangeEvent<HTMLInputElement|HTMLTextAreaElement>)=>setProfile(p=>({...p,[key]:e.target.value}))};
  return <div><label htmlFor={props.id}>{label}</label>{multiline?<textarea {...props} rows={key==='faqs'?7:4}/>:<input {...props} type={type}/>}</div>;
 }
 if(!businessId)return <section className="panel">Create or select a business to begin setup.</section>;
 if(!draft)return <section className="panel">{error?<p role="alert">{error}</p>:'Loading business setup…'}</section>;
 return <div className="max-w-5xl space-y-6">
  <section className="panel"><div className="flex flex-wrap justify-between gap-4"><div><h2>Business setup</h2><p className="text-slate-400 text-sm mt-3">Save your business facts, then send them to the owner for approval. Drafts never change a running agent.</p></div><div><p className="text-emerald-200">{labels[draft.status]}</p><small>Revision {draft.version}</small></div></div>
   {!canManage&&<p className="text-amber-200 text-sm mt-5">You can view this setup. Ask the platform owner for Manager access to edit and submit it.</p>}
   {draft.reviewer_notes&&<div className="bg-slate-800 rounded-xl p-4 mt-5"><p className="text-sm text-emerald-200">Owner review notes</p><p className="mt-2 whitespace-pre-wrap">{draft.reviewer_notes}</p></div>}
   {draft.status==='published'&&<p role="status" className="text-emerald-200 mt-5">Your approved agent and knowledge are in the workspace. AI replies still require a connected inference provider. Editing starts a new draft without changing the approved configuration.</p>}
  </section>
  {error&&<p role="alert" className="text-red-300">{error}</p>}{notice&&<p role="status" className="text-emerald-200">{notice}</p>}
  <form className="panel" onSubmit={e=>{e.preventDefault();run(async()=>{await save();setNotice('Draft saved. You can return to it later.')})}}>
   <nav aria-label="Business setup steps" className="flex flex-wrap gap-3 mb-6">{['Business profile','Services & FAQs','Handoff & review'].map((label,i)=><button type="button" className={step===i?'btn':'quiet'} aria-current={step===i?'step':undefined} onClick={()=>setStep(i)} key={label}>{i+1}. {label}</button>)}</nav>
   {step===0&&<div className="grid md:grid-cols-2 gap-x-6">{field('business_name','Business name',120)}{field('contact_name','Primary contact name',120)}{field('contact_email','Business contact email',254,false,'email')}{field('phone','Business phone',80)}{field('website','Business website',2048,false,'url')}{field('hours','Opening hours',1000,true)}<div className="md:col-span-2">{field('description','About your business',2000,true)}</div></div>}
   {step===1&&<>{field('services','Services or products',4000,true)}{field('faqs','Frequently asked questions and answers',6000,true)}<p className="text-slate-400 text-sm mt-4">Use plain text. Website crawling, PDF import and automatic URL fetching are not part of this setup.</p></>}
   {step===2&&<>{field('handoff_preferences','When and how should a person take over?',2000,true)}<label htmlFor="setup-template">Preferred starter template</label><select id="setup-template" value={profile.template} disabled={!editable} onChange={e=>setProfile(p=>({...p,template:e.target.value}))}><option value="reception">General reception</option><option value="support">Customer support</option><option value="leads">Lead qualification</option></select><p className="text-slate-400 text-sm mt-4">The owner reviews your preferred template and controls the model and publication.</p></>}
   <div className="flex flex-wrap gap-3 mt-7">
    {editable&&<><button className="btn" disabled={busy}>{busy?'Working…':'Save draft'}</button><button type="button" className="quiet" disabled={busy} onClick={()=>run(async()=>{const d=dirty||draft.version===0?await save():draft;accept(await api<Draft>(base+'/submit','POST',{expected_version:d.version}));setNotice('Setup submitted. The owner will review it before publication.')})}>Submit for owner review</button></>}
    <button type="button" className="quiet" disabled={busy} onClick={()=>run(async()=>{accept(await api<Draft>(base));setNotice('Loaded the latest saved version.')})}>Reload saved setup</button>
    <button type="button" className="quiet" disabled={busy||draft.version===0} onClick={()=>run(async()=>{setPreview(await api(base+'/preview'))})}>Preview saved setup</button>
   </div>
   {dirty&&<small className="block mt-4">You have unsaved changes.</small>}
  </form>
  {preview&&<section className="panel"><h2>Saved setup preview</h2><p className="text-slate-400 text-sm my-3">Preview only. No model is called and no running agent is changed.</p><h3>Template instructions</h3><p className="text-sm whitespace-pre-wrap my-4">{preview.system_prompt}</p><h3>Business reference facts</h3><pre className="whitespace-pre-wrap break-words text-sm mt-4">{preview.knowledge}</pre></section>}
  {role==='admin'&&['submitted','approved'].includes(draft.status)&&<section className="panel"><h2>Owner review</h2><p className="text-slate-400 text-sm mt-3">Review the saved setup and preview before approving. Publication updates only this setup’s managed starter agent and reference document.</p>
   <label htmlFor="review-notes">Feedback for the client</label><textarea id="review-notes" value={notes} onChange={e=>setNotes(e.target.value)} maxLength={4000} rows={4}/>
   <div className="flex flex-wrap gap-3 mt-4"><button className="quiet" disabled={busy||!notes.trim()} onClick={()=>run(async()=>{accept(await api<Draft>(base+'/review','POST',{expected_version:draft.version,decision:'changes_requested',notes}))})}>Request changes</button>
   {draft.status==='submitted'&&<button className="btn" disabled={busy} onClick={()=>run(async()=>{accept(await api<Draft>(base+'/review','POST',{expected_version:draft.version,decision:'approved',notes}))})}>Approve setup</button>}</div>
   {draft.status==='approved'&&<><label htmlFor="publish-model">Owner-selected model</label><input id="publish-model" value={model} maxLength={100} required onChange={e=>setModel(e.target.value)}/><label><input type="checkbox" className="!w-auto mr-2" checked={enabled} onChange={e=>setEnabled(e.target.checked)}/>Enable this agent in the workspace</label><p className="text-sm text-slate-400 mt-3">This publishes workspace configuration. It does not create a public website widget or enable an AI provider.</p><button className="btn mt-5" disabled={busy||!model.trim()} onClick={()=>run(async()=>{accept(await api<Draft>(base+'/publish','POST',{expected_version:draft.version,model,enabled}));await onPublished();setNotice('Approved setup published to the workspace.')})}>Publish approved setup</button></>}
  </section>}
 </div>;
}
