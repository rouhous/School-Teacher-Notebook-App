/* Short-lived Google ID credential: session-only, never permanent localStorage. */
const SCHOOL_AUTH_KEY='school-notebook-google-session-v1';
function schoolAuthSave(credential){try{const p=JSON.parse(atob(credential.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));if(!p.exp||p.exp*1000<Date.now()+60000)return;sessionStorage.setItem(SCHOOL_AUTH_KEY,JSON.stringify({credential,exp:p.exp}));}catch{}}
function schoolAuthRestore(){try{const o=JSON.parse(sessionStorage.getItem(SCHOOL_AUTH_KEY)||'null');if(o&&o.exp*1000>Date.now()+60000&&typeof o.credential==='string')return o.credential;}catch{}sessionStorage.removeItem(SCHOOL_AUTH_KEY);return null;}
function schoolAuthClear(){sessionStorage.removeItem(SCHOOL_AUTH_KEY)}
