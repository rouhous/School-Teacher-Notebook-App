/* Offline shell only. Authorization remains in application/session layer. */
const CACHE_PREFIX='school-notebook-shell-';
const CACHE_NAME='school-notebook-shell-20261128-fix-e';
const ASSETS=['./teacher-home.html','./attendance.html','./founder-dashboard.html','./duty-roster-admin.html','./supervisor-timetables.html','./data-admin.html','./manifest.webmanifest','./app-icon.svg','./school-notebook.html','./update-banner.js','./firefox-addon-install.js','./session-auth.js','./offline-pin.js','./passkey-auth.js','../index.html','../assets/school-home-approved.png','../assets/school-home-reference-clean1.png','../assets/school-home-reference-clean2.png'];
const REQUIRED=['./school-notebook.html','./update-banner.js','./session-auth.js','./offline-pin.js','../index.html'];
async function cacheOfflineFiles(){
 const cache=await caches.open(CACHE_NAME);
 await Promise.all(REQUIRED.map(path=>cache.add(new Request(path,{cache:'reload'}))));
 const additional=ASSETS.filter(path=>!REQUIRED.includes(path));
 const results=await Promise.allSettled(additional.map(path=>cache.add(new Request(path,{cache:'reload'}))));
 return {required:REQUIRED.length,optionalCached:results.filter(x=>x.status==='fulfilled').length,optionalFailed:results.filter(x=>x.status==='rejected').length};
}
self.addEventListener('install',event=>{event.waitUntil(cacheOfflineFiles())});
self.addEventListener('message',event=>{
 if(event.data?.type==='SKIP_WAITING'){event.waitUntil(self.skipWaiting());return}
 if(event.data?.type!=='PREPARE_NOTEBOOK_OFFLINE')return;
 event.waitUntil(cacheOfflineFiles().then(summary=>event.ports?.[0]?.postMessage({ok:true,...summary}))
  .catch(error=>event.ports?.[0]?.postMessage({ok:false,error:String(error?.message||error)})));
});
self.addEventListener('activate',event=>{
 event.waitUntil((async()=>{
  const current=CACHE_NAME
  const keys=await caches.keys();
  await Promise.all(keys.filter(key=>key.startsWith(CACHE_PREFIX)&&key!==current).map(key=>caches.delete(key)));
  await self.clients.claim();
 })());
});
self.addEventListener('fetch',event=>{
 const req=event.request;
 const u=new URL(req.url);
 if(req.method!=='GET'||u.origin!==self.location.origin||!u.pathname.startsWith('/School-Teacher-Notebook-App/school-edition/'))return;
 if(req.mode==='navigate'){
  event.respondWith((async()=>{
   const cache=await caches.open(CACHE_NAME);
   try{
    const fresh=await fetch(req,{cache:'no-store'});
    if(fresh.ok)await cache.put(req,fresh.clone());
    return fresh;
   }catch{return (await cache.match(req,{ignoreSearch:true}))||Response.error()}
  })());
  return;
 }
 if(/\.(?:js|css|html|svg|webmanifest|png|jpg|jpeg|webp)$/.test(u.pathname)){
  event.respondWith((async()=>{
   const cache=await caches.open(CACHE_NAME);
   try{
    const fresh=await fetch(req,{cache:'no-store'});
    if(fresh.ok)await cache.put(req,fresh.clone());
    return fresh;
   }catch{return (await cache.match(req))||Response.error()}
  })());
 }
});
/* Push delivery requires an authenticated subscription and a trusted sender. */
self.addEventListener('push',event=>{
 let payload={};try{payload=event.data?.json()||{}}catch{payload={body:event.data?.text()||''}}
 const title=String(payload.title||'إشعار دفتر المعلم').slice(0,140);
 const kind=String(payload.kind||'lesson').slice(0,30);
 const options={
  body:String(payload.body||'لديك إشعار جديد').slice(0,300),
  tag:String(payload.tag||'school-'+kind).slice(0,100),
  icon:'../assets/school-icon-192.png',
  badge:'../assets/school-icon-192.png',
  requireInteraction:true,
  renotify:true,
  vibrate:[400,250,400,250,400],
  data:{url:'./school-notebook.html',assignmentId:payload.assignmentId||null},
  actions:[{action:'open',title:'فتح دفتر المعلم'},{action:'dismiss',title:'إغلاق'}]
 };
 event.waitUntil(self.registration.showNotification(title,options));
});
self.addEventListener('notificationclick',event=>{
 event.notification.close();
 if(event.action==='dismiss')return;
 event.waitUntil((async()=>{
  const target=new URL('./school-notebook.html',self.registration.scope).href;
  const windows=await self.clients.matchAll({type:'window',includeUncontrolled:true});
  const existing=windows.find(c=>c.url.startsWith(self.registration.scope));
  if(existing){await existing.focus();existing.navigate(target);return}
  await self.clients.openWindow(target);
 })());
});
