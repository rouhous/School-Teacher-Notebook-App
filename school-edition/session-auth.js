/* Short-lived Google ID credential: session-only, never permanent localStorage. */
const SCHOOL_AUTH_KEY='school-notebook-google-session-v1';
function schoolAuthSave(credential){try{const p=JSON.parse(atob(credential.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));if(!p.exp||p.exp*1000<Date.now()+60000)return;sessionStorage.setItem(SCHOOL_AUTH_KEY,JSON.stringify({credential,exp:p.exp}));}catch{}}
function schoolAuthRestore(){try{const o=JSON.parse(sessionStorage.getItem(SCHOOL_AUTH_KEY)||'null');if(o&&o.exp*1000>Date.now()+60000&&typeof o.credential==='string')return o.credential;}catch{}sessionStorage.removeItem(SCHOOL_AUTH_KEY);return null;}
function schoolAuthClear(){sessionStorage.removeItem(SCHOOL_AUTH_KEY)}

/* Shared internal supervisor session. UI login occurs only at the app entrance.
   Never trust local enrolment flags for authorization; APIs verify each request. */
let schoolSupervisorClientPromise=null;
async function schoolSupervisorSession(){
 const google=schoolAuthRestore();
 if(google)return {credential:google};
 try{
  if(!schoolSupervisorClientPromise)schoolSupervisorClientPromise=import('https://esm.sh/@supabase/supabase-js@2.105.0').then(({createClient})=>
   createClient('https://czljzhwmtqmtmlsbwgyz.supabase.co','sb_publishable_fwWBrwdO6rsJxzQRS1dfLw_laESLi4U',{
    auth:{storage:sessionStorage,storageKey:'school-notebook-passkey-auth-v1',persistSession:true,autoRefreshToken:true,detectSessionInUrl:false}
   })
  );
  const client=await schoolSupervisorClientPromise;
  const {data,error}=await client.auth.getSession();
  if(!error&&data.session?.access_token)return {access_token:data.session.access_token};
 }catch(e){console.warn('Supervisor session restore unavailable',e)}
 return null;
}
