// Pure timetable change preview. Authorization, persistence and audit must be server-side.
// No student records are handled by this module.
const priorities=new Set(['A','B','C','D']);
const slotKey=s=>[s.schoolId,s.teacherId,s.day,s.period].join('|');
export function validateSlot(s){
 if(!s||!['boys','girls'].includes(s.schoolId)||!s.teacherId||!Number.isInteger(s.day)||s.day<0||s.day>6||!Number.isInteger(s.period)||s.period<1)return 'INVALID_SLOT';
 if(s.kind==='reserve')return priorities.has(s.priority)?null:'INVALID_PRIORITY';
 if(s.kind==='lesson')return s.classId&&s.subject?null:'INCOMPLETE_LESSON';
 return 'INVALID_KIND';
}
export function previewTimetableChange({current=[],incoming=[],scope,schoolId,teacherId}){
 if(!['school','teacher','slot'].includes(scope))throw Error('INVALID_SCOPE');
 if(!['boys','girls'].includes(schoolId))throw Error('INVALID_SCHOOL');
 if(scope!=='school'&&!teacherId)throw Error('TEACHER_REQUIRED');
 const belongs=s=>s.schoolId===schoolId&&(scope==='school'||s.teacherId===teacherId);
 if(incoming.some(s=>!belongs(s)||validateSlot(s)))throw Error('INVALID_INCOMING_SLOTS');
 if(current.some(s=>validateSlot(s)))throw Error('INVALID_EXISTING_SLOTS');
 const duplicates=new Set();
 for(const s of incoming){const k=slotKey(s);if(duplicates.has(k))throw Error('DUPLICATE_SLOT');duplicates.add(k)}
 if(scope==='slot'&&incoming.length!==1)throw Error('ONE_SLOT_REQUIRED');
 const replaced=scope==='slot'?current.filter(s=>slotKey(s)===slotKey(incoming[0])):current.filter(belongs);
 const keep=scope==='slot'?current.filter(s=>slotKey(s)!==slotKey(incoming[0])):current.filter(s=>!belongs(s));
 const next=[...keep,...incoming];
 const keys=new Set();
 for(const s of next){const k=slotKey(s);if(keys.has(k))throw Error('DUPLICATE_FINAL_SLOT');keys.add(k)}
 const added=incoming.filter(s=>!replaced.some(old=>slotKey(old)===slotKey(s)));
 const removed=replaced.filter(old=>!incoming.some(s=>slotKey(s)===slotKey(old)));
 const changed=incoming.filter(s=>replaced.some(old=>slotKey(old)===slotKey(s)&&JSON.stringify(old)!==JSON.stringify(s)));
 return {next,summary:{added:added.length,removed:removed.length,changed:changed.length,untouched:keep.length},requiresReplan:[...new Set([...replaced,...incoming].map(s=>s.day))]};
}
// The server must: verify supervisor role; check version precondition; atomically
// save new timetable and audit log; recalculate affected reserve assignments;
// queue cancellation/update/new notification events AFTER successful commit.
// Do not silently overwrite already activated assignments.
