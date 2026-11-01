/* Offline PIN: local convenience unlock, never a server authorization token. */
(function(){
 const PREFIX='school-offline-pin-v1:',SESSION='school-offline-unlocked-v1';
 const encoder=new TextEncoder();
 const b64=bytes=>btoa(String.fromCharCode(...bytes));
 const un64=str=>Uint8Array.from(atob(str),c=>c.charCodeAt(0));
 async function digest(pin,salt){
  const base=await crypto.subtle.importKey('raw',encoder.encode(pin),'PBKDF2',false,['deriveBits']);
  const bits=await crypto.subtle.deriveBits({name:'PBKDF2',salt,iterations:210000,hash:'SHA-256'},base,256);
  return b64(new Uint8Array(bits));
 }
 function read(){try{return JSON.parse(localStorage.getItem(PREFIX+'profile')||'null')}catch{return null}}
 function active(){try{const x=JSON.parse(sessionStorage.getItem(SESSION)||'null');return x&&x.subject&&x.until>Date.now()?x:null}catch{return null}}
 function clear(){sessionStorage.removeItem(SESSION)}
 async function enroll(subject,pin){
  if(!subject||!/^\\d{6,10}$/.test(pin))throw Error('استخدم رمزًا من 6 إلى 10 أرقام.');
  const salt=crypto.getRandomValues(new Uint8Array(16));
  const verifier=await digest(pin,salt);
  localStorage.setItem(PREFIX+'profile',JSON.stringify({subject,salt:b64(salt),verifier,verifiedAt:Date.now(),failures:0,blockedUntil:0}));
  clear();
 }
 async function unlock(pin){
  const p=read();if(!p)throw Error('لم يُفعّل رمز الدخول على هذا الجهاز.');
  if(Date.now()>p.verifiedAt+72*60*60*1000)throw Error('انتهت صلاحية الدخول المحلي. اتصل بالإنترنت للتحقق من الحساب.');
  if(Date.now()<p.blockedUntil)throw Error('محاولات كثيرة. حاول لاحقًا.');
  const result=await digest(pin,un64(p.salt));
  if(result!==p.verifier){
   p.failures=(p.failures||0)+1;
   if(p.failures>=5){p.blockedUntil=Date.now()+15*60*1000;p.failures=0}
   localStorage.setItem(PREFIX+'profile',JSON.stringify(p));
   throw Error('رمز الدخول غير صحيح.');
  }
  p.failures=0;p.blockedUntil=0;
  localStorage.setItem(PREFIX+'profile',JSON.stringify(p));
  sessionStorage.setItem(SESSION,JSON.stringify({subject:p.subject,until:Date.now()+8*60*60*1000}));
  return p.subject;
 }
 function refresh(subject){
  const p=read();if(p&&p.subject===subject){p.verifiedAt=Date.now();localStorage.setItem(PREFIX+'profile',JSON.stringify(p))}
 }
 window.schoolOfflinePin={read,active,clear,enroll,unlock,refresh};
})();
