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
