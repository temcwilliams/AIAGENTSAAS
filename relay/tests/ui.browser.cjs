// Requires Playwright and a running server for dist. See README.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.RELAY_BROWSER_EXECUTABLE?{executablePath:process.env.RELAY_BROWSER_EXECUTABLE}:{}),args:['--no-sandbox']});
 try{
  for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:375,height:667},{width:320,height:568}]){
   const context=await browser.newContext({viewport,isMobile:viewport.width<=760,hasTouch:viewport.width<=760});const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(process.env.RELAY_TEST_URL||'http://127.0.0.1:4173');
   const metrics=await page.evaluate(()=>({outer:document.documentElement.scrollWidth<=innerWidth&&document.body.scrollHeight<=innerHeight,chat:chat.scrollHeight<=chat.clientHeight+1,theme:document.documentElement.dataset.theme,filter:getComputedStyle(document.body).filter}));assert.equal(metrics.outer,true,JSON.stringify(viewport)+' outer scroll');assert.equal(metrics.chat,true,JSON.stringify(viewport)+' welcome scroll');assert.equal(metrics.theme,'dark');assert.equal(metrics.filter,'none');
   await page.click('#themeToggle');assert.equal(await page.getAttribute('html','data-theme'),'light');await page.reload();assert.equal(await page.getAttribute('html','data-theme'),'light');await page.click('#themeToggle');
   if(viewport.width<=760){
    assert.equal(await page.locator('#sidebar').evaluate(e=>e.inert),true);
    await page.click('#menu');assert.equal(await page.locator('#sidebar').evaluate(e=>e.inert),false);assert.equal(await page.locator('.main').evaluate(e=>e.inert),true);await page.click('#closeSidebar');assert.equal(await page.getAttribute('#menu','aria-expanded'),'false');
    await page.click('#menu');await page.click('#sidebarBackdrop',{position:{x:viewport.width-10,y:viewport.height/2}});assert.equal(await page.getAttribute('#menu','aria-expanded'),'false');
    await page.click('#menu');await page.click('#codingNav');assert.equal(await page.getAttribute('#menu','aria-expanded'),'false');assert.equal(await page.locator('#sidebar').evaluate(e=>e.inert),true);
    await page.click('#menu');await page.keyboard.press('Escape');assert.equal(await page.getAttribute('#menu','aria-expanded'),'false');
   }
   for(const [trigger,dialog,close] of [['settingsButton','settings','closeSettings'],['installHelp','installGuide','closeInstallGuide'],['cookieInfo','privacyGuide','closePrivacyGuide'],['voiceToggle','voiceGuide','closeVoiceGuide']]){
    await page.click('#'+trigger);assert.equal(await page.locator('dialog[open]').count(),1);await page.locator('#'+dialog).evaluate(e=>{e.querySelectorAll('details').forEach(d=>d.open=true);e.scrollTop=e.scrollHeight});const box=await page.locator('#'+close).boundingBox();assert.ok(box&&box.y>=0&&box.y+box.height<=viewport.height,'close remains visible: '+dialog);await page.click('#'+close);assert.equal(await page.locator('dialog[open]').count(),0);
    await page.click('#'+trigger);assert.equal(await page.locator('#'+dialog).evaluate(e=>e.scrollTop),0);await page.keyboard.press('Escape');assert.equal(await page.locator('dialog[open]').count(),0);
   }
   await page.evaluate(()=>{openDialog(document.getElementById('settings'));openDialog(document.getElementById('installGuide'))});assert.equal(await page.locator('dialog[open]').count(),1);await page.mouse.click(2,2);assert.equal(await page.locator('dialog[open]').count(),0);
   await page.evaluate(()=>{chats=[{id:'scroll-fixture',title:'Long chat',mode,messages:Array.from({length:70},(_,i)=>({role:i%2?'assistant':'user',content:'A long conversation to check scrolling. '.repeat(10)}))}];active='scroll-fixture';render()});assert.equal(await page.locator('#chat').evaluate(e=>e.scrollHeight>e.clientHeight),true);const composer=await page.locator('#composer').boundingBox();assert.ok(composer.y>=0&&composer.y+composer.height<=viewport.height);assert.equal(await page.evaluate(()=>document.body.scrollHeight<=innerHeight),true);assert.deepEqual(errors,[]);await context.close();console.log('PASS viewport '+viewport.width+'×'+viewport.height+': theme, menus, no welcome/outer overflow, long-chat scrolling');
  }
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
