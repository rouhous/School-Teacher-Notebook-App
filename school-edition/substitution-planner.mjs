// School edition: substitution planning only. No database writes or notifications.
// Input: lessons [{id,date,period,teacherId,schoolId,classId,subject}]
// reserveSlots [{teacherId,date,period,schoolId,priority:'A'|'B'|'C'|'D'}]
// absences [{teacherId,date,periods?:number[]}] (omitted periods = full day)
// existingAssignments [{date,period,substituteTeacherId,originalLessonId}]
const rank={A:0,B:1,C:2,D:3};
const key=(d,p,t)=>[d,p,t].join('|');
export function planSubstitutions({lessons=[],reserveSlots=[],absences=[],existingAssignments=[]}={}){
 const isAbsent=(teacherId,date,period)=>absences.some(a=>a.teacherId===teacherId&&a.date===date&&(!Array.isArray(a.periods)||a.periods.includes(period)));
 // Resolve all absences first. An absent teacher can never be a substitute,
 // even if the teacher has an A reserve slot or a previous assignment.
 const absentSlotKeys=new Set();
 for(const a of absences){
  const periods=Array.isArray(a.periods)?a.periods:[...new Set([...lessons,...reserveSlots].filter(x=>x.date===a.date).map(x=>x.period))];
  for(const period of periods)absentSlotKeys.add(key(a.date,period,a.teacherId));
 }
 const occupied=new Set(lessons.filter(l=>!isAbsent(l.teacherId,l.date,l.period)).map(l=>key(l.date,l.period,l.teacherId)));
 for(const a of existingAssignments)occupied.add(key(a.date,a.period,a.substituteTeacherId));
 const workloads=new Map();
 for(const a of existingAssignments)workloads.set(a.substituteTeacherId,(workloads.get(a.substituteTeacherId)||0)+1);
 const assignments=[],uncovered=[];
 const missing=lessons.filter(l=>isAbsent(l.teacherId,l.date,l.period)&&!existingAssignments.some(a=>a.originalLessonId===l.id));
 missing.sort((a,b)=>a.date.localeCompare(b.date)||a.period-b.period||String(a.id).localeCompare(String(b.id)));
 for(const lesson of missing){
  const candidates=reserveSlots.filter(s=>s.date===lesson.date&&s.period===lesson.period&&s.schoolId===lesson.schoolId&&Object.hasOwn(rank,s.priority)&&s.teacherId!==lesson.teacherId&&!absentSlotKeys.has(key(s.date,s.period,s.teacherId))&&!isAbsent(s.teacherId,s.date,s.period)&&!occupied.has(key(s.date,s.period,s.teacherId)));
  candidates.sort((a,b)=>rank[a.priority]-rank[b.priority]||(workloads.get(a.teacherId)||0)-(workloads.get(b.teacherId)||0)||String(a.teacherId).localeCompare(String(b.teacherId)));
  const pick=candidates[0];
  if(!pick){uncovered.push({originalLessonId:lesson.id,date:lesson.date,period:lesson.period,schoolId:lesson.schoolId,classId:lesson.classId,reason:'NO_AVAILABLE_RESERVE'});continue;}
  assignments.push({originalLessonId:lesson.id,date:lesson.date,period:lesson.period,schoolId:lesson.schoolId,classId:lesson.classId,subject:lesson.subject,originalTeacherId:lesson.teacherId,substituteTeacherId:pick.teacherId,priority:pick.priority,status:'proposed'});
  occupied.add(key(pick.date,pick.period,pick.teacherId));
  workloads.set(pick.teacherId,(workloads.get(pick.teacherId)||0)+1);
 }
 return {assignments,uncovered};
}
// Proposed assignments must be validated and committed atomically by the
// authenticated backend before notifications are queued. Never send push from
// this module, never store student information in GitHub, and never treat a
// local proposal as a confirmed assignment.
