import { NextRequest } from 'next/server';
import { BodyTooLarge, readBoundedBody } from '../../../lib/request-body';
export const dynamic = 'force-dynamic';
async function proxy(req: NextRequest, ctx: {params: Promise<{path: string[]}>}) {
  const {path} = await ctx.params;
  const origin = process.env.APP_ORIGIN;
  if (!origin || !process.env.BACKEND_URL) return Response.json({detail:'Server configuration missing'}, {status:503});
  if (!['GET','HEAD'].includes(req.method) && req.headers.get('origin') !== origin)
    return Response.json({detail:'Invalid origin'}, {status:403});
  const allowed = ['auth','businesses','users'];
  if (!allowed.includes(path[0]) || path.some(p => p === '.' || p === '..' || p.includes('/'))) return new Response(null,{status:404});
  const headers = new Headers({'Origin': origin});
  const cookie = req.headers.get('cookie'); if (cookie) headers.set('cookie',cookie);
  if (req.method !== 'GET') headers.set('Content-Type','application/json');
  try {
    const bytes = ['GET','HEAD'].includes(req.method) ? undefined : await readBoundedBody(req);
    let body: string | undefined;
    try { body = bytes === undefined ? undefined : new TextDecoder('utf-8', {fatal:true}).decode(bytes); }
    catch { return Response.json({detail:'Invalid UTF-8'},{status:400}); }
    const upstream = await fetch(`${process.env.BACKEND_URL.replace(/\/$/,'')}/${path.map(encodeURIComponent).join('/')}${req.nextUrl.search}`, {method:req.method,headers,body,cache:'no-store',redirect:'manual',signal:AbortSignal.timeout(190000)});
    const out = new Headers({'Content-Type':'application/json','Cache-Control':'no-store'});
    const retryAfter = upstream.headers.get('retry-after'); if (retryAfter) out.set('Retry-After',retryAfter);
    for (const cookie of upstream.headers.getSetCookie()) out.append('Set-Cookie',cookie);
    return new Response(upstream.body,{status:upstream.status,headers:out});
  } catch (error) {
    if (error instanceof BodyTooLarge) return Response.json({detail:'Request too large'},{status:413});
    return Response.json({detail:'API unavailable'},{status:502});
  }
}
export {proxy as GET,proxy as POST,proxy as PUT};
