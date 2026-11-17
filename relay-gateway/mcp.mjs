import {Client} from '@modelcontextprotocol/sdk/client/index.js';
import {StdioClientTransport} from '@modelcontextprotocol/sdk/client/stdio.js';
import {fileURLToPath} from 'node:url';
import {mkdtemp,rm,realpath,readFile,stat} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';

export async function playwrightClient(){
 const home=await mkdtemp(path.join(tmpdir(),'relay-browser-'));
 const args=[fileURLToPath(new URL('./node_modules/@playwright/mcp/cli.js',import.meta.url)),'--headless','--isolated','--no-webmcp','--output-dir',home];
 if(process.env.RELAY_BROWSER_EXECUTABLE)args.push('--executable-path',process.env.RELAY_BROWSER_EXECUTABLE);
 if(process.env.RELAY_MCP_NO_SANDBOX==='1')args.push('--no-sandbox');
 const client=new Client({name:'relay',version:'1.0.0'});
 const env={PATH:process.env.PATH||'',HOME:home,TMPDIR:home};
 if(process.env.PLAYWRIGHT_BROWSERS_PATH)env.PLAYWRIGHT_BROWSERS_PATH=process.env.PLAYWRIGHT_BROWSERS_PATH;
 const transport=new StdioClientTransport({command:process.execPath,args,env,cwd:home,stderr:'pipe'});
 // Plugin logs are not reflected into HTTP replies or production logs.
 transport.stderr?.on('data',()=>{});
 try{await client.connect(transport);const listed=await client.listTools();return {tools:listed.tools.filter(t=>!['browser_run_code','browser_run_code_unsafe'].includes(t.name)),call:async(name,args)=>{if(['browser_run_code','browser_run_code_unsafe'].includes(name))throw Error('Host code execution is not exposed.');return hydrate(await client.callTool({name,arguments:args},undefined,{timeout:45000}),home)},close:async()=>{await client.close();await rm(home,{recursive:true,force:true})}}}
 catch(error){await client.close().catch(()=>{});await rm(home,{recursive:true,force:true});throw error}
}

async function hydrate(result,root){
 const extras=[],seen=new Set();let count=0;for(const item of result.content||[]){if(item.type!=='text')continue;for(const match of item.text.slice(0,64000).matchAll(/\[[^\]]*\]\(([^)]+)\)/g)){try{if(count>=8)break;const file=await realpath(path.resolve(root,match[1]));if(!file.startsWith(root+path.sep)||seen.has(file))continue;seen.add(file);count++;const info=await stat(file);if(!info.isFile())continue;const ext=path.extname(file).toLowerCase();if(['.yml','.yaml','.txt','.md','.json'].includes(ext)){if(info.size>2000000)continue;const handle=await readFile(file);extras.push({type:'text',text:handle.subarray(0,100000).toString('utf8')+(handle.length>100000?'\n[Output truncated; use targeted browser tools.]':'')})}else if(['.png','.jpg','.jpeg','.webp'].includes(ext)&&info.size<1400000){extras.push({type:'image',mimeType:ext==='.png'?'image/png':ext==='.webp'?'image/webp':'image/jpeg',data:(await readFile(file)).toString('base64')})}}catch{}}}return {...result,content:[...(result.content||[]),...extras]};
}
