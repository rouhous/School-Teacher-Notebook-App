import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.105.0';
const ROOT='https://czljzhwmtqmtmlsbwgyz.supabase.co';
const client=createClient(ROOT,'sb_publishable_fwWBrwdO6rsJxzQRS1dfLw_laESLi4U',{
 auth:{experimental:{passkey:true},storage:sessionStorage,storageKey:'school-notebook-passkey-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
});
const $=id=>document.getElementById(id);
const message=$('supervisorPasskeyStatus');
const supervisorEnrolledKey='school-notebook-supervisor-passkey-enrolled-v1';
const previouslyEnabled=localStorage.getItem(supervisorEnrolledKey)==='1';
function inform(txt){if(message)message.textContent=txt}
function friendly(error){
 const msg=String(error?.message||error||'');
 if(/NotAllowedError|cancelled|canceled|timed out|no credentials|no passkeys|not allowed/i.test(msg))return 'لم تكتمل عملية البصمة أو تم إلغاؤها. يمكنك استخدام Google.';
 if(/passkey.*(disabled|unsupported)|webauthn.*(disabled|unsupported)/i.test(msg))return 'خدمة مفاتيح المرور غير متاحة على الجهاز أو الخادم.';
 if(/FOUNDER_ONLY|NOT_APPROVED|ACCESS_DENIED/i.test(msg))return 'الحساب لا يملك صلاحية المشرف المؤسس.';
 return msg.length>160?'تعذر إكمال العملية. يرجى استخدام تسجيل الدخول عبر Google.':msg;
}
async function call(path,body){
 const response=await fetch(ROOT+'/functions/v1/'+path,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify(body)});
 const result=await response.json().catch(()=>({}));
 if(!response.ok||!result.ok)throw Error(result.error||'تعذر التحقق من حساب المشرف');
 return result;
}
async function accessToken(){
 const {data,error}=await client.auth.getSession();
 if(error||!data.session?.access_token)throw Error('جلسة البصمة غير متاحة');
 return data.session.access_token;
}
async function verifiedDashboard(access_token){
 return await call('school-founder-dashboard',{access_token});
}
async function enter(){
 const session=await accessToken();
 await verifiedDashboard(session);
 if(typeof window.supervisorPasskeyLogin!=='function')throw Error('واجهة المشرف غير جاهزة');
 await window.supervisorPasskeyLogin(session);
}
const login=$('supervisorPasskeyLogin'),register=$('supervisorPasskeyRegister');
if(login){
 login.onclick=async()=>{
  login.disabled=true;inform('جارٍ التحقق بالبصمة أو قفل الجهاز...');
  try{
   const result=await client.auth.signInWithPasskey();
   if(result.error)throw result.error;
   await enter();inform('تم الدخول إلى لوحة المشرف.');
  }catch(e){inform(friendly(e))}
  finally{login.disabled=false}
 };
}
if(register){
 register.onclick=async()=>{
  register.disabled=true;inform('جارٍ تفعيل مفتاح المرور بعد التحقق من Google...');
  try{
   const credential=typeof schoolAuthRestore==='function'?schoolAuthRestore():null;
   if(!credential)throw Error('سجّل الدخول إلى لوحة المشرف باستخدام Google أولًا، ثم فعّل البصمة.');
   // Bootstrap is restricted server-side to the authorized founder identity.
   const result=await call('school-supervisor-passkey-bootstrap',{credential});
   const {error}=await client.auth.setSession(result.session);
   if(error)throw error;
   const registered=await client.auth.registerPasskey();
   if(registered.error)throw registered.error;
   await verifiedDashboard(await accessToken());
   localStorage.setItem(supervisorEnrolledKey,'1');
   inform('✓ البصمة مفعّلة على هذا الجهاز. سيظهر دخول البصمة مباشرة في المرات القادمة.');
   register.textContent='✓ البصمة مفعّلة';register.disabled=true;
   if(login)login.hidden=true;
  }catch(e){inform(friendly(e))}
  finally{register.disabled=false}
 };
}
function reflectEnrollment(){
 if(register){
  register.hidden=!(window.supervisorGoogleVerified===true);
  if(previouslyEnabled){register.textContent='✓ البصمة مفعّلة';register.disabled=true}
 }
}
window.addEventListener('supervisor-google-verified',reflectEnrollment);
reflectEnrollment();
if(previouslyEnabled&&login&&!window.supervisorGoogleVerified){
 document.body.classList.add('supervisor-passkey-mode');
 const fallback=document.getElementById('supervisorPasskeyFallback');
 if(fallback)fallback.hidden=false;
 inform('جارٍ التحقق من الجلسة المحفوظة...');
 (async()=>{
  try{
   // Reuse the passkey-authenticated session after coming from the teacher entry.
   await enter();
   inform('تم الدخول إلى لوحة المشرف.');
  }catch(e){
   inform('البصمة مفعّلة على هذا الجهاز. أكّد هويتك للمتابعة.');
   login.click();
  }
 })();
}
const fallback=document.getElementById('supervisorPasskeyFallback');
if(fallback)fallback.addEventListener('click',()=>{
 document.body.classList.remove('supervisor-passkey-mode');
 fallback.hidden=true;
 document.querySelector('#signin')?.closest('section')?.removeAttribute('hidden');
 inform('يمكنك اختيار حساب Google للدخول أو استعادة الوصول.');
});

