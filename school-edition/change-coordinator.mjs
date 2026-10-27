// Version-aware, read-only supervisor change preparation.
// This module never authenticates users or commits writes.
import {previewTimetableChange} from './timetable-change.mjs';
import {previewTeacherTransfer} from './teacher-transfer.mjs';
import {auditTimetable} from './timetable-audit.mjs';
const stable=s=>JSON.stringify(s);
export function prepareSchoolChange({snapshot,request}={}){
 if(!snapshot||!Number.isInteger(snapshot.version)||snapshot.version<0||!Array.isArray(snapshot.slots)||!Array.isArray(snapshot.teachers))throw Error('INVALID_SNAPSHOT');
 if(!request||request.expectedVersion!==snapshot.version)throw Error('STALE_VERSION');
 let slots,details;
 if(request.type==='timetable'){
  const p=previewTimetableChange({current:snapshot.slots,incoming:request.incoming,scope:request.scope,schoolId:request.schoolId,teacherId:request.teacherId});
  slots=p.next;details=p.summary;
 }else if(request.type==='teacher-transfer'){
  const p=previewTeacherTransfer({teachers:snapshot.teachers,slots:snapshot.slots,sourceTeacherId:request.sourceTeacherId,targetTeacherId:request.targetTeacherId,schoolId:request.schoolId});
  if(!p.ok)return {ok:false,reason:'TRANSFER_CONFLICT',conflicts:p.conflicts};
  slots=p.nextSlots;details={transferred:p.transferred.length,retireTeacherId:request.sourceTeacherId};
 }else throw Error('INVALID_CHANGE_TYPE');
 const audit=auditTimetable(slots,snapshot.teachers);
 // A retired teacher no longer has timetable slots, and must remain in the
 // audit roster until server-side retirement is committed.
 if(!audit.ok)return {ok:false,reason:'TIMETABLE_CONFLICT',errors:audit.errors};
 if(stable(slots)===stable(snapshot.slots))return {ok:true,noChange:true,expectedVersion:snapshot.version};
 return {ok:true,noChange:false,expectedVersion:snapshot.version,nextVersion:snapshot.version+1,proposedSlots:slots,details,
  commitRequirements:['authenticated_supervisor','atomic_compare_and_swap','audit_log','replan_active_substitutions','notification_outbox']};
}
// This is a preview contract. The backend must re-run all checks in one
// authenticated transaction and must never trust a browser-supplied snapshot.
