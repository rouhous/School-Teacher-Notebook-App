const CACHE_PREFIX='school-pwa-';
const BUILD_FILES=['./sw.js','./index.html','./manifest.webmanifest','./school-edition/school-notebook.html','./school-edition/session-auth.js','./school-edition/offline-pin.js','./school-edition/passkey-auth.js'];
const SHELL=['./','./index.html','./manifest.webmanifest','./assets/school-icon-192.png','./assets/school-icon-512.png','./assets/school-home-reference-clean1.png','./assets/school-home-reference-clean2.png','./assets/school-home-approved.png','./school-edition/school-notebook.html','./school-edition/session-auth.js','./school-edition/offline-pin.js','./school-edition/passkey-auth.js','./school-edition/manifest.webmanifest'];
const REQUIRED=['./','./index.html','./school-edition/school-notebook.html','./school-edition/session-auth.js','./school-edition/offline-pin.js'];
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
async function openBuildCache(){return caches.open(await CACHE_NAME_PROMISE)}
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
  const current=await CACHE_NAME_PROMISE;
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
