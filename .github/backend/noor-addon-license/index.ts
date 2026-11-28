// Noor Tools: short-lived, teacher-bound entitlement. Never store or return Google credentials.
const ORIGIN = 'https://rouhous.github.io';
const CLIENT = '825380653679-u542mtddqblq5nrt0pctj8sbfe9sg4dj.apps.googleusercontent.com';
const BASE = 'https://czljzhwmtqmtmlsbwgyz.supabase.co';
const enc = new TextEncoder();
const expirySeconds = 24 * 3600;
const issuer = 'stn-noor-license-v1';
function headers(origin = ''): Record<string,string> {return {'content-type':'application/json; charset=utf-8','cache-control':'no-store','vary':'Origin','access-control-allow-origin':origin === ORIGIN ? ORIGIN : '*','access-control-allow-methods':'POST, OPTIONS','access-control-allow-headers':'content-type'};}
function send(status:number,data:unknown,origin=''){return new Response(JSON.stringify(data),{status,headers:headers(origin)});}
const b64 = (bytes:Uint8Array) => btoa(String.fromCharCode(...bytes)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/g,'');
const fromB64 = (value:string) => Uint8Array.from(atob(value.replace(/-/g,'+').replace(/_/g,'/')+'='.repeat((4-value.length%4)%4)),c=>c.charCodeAt(0));
async function hmacKey(){
  // Dedicated server-only signing key; never sent to the extension.
  // Fail closed when it is absent or too short. Never derive signing keys
  // from Supabase credentials or any other fallback secret.
  const secret = Deno.env.get('NOOR_ADDON_SIGNING_SECRET');
  if (!secret || secret.length < 30) throw Error('NOT_CONFIGURED');
  const material = await crypto.subtle.digest('SHA-256',enc.encode('noor-addon-token-v1:'+secret));
  return crypto.subtle.importKey('raw',material,{name:'HMAC',hash:'SHA-256'},false,['sign','verify']);
}
async function sign(payload:Record<string,unknown>){
 const body=b64(enc.encode(JSON.stringify(payload)));
 const sig=await crypto.subtle.sign('HMAC',await hmacKey(),enc.encode(body));
 return body+'.'+b64(new Uint8Array(sig));
}
async function decode(token:string){
 if(!/^[\w-]{30,2500}\.[\w-]{40,120}$/.test(token))return null;
 const [body,sig]=token.split('.');
 if(!await crypto.subtle.verify('HMAC',await hmacKey(),fromB64(sig),enc.encode(body)))return null;
 let payload:Record<string,unknown>;
 try{payload=JSON.parse(new TextDecoder().decode(fromB64(body)))}catch{return null}
 const now=Math.floor(Date.now()/1000);
 if(payload.aud!==issuer||payload.v!==1||typeof payload.sub!=='string'||!/^([a-zA-Z0-9_:\-.]){3,200}$/.test(payload.sub)||!/^([a-f0-9]){32}$/.test(String(payload.installId||''))||typeof payload.exp!=='number'||payload.exp<now||payload.exp>now+expirySeconds||typeof payload.iat!=='number'||payload.iat>now+90)return null;
 return payload;
}
async function activeTeacher(sub:string){
 const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY'); if(!service)throw Error('NOT_CONFIGURED');
 const response=await fetch(BASE+'/rest/v1/rpc/school_teacher_session',{method:'POST',headers:{apikey:service,authorization:'Bearer '+service,'content-type':'application/json'},body:JSON.stringify({p_subject:sub})});
 if(!response.ok)throw Error('MEMBERSHIP_CHECK_FAILED');
 const data=await response.json();
 return data?.approved===true && !!data.teacherId ? {teacherId:String(data.teacherId).slice(0,80),role:String(data.role||'teacher').slice(0,40)} : null;
}
async function resolveIdentity(input:any){
 const google=typeof input.credential==='string'&&input.credential.length>50&&input.credential.length<=8192;
 const passkey=typeof input.access_token==='string'&&input.access_token.length>50&&input.access_token.length<=8192;
 if(google===passkey)return null;
 if(google){
  const resp=await fetch('https://oauth2.googleapis.com/tokeninfo?id_token='+encodeURIComponent(input.credential),{redirect:'error'});
  if(!resp.ok)return null;
  const user=await resp.json();
  if(user.aud!==CLIENT||!['accounts.google.com','https://accounts.google.com'].includes(user.iss)||!(user.email_verified===true||user.email_verified==='true')||Number(user.exp)*1000<=Date.now()||typeof user.sub!=='string')return null;
  return user.sub;
 }
 const service=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');if(!service)throw Error('NOT_CONFIGURED');
 const userResp=await fetch(BASE+'/auth/v1/user',{headers:{apikey:service,authorization:'Bearer '+input.access_token}});
 if(!userResp.ok)return null;
 const user=await userResp.json();if(!user?.id||user.is_anonymous)return null;
 const link=await fetch(BASE+'/rest/v1/rpc/school_passkey_resolve',{method:'POST',headers:{apikey:service,authorization:'Bearer '+service,'content-type':'application/json'},body:JSON.stringify({p_auth_user:user.id})});
 if(!link.ok)return null;
 const sub=await link.json();return typeof sub==='string'&&sub?sub:null;
}
Deno.serve(async(req:Request)=>{
 const origin=req.headers.get('origin')||'';
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:headers(origin)});
 if(req.method!=='POST')return send(405,{ok:false,reason:'METHOD_NOT_ALLOWED'},origin);
 try{
  const text=await req.text();if(text.length>12000)return send(413,{ok:false,reason:'TOO_LARGE'},origin);
  const data=JSON.parse(text);const action=data?.action;
  if(action==='issue'){
   if(origin!==ORIGIN)return send(403,{ok:false,reason:'ORIGIN_DENIED'},origin);
   if(!/^([a-f0-9]){32}$/.test(String(data.installId||'')))return send(400,{ok:false,reason:'INSTALL_ID_INVALID'},origin);
   const subject=await resolveIdentity(data);
   if(!subject)return send(401,{ok:false,reason:'LOGIN_REQUIRED'},origin);
   const teacher=await activeTeacher(subject);
   if(!teacher)return send(403,{ok:false,reason:'NOTEBOOK_MEMBERSHIP_REQUIRED'},origin);
   const now=Math.floor(Date.now()/1000);
   const expiresAt=now+expirySeconds;
   const permit=await sign({v:1,aud:issuer,sub:subject,installId:data.installId,teacherId:teacher.teacherId,iat:now,exp:expiresAt});
   return send(200,{ok:true,subject,permit,expiresAt},origin);
  }
  if(action==='verify'){
   const payload=await decode(data?.permit);
   if(!payload||payload.installId!==data.installId||payload.sub!==data.subject)return send(401,{ok:false,reason:'INVALID_OR_EXPIRED_PERMIT'},origin);
   const teacher=await activeTeacher(String(payload.sub));
   if(!teacher||teacher.teacherId!==payload.teacherId)return send(403,{ok:false,reason:'MEMBERSHIP_INACTIVE'},origin);
   return send(200,{ok:true,subject:payload.sub,expiresAt:payload.exp,teacherId:teacher.teacherId},origin);
  }
  return send(400,{ok:false,reason:'UNKNOWN_ACTION'},origin);
 }catch(e){
  const reason=String((e as Error).message||'');
  if(reason==='NOT_CONFIGURED'||reason==='MEMBERSHIP_CHECK_FAILED')return send(503,{ok:false,reason:'SERVICE_TEMPORARILY_UNAVAILABLE'},origin);
  return send(400,{ok:false,reason:'INVALID_REQUEST'},origin);
 }
});