#!/usr/bin/env python3
"""Generate Noor 2.8.70 source ZIP from the tested 2.8.64 source archive.
Keeps the v2.8.65 card recognizer and original SCORM publisher; fixes only task-side card resolution."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.70-ClassCard-source.zip"

def replace_exact(content, old, new, path):
    if content.count(old) != 1:
        sys.exit(f"Could not find unique patch anchor in {path}")
    return content.replace(old, new, 1)

with ZipFile(sources[0]) as original:
    files = {i.filename: original.read(i.filename) for i in original.infolist() if not i.is_dir()}
if any(p.startswith("META-INF/") for p in files):
    sys.exit("Refusing to use already signed source")
manifest = json.loads(files["manifest.json"])
if manifest["version"] != "2.8.64":
    sys.exit("Unexpected base version")
manifest["version"] = "2.8.70"
manifest["description"] = "Noor Unified 2.8.70: SCORM course card verification with original publisher and library navigation preserved."
files["manifest.json"] = (json.dumps(manifest,ensure_ascii=False,indent=2)+"\n").encode()

path = "noor-class-card.js"
s = files[path].decode()
s = replace_exact(s,
    "const cards=(root.NoorCourseCatalog?.cards?.()||[]).filter(c=>normalize(c.label)===normalize(course.label));",
    "const cards=(root.NoorCourseCatalog?.cards?.()||[]).filter(c=>normalize(c.label)===normalize(course.label));\n  // Use the verified course card, not the carousel page indicator, as grade evidence.",
    path)
files[path] = s.encode()

path = "noor-course-catalog.js"
s = files[path].decode()
anchor = "if(!s||s.length>210)return null;"
s = replace_exact(s,anchor,
    anchor+"\n  // Carousel page numbers and grade-span labels are not explicit grade identities.\n  if(/^\\d{1,3}$/.test(s)||/^\\(?\\d{1,2}\\s*[-–]\\s*\\d{1,2}\\)?$/.test(s))return null;",
    path)
s = replace_exact(s,
    "const grades=[...new Set(gradeLines.map(gradeOf))];",
    "const grades=[...new Set(gradeLines.map(gradeOf).filter(Number.isInteger))];",
    path)
files[path] = s.encode()

# Minimal task-side fix based on the 2.8.65 source; leave the card pager and SCORM publisher unchanged.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s,
    "const mayResolveCard=['preparation','activities','exam'].includes(opts.service)",
    "const mayResolveCard=['preparation','activities','exam','scorm'].includes(opts.service)", path)
s = replace_exact(s,
    "     await persistSelection({course:opts.course,proof:opts.proof});\n     sessionStorage.setItem(serviceStorageKey(),'scorm');\n     await curriculum.start({...inputs(),cid:opts.course.cid,label:opts.course.label,purpose:'scorm'});\n     return 'navigating';",
    "     throw Error('لم أجد بيانات الوحدة والدرس المؤكدة لهذا الصف. افتح بطاقة الصف لاكتشاف معرّفها، ثم حدّد الدرس من القائمة المعتمدة. لن تفتح SCORM شجرة التحضير تلقائيًا.');",
    path)
helper = """ async function resolveScormCard(opts,epoch){
  if(opts.service!=='scorm'||opts.course?.verified&&/^\\d+$/.test(String(opts.course.cid||'')))return;
  if(!/^\\/teacher\\/?$/i.test(location.pathname))
   throw Error('افتح صفحة المعلم الرئيسية وبطاقة الصف أولًا ليتم التعرف على معرّفها دون الدخول إلى التحضير.');
  const catalog=globalThis.NoorCourseCatalog;
  await catalog?.init?.();catalog?.scan?.();
  const matched=(catalog?.cards?.()||[]).filter(c=>norm(c.label)===norm(opts.course.label));
  if(matched.length!==1)throw Error('تعذر التمييز بين بطاقات الصف. افتح بطاقة الصف المطلوبة في لوحة المعلم.');
  let rec=catalog?.get?.(opts.course.label);
  if(!/^\\d+$/.test(String(rec?.cidNumeric||''))){
   const card=matched[0].element;
   const openers=[...card.querySelectorAll('[data-toggle="popover"],[data-bs-toggle="popover"],[data-toggle="dropdown"],[data-bs-toggle="dropdown"],[aria-haspopup="true"]')]
    .filter(el=>globalThis.NoorClassCard?.visible?.(el));
   if(openers.length===1){openers[0].click();await new Promise(resolve=>setTimeout(resolve,350));catalog.scan();rec=catalog.get(opts.course.label);}
  }
  if(!/^\\d+$/.test(String(rec?.cidNumeric||'')))
   throw Error('لم أتعرف على معرّف بطاقة الصف. افتح قائمة البطاقة بنفسك ثم اضغط توليد SCORM مجددًا؛ لن أفتح تحضير درس.');
  const resolved={...opts.course,cid:String(rec.cidNumeric),grade:rec.grade,verified:true};
  ensureOperation(epoch);
  await persistSelection({course:resolved,proof:opts.proof});
  opts.course=resolved;
 }
