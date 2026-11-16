// Read-only smoke check: public and legacy signup are disabled.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,headless:true,args:process.env.PW_DISABLE_SANDBOX==='1'?['--no-sandbox']:[]});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const base=process.env.PWA_TEST_URL||'http://localhost:3192';
  await page.goto(base);
  await page.getByRole('button',{name:'Sign in →',exact:true}).waitFor();
  async function assertClosed(){
   assert.equal(await page.getByRole('button',{name:/create account/i}).count(),0);
   assert.equal(await page.getByLabel('Business name',{exact:true}).count(),0);
   assert.equal(await page.getByLabel('Confirm password',{exact:true}).count(),0);
   const link=page.getByRole('link',{name:'Request access by email',exact:true});
   assert.equal(await link.getAttribute('href'),'mailto:tmcwilliams2010@outlook.com?subject=Agent%20Meadow%20account%20request');
  }
  await assertClosed();
  // Old setup links are scrubbed without revealing a registration form.
  await page.goto(base+'/#owner-setup=test-only-retired-code');
  await page.waitForFunction(()=>!window.location.hash);
  await assertClosed();
  await page.evaluate(()=>{window.location.hash='owner-setup=second-test-only-retired-code'});
  await page.waitForFunction(()=>!window.location.hash);
  await assertClosed();
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: sign-in only, owner contact email, no public signup fields/buttons, retired owner links cleared on load/hashchange, mobile width, no browser exceptions. No account created.');
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
