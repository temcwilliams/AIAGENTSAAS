export async function api<T>(path:string,method='GET',body?:unknown,signal?:AbortSignal):Promise<T>{
  const response=await fetch('/api'+path,{method,headers:{'Content-Type':'application/json'},body:body===undefined?undefined:JSON.stringify(body),signal,cache:'no-store'});
  if(!response.ok){const data=await response.json();throw Error(typeof data.detail==='string'?data.detail:'Please check your input');}
  return response.status===204?undefined as T:response.json();
}
