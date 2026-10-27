// Pure preview for supervisor-directed teacher retirement and timetable transfer.
// No mutation, authorization, student-data migration or notifications here.
import {validateSlot} from './timetable-change.mjs';
const key=s=>[s.schoolId,s.teacherId,s.day,s.period].join('|');
export function previewTeacherTransfer({teachers=[],slots=[],sourceTeacherId,targetTeacherId,schoolId,mode='reject-conflicts'}={}){
 if(!sourceTeacherId||!targetTeacherId||sourceTeacherId===targetTeacherId)throw Error('DISTINCT_TEACHERS_REQUIRED');
 if(!['boys','girls'].includes(schoolId))throw Error('INVALID_SCHOOL');
 if(mode!=='reject-conflicts')throw Error('UNSUPPORTED_CONFLICT_POLICY');
 const source=teachers.find(t=>t.id===sourceTeacherId);
 const target=teachers.find(t=>t.id===targetTeacherId);
 if(!source||!target||source.schoolId!==schoolId||target.schoolId!==schoolId)throw Error('TEACHER_SCHOOL_MISMATCH');
 if(source.status==='retired'||target.status==='retired'||target.status==='suspended')throw Error('INACTIVE_TEACHER');
 if(slots.some(s=>validateSlot(s)))throw Error('INVALID_TIMETABLE');
 const from=slots.filter(s=>s.schoolId===schoolId&&s.teacherId===sourceTeacherId);
 const occupied=new Set(slots.filter(s=>s.schoolId===schoolId&&s.teacherId===targetTeacherId).map(key));
 const transferred=from.map(s=>({...s,teacherId:targetTeacherId}));
 const conflicts=transferred.filter(s=>occupied.has(key(s)));
 if(conflicts.length)return {ok:false,conflicts:conflicts.map(s=>({day:s.day,period:s.period,kind:s.kind})),transferred:[],nextSlots:null};
 const nextSlots=[...slots.filter(s=>!(s.schoolId===schoolId&&s.teacherId===sourceTeacherId)),...transferred];
 const targetAfter=nextSlots.filter(s=>s.schoolId===schoolId&&s.teacherId===targetTeacherId);
 const duplicates=new Set();
 for(const s of targetAfter){const k=key(s);if(duplicates.has(k))throw Error('DUPLICATE_TARGET_SLOT');duplicates.add(k)}
 return {ok:true,conflicts:[],transferred, nextSlots,
  teacherChange:{teacherId:sourceTeacherId,schoolId,status:'retired',accountAccess:'revoke'},
  affectedDays:[...new Set(from.map(s=>s.day))].sort((a,b)=>a-b),
  requiresReplan:true,requiresNotification:true,
  historicalRecordsPolicy:'retain_original_teacher_and_audit',
  studentRecordsPolicy:'no_automatic_reassignment_without_class_ownership_validation'};
}
// Server-side activation requirements:
// 1. Verify supervisor identity and school scope.
// 2. Re-check conflicts and roster versions in one transaction.
// 3. Revoke retired teacher access immediately; preserve historic attribution.
// 4. Reassign class ownership only after checking shared teaching assignments.
// 5. Recompute current/future substitution assignments, notify affected teachers.
// 6. Keep audit trail, prior timetable snapshot and rollback mechanism.
