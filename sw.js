const VERSION='school-pwa-v8-offline-first-home';
const SHELL=['./','./index.html','./manifest.webmanifest','./assets/school-icon-192.png','./assets/school-icon-512.png','./assets/school-home-reference-clean1.png','./assets/school-home-reference-clean.webp'];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(VERSION).then(cache=>cache.addAll(SHELL)));
 self.skipWaiting();
});
self.addEventListener('activate',event=>{
 event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(k=>k.startsWith('school-pwa-')&&k!==VERSION).map(k=>caches.delete(k)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
 const req=event.request;
 if(req.method!=='GET')return;
 const u=new URL(req.url);
 if(u.origin!==self.location.origin||!u.pathname.startsWith('/School-Teacher-Notebook-App/'))return;
 if(req.mode==='navigate'){
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     const local=await cache.match('./index.html');
     if(local){event.waitUntil(fetch('./index.html',{cache:'no-store'}).then(res=>{if(res.ok)return cache.put('./index.html',res.clone())}).catch(()=>{}));return local;}
     try{const res=await fetch(req);if(res.ok)cache.put('./index.html',res.clone());return res}catch(e){return (await caches.match('./index.html'))||Response.error()}
   })());
   return;
 }
 if(/\/assets\/school-home-reference-clean(?:1\.png|\.webp)$/.test(u.pathname)){
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     const local=await cache.match(u.pathname);
     if(local)return local;
     const res=await fetch(req);
     if(res.ok)await cache.put(u.pathname,res.clone());
     return res;
   })());
   return;
 }
 if(u.pathname.endsWith('/manifest.webmanifest')){
   event.respondWith(caches.match(req).then(x=>x||fetch(req)));
 }
});
