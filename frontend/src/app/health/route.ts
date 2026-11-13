export const dynamic='force-dynamic';
export async function GET(){
  try {
    if(!process.env.BACKEND_URL)throw Error();
    const r=await fetch(`${process.env.BACKEND_URL}/health`,{cache:'no-store',signal:AbortSignal.timeout(5000)});
    return Response.json({status:r.ok?'ok':'unavailable'},{status:r.ok?200:503});
  }catch{return Response.json({status:'unavailable'},{status:503});}
}
