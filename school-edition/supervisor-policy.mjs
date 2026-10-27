// School edition: pure supervisor access-policy decisions (no login or persistence).
// The backend MUST authenticate Google OIDC tokens (issuer, audience, signature,
// expiry, email_verified) and bind identities to immutable Google subject IDs.
// Founder identity is provisioned server-side, NEVER taken from browser input.
const active=r=>r.status==='active';
const admin=r=>r.role==='supervisor';
export function evaluateSupervisorAction({actorSub,supervisors=[],action,targetSub,founderSub}={}){
 if(!actorSub||!founderSub)throw Error('SERVER_IDENTITY_REQUIRED');
 const actor=supervisors.find(s=>s.sub===actorSub);
 const target=supervisors.find(s=>s.sub===targetSub);
 const activeAdmins=supervisors.filter(s=>admin(s)&&active(s));
 if(action==='bootstrap'){
  if(activeAdmins.length)throw Error('ACTIVE_SUPERVISOR_EXISTS');
  if(actorSub!==founderSub)throw Error('FOUNDER_ONLY_RECOVERY');
  return {allowed:true,operation:'activate_founder',requiresServerProof:true};
 }
 if(!actor||!admin(actor)||!active(actor))throw Error('ACTIVE_SUPERVISOR_REQUIRED');
 if(action==='invite'){
  if(!targetSub||target)throw Error('INVALID_NEW_SUPERVISOR');
  return {allowed:true,operation:'invite_supervisor',targetSub,requiresServerProof:true};
 }
 if(action==='activate'){
  if(!target||!admin(target)||target.status!=='pending')throw Error('INVALID_PENDING_SUPERVISOR');
  return {allowed:true,operation:'activate_supervisor',targetSub,requiresServerProof:true};
 }
 if(action==='deactivate'){
  if(!target||!admin(target)||!active(target))throw Error('INVALID_ACTIVE_SUPERVISOR');
  if(target.sub===founderSub)throw Error('FOUNDER_PROTECTED');
  if(activeAdmins.length<=1)throw Error('LAST_ACTIVE_SUPERVISOR');
  return {allowed:true,operation:'deactivate_supervisor',targetSub,requiresServerProof:true};
 }
 throw Error('UNSUPPORTED_ACTION');
}
// Server requirements: authenticated transactions, version checks, audit log,
// rate limits, notification to founder on every admin change, and explicit
// revocation of active sessions when deactivated. No client-only bootstrap.
