const VERSION='school-pwa-v14-remove-old-login-ghost';
const SHELL=['./','./index.html','./manifest.webmanifest','./assets/school-icon-192.png','./assets/school-icon-512.png','./assets/school-home-reference-clean1.png','./assets/school-home-reference-clean2.png'];
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
   // Never serve the login document in place of a protected notebook or dashboard.
   if(!['/School-Teacher-Notebook-App/','/School-Teacher-Notebook-App/index.html'].includes(u.pathname))return;
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     try{
       const fresh=await fetch(req,{cache:'no-store'});
       if(fresh.ok)await cache.put('./index.html',fresh.clone());
       return fresh;
     }catch{
       return (await cache.match('./index.html'))||Response.error();
     }
   })());
   return;
 }
 if(/\/assets\/school-home-reference-clean(?:1\.png|2\.png)$/.test(u.pathname)){
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
