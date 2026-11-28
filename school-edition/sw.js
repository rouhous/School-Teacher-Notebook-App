/* Offline shell only. Authorization remains in application/session layer. */
const CACHE_PREFIX='school-notebook-shell-';
const BUILD_FILES=['./sw.js','./school-notebook.html','./session-auth.js','./offline-pin.js','./passkey-auth.js','./manifest.webmanifest','../index.html'];
const ASSETS=['./teacher-home.html','./attendance.html','./founder-dashboard.html','./duty-roster-admin.html','./supervisor-timetables.html','./data-admin.html','./manifest.webmanifest','./app-icon.svg','./school-notebook.html','./firefox-addon-install.js','./session-auth.js','./offline-pin.js','./passkey-auth.js','../index.html','../assets/school-home-approved.png','../assets/school-home-reference-clean1.png','../assets/school-home-reference-clean2.png'];
const REQUIRED=['./school-notebook.html','./session-auth.js','./offline-pin.js','../index.html'];
const hex=bytes=>Array.from(new Uint8Array(bytes),b=>b.toString(16).padStart(2,'0')).join('');
async function resolveCacheName(){
 try{
  const parts=await Promise.all(BUILD_FILES.map(async path=>{
   const response=await fetch(new URL(path,self.registration.scope),{cache:'no-store'});
   if(!response.ok)throw Error('BUILD_RESOURCE_UNAVAILABLE:'+path);
   const digest=await crypto.subtle.digest('SHA-256',await response.arrayBuffer());
   return path+':'+hex(digest);
  }));
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(parts.join('\n')));
  return CACHE_PREFIX+hex(digest).slice(0,20);
 }catch(error){
  const keys=await caches.keys();
  const existing=keys.filter(key=>key.startsWith(CACHE_PREFIX));
  if(existing.length)return existing[existing.length-1];
  throw error;
 }
}
const CACHE_NAME_PROMISE=resolveCacheName();
async function cacheOfflineFiles(){
 const cache=await caches.open(await CACHE_NAME_PROMISE);
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
  const current=await CACHE_NAME_PROMISE;
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
   const cache=await caches.open(await CACHE_NAME_PROMISE);
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
   const cache=await caches.open(await CACHE_NAME_PROMISE);
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
