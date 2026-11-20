#!/usr/bin/env python3
"""Generate Noor 2.8.71 source ZIP from the tested 2.8.64 source archive.
Keeps the v2.8.65 card recognizer and original SCORM publisher; fixes only task-side card resolution."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.71-ClassCard-source.zip"

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
manifest["version"] = "2.8.71"
manifest["description"] = "Noor Unified 2.8.71: SCORM course card verification with original publisher and library navigation preserved."
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


# SCORM needs its verified course and the already displayed unit/lesson names,
# NOT a preparation tree or an uploaded reference. Preserve class-card paging,
# digital library navigation, and the existing publisher verbatim.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s,
    '    <label for="stnHubScormReference">مرجع الدرس من التحضير أو دليل المعلم</label>\n    <textarea id="stnHubScormReference" rows="4" maxlength="12000" placeholder="ألصق أهداف الدرس أو صفحاته عند الحاجة"></textarea>\n    <label for="stnHubScormReferenceFile">استيراد صفحات الدرس (PDF أو DOCX أو TXT)</label>\n    <input type="file" id="stnHubScormReferenceFile" accept=".pdf,.docx,.txt">\n',
    '',
    path)
s = replace_exact(s,
    "'stnHubScormScope','stnHubScormImageMode','stnHubScormReference','stnHubItemMode'",
    "'stnHubScormScope','stnHubScormImageMode','stnHubItemMode'",path)
s = replace_exact(s,
    "   if(taskService()==='scorm')$('stnHubScormReference').value='';\n",
    "",path)
start_handler=s.index("  $('stnHubScormReferenceFile').addEventListener('change',async event=>{")
end_handler=s.index("  $('stnHubActivityPause')?.addEventListener",start_handler)
if start_handler<0 or end_handler<0:
    sys.exit('Could not locate standalone SCORM reference file listener')
s=s[:start_handler]+s[end_handler:]

# No curriculum.start for an SCORM task. A single lesson needs only an
# explicitly selected numeric position and the titles already shown in Noor.
start_guard=s.index("   if(opts.service==='scorm'){",s.index(" async function generate(resumeId){"))
end_guard=s.index("   if(opts.service==='preparation'",start_guard)
if start_guard<0 or end_guard<0:
    sys.exit('SCORM pre-generation guard not found')
s=s[:start_guard]+"""   if(opts.service==='scorm'){
    if(!opts.unitNo||(!bulk&&!opts.lessonNo))
     throw Error('حدد ترتيب الوحدة والدرس أولًا.');
    if(bulk&&(!opts.proof?.unitId||!await orderedBranch(opts)))
     throw Error('لإنشاء جميع دروس الوحدة، تحقّق من دروس الوحدة أولًا.');
   }
"""+s[end_guard:]

# Keep the already-displayed verified lesson titles when the cached
# preparation tree is absent. No made-up title or preparation navigation.
start_scorm=s.index(" async function scorm(opts){")
end_scorm=s.index("  status('جارٍ إنشاء مغامرة SCORM عمانية",start_scorm)
if start_scorm<0 or end_scorm<0:
    sys.exit('SCORM generator not found')
s=s[:start_scorm]+""" async function scorm(opts){
  const epoch=operationEpoch;
  const branch=await orderedBranch(opts);
  const lesson=branch?lookup.lessonAt(branch,opts.lessonNo):null;
  const unitTitle=String(branch?.unit||$('stnHubUnitTitle').textContent||'').trim();
  const lessonTitle=String(lesson?.title||$('stnHubLessonTitle').textContent||'').trim();
  if(!unitTitle||!lessonTitle)
   throw Error('تعذّر قراءة عنوان الوحدة والدرس الظاهرين في الإضافة. أعد تحديد ترتيب الوحدة والدرس ولا تفتح شجرة التحضير.');
  const target={lessonId:lesson?.id||opts.proof?.lessonId||'',unit:unitTitle,title:lessonTitle};
  const reference={outcomes:[],objectives:'',concepts:'',practice:'',teacherText:''};
  if(lesson){
   const key=lessonReferenceKey(opts.course.cid,lesson.id);
   const saved=(await browser.storage.local.get(key))[key];
   reference.objectives=saved?.objectives||'';
   reference.concepts=saved?.concepts||'';
  }
  ensureOperation(epoch);
  opts.proof=lesson?lessonProof(branch,lesson):null;
  opts.unit=target.unit;opts.lesson=target.title;
"""+s[end_scorm:]
s = replace_exact(s,
    "await globalThis.NoorScormPublisher.start(file,{...opts,positionProof:opts.proof,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",
    "await globalThis.NoorScormPublisher.start(file,{...opts,positionProof:opts.proof,allowUnlinkedLesson:!opts.proof?.lessonId,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",
    path)
s = replace_exact(s,
    "    entry.reference=await scormReference(opts,{...entry,title:entry.lesson});",
    "    entry.reference={outcomes:[],objectives:'',concepts:'',practice:'',teacherText:''};",
    path)
files[path]=s.encode()

# Optional curriculum references should enrich generation, not prevent it.
path = "gemini-background.js"
s=files[path].decode()
s=replace_exact(s,
    "  if(!text(msg.lessonId,128)||!Object.values(reference).some(value=>value.length))\n   return {ok:false,error:'يتطلب توليد SCORM درسًا محددًا من شجرة نور ومرجعًا من أهدافه أو تحضيره أو دليل المعلم.'};\n",
    "",path)
s=replace_exact(s,
    "Ground every scored question in the learning outcomes, examples, skills, structures, and vocabulary taught in THIS lesson. The teacher-provided guide has priority, followed by visible Noor outcomes, then the approved preparation. Choose 1–4 measurable objectives supported by those references. A unit title or topic by itself is too broad. Exclude prerequisites that are not reviewed in the reference, material from adjacent lessons, above-grade terminology, and outside recall. Use only the relevant lesson section when the reference includes surrounding text.",
    "Use the verified subject, grade, unit and lesson titles. If optional reference content is present, prioritize its learning outcomes. If reference content is absent, create original self-contained practice based on the stated lesson topic and grade; supply any needed facts in the question itself, and NEVER claim to quote the textbook or invent hidden syllabus details. Choose 1–4 measurable objectives and avoid unrelated units, adjacent lessons and above-grade terminology.",
    path)
files[path]=s.encode()

# Regression checks: retain the original digital-library publisher exactly.
with ZipFile(sources[0]) as original:
    assert files["noor-scorm-publisher.js"]==original.read("noor-scorm-publisher.js")
assert "stnHubScormReference" not in files["noor-hub.js"].decode()
assert "await curriculum.start({...inputs(),cid:opts.course.cid,label:opts.course.label,purpose:'scorm'})" not in files["noor-hub.js"].decode()
assert "cards.next({label:j.label},3,REPOSITORY_ACTION)" in files["noor-scorm-publisher.js"].decode()

with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dest:
    for path,data in files.items():
        dest.writestr(path,data)
print(f"Generated {output} ({output.stat().st_size} bytes)")
