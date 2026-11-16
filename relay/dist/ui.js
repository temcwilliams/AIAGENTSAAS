'use strict';
function setSidebar(open){
  document.body.classList.toggle('sidebar-open',open);
  const backdrop=document.getElementById('sidebarBackdrop'),menu=document.getElementById('menu'),sidebar=document.getElementById('sidebar');
  const mobile=window.innerWidth<=760,hadFocus=sidebar?.contains?.(document.activeElement);
  if(sidebar)sidebar.inert=mobile&&!open;
  const main=document.querySelector('.main');if(main)main.inert=mobile&&open;
  if(backdrop)backdrop.hidden=!open;
  menu?.setAttribute('aria-expanded',String(open));
  if(open&&mobile)document.getElementById('closeSidebar')?.focus?.();else if(!open&&mobile&&hadFocus)menu?.focus?.();
}
function applyTheme(theme){
  const next=theme==='light'?'light':'dark';document.documentElement.dataset.theme=next;
  const button=document.getElementById('themeToggle');button.textContent=next==='dark'?'☾ Dark':'☀ Light';
  button.setAttribute('aria-label',next==='dark'?'Switch to light mode':'Switch to dark mode');button.title=button.getAttribute('aria-label');
  document.querySelector('meta[name="theme-color"]')?.setAttribute('content',next==='dark'?'#080d17':'#edf2fa');
  return next;
}
function toggleTheme(){preferences.set({theme:applyTheme(document.documentElement.dataset.theme==='dark'?'light':'dark')})}
if(typeof document!=='undefined'){
  applyTheme(preferences.get().theme);
  document.getElementById('themeToggle').onclick=toggleTheme;
  document.getElementById('menu').onclick=()=>setSidebar(!document.body.classList.contains('sidebar-open'));
  document.getElementById('sidebarBackdrop').onclick=()=>setSidebar(false);
  document.getElementById('closeSidebar').onclick=()=>setSidebar(false);
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){setSidebar(false);document.querySelectorAll('dialog[open]').forEach(dialog=>closeDialog(dialog))}});
  document.querySelectorAll('dialog').forEach(dialog=>{
    dialog.addEventListener('cancel',event=>{event.preventDefault();closeDialog(dialog)});
    dialog.addEventListener('click',event=>{
      if(event.target!==dialog)return;const r=dialog.getBoundingClientRect();
      if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)closeDialog(dialog);
    });
  });
  window.addEventListener('resize',()=>setSidebar(false));
  setSidebar(false);
}
