const VERSION='school-pwa-v26-english-reset';
const SHELL=['./','./index.html','./manifest.webmanifest','./assets/school-icon-192.png','./assets/school-icon-512.png','./assets/school-home-reference-clean1.png','./assets/school-home-reference-clean2.png','./school-edition/school-notebook.html','./school-edition/session-auth.js','./school-edition/manifest.webmanifest'];
self.addEventListener('install',event=>{
 event.waitUntil(caches.open(VERSION).then(async cache=>{
   await Promise.allSettled(SHELL.map(path=>cache.add(path)));
 }));
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
   if(!['/School-Teacher-Notebook-App/','/School-Teacher-Notebook-App/index.html','/School-Teacher-Notebook-App/school-edition/school-notebook.html'].includes(u.pathname))return;
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     try{
       const fresh=await fetch(req,{cache:'no-store'});
       if(fresh.ok)await cache.put(req,fresh.clone());
       return fresh;
     }catch{
       return (await cache.match(req,{ignoreSearch:true}))||Response.error();
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
 if(u.pathname.endsWith('/school-edition/session-auth.js')||u.pathname.endsWith('/school-edition/manifest.webmanifest')){
   event.respondWith((async()=>{
     const cache=await caches.open(VERSION);
     try{
       const response=await fetch(req,{cache:'no-store'});
       if(response.ok)await cache.put(req,response.clone());
       return response;
     }catch{return (await cache.match(req))||Response.error()}
   })());
   return;
 }
 if(u.pathname.endsWith('/manifest.webmanifest')){
   event.respondWith(caches.match(req).then(x=>x||fetch(req)));
 }
});
