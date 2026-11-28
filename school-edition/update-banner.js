/* Shared, external PWA update notice for both notebook entry pages. */
(function(){
 if(!('serviceWorker' in navigator)||document.getElementById('school-update-notice-ui'))return;
 const style=document.createElement('style');
 style.textContent='#school-update-notice-ui{position:fixed;top:calc(env(safe-area-inset-top,0px) + 10px);left:12px;right:12px;z-index:2147483647;max-width:720px;margin:0 auto;display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;padding:12px 14px;border:1px solid #d6b96f;border-radius:14px;background:#075b47;color:#fff;box-shadow:0 8px 28px #0003;font:700 14px Tahoma,Arial,sans-serif}#school-update-notice-ui[hidden]{display:none!important}#school-update-notice-ui .update-actions{display:flex;gap:7px;align-items:center}#school-update-notice-ui button{border:1px solid #e6d4a5;border-radius:9px;padding:8px 12px;font:700 13px Tahoma,Arial,sans-serif;cursor:pointer}#school-update-apply{background:#fff;color:#075b47}#school-update-later{background:transparent;color:#fff}';
 document.head.appendChild(style);
 const banner=document.createElement('aside');
 banner.id='school-update-notice-ui';banner.hidden=true;banner.dir='rtl';banner.setAttribute('role','status');banner.setAttribute('aria-live','polite');
 const message=document.createElement('span');message.textContent='يتوفر تحديث جديد لدفتر المعلم. حدّث التطبيق لتطبيق التحسينات.';
 const actions=document.createElement('div');actions.className='update-actions';
 const apply=document.createElement('button');apply.id='school-update-apply';apply.type='button';apply.textContent='تحديث الآن';
 const later=document.createElement('button');later.id='school-update-later';later.type='button';later.textContent='لاحقًا';
 actions.append(apply,later);banner.append(message,actions);document.body.appendChild(banner);
 let registration=null,reloadAfterUpdate=false;
 const show=()=>{if(registration?.waiting&&navigator.serviceWorker.controller)banner.hidden=false};
 later.addEventListener('click',()=>{banner.hidden=true});
 apply.addEventListener('click',()=>{
  const waiting=registration?.waiting;
  if(!waiting)return;
  reloadAfterUpdate=true;
  waiting.postMessage({type:'SKIP_WAITING'});
 });
 navigator.serviceWorker.addEventListener('controllerchange',()=>{
  if(reloadAfterUpdate)window.location.reload();
 });
 navigator.serviceWorker.ready.then(reg=>{
  registration=reg;
  show();
  reg.addEventListener('updatefound',()=>{
   const installing=reg.installing;
   if(!installing)return;
   installing.addEventListener('statechange',()=>{
    if(installing.state==='installed'&&navigator.serviceWorker.controller)banner.hidden=false;
   });
  });
  reg.update().catch(()=>{});
 }).catch(()=>{});
})();