// Pure, non-mutating plan for verified email/Google-account relinking.
// This module NEVER grants access. Apply only in an authenticated backend transaction.
export function previewIdentityRelink({teachers=[],actorTeacherId,oldSub,newSub,newEmail,verifiedOld=false,verifiedNew=false}={}){
 if(!actorTeacherId||!oldSub||!newSub||oldSub===newSub)throw Error('INVALID_IDENTITIES');
 if(!verifiedOld||!verifiedNew)throw Error('BOTH_IDENTITIES_MUST_BE_VERIFIED');
 if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(String(newEmail||'')))throw Error('INVALID_EMAIL');
 const owner=teachers.find(t=>t.id===actorTeacherId);
 if(!owner||owner.sub!==oldSub)throw Error('OLD_ACCOUNT_MISMATCH');
 if(teachers.some(t=>t.id!==actorTeacherId&&(t.sub===newSub||String(t.email||'').toLowerCase()===newEmail.toLowerCase())))throw Error('TARGET_IDENTITY_ALREADY_ASSIGNED');
 return {ok:true,teacherId:owner.id,oldSub,newSub,newEmail:newEmail.toLowerCase(),
  preserve:['teacherId','roles','schoolId','classes','rosters','timetable','attendance','grades','historicalRecords'],
  revokeOldSessions:true,requiresBackendTransaction:true,requiresAudit:true,
  mutationPerformed:false};
}
// Backend MUST verify signed OIDC identity tokens for both accounts, ensure
// school scope and authorized consent, lock teacher and identity rows,
// check uniqueness and versions, update identity binding atomically,
// preserve all foreign keys, audit, revoke old sessions and provide rollback.
// A supervisor role alone cannot prove ownership of a second Google account.