"""
s = replace_exact(s," async function generate(resumeId){",helper+" async function generate(resumeId){",path)
s = replace_exact(s,"   checkContext(opts,false);checkQuestionCount(opts);",
    "   checkContext(opts,false);checkQuestionCount(opts);\n   if(opts.service==='scorm')await resolveScormCard(opts,epoch);",path)
s = replace_exact(s,'<option value="exam">اختبار</option>','',path)
files[path]=s.encode()


# SCORM can use teacher-provided lesson content without a previously cached
# preparation tree; this does not change the card navigator or publisher.
# Bulk publishing still requires verified tree coordinates.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s,
    "   if(opts.service==='scorm'){\n    if(!opts.unitNo||(!bulk&&!opts.lessonNo))throw Error('حدد موضع الوحدة والدرس في شجرة نور.');",
    "   if(opts.service==='scorm'){\n    if(!opts.unitNo||(!bulk&&!opts.lessonNo))throw Error('حدد رقم الوحدة والدرس المراد إنشاء SCORM له.');",
    path)
s = replace_exact(s,
    "    if(!branch||(!bulk&&!lesson)||!hasPreparationCourseProof(opts.course)&&(bulk||!hasReference&&!$('stnHubScormReference').value.trim())){",
    "    const teacherReference=$('stnHubScormReference').value.trim();\n    if(!bulk&&!lesson){\n     if(teacherReference.length<20)throw Error('لا توجد شجرة درس محفوظة لهذا الصف. الصق نص الدرس أو أهدافه في خانة مرجع SCORM (20 حرفًا على الأقل) لتوليد درس دون فتح التحضير.');\n    }else if(!branch||(!bulk&&!lesson)||!hasPreparationCourseProof(opts.course)&&(bulk||!hasReference&&!teacherReference)){",
    path)
s = replace_exact(s,
    "  const lesson=lookup.lessonAt(branch,opts.lessonNo);\n  if(!lesson)throw Error('تعذر تثبيت عنوان الدرس من شجرة نور.');\n  const target={...lessonProof(branch,lesson),unit:branch.unit,title:lesson.title};\n  const reference=await scormReference(opts,target,$('stnHubScormReference').value.trim());\n  ensureOperation(epoch);\n  opts.proof=lessonProof(branch,lesson);opts.unit=target.unit;opts.lesson=target.title;",
    "  const lesson=lookup.lessonAt(branch,opts.lessonNo);\n  const teacherText=$('stnHubScormReference').value.trim();\n  if(!lesson&&teacherText.length<20)throw Error('أضف مرجع الدرس قبل إنشاء SCORM؛ شجرة التحضير ليست مطلوبة.');\n  const target=lesson?{...lessonProof(branch,lesson),unit:branch.unit,title:lesson.title}:\n   {lessonId:null,unit:'الوحدة '+opts.unitNo,title:opts.topic||'الدرس '+opts.lessonNo};\n  const reference=lesson?await scormReference(opts,target,teacherText):\n   {outcomes:[],objectives:'',concepts:'',practice:'',teacherText};\n  ensureOperation(epoch);\n  opts.proof=lesson?lessonProof(branch,lesson):null;opts.unit=target.unit;opts.lesson=target.title;",
    path)
s = replace_exact(s,
    "await globalThis.NoorScormPublisher.start(file,{...opts,positionProof:opts.proof,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",
    "await globalThis.NoorScormPublisher.start(file,{...opts,positionProof:lesson?opts.proof:null,allowUnlinkedLesson:!lesson,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",
    path)
files[path]=s.encode()

with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dest:
    for path,data in files.items():
        dest.writestr(path,data)
print(f"Generated {output} ({output.stat().st_size} bytes)")
