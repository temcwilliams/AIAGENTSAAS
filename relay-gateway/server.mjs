import http from 'node:http';
import {timingSafeEqual} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {Agent,AgentError} from './agent.mjs';
import {playwrightClient} from './mcp.mjs';

export function createGateway({token,origins,agent,listModels}){
 if(typeof token!=='string'||token.length<32)throw Error('Set RELAY_GATEWAY_TOKEN to at least 32 random characters.');const expected=Buffer.from('Bearer '+token);
 return http.createServer(async(req,res)=>{
  const origin=req.headers.origin;if(origin&&!origins.includes(origin)){res.writeHead(403).end();return}if(origin){res.setHeader('Access-Control-Allow-Origin',origin);res.setHeader('Vary','Origin')}res.setHeader('Cache-Control','no-store');res.setHeader('X-Content-Type-Options','nosniff');
  if(req.method==='OPTIONS'){res.setHeader('Access-Control-Allow-Headers','Authorization, Content-Type');res.setHeader('Access-Control-Allow-Methods','GET, POST, DELETE, OPTIONS');res.writeHead(204).end();return}
  const pathname=new URL(req.url,'http://gateway').pathname;if(req.method==='GET'&&pathname==='/health'){res.setHeader('Content-Type','application/json');res.end('{"status":"ok"}');return}
  const supplied=Buffer.from(req.headers.authorization||'');if(supplied.length!==expected.length||!timingSafeEqual(supplied,expected)){res.writeHead(401).end();return}
  const disconnected=new AbortController();res.on('close',()=>{if(!res.writableEnded)disconnected.abort()});
  let timer=setTimeout(()=>req.destroy(),15000),size=0;
  try{const chunks=[];for await(const chunk of req){size+=chunk.length;if(size>256000)throw new AgentError('Request too large.',413);chunks.push(chunk)}const raw=Buffer.concat(chunks).toString('utf8');clearTimeout(timer);timer=null;const body=raw?JSON.parse(raw):{};let result;
   if(pathname==='/v1/status'&&req.method==='GET')result={name:'Relay plugin gateway',plugins:['playwright'],models:await listModels()};
   else if(pathname==='/v1/chat'&&req.method==='POST'){if(typeof body.model!=='string'||!body.model||body.model.length>200)throw new AgentError('Choose a model.');result=await agent.begin(body,disconnected.signal)}
   else if(pathname==='/v1/continue'&&req.method==='POST')result=await agent.continue(body,disconnected.signal);
   else if(pathname==='/v1/session'&&req.method==='DELETE'){if(typeof body.session==='string')await agent.close(body.session);result={closed:true}}
   else throw new AgentError('Not found.',404);
   const output=JSON.stringify(result);if(output.length>4000000)throw new AgentError('Plugin result too large.',502);res.writeHead(200,{'Content-Type':'application/json'}).end(output);
  }catch(error){if(!res.headersSent)res.writeHead(error.status||400,{'Content-Type':'application/json'});res.end(JSON.stringify({error:error instanceof AgentError?error.message:'Plugin request failed. Check the gateway and Ollama configuration.'}))}finally{if(timer)clearTimeout(timer)}
 });
}
export function ollamaClient({url,token=''}){const base=new URL(url);if(!['http:','https:'].includes(base.protocol)||base.username||base.password||base.search||base.hash)throw Error('Invalid OLLAMA_URL.');return async(path,body,signal)=>{
 const response=await fetch(new URL(path,base.href.replace(/\/?$/,'/')),{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},body:body?JSON.stringify(body):undefined,redirect:'error',signal:signal?AbortSignal.any([signal,AbortSignal.timeout(120000)]):AbortSignal.timeout(120000)});
 if(!response.ok)throw new AgentError('Ollama request failed. Choose an installed tool-capable model and check server settings.',502);const reader=response.body.getReader();let text='',bytes=0;const decoder=new TextDecoder();while(true){const part=await reader.read();if(part.done)break;bytes+=part.value.length;if(bytes>4000000){await reader.cancel();throw new AgentError('Ollama result too large.',502)}text+=decoder.decode(part.value,{stream:true})}return JSON.parse(text+decoder.decode())
}}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const request=ollamaClient({url:process.env.OLLAMA_URL||'http://127.0.0.1:11434/',token:process.env.OLLAMA_TOKEN});const agent=new Agent({model:async(body,signal)=>(await request('api/chat',{...body,stream:false},signal)).message,createPlugin:playwrightClient});
 const server=createGateway({token:process.env.RELAY_GATEWAY_TOKEN,origins:(process.env.RELAY_ALLOWED_ORIGINS||'https://relay-ollama.onrender.com').split(',').map(v=>v.trim()),agent,listModels:async()=>(await request('api/tags')).models.map(m=>m.name)});
 const cleanup=setInterval(()=>agent.prune().catch(()=>{}),60000);cleanup.unref();server.requestTimeout=150000;server.listen(Number(process.env.PORT||8787),process.env.HOST||'127.0.0.1',()=>console.log('Relay plugin gateway listening.'));
 for(const sig of ['SIGTERM','SIGINT'])process.on(sig,async()=>{clearInterval(cleanup);server.close();await Promise.allSettled([...agent.sessions.keys()].map(id=>agent.close(id)));process.exit(0)});
}
