'use strict';
function cleanPreferences(value={}){
  const model=v=>typeof v==='string'&&v.length<=200?v:'';
  return {theme:value?.theme==='light'?'light':'dark',mode:value?.mode==='coding'?'coding':'chat',chatModel:model(value?.chatModel),codingModel:model(value?.codingModel),readAloud:value?.readAloud!==false};
}
function createPreferences(doc,secure=true){
  let memory=cleanPreferences();
  try{const cookie=doc.cookie.split(';').map(v=>v.trim()).find(v=>v.startsWith('relay_preferences='));if(cookie)memory=cleanPreferences(JSON.parse(decodeURIComponent(cookie.slice('relay_preferences='.length))))}catch{}
  return {get:()=>({...memory}),set(patch){memory=cleanPreferences({...memory,...patch});try{doc.cookie='relay_preferences='+encodeURIComponent(JSON.stringify(memory))+'; Max-Age=15552000; Path=/; SameSite=Strict'+(secure?'; Secure':'')}catch{}return {...memory}}};
}
if(typeof module!=='undefined')module.exports={cleanPreferences,createPreferences};
const preferences=typeof document!=='undefined'?createPreferences(document,location.protocol==='https:'):null;
