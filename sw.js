const CACHE_PREFIX='school-pwa-';
const CACHE_NAME='school-pwa-20261128-fix-e';
const SHELL=['./','./index.html','./manifest.webmanifest','./assets/school-icon-192.png','./assets/school-icon-512.png','./assets/school-home-reference-clean1.png','./assets/school-home-reference-clean2.png','./assets/school-home-approved.png','./school-edition/school-notebook.html','./school-edition/update-banner.js','./school-edition/session-auth.js','./school-edition/offline-pin.js','./school-edition/passkey-auth.js','./school-edition/manifest.webmanifest'];
const REQUIRED=['./','./index.html','./school-edition/school-notebook.html','./school-edition/update-banner.js','./school-edition/session-auth.js','./school-edition/offline-pin.js'];
async function openBuildCache(){return caches.open(CACHE_NAME)}
self.addEventListener('install',event=>{
 event.waitUntil((async()=>{
  const cache=await openBuildCache();
  await Promise.all(REQUIRED.map(path=>cache.add(new Request(path,{cache:'reload'}))));
  await Promise.allSettled(SHELL.filter(path=>!REQUIRED.includes(path)).map(path=>cache.add(new Request(path,{cache:'reload'}))));
 })());
});
self.addEventListener('message',event=>{
 if(event.data?.type==='SKIP_WAITING')event.waitUntil(self.skipWaiting());
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
 if(req.method!=='GET')return;
 const u=new URL(req.url);
 if(u.origin!==self.location.origin||!u.pathname.startsWith('/School-Teacher-Notebook-App/'))return;
 if(req.mode==='navigate'){
  if(!['/School-Teacher-Notebook-App/','/School-Teacher-Notebook-App/index.html','/School-Teacher-Notebook-App/school-edition/school-notebook.html'].includes(u.pathname))return;
  event.respondWith((async()=>{
   const cache=await openBuildCache();
   try{
    const fresh=await fetch(req,{cache:'no-store'});
    if(fresh.ok)await cache.put(req,fresh.clone());
    return fresh;
   }catch{return (await cache.match(req,{ignoreSearch:true}))||Response.error()}
  })());
  return;
 }
 if(/\/assets\/school-home-(?:reference-clean[12]|approved)\.png$/.test(u.pathname)){
  event.respondWith((async()=>{
   const cache=await openBuildCache();
   const local=await cache.match(u.pathname);
   if(local)return local;
   const res=await fetch(req);
   if(res.ok)await cache.put(u.pathname,res.clone());
   return res;
  })());
  return;
 }
 if(u.pathname.endsWith('/school-edition/update-banner.js')){
  event.respondWith((async()=>{
   const cache=await openBuildCache();
   try{const response=await fetch(req,{cache:'no-store'});if(response.ok)await cache.put(req,response.clone());return response}
   catch{return (await cache.match(req))||Response.error()}
  })());
  return;
 }
 if(['/school-edition/session-auth.js','/school-edition/offline-pin.js','/school-edition/passkey-auth.js','/school-edition/manifest.webmanifest'].some(path=>u.pathname.endsWith(path))){
  event.respondWith((async()=>{
   const cache=await openBuildCache();
   try{
    const response=await fetch(req,{cache:'no-store'});
    if(response.ok)await cache.put(req,response.clone());
    return response;
   }catch{return (await cache.match(req))||Response.error()}
  })());
  return;
 }
 if(u.pathname.endsWith('/manifest.webmanifest')){
  event.respondWith((async()=>{
   const cache=await openBuildCache();
   return (await cache.match(req))||fetch(req);
  })());
 }
});
