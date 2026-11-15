/* Firefox installer prompt for School Teacher Notebook, 2.8.21.
 * Never initiates an extension install without a teacher click. */
(function(){
'use strict';
const ua=navigator.userAgent||'';
if(!/Firefox\/\d+/.test(ua)||/FxiOS/.test(ua))return;
const android=/Android/.test(ua);
const version=Number((ua.match(/Firefox\/(\d+)/)||[])[1]||0);
const MIN_VERSION=android?142:140;
const FILE='../addons/files/Noor-Prep-Filler-v2.8.21-signed.xpi';
const LIB='../addons/';
const STORAGE='school-notebook-ff-prep-2.8.21:'+(typeof schoolNotebookSubject==='string'?schoolNotebookSubject:'browser');
function makeLink(text,href,extraClass){
 const a=document.createElement('a');a.textContent=text;a.href=href;
 a.className=extraClass||'btn btn-outline btn-block';return a;
}
function enhanceServices(){
 const old=document.querySelector('#sc-moe a[href="../addons/"]');
 if(!old||document.getElementById('noorFirefoxInstallService'))return;
 const link=makeLink(android?'📥 تنزيل إضافة تحضير نور (XPI)':'🧩 تثبيت إضافة تحضير نور في Firefox',version>=MIN_VERSION?FILE:LIB);
 link.id='noorFirefoxInstallService';
 link.className='btn btn-primary btn-block';
 if(android&&version>=MIN_VERSION)link.download='Noor-Prep-Filler-v2.8.21-signed.xpi';
 old.insertAdjacentElement('afterend',link);
}
function dismissed(){try{return localStorage.getItem(STORAGE)==='dismissed'}catch(_){return false}}
function dismiss(){
 try{localStorage.setItem(STORAGE,'dismissed')}catch(_){}
 document.getElementById('schoolFirefoxPrepOffer')?.remove();
}
function offer(){
 if(dismissed()||!navigator.onLine||document.getElementById('schoolFirefoxPrepOffer'))return;
 const box=document.createElement('aside');
 box.id='schoolFirefoxPrepOffer';box.setAttribute('role','region');box.setAttribute('aria-label','إضافة تحضير نور لمتصفح Firefox');
 box.dir='rtl';
 box.style.cssText='position:fixed;inset:auto 12px 78px auto;z-index:16000;width:min(390px,calc(100vw - 24px));max-height:65vh;overflow:auto;background:#fffdf5;color:#184e3b;border:1px solid #c9ad68;border-radius:16px;padding:13px 14px;box-shadow:0 10px 30px #102e2450;font:13px/1.8 Tahoma,Arial,sans-serif';
 const heading=document.createElement('div');heading.style.cssText='font-weight:bold;font-size:15px;margin-bottom:5px';heading.textContent='🧩 إضافة تحضير دروس نور — 2.8.21';
 const p=document.createElement('p');p.style.cssText='margin:4px 0 8px';
 p.textContent=version<MIN_VERSION?'لتثبيت الإضافة يجب تحديث Firefox أولًا.':android?'يمكن تنزيل الإضافة الموقّعة وتثبيتها من ملف XPI في إعدادات Firefox.':'يمكن تثبيت إضافة تحضير الدروس الموقّعة مباشرةً بعد موافقتك في Firefox.';
 const actions=document.createElement('div');actions.style.cssText='display:flex;gap:6px;flex-wrap:wrap;align-items:center';
 const action=makeLink(version<MIN_VERSION?'تعليمات التحديث':android?'تنزيل XPI':'تثبيت الإضافة',version>=MIN_VERSION?FILE:LIB);
 action.style.cssText='display:inline-block;background:#087a5b;border-radius:9px;color:white;padding:6px 11px;text-decoration:none;font-weight:700';
 if(android&&version>=MIN_VERSION)action.download='Noor-Prep-Filler-v2.8.21-signed.xpi';
 const guide=makeLink('طريقة التثبيت',LIB);guide.style.cssText='display:inline-block;border:1px solid #087a5b;border-radius:9px;color:#087a5b;padding:6px 10px;text-decoration:none;font-weight:700';
 const close=document.createElement('button');close.type='button';close.textContent='لا تعرض مجددًا';
 close.style.cssText='border:0;background:transparent;color:#53695e;padding:6px;cursor:pointer;text-decoration:underline';
 close.addEventListener('click',dismiss);
 actions.append(action,guide,close);box.append(heading,p,actions);document.body.appendChild(box);
}
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