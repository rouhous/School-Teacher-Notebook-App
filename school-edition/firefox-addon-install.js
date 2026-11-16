/* Firefox installer prompt for School Teacher Notebook, signed Noor Tools 2.8.24.
 * Installation only on a click by the teacher. */
(function(){
'use strict';
const ua=navigator.userAgent||'';
if(!/Firefox\/\d+/.test(ua)||/FxiOS/.test(ua))return;
const android=/Android/.test(ua);
const version=Number((ua.match(/Firefox\/(\d+)/)||[])[1]||0);
const MIN_VERSION=android?142:140;
const FILE='../addons/files/Noor-Unified-v2.8.24-Gemini-AQ-signed.xpi';
const LIB='../addons/';
const STORAGE='school-notebook-ff-noor-2.8.24:'+(typeof schoolNotebookSubject==='string'?schoolNotebookSubject:'browser');
let addonLinked=false;
function link(text,href){
  const a=document.createElement('a');a.href=href;a.textContent=text;return a;
}
function enhanceServices(){
 const old=document.querySelector('#sc-moe a[href="../addons/"]');
 if(!old||document.getElementById('noorFirefoxInstallService'))return;
 const action=link(version>=MIN_VERSION?android?'📥 تنزيل أدوات نور 2.8.24':'🧩 تثبيت أدوات نور 2.8.24':'🧩 أدوات نور — تعليمات التحديث',version>=MIN_VERSION?FILE:LIB);
 action.className='btn btn-primary btn-block';action.id='noorFirefoxInstallService';
 if(android&&version>=MIN_VERSION)action.download='Noor-Unified-v2.8.24-Gemini-AQ-signed.xpi';
 old.insertAdjacentElement('afterend',action);
}
function dismiss(){
 try{localStorage.setItem(STORAGE,'dismissed')}catch(_){}
 document.getElementById('schoolFirefoxPrepOffer')?.remove();
}
function offer(){
 if(addonLinked||!navigator.onLine||document.getElementById('schoolFirefoxPrepOffer'))return;
 try{if(localStorage.getItem(STORAGE)==='dismissed')return}catch(_){}
 const box=document.createElement('aside');box.id='schoolFirefoxPrepOffer';box.dir='rtl';
 box.setAttribute('role','region');box.setAttribute('aria-label','إضافة أدوات نور في Firefox');
 box.style.cssText='position:fixed;inset:auto 12px 78px auto;z-index:16000;width:min(390px,calc(100vw - 24px));max-height:65vh;overflow:auto;background:#fffdf5;color:#184e3b;border:1px solid #c9ad68;border-radius:16px;padding:13px 14px;box-shadow:0 10px 30px #102e2450;font:13px/1.8 Tahoma,Arial,sans-serif';
 const h=document.createElement('strong');h.textContent='🧩 أدوات نور — 2.8.24';
 const p=document.createElement('p');p.style.cssText='margin:4px 0 8px';
 p.textContent=version<MIN_VERSION?'للتثبيت يجب تحديث Firefox أولًا.':android?'الإضافة الموقّعة متوفرة. نزّل XPI ثم ثبتها من خيارات Firefox Android.':'الإضافة الموقّعة جاهزة. يمكنك تثبيتها بعد الموافقة في Firefox.';
 const actions=document.createElement('div');actions.style.cssText='display:flex;gap:6px;flex-wrap:wrap;align-items:center';
 const action=link(version<MIN_VERSION?'تعليمات التحديث':android?'تنزيل XPI':'تثبيت الإضافة',version>=MIN_VERSION?FILE:LIB);
 action.style.cssText='display:inline-block;background:#087a5b;border-radius:9px;color:white;padding:6px 11px;text-decoration:none;font-weight:700';
 if(android&&version>=MIN_VERSION)action.download='Noor-Unified-v2.8.24-Gemini-AQ-signed.xpi';
 const guide=link('طريقة التثبيت',LIB);guide.style.cssText='display:inline-block;border:1px solid #087a5b;border-radius:9px;color:#087a5b;padding:6px 10px;text-decoration:none;font-weight:700';
 const close=document.createElement('button');close.type='button';close.textContent='لا تعرض مجددًا';
 close.style.cssText='border:0;background:transparent;color:#53695e;padding:6px;cursor:pointer;text-decoration:underline';
 close.addEventListener('click',dismiss);
 actions.append(action,guide,close);box.append(h,p,actions);document.body.appendChild(box);
}
// Only share the logged-in teacher's opaque ID with the extension after approval.
// Never expose the Google token or Gemini API key.
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
  if(anchor){anchor.textContent='✅ إضافة نور متصلة — إدارة الأدوات';anchor.href=LIB;anchor.removeAttribute('download');}
 }
});
function ready(){
 enhanceServices();
 let count=0;
 const timer=setInterval(()=>{
  if(++count>=75){clearInterval(timer);return}
  if(!document.getElementById('schoolAuthCover')){
   clearInterval(timer);
   if(!document.getElementById('schoolOfflinePinSetup'))offer();
  }
 },500);
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',ready,{once:true});else ready();
})();