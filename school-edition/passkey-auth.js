import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.105.0';
const ROOT='https://czljzhwmtqmtmlsbwgyz.supabase.co';
const client=createClient(ROOT,'sb_publishable_fwWBrwdO6rsJxzQRS1dfLw_laESLi4U',{auth:{experimental:{passkey:true},storage:sessionStorage,storageKey:'school-notebook-passkey-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
const SUBKEY='school-notebook-passkey-subject-v1';
const ENROLLED_KEY='school-notebook-passkey-enrolled-v1';
async function call(path,payload,token){
 const response=await fetch(ROOT+'/functions/v1/'+path,{method:'POST',headers:{'content-type':'application/json',...(token?{authorization:'Bearer '+token}:{})},body:JSON.stringify(payload)});
 const json=await response.json().catch(()=>({}));
 if(!response.ok||!json.ok)throw Error(json.error||'تعذر التحقق من حساب المعلم.');
 return json;
}
async function token(){
 const {data,error}=await client.auth.getSession();
 if(error||!data.session?.access_token)return null;
 return data.session.access_token;
}
async function registerWithGoogle(credential){
 if(!credential)throw Error('يرجى تسجيل الدخول باستخدام Google مجددًا ثم تفعيل البصمة.');
 const bootstrap=await call('school-passkey-bootstrap',{credential});
 const {error:sessionError}=await client.auth.setSession(bootstrap.session);
 if(sessionError)throw sessionError;
 const result=await client.auth.registerPasskey();
 if(result.error)throw result.error;
 sessionStorage.setItem(SUBKEY,bootstrap.google_sub);
 localStorage.setItem(ENROLLED_KEY,'1');
 return result.data;
}
async function signIn(){
 const result=await client.auth.signInWithPasskey();
 if(result.error)throw result.error;
 const access=await token();
 if(!access)throw Error('تعذر إنشاء جلسة البصمة.');
 // Supervisor privilege is checked FIRST by the protected server endpoint.
 const supervisorResponse=await fetch(ROOT+'/functions/v1/school-founder-dashboard',{
  method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({access_token:access})
 });
 if(supervisorResponse.ok){
  const supervisor=await supervisorResponse.json();
  if(supervisor.ok){
   localStorage.setItem('school-notebook-supervisor-passkey-enrolled-v1','1');
   return {role:'supervisor',access_token:access};
  }
 }else if(supervisorResponse.status!==403&&supervisorResponse.status!==401){
  throw Error('تعذر التحقق من صلاحيات المشرف. تحقق من الاتصال وأعد المحاولة.');
 }
 // Non-supervisors retain their normal teacher access; no new identities are created.
 const verify=await call('school-passkey-identity',{action:'resolve'},access);
 if(!verify?.data?.approved)throw Error('NOT_APPROVED');
 sessionStorage.setItem(SUBKEY,verify.google_sub);
 localStorage.setItem(ENROLLED_KEY,'1');
 return {...verify,role:'teacher'};
}
async function existing(){
 const access=await token();
 if(!access)return false;
 try{const r=await call('school-passkey-identity',{action:'resolve'},access);sessionStorage.setItem(SUBKEY,r.google_sub);return true;}catch{sessionStorage.removeItem(SUBKEY);return false;}
}
async function signOut(){await client.auth.signOut();sessionStorage.removeItem(SUBKEY);}
window.schoolPasskey={registerWithGoogle,signIn,token,existing,signOut,getSubject:()=>sessionStorage.getItem(SUBKEY)||'',friendlyPasskeyError};
window.dispatchEvent(new Event('school-passkey-ready'));

function friendlyPasskeyError(error,phase){
 const raw=String(error?.message||error||'');
 const code=String(error?.name||'');
 if(/NotAllowedError|not allowed|timed out|cancelled|canceled|no passkeys|no credentials/i.test(code+' '+raw))
  return phase==='login'?'لم يُعثر على مفتاح مرور، أو أُلغيت العملية. إذا كانت هذه أول مرة، ادخل باستخدام Google ثم فعّل البصمة داخل الدفتر.':'لم تكتمل عملية إنشاء المفتاح. تأكد من إعداد قفل الشاشة أو البصمة، ثم أعد المحاولة.';
 if(/passkey.*(disabled|not enabled|unsupported)|webauthn.*(disabled|not enabled)|feature.*disabled/i.test(raw))
  return 'خدمة مفاتيح المرور غير مفعّلة على الخادم. يجب تفعيلها من إعدادات المصادقة أولاً.';
 if(/AUTH_BOOTSTRAP_FAILED|AUTH_VERIFY_FAILED|AUTH_SESSION_FAILED|AUTH_LINK_MISSING|IDENTITY_LINK_FAILED/.test(raw))
  return 'تعذر تجهيز حساب مفتاح المرور على الخادم. لم يتم تفعيل البصمة؛ جرّب الدخول باستخدام Google.';
 if(/NOT_APPROVED|IDENTITY_ALREADY_LINKED/.test(raw))
  return 'تعذر ربط المفتاح بالمعلم المعتمد. يُرجى مراجعة المشرف دون إنشاء حساب معلم جديد.';
 return raw.length>160?'حدث خطأ في خدمة مفاتيح المرور. حاول تسجيل الدخول باستخدام Google ثم إعادة التفعيل.':raw;
}
function makeButton(label,action,phase){
 const b=document.createElement('button');
 b.type='button';b.textContent=label;
 b.style.cssText='border:1px solid #9bbfae;border-radius:10px;background:#fff;color:#086147;padding:8px 12px;margin:6px auto;display:block;font-size:.85rem;line-height:1.4;font-weight:750;cursor:pointer;max-width:100%;white-space:normal';
 const msg=document.createElement('p');msg.setAttribute('role','status');
 msg.style.cssText='font-size:13px;color:#426657;margin:6px;text-align:center;line-height:1.7;overflow-wrap:anywhere';
 b.addEventListener('click',async()=>{
  b.disabled=true;msg.textContent=phase==='login'?'جارٍ التحقق من مفتاح المرور المسجّل...':'جارٍ تسجيل مفتاح مرور جديد لهذا الجهاز...';
  try{
   await action();
   msg.textContent=phase==='login'?'تم التحقق من مفتاح المرور.':'تم تفعيل مفتاح المرور. يمكنك استخدامه عند الدخول في المرة القادمة.';
  }catch(e){
   msg.textContent=friendlyPasskeyError(e,phase);
  }finally{b.disabled=false}
 });
 return {b,msg};
}
if(document.getElementById('teacher-google')){
 const holder=document.getElementById('teacher-google');
 const entry=document.getElementById('teacher-passkey-entry');
 const enrolled=localStorage.getItem(ENROLLED_KEY)==='1'||localStorage.getItem('school-notebook-supervisor-passkey-enrolled-v1')==='1';
 const route=role=>location.replace(role==='supervisor'?'school-edition/founder-dashboard.html':'school-edition/school-notebook.html');
 const action=async()=>route((await signIn()).role);
 if(enrolled&&entry){
  document.body.classList.add('teacher-passkey-mode');
  entry.hidden=false;
  const status=document.getElementById('teacher-passkey-direct-status');
  const go=document.getElementById('teacher-passkey-direct');
  const fallback=document.getElementById('teacher-passkey-google-fallback');
  let running=false;
  go.onclick=async()=>{
   if(running)return;
   running=true;go.disabled=true;
   status.textContent='جارٍ التحقق من بصمة الجهاز…';
   try{await action()}
   catch(e){status.textContent=friendlyPasskeyError(e,'login')}
   finally{running=false;go.disabled=false}
  };
  fallback.onclick=()=>{
   document.body.classList.remove('teacher-passkey-mode');
   entry.hidden=true;
   holder.hidden=false;
   const help=document.getElementById('passkey-help');
   if(help)help.hidden=false;
  };
  // A verified existing session needs no biometric prompt; otherwise request
  // the saved passkey once at launch. Browsers may require a tap to proceed.
  (async()=>{
   let promptRequired=true;
   try{
    const access=await token();
    if(access){
     const supervisor=await fetch(ROOT+'/functions/v1/school-founder-dashboard',{
      method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({access_token:access})
     });
     if(supervisor.ok&&(await supervisor.json()).ok){route('supervisor');return}
     if([401,403].includes(supervisor.status)){
      try{
       const teacher=await call('school-passkey-identity',{action:'resolve'},access);
       if(teacher.data?.approved){sessionStorage.setItem(SUBKEY,teacher.google_sub);route('teacher');return}
      }catch(e){/* A valid local token without role authorization still needs re-authentication. */}
     }else{
      promptRequired=false;
      status.textContent='تعذر الاتصال للتحقق من الجلسة. يمكنك المحاولة مجددًا.';
     }
    }
   }catch(e){/* Request a fresh passkey assertion if a cached session cannot be restored. */}
   if(promptRequired&&document.visibilityState!=='hidden'&&!running){
    go.click();
   }
  })();
 }else{
  const {b,msg}=makeButton('🔐 الدخول بالبصمة / Face ID',action,'login');
  holder.insertAdjacentElement('afterend',b);
  b.insertAdjacentElement('afterend',msg);
  if(entry)entry.hidden=true;
 }
}
