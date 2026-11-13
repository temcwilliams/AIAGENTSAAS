// Requires Playwright: npm install --no-save playwright; npx playwright install chromium
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
  const browser=await chromium.launch({headless:true,args:process.env.PW_DISABLE_SANDBOX==='1'?['--no-sandbox']:[]});
  try{
    const context=await browser.newContext({viewport:{width:1280,height:900}});
    await context.addInitScript(()=>window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();event.stopImmediatePropagation()}));
    const page=await context.newPage();
    const base=process.env.PWA_TEST_URL||'http://localhost:3188';
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    await page.goto(base);
    await page.getByRole('button',{name:'Install app ↗'}).waitFor();
    const manifest=await (await context.request.get(base+'/manifest.webmanifest')).json();
    assert.equal(manifest.display,'standalone');assert.equal(manifest.start_url,'/');
    assert.ok(manifest.icons.some(icon=>icon.purpose==='maskable'));
    for(const icon of manifest.icons)assert.equal((await context.request.get(base+icon.src)).status(),200);
    const worker=await context.request.get(base+'/sw.js');
    assert.match(worker.headers()['cache-control'],/no-store/);
    await page.evaluate(()=>navigator.serviceWorker.ready);
    await page.reload();
    await page.waitForFunction(()=>Boolean(navigator.serviceWorker.controller));
    await page.evaluate(()=>fetch('/api/auth/me'));
    const paths=await page.evaluate(async()=>{
      const names=(await caches.keys()).filter(key=>key.startsWith('agent-meadow-public-'));
      return (await Promise.all(names.map(async name=>(await (await caches.open(name)).keys()).map(request=>new URL(request.url).pathname)))).flat();
    });
    assert.ok(paths.includes('/offline.html'));
    assert.ok(paths.every(path=>path==='/offline.html'||path.startsWith('/icons/')));
    await context.setOffline(true);
    await page.goto(base+'/unavailable-while-offline');
    await page.getByRole('heading',{name:"You're offline."}).waitFor();
    await context.setOffline(false);
    await page.goto(base);
    await page.getByLabel('Email address').waitFor();
    assert.equal((await context.request.get(base+'/health')).status(),200);
    await page.getByRole('button',{name:'Install app ↗'}).click();
    await page.getByRole('button',{name:'Close instructions'}).waitFor();
    assert.deepEqual(errors,[]);
    console.log('PWA smoke passed: manifest, icons, worker headers/control, public-only caches, offline navigation, recovery, install guidance, health.');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
