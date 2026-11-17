import {randomUUID} from 'node:crypto';
export class AgentError extends Error{constructor(message,status=400){super(message);this.status=status}}
export function cleanMessages(messages){if(!Array.isArray(messages)||!messages.length||messages.length>40)throw new AgentError('Provide 1–40 messages.');return messages.map(m=>{if(!['system','user','assistant'].includes(m.role)||typeof m.content!=='string'||m.content.length>64000)throw new AgentError('Invalid chat message.');return {role:m.role,content:m.content}})}
export function toolText(result){return (result.content||[]).filter(c=>c.type==='text').map(c=>c.text).join('\n').slice(0,64000)||'Tool completed. Non-text output is shown in Relay.'}
export class Agent{
 constructor({model,createPlugin,maxSessions=2,now=()=>Date.now()}){Object.assign(this,{model,createPlugin,maxSessions,now});this.sessions=new Map();this.creating=0}
 async prune(){for(const [id,s]of this.sessions)if(!s.busy&&this.now()-s.updated>15*60*1000)await this.close(id)}
 async close(id){const s=this.sessions.get(id);this.sessions.delete(id);if(s){s.abort.abort();await s.plugin.close()}}
 async begin({session:sessionId,model,messages},signal){
  await this.prune();let s=this.sessions.get(sessionId);
  if(sessionId&&!s)throw new AgentError('Plugin session expired. Reconnect the plugin gateway.',410);
  const clean=cleanMessages(messages);if(clean.at(-1).role!=='user')throw new AgentError('A user message must end the conversation.');
  if(s&&(s.pending||s.busy))throw new AgentError('Finish or decline the pending tool action first.',409);
  if(!s){if(this.sessions.size+this.creating>=this.maxSessions)throw new AgentError('Gateway is busy. Close another plugin session or wait 15 minutes.',429);this.creating++;let plugin;try{plugin=await this.createPlugin()}finally{this.creating--}s={abort:new AbortController(),id:randomUUID(),plugin,messages:clean,updated:this.now(),model,busy:false,rounds:0,pending:null};this.sessions.set(s.id,s)}else{if(s.model!==model)throw new AgentError('Reconnect plugins after changing model.');s.messages.push(clean.at(-1));s.rounds=0}
  const cancel=()=>{void this.close(s.id)};if(signal?.aborted){await this.close(s.id);throw new AgentError('Request cancelled.',499)}signal?.addEventListener('abort',cancel,{once:true});try{return await this.advance(s)}finally{signal?.removeEventListener('abort',cancel)}
 }
 async advance(s){s.busy=true;s.updated=this.now();try{
  if(s.messages.length>80)throw new AgentError('Plugin context limit reached. Start a new conversation.');
  const tools=s.plugin.tools.map(t=>({type:'function',function:{name:t.name,description:t.description||t.name,parameters:t.inputSchema}}));
  const message=await this.model({model:s.model,messages:s.messages,tools},s.abort.signal);if(!message||message.role&&message.role!=='assistant')throw new AgentError('Ollama returned an invalid assistant message.',502);
  const calls=message.tool_calls||[];if(!Array.isArray(calls)||calls.length>4)throw new AgentError('Too many tool calls in one step.',502);
  if(!calls.length){const text=String(message.content||'');if(!text.trim())throw new AgentError('The model returned an empty reply.',502);s.messages.push({role:'assistant',content:text});return {session:s.id,done:true,content:text}}
  if(++s.rounds>8)throw new AgentError('Tool step limit reached. Send a new instruction to continue.');
  const checked=calls.map(call=>{const f=call.function;if(!f||!s.plugin.tools.some(t=>t.name===f.name)||!f.arguments||typeof f.arguments!=='object'||Array.isArray(f.arguments))throw new AgentError('The model requested an invalid/unavailable tool.',502);return {id:call.id||randomUUID(),type:'function',function:{name:f.name,arguments:f.arguments}}});
  s.messages.push({role:'assistant',content:String(message.content||''),tool_calls:checked});s.pending={id:randomUUID(),calls:checked};
  return {session:s.id,done:false,approval:{id:s.pending.id,calls:checked.map(c=>({name:c.function.name,arguments:c.function.arguments}))}}
 }finally{s.busy=false;s.updated=this.now()}}
 async continue({session,approvalId,allow},signal){const s=this.sessions.get(session);if(!s)throw new AgentError('Plugin session expired.',410);if(s.busy)throw new AgentError('Tool action is running.',409);if(!s.pending||s.pending.id!==approvalId||typeof allow!=='boolean')throw new AgentError('Approval expired or invalid.',409);const cancel=()=>{void this.close(s.id)};if(signal?.aborted)throw new AgentError('Request cancelled.',499);signal?.addEventListener('abort',cancel,{once:true});const pending=s.pending;s.pending=null;s.busy=true;s.updated=this.now();const events=[];
 try{for(const call of pending.calls){let result;if(allow){try{result=await s.plugin.call(call.function.name,call.function.arguments)}catch{result={isError:true,content:[{type:'text',text:'Tool failed. Check the plugin server and browser.'}]}}}else result={content:[{type:'text',text:'User declined this tool action. Do not retry it without a new request.'}]};
 s.messages.push({role:'tool',tool_name:call.function.name,tool_call_id:call.id,content:toolText(result)});
 events.push({name:call.function.name,approved:allow,isError:!!result.isError,content:(result.content||[]).filter(c=>c.type==='text'||(c.type==='image'&&typeof c.data==='string'&&c.data.length<=2000000)).map(c=>c.type==='text'?{type:'text',text:String(c.text).slice(0,64000)}:c)});
 }if(!allow){signal?.removeEventListener('abort',cancel);const content='Tool action declined. No browser action was run.';s.messages.push({role:'assistant',content});return {session:s.id,done:true,content,events}}
 }finally{s.busy=false;s.updated=this.now()}
 try{return {...await this.advance(s),events}}finally{signal?.removeEventListener('abort',cancel)}
 }
}
