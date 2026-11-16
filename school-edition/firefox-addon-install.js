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
  if(!document.getElementById('schoolAuthCover')&&typeof schoolNotebookSubject==='string'&&schoolNotebookSubject){
   window.postMessage({type:'STN_NOOR_ACTIVE_TEACHER',teacherId:schoolNotebookSubject},location.origin);
  }
 }
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