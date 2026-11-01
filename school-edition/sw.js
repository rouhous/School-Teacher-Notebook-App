/* Offline shell only. Authorization remains in application/session layer. */
const CACHE='school-notebook-shell-v19-english-reset';
const ASSETS=['./teacher-home.html','./attendance.html','./founder-dashboard.html','./data-admin.html','./manifest.webmanifest','./app-icon.svg','./school-notebook.html','./session-auth.js','./offline-pin.js'];
self.addEventListener('install',e=>{
 e.waitUntil(caches.open(CACHE).then(async cache=>{
  await Promise.allSettled(ASSETS.map(path=>cache.add(path)));
 }));
 self.skipWaiting();
});
self.addEventListener('activate',e=>{
 e.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('school-notebook-shell-')&&k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',e=>{
 const req=e.request;
 const u=new URL(req.url);
 if(req.method!=='GET'||u.origin!==self.location.origin||!u.pathname.startsWith('/School-Teacher-Notebook-App/school-edition/'))return;
 if(req.mode==='navigate'){
  e.respondWith((async()=>{
   const cache=await caches.open(CACHE);
   try{
    const fresh=await fetch(req,{cache:'no-store'});
    if(fresh.ok)await cache.put(req,fresh.clone());
    return fresh;
   }catch{
    // Never replace a protected route with a different document.
    return (await cache.match(req,{ignoreSearch:true}))||Response.error();
   }
  })());
  return;
 }
 if(/\.(?:js|css|html|svg|webmanifest)$/.test(u.pathname)){
  e.respondWith((async()=>{
   const cache=await caches.open(CACHE);
   try{
    const fresh=await fetch(req,{cache:'no-store'});
    if(fresh.ok)await cache.put(req,fresh.clone());
    return fresh;
   }catch{return (await cache.match(req))||Response.error()}
  })());
 }
});

/* Web Push receiver: delivery requires a registered subscription and a server sender. */
self.addEventListener('push',event=>{
 let payload={};try{payload=event.data?.json()||{}}catch{payload={body:event.data?.text()||''}}
 const title=String(payload.title||'تكليف احتياط مدرسي');
 const options={body:String(payload.body||'لديك إشعار جديد من دفتر المعلم المدرسي'),tag:String(payload.tag||'school-cover'),icon:'./app-icon.svg',badge:'./app-icon.svg',requireInteraction:true,data:{url:'./school-notebook.html',assignmentId:payload.assignmentId||null}};
 event.waitUntil(self.registration.showNotification(title,options));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 event.waitUntil((async()=>{
  const target=new URL('./school-notebook.html',self.registration.scope).href;
  const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=windows.find(c=>c.url.startsWith(self.registration.scope));
  if(existing){await existing.focus();existing.navigate(target);return}
  await self.clients.openWindow(target);
 })());
});
