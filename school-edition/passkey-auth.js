import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.105.0';
const ROOT='https://czljzhwmtqmtmlsbwgyz.supabase.co';
const client=createClient(ROOT,'sb_publishable_fwWBrwdO6rsJxzQRS1dfLw_laESLi4U',{auth:{experimental:{passkey:true},storage:sessionStorage,storageKey:'school-notebook-passkey-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}});
const SUBKEY='school-notebook-passkey-subject-v1';
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
 return result.data;
}
async function signIn(){
 const result=await client.auth.signInWithPasskey();
 if(result.error)throw result.error;
 const access=await token();
 if(!access)throw Error('تعذر إنشاء جلسة البصمة.');
 const verify=await call('school-passkey-identity',{action:'resolve'},access);
 sessionStorage.setItem(SUBKEY,verify.google_sub);
 return verify;
}
async function existing(){
 const access=await token();
 if(!access)return false;
 try{const r=await call('school-passkey-identity',{action:'resolve'},access);sessionStorage.setItem(SUBKEY,r.google_sub);return true;}catch{sessionStorage.removeItem(SUBKEY);return false;}
}
async function signOut(){await client.auth.signOut();sessionStorage.removeItem(SUBKEY);}
window.schoolPasskey={registerWithGoogle,signIn,token,existing,signOut,getSubject:()=>sessionStorage.getItem(SUBKEY)||''};
window.dispatchEvent(new Event('school-passkey-ready'));

function makeButton(text,action){const b=document.createElement('button');b.type='button';b.textContent=text;b.style.cssText='border:1px solid #9bbfae;border-radius:12px;background:#fff;color:#086147;padding:12px 14px;margin:8px;font-weight:800;cursor:pointer';const msg=document.createElement('p');msg.style.cssText='font-size:13px;color:#426657;margin:6px;text-align:center';b.addEventListener('click',async()=>{b.disabled=true;msg.textContent='جارٍ تنفيذ المصادقة الآمنة...';try{await action();msg.textContent='تم تسجيل مفتاح المرور بنجاح.';}catch(e){msg.textContent='تعذر استخدام مفتاح المرور: '+(e.message||e)}finally{b.disabled=false}});return {b,msg};}
if(document.getElementById('teacher-google')){
 const holder=document.getElementById('teacher-google');
 const {b,msg}=makeButton('🔐 الدخول بالبصمة أو Face ID',async()=>{await signIn();location.assign('school-edition/school-notebook.html')});
 holder.insertAdjacentElement('afterend',b);b.insertAdjacentElement('afterend',msg);
}
if(location.pathname.endsWith('/school-edition/school-notebook.html')&&typeof schoolAuthRestore==='function'&&schoolAuthRestore()){
 const {b,msg}=makeButton('🔐 تفعيل البصمة / Face ID',async()=>registerWithGoogle(schoolAuthRestore()));
 const panel=document.createElement('div');panel.style.cssText='position:fixed;left:9px;bottom:105px;z-index:500;background:#f5fffa;border:1px solid #bed8c9;border-radius:16px;max-width:210px;box-shadow:0 4px 16px #0438;text-align:center;padding:4px';panel.append(b,msg);const test=document.createElement('button');test.type='button';test.textContent='تجربة الدخول بالبصمة';test.style.cssText='border:1px solid #9bbfae;border-radius:10px;padding:9px;background:#e5f7ed;color:#075a43;font-weight:700;margin:6px';test.onclick=async()=>{await signOut();schoolAuthClear();location.assign('../')};panel.append(test);document.body.append(panel);
}
