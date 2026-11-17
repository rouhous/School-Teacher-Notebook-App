/* Simple Firefox add-on entry in the School Teacher Notebook.
 * The indicator is shown only after a live connection message from Noor Tools. */
(function(){
'use strict';
const LIB='../addons/';
let connected=false;

function updateLink(){
 const anchor=document.querySelector('#sc-moe a[href="../addons/"]') || document.getElementById('noorFirefoxInstallService');
 if(!anchor)return;
 anchor.id='noorFirefoxInstallService';
 anchor.href=LIB;
 anchor.textContent=connected?'🧩 إضافة نور ✅':'🧩 إضافة نور';
 anchor.title=connected?'إضافة نور متصلة — فتح صفحة الإضافة':'فتح صفحة تنزيل إضافة نور وتثبيتها';
 anchor.setAttribute('aria-label',anchor.title);
 if(connected){
  anchor.dataset.addonConnected='true';
 }else{
  delete anchor.dataset.addonConnected;
 }
}

window.addEventListener('message',event=>{
 if(event.source!==window||event.origin!==location.origin||!event.data||typeof event.data!=='object')return;
 if(event.data.type==='STN_NOOR_WHOAMI'){
  void (async()=>{
   const installId=String(event.data.installId||'');
   if(!/^[a-f0-9]{32}$/.test(installId)){
    // Compatibility with earlier, already distributed signed XPIs. These older
    // builds only support the legacy identity handshake; do not revoke them.
    // The 2.8.37 extension always sends a 32-character install challenge.
    if(!document.getElementById('schoolAuthCover')&&typeof schoolNotebookSubject==='string'&&schoolNotebookSubject){
     window.postMessage({type:'STN_NOOR_ACTIVE_TEACHER',teacherId:schoolNotebookSubject},location.origin);
    }
    return;
   }
   if(document.getElementById('schoolAuthCover')||typeof schoolNotebookSubject!=='string'||!schoolNotebookSubject)return;
   try{
    // The Google/Passkey credential is sent ONLY from this page to our trusted
    // Supabase membership function. The extension receives a short-lived permit,
    // NEVER the Google credential, passkey token or Gemini key.
    const credential=typeof schoolNotebookCredential==='string'?schoolNotebookCredential:'';
    const auth=credential?{credential}:{access_token:typeof schoolNotebookPasskeyToken==='function'?await schoolNotebookPasskeyToken():''};
    if(!auth.credential&&!auth.access_token)throw Error('SESSION_REQUIRED');
    const response=await fetch('https://czljzhwmtqmtmlsbwgyz.supabase.co/functions/v1/noor-addon-license',{
     method:'POST',headers:{'content-type':'application/json'},cache:'no-store',
     body:JSON.stringify({action:'issue',installId,...auth})
    });
    const result=await response.json();
    if(!response.ok||!result.ok||result.subject!==schoolNotebookSubject||!result.permit)throw Error(result.reason||'NOT_APPROVED');
    window.postMessage({type:'STN_NOOR_ACTIVE_TEACHER',teacherId:result.subject,installId,permit:result.permit},location.origin);
   }catch(error){
    const anchor=document.getElementById('noorFirefoxInstallService');
    if(anchor){anchor.textContent='🧩 إضافة نور — تحقق من العضوية';anchor.title='أعد تسجيل الدخول إلى دفتر المعلم للتحقق من حسابك النشط.';}
    console.warn('[Noor membership] Verification unavailable; no access granted.');
   }
  })();
 }
 if(event.data.type==='STN_NOOR_MEMBERSHIP_ERROR'){const a=document.getElementById('noorFirefoxInstallService');if(a)a.title='لم تكتمل صلاحية إضافة نور؛ حدّث الجلسة وأعد فتح دفتر المعلم.';}
 if(event.data.type==='STN_NOOR_ADDON_CONNECTED'){
  connected=true;
  updateLink();
 }
});

if(document.readyState==='loading'){
 document.addEventListener('DOMContentLoaded',updateLink,{once:true});
}else{
 updateLink();
}
})();