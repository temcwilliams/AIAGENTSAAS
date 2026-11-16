const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.RELAY_BROWSER_EXECUTABLE?{executablePath:process.env.RELAY_BROWSER_EXECUTABLE}:{}),args:['--no-sandbox']});try{
for(const viewport of [{width:1440,height:900},{width:390,height:844},{width:320,height:568}]){
 const context=await browser.newContext({viewport,isMobile:viewport.width<760,hasTouch:viewport.width<760}),page=await context.newPage();await page.goto(process.env.RELAY_TEST_URL||'http://127.0.0.1:4173');
 for(const theme of ['dark','light']){
  await page.evaluate(t=>applyTheme(t),theme);await page.click('#input');
  for(const text of ['A long prompt with words and spaces. '.repeat(50),'very_long_code_identifier_or_url_without_spaces_'.repeat(40),'First line\nSecond line\nThird line']){
   await page.fill('#input',text);const result=await page.locator('#input').evaluate(e=>{const c=getComputedStyle(e),p=getComputedStyle(document.getElementById('composer'));return{background:c.backgroundColor,panel:p.backgroundColor,color:c.color,caret:c.caretColor,appearance:c.appearance,whiteSpace:c.whiteSpace,wrap:e.wrap,width:e.clientWidth,scrollWidth:e.scrollWidth,height:e.clientHeight,scrollHeight:e.scrollHeight,value:e.value}});
   assert.equal(result.background,result.panel,'field must match composer while focused');assert.notEqual(result.background,'rgba(0, 0, 0, 0)');if(theme==='dark')assert.notEqual(result.background,'rgb(255, 255, 255)');assert.equal(result.appearance,'none');assert.equal(result.wrap,'soft');assert.equal(result.whiteSpace,'pre-wrap');assert.ok(result.scrollWidth<=result.width+1,'horizontal prompt overflow');assert.equal(result.value,text,'soft wrapping must not alter submitted text');if(text.length>500)assert.ok(result.scrollHeight>result.height,'long text must continue on rows');
  }
 }
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);console.log('PASS prompt wrapping/background '+viewport.width+'×'+viewport.height+' in dark and light');await context.close();
}
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exit(1)});
