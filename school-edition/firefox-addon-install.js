/* Firefox installer prompt for School Teacher Notebook, 2.8.23.
 * Never initiates an extension install without a teacher click. */
(function(){
'use strict';
const ua=navigator.userAgent||'';
if(!/Firefox\/\d+/.test(ua)||/FxiOS/.test(ua))return;
const android=/Android/.test(ua);
const version=Number((ua.match(/Firefox\/(\d+)/)||[])[1]||0);
const MIN_VERSION=android?142:140;
const FILE='../addons/'; // New clean release awaits Mozilla signing.
const LIB='../addons/';
let addonLinked=false;
const STORAGE='school-notebook-ff-prep-2.8.23:'+(typeof schoolNotebookSubject==='string'?schoolNotebookSubject:'browser');
function makeLink(text,href,extraClass){
 const a=document.createElement('a');a.textContent=text;a.href=href;
 a.className=extraClass||'btn btn-outline btn-block';return a;
}
function enhanceServices(){
 const old=document.querySelector('#sc-moe a[href="../addons/"]');
 if(!old||document.getElementById('noorFirefoxInstallService'))return;
 const link=makeLink('🧩 أدوات نور — إصدار نظيف 2.8.23 قيد التوقيع',version>=MIN_VERSION?FILE:LIB);
 link.id='noorFirefoxInstallService';
 link.className='btn btn-primary btn-block';
 
 old.insertAdjacentElement('afterend',link);
}
function dismissed(){try{return localStorage.getItem(STORAGE)==='dismissed'}catch(_){return false}}
function dismiss(){
 try{localStorage.setItem(STORAGE,'dismissed')}catch(_){}
 document.getElementById('schoolFirefoxPrepOffer')?.remove();
}
function offer(){
 if(addonLinked||dismissed()||!navigator.onLine||document.getElementById('schoolFirefoxPrepOffer'))return;
 const box=document.createElement('aside');
 box.id='schoolFirefoxPrepOffer';box.setAttribute('role','region');box.setAttribute('aria-label','إضافة تحضير نور لمتصفح Firefox');
 box.dir='rtl';
 box.style.cssText='position:fixed;inset:auto 12px 78px auto;z-index:16000;width:min(390px,calc(100vw - 24px));max-height:65vh;overflow:auto;background:#fffdf5;color:#184e3b;border:1px solid #c9ad68;border-radius:16px;padding:13px 14px;box-shadow:0 10px 30px #102e2450;font:13px/1.8 Tahoma,Arial,sans-serif';
 const heading=document.createElement('div');heading.style.cssText='font-weight:bold;font-size:15px;margin-bottom:5px';heading.textContent='🧩 أدوات نور — الإصدار النظيف 2.8.23';
 const p=document.createElement('p');p.style.cssText='margin:4px 0 8px';
 p.textContent='تمت إزالة تحاضير النسخ السابقة. النسخة النظيفة 2.8.23 بانتظار توقيع Mozilla، ولذلك لا نتيح تثبيت نسخة قديمة.';
 const actions=document.createElement('div');actions.style.cssText='display:flex;gap:6px;flex-wrap:wrap;align-items:center';
 const action=makeLink('حالة النسخة النظيفة',LIB);
 action.style.cssText='display:inline-block;background:#087a5b;border-radius:9px;color:white;padding:6px 11px;text-decoration:none;font-weight:700';
 
 const guide=makeLink('طريقة التثبيت',LIB);guide.style.cssText='display:inline-block;border:1px solid #087a5b;border-radius:9px;color:#087a5b;padding:6px 10px;text-decoration:none;font-weight:700';
 const close=document.createElement('button');close.type='button';close.textContent='لا تعرض مجددًا';
 close.style.cssText='border:0;background:transparent;color:#53695e;padding:6px;cursor:pointer;text-decoration:underline';
 close.addEventListener('click',dismiss);
 actions.append(action,guide,close);box.append(heading,p,actions);document.body.appendChild(box);
}
// The Firefox extension requests only an opaque teacher identifier AFTER approved login.
// Google ID tokens and Gemini API keys never pass through this window message.
window.addEventListener('message',event=>{
 if(event.source!==window||event.origin!==location.origin||!event.data||typeof event.data!=='object')return;
 if(event.data.type==='STN_NOOR_WHOAMI'){
   if(!document.getElementById('schoolAuthCover')&&typeof schoolNotebookSubject==='string'&&schoolNotebookSubject){
     window.postMessage({type:'STN_NOOR_ACTIVE_TEACHER',teacherId:schoolNotebookSubject},location.origin);
   }
 }
 if(event.data.type==='STN_NOOR_ADDON_CONNECTED'){
   addonLinked=true;
   document.getElementById('schoolFirefoxPrepOffer')?.remove();
   const anchor=document.getElementById('noorFirefoxInstallService');
   if(anchor){anchor.textContent='✅ إضافة نور متصلة — إدارة الأدوات';anchor.href='../addons/';anchor.removeAttribute('download');}
 }
});
function ready(){
 enhanceServices();
 let count=0;
 const interval=setInterval(function(){
  count++;
  if(!document.getElementById('schoolAuthCover')){
    clearInterval(interval);
    if(document.getElementById('schoolOfflinePinSetup'))return;
    offer();
  }
  if(count>=75)clearInterval(interval);
 },500);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();
})();