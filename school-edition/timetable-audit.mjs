// Read-only timetable integrity checks before supervisor commits changes.
// Day 0=Sunday; periods are positive integers.
import {validateSlot} from './timetable-change.mjs';
const key=(...x)=>x.join('|');
export function auditTimetable(slots=[],teachers=[]){
 const errors=[],warnings=[];
 const teacherIds=new Map(teachers.map(t=>[key(t.schoolId,t.id),t]));
 const teacherPeriods=new Map(),classPeriods=new Map();
 for(let i=0;i<slots.length;i++){
  const s=slots[i],invalid=validateSlot(s);
  if(invalid){errors.push({code:invalid,index:i});continue}
  const teacher=teacherIds.get(key(s.schoolId,s.teacherId));
  if(!teacher)errors.push({code:'UNKNOWN_TEACHER',index:i});
  else if(teacher.status==='retired'||teacher.status==='suspended')errors.push({code:'INACTIVE_TEACHER',index:i});
  const tKey=key(s.schoolId,s.teacherId,s.day,s.period);
  if(teacherPeriods.has(tKey))errors.push({code:'TEACHER_DOUBLE_BOOKED',index:i,otherIndex:teacherPeriods.get(tKey)});
  else teacherPeriods.set(tKey,i);
  if(s.kind==='lesson'){
   const cKey=key(s.schoolId,s.classId,s.day,s.period);
   if(classPeriods.has(cKey))errors.push({code:'CLASS_DOUBLE_BOOKED',index:i,otherIndex:classPeriods.get(cKey)});
   else classPeriods.set(cKey,i);
  }
 }
 const schools=new Set(slots.map(s=>s.schoolId));
 if(schools.size>1)warnings.push({code:'MULTI_SCHOOL_DATASET'});
 return {ok:errors.length===0,errors,warnings,slotCount:slots.length};
}
// This audit is advisory; the server must revalidate on the committed version.
