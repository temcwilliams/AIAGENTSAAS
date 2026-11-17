// Mutating end-to-end checks are restricted to disposable local preview data.
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.RELEASE_A_TEST_URL||'http://127.0.0.1:3211';
if(!['127.0.0.1','localhost'].includes(new URL(base).hostname))throw Error('This fixture test must never target a hosted or production app.');
const fixturePassword='Preview-only-password-123!';
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);
  await page.getByRole('button',{name:'Forgot password?',exact:true}).click();
  await page.getByText('Email delivery is unavailable.',{exact:false}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Request password reset',exact:true}).isDisabled(),true);
  assert.equal(await page.getByRole('button',{name:'Create account',exact:true}).count(),0);
  await page.getByRole('button',{name:'Back to sign in',exact:true}).click();
  // These tokens refer only to deliberately seeded local fixtures, not email.
  await page.goto(base+'/#account-action=verify&token=preview-verify-token-only-for-local-tests-2026');
  await page.getByRole('heading',{name:'Verify your email',exact:true}).waitFor();
  await page.waitForFunction(()=>!window.location.hash);
  await page.getByRole('button',{name:'Verify email',exact:true}).click();
  await page.getByText('Your email is verified.',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Continue',exact:true}).click();
  await page.goto(base+'/#account-action=setup&token=preview-setup-token-only-for-local-tests-2026');
  await page.getByRole('heading',{name:'Set your password',exact:true}).waitFor();
  await page.waitForFunction(()=>!window.location.hash);
  await page.getByLabel('New password',{exact:true}).fill(fixturePassword);
  await page.getByLabel('Confirm new password',{exact:true}).fill('Mismatch-password-123!');
  await page.getByRole('button',{name:'Save password',exact:true}).click();
  await page.getByRole('alert').filter({hasText:'Your passwords do not match.'}).waitFor();
  await page.getByLabel('Confirm new password',{exact:true}).fill(fixturePassword);
  await page.getByRole('button',{name:'Save password',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Your password is updated.'}).waitFor();
  await page.getByRole('button',{name:'Continue',exact:true}).click();

  async function signIn(email){
   await page.getByLabel('Email address',{exact:true}).fill(email);
   await page.getByLabel('Password',{exact:true}).fill(fixturePassword);
   await page.getByRole('button',{name:'Sign in →',exact:true}).click();
   await page.getByRole('button',{name:'Sign out',exact:true}).waitFor();
  }
  async function signOut(){await page.getByRole('button',{name:'Sign out',exact:true}).click();await page.getByRole('heading',{name:'Welcome back.',exact:true}).waitFor()}
  async function setupTab(){await page.getByRole('button',{name:'Business setup',exact:true}).click();await page.getByRole('heading',{name:'Business setup',exact:true}).waitFor()}
  await signIn('manager-preview@example.com');await setupTab();
  await page.getByLabel('Business name',{exact:true}).fill('Release A approved preview fixture');
  await page.getByLabel('Primary contact name',{exact:true}).fill('Preview contact');
  await page.getByLabel('Business contact email',{exact:true}).fill('contact-preview@example.com');
  await page.getByLabel('About your business',{exact:true}).fill('Disposable local browser-test business, not a real customer.');
  await page.getByRole('button',{name:'2. Services & FAQs',exact:true}).click();
  await page.getByLabel('Services or products',{exact:true}).fill('Preview service information.');
  await page.getByLabel('Frequently asked questions and answers',{exact:true}).fill('Q: Is this production? A: No, it is a disposable test.');
  await page.getByRole('button',{name:'3. Handoff & review',exact:true}).click();
  await page.getByLabel('When and how should a person take over?',{exact:true}).fill('Ask the owner for complex requests.');
  await page.getByLabel('Preferred starter template',{exact:true}).selectOption('support');
  await page.getByRole('button',{name:'Save draft',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Draft saved.'}).waitFor();
  await signOut();await signIn('manager-preview@example.com');await setupTab();
  await page.getByRole('button',{name:'1. Business profile',exact:true}).click();
  assert.equal(await page.getByLabel('Business name',{exact:true}).inputValue(),'Release A approved preview fixture');
  await page.getByRole('button',{name:'Submit for owner review',exact:true}).click();
  await page.getByText('Submitted for review',{exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Approve setup',exact:true}).count(),0);
  await page.getByRole('button',{name:'Preview saved setup',exact:true}).click();
  await page.getByRole('heading',{name:'Saved setup preview',exact:true}).waitFor();
  await signOut();await signIn('owner-preview@example.com');await setupTab();
  await page.getByLabel('Feedback for the client',{exact:true}).fill('Please include a phone number for handoff.');
  await page.getByRole('button',{name:'Request changes',exact:true}).click();
  await page.getByText('Changes requested',{exact:true}).waitFor();
  await signOut();await signIn('manager-preview@example.com');await setupTab();
  await page.getByLabel('Business phone',{exact:true}).fill('555-0100');
  await page.getByRole('button',{name:'Submit for owner review',exact:true}).click();
  await page.getByText('Submitted for review',{exact:true}).waitFor();
  await signOut();await signIn('owner-preview@example.com');await setupTab();
  await page.getByRole('button',{name:'Approve setup',exact:true}).click();
  await page.getByText('Approved',{exact:true}).waitFor();
  await page.getByRole('button',{name:'Publish approved setup',exact:true}).click();
  await page.getByText('Published to workspace',{exact:true}).waitFor();
  const config=await page.evaluate(async()=>{
   const b='/api/businesses/release-a-preview';
   return {agents:await (await fetch(b+'/agents')).json(),knowledge:await (await fetch(b+'/knowledge')).json()};
  });
  assert.equal(config.agents.length,1);assert.equal(config.knowledge.length,1);
  assert.match(config.knowledge[0].content,/555-0100/);
  await page.getByRole('button',{name:'Account security',exact:true}).click();
  await page.getByText('Email delivery is unavailable.',{exact:false}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Send verification email',exact:true}).isDisabled(),true);
  await page.getByRole('button',{name:'Business settings',exact:true}).click();
  await page.getByRole('heading',{name:'Account access',exact:true}).waitFor();
  assert.equal(await page.getByRole('button',{name:'Create account and email setup link',exact:true}).isDisabled(),true);
  await page.getByLabel('Client email',{exact:true}).fill('manual-preview@example.com');
  await page.getByLabel('Temporary password · share securely',{exact:true}).fill(fixturePassword);
  await page.getByLabel('Business role',{exact:true}).last().selectOption('manager');
  await page.getByRole('button',{name:'Create client account',exact:true}).click();
  await page.getByRole('status').filter({hasText:'Client account created.'}).waitFor();
  await page.getByRole('combobox',{name:'Business role for viewer-preview@example.com',exact:true}).selectOption('responder');
  await page.getByRole('status').filter({hasText:'Business role updated.'}).waitFor();
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
  assert.deepEqual(errors,[]);
  console.log('PASS: local fixture verification/setup UI, hash removal, password confirmation, honest disabled-email state, closed public signup, resumable manager draft, owner change request/approval/publication, managed agent/knowledge, manual client creation, scoped role grant, mobile layout. No real email or inference.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
