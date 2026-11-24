#!/usr/bin/env python3
# [release-noor] 2.8.108 corrected selection-dock row selector
"""Generate Noor 2.8.97 lesson-grounded activity generation and compact inline-field teacher panel.
Keeps the v2.8.65 card recognizer and original SCORM publisher; fixes only task-side card resolution."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.110-TeacherWorkspace-source.zip"

def replace_exact(content, old, new, path):
    if content.count(old) != 1:
        sys.exit(f"Could not find unique patch anchor in {path}: {repr(old[:125])}; count={content.count(old)}")
    return content.replace(old, new, 1)

with ZipFile(sources[0]) as original:
    files = {i.filename: original.read(i.filename) for i in original.infolist() if not i.is_dir()}
base_scorm_publisher = files["noor-scorm-publisher.js"]
if any(p.startswith("META-INF/") for p in files):
    sys.exit("Refusing to use already signed source")
manifest = json.loads(files["manifest.json"])
if manifest["version"] != "2.8.64":
    sys.exit("Unexpected base version")
manifest["version"] = "2.8.110"
manifest["name"] = "دفتر نور | المساعد الذكي لدفتر المعلم المدرسي"
manifest["description"] = "دفتر نور: مساحة عمل متجاوبة للتحضير والأنشطة والدروس التفاعلية والتكامل مع دفتر المعلم المدرسي."
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
  // The SCORM publisher owns page 3, library and lesson-tree navigation.
  // Card identification must not depend on a fixed URL or a literal label.
  const catalog=globalThis.NoorCourseCatalog;
  await catalog?.init?.();catalog?.scan?.();
  const allCards=catalog?.cards?.()||[];
  const labelMatches=allCards.filter(c=>norm(c.label)===norm(opts.course.label));
  const selectedGrade=Number(opts.course.grade);
  const gradeMatches=Number.isInteger(selectedGrade)&&selectedGrade>=1&&selectedGrade<=12
   ?allCards.filter(c=>Number(c.grade)===selectedGrade):[];
  const matched=labelMatches.length===1?labelMatches:gradeMatches.length===1?gradeMatches:[];
  if(matched.length!==1)throw Error('تعذر تحديد بطاقة الصف بشكل فريد. افتح لوحة المعلم وتحقق من بطاقة الصف المختارة قبل توليد SCORM.');
  let rec=catalog?.get?.(matched[0].label);
  if(!/^\\d+$/.test(String(rec?.cidNumeric||''))){
   const card=matched[0].element;
   const openers=[...card.querySelectorAll('[data-toggle="popover"],[data-bs-toggle="popover"],[data-toggle="dropdown"],[data-bs-toggle="dropdown"],[aria-haspopup="true"]')]
    .filter(el=>globalThis.NoorClassCard?.visible?.(el));
   if(openers.length===1){openers[0].click();await new Promise(resolve=>setTimeout(resolve,350));catalog.scan();rec=catalog.get(matched[0].label);}
  }
  if(!/^\\d+$/.test(String(rec?.cidNumeric||'')))
   throw Error('لم أتعرف على معرّف بطاقة الصف. افتح قائمة البطاقة بنفسك ثم اضغط توليد SCORM مجددًا؛ لن أفتح تحضير درس.');
  const resolved={...opts.course,label:matched[0].label,cid:String(rec.cidNumeric),grade:rec.grade||opts.course.grade,verified:true};
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


# Reuse the exact card opener from the successful preparation/activity transfer.
# On the first SCORM pass, OPEN the selected course card BEFORE page 3 discovery.
# If a Noor UI animation ignores the opener click, retry once using the card
# surface. Never press another course's tile or pick an ambiguous course.
path = "noor-class-card.js"
s = files[path].decode()
s = replace_exact(s,
    " function next(course,page,match,createForScope){",
    """ function openControl(card){
  if(!card)return null;
  return card.querySelector('[data-toggle="popover"],[data-bs-toggle="popover"],button[type="button"]')||card;
 }
 function courseCard(course){
  const catalog=root.NoorCourseCatalog;
  const cards=catalog?.cards?.()||[];
  const matchLabel=c=>normalize(c.label)===normalize(course.label);
  const exact=cards.filter(matchLabel);
  if(exact.length===1)return exact[0];
  if(exact.length>1)return null;
  const byCid=/^\\d+$/.test(String(course.cid||''))
   ?cards.filter(c=>String(catalog?.get?.(c.label)?.cidNumeric||'')===String(course.cid)):[];
  if(byCid.length===1)return byCid[0];
  if(byCid.length>1)return null;
  const grade=Number(course.grade);
  const subject=catalog?.subjectOf?.(course.label);
  const byClass=Number.isInteger(grade)&&grade>=1&&grade<=12&&subject
   ?cards.filter(c=>catalog.gradeOf(c.label)===grade&&catalog.subjectOf(c.label)===subject):[];
  return byClass.length===1?byClass[0]:null;
 }
 function next(course,page,match,createForScope){""",path)
s = replace_exact(s,
    "  const cards=(root.NoorCourseCatalog?.cards?.()||[]).filter(c=>normalize(c.label)===normalize(course.label));\n  // Use the verified course card, not the carousel page indicator, as grade evidence.\n  if(cards.length!==1)return null;\n  const card=cards[0].element;",
    "  const matched=courseCard(course);\n  if(!matched)return null;\n  const card=matched.element;",path)
s = replace_exact(s,
    "  let scopes=[card];\n  if(opened?.card===card){",
    """  // Course card must be explicitly opened before inspecting its page-3 pager.
  if(opened?.card!==card){
   opened={card,previous:new Map(popovers().map(el=>[el,normalize(el.textContent)])),retry:0};
   const opener=openControl(card);
   if(opener)return {element:opener,step:'open'};
  }
  let scopes=[card];
  if(opened?.card===card){""",path)
s = replace_exact(s,
    "  if(opened?.card===card)return null;\n  opened={card,previous:new Map(popovers().map(el=>[el,normalize(el.textContent)]))};\n  return {element:card.querySelector('[data-toggle=\"popover\"],[data-bs-toggle=\"popover\"],[data-toggle=\"dropdown\"],[data-bs-toggle=\"dropdown\"],[aria-haspopup],button[type=\"button\"],[role=\"button\"]')||card,step:'open'};",
    """  // The control used by preparation/activity may do nothing on some Noor
  // layouts. Retry the same selected tile itself once before pausing.
  if(opened?.card===card&&opened.retry===0&&openControl(card)!==card){
   opened.retry=1;
   return {element:card,step:'open'};
  }
  return null;""",path)
s = replace_exact(s,
    "root.NoorClassCard=Object.freeze({action,next,safeClick,visible,normalize,isHome:",
    "root.NoorClassCard=Object.freeze({action,next,openControl,safeClick,visible,normalize,isHome:",path)
files[path]=s.encode()

path = "noor-scorm-publisher.js"
s = files[path].decode()
s = replace_exact(s,
   "const action=cards.next({label:j.label},3,REPOSITORY_ACTION);",
   "const action=cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION);",path)
s = replace_exact(s,
   "return takeNavigation(j,action.element,action.step==='feature'?'المكتبة الرقمية':'صفحة بطاقة الصف '+attempts);",
   "return takeNavigation(j,action.element,action.step==='feature'?'المكتبة الرقمية':action.step==='open'?'فتح بطاقة الصف '+j.grade+' - محاولة '+attempts:'الانتقال للصفحة الثالثة - خطوة '+attempts);",path)
files[path]=s.encode()

# Regression checks: preparation and activity routes remain intact; SCORM uses
# their card-opening control before attempting navigation to the third page.
assert "function openControl(card)" in files["noor-class-card.js"].decode()
assert "const opener=openControl(card)" in files["noor-class-card.js"].decode()
assert "cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION)" in files["noor-scorm-publisher.js"].decode()
assert "return location.origin+url+encodeURIComponent(opts.course.cid)" in files["noor-hub.js"].decode()
assert "stnHubScormReference" not in files["noor-hub.js"].decode()


# Combined activity / SCORM UI: two explicit actions, one selected course.
# Internally preserve the separate job types and existing generation pipelines.
path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
  '<option value="activities">نشاط</option><option value="scorm">SCORM</option>',
  '<option value="activities">نشاط / SCORM</option><option value="scorm" hidden>نشاط / SCORM</option>',path)
s=replace_exact(s,
  '<button id="stnHubGenerate" type="button" class="stnBtn stnGenerateMini">✨ توليد باستخدام Gemini</button>',
  '<button id="stnHubGenerate" type="button" class="stnBtn stnGenerateMini">✨ توليد باستخدام Gemini</button><button id="stnHubGenerateOther" type="button" class="stnBtn outline" hidden>توليد SCORM</button>',path)
s=replace_exact(s,
  "  $('stnHubScormOptions').hidden=s!=='scorm';",
  """  $('stnHubScormOptions').hidden=s!=='scorm';
  $('stnHubGenerateOther').hidden=!['activities','scorm'].includes(s);
  if(s==='activities'){$('stnHubGenerate').textContent='✨ توليد نشاط';$('stnHubGenerateOther').textContent='✨ توليد SCORM';}
  if(s==='scorm'){$('stnHubGenerate').textContent='✨ توليد SCORM';$('stnHubGenerateOther').textContent='✨ توليد نشاط';}""",path)
# The generate label is overwritten later in showStatus, so update that late assignment.
s=replace_exact(s,
  "  if(s!=='grades')$('stnHubGenerate').textContent=s==='preparation'?(prepSaveMode()==='auto'?'✨ توليد التحضير وحفظه تلقائيًا':'✨ توليد التحضير للمراجعة'):'✨ توليد باستخدام Gemini';",
  "  if(s!=='grades')$('stnHubGenerate').textContent=s==='preparation'?(prepSaveMode()==='auto'?'✨ توليد التحضير وحفظه تلقائيًا':'✨ توليد التحضير للمراجعة'):s==='activities'?'✨ توليد نشاط':s==='scorm'?'✨ توليد SCORM':'✨ توليد باستخدام Gemini';",path)
s=replace_exact(s,
  "  $('stnHubGenerate').addEventListener('click',()=>generate().catch(error=>actionStatus('تعذر بدء التوليد: '+String(error.message||error))));",
  """  $('stnHubGenerate').addEventListener('click',()=>generate().catch(error=>actionStatus('تعذر بدء التوليد: '+String(error.message||error))));
  $('stnHubGenerateOther').addEventListener('click',async()=>{
   if(actionBlocked()||!['activities','scorm'].includes(taskService()))return;
   const course=selected();
   const target=taskService()==='activities'?'scorm':'activities';
   try{
    if(!course.course||!course.unitNo||!course.lessonNo)throw Error('حدد الصف والوحدة والدرس قبل التوليد.');
    await persistSelection({course:course.course,proof:course.proof,task:target});
    $('stnHubService').value=target;
    sessionStorage.setItem(serviceStorageKey(),target);
    await switchTask(target);
    await generate();
   }catch(e){actionStatus('تعذر بدء التوليد: '+String(e.message||e));}
  });""",path)
# Both services now share the activity's exact verified course-card opener.
s=replace_exact(s,
  """       const card=cards[0].element;
       const control=card?.querySelector('[data-toggle="popover"],[data-bs-toggle="popover"],button[type="button"]')||card;
       if(control){openedCard=true;control.click();}""",
  """       const control=globalThis.NoorClassCard?.activityCourseOpener?.(p.course)||cards[0].element;
       if(control){openedCard=true;control.click();}""",path)
files[path]=s.encode()

path="noor-class-card.js"
s=files[path].decode()
s=replace_exact(s,
    "root.NoorClassCard=Object.freeze({action,next,openControl,safeClick,visible,normalize,isHome:",
    """function activityCourseOpener(course){
  const matched=courseCard(course);
  return matched?openControl(matched.element):null;
 }
 root.NoorClassCard=Object.freeze({action,next,openControl,activityCourseOpener,safeClick,visible,normalize,isHome:""",path)
files[path]=s.encode()

# Prefer an official link discovered when a teacher previously opened the same
# digital library. This is the activity/preparation CID-based routing principle;
# NEVER guess a Noor URL or trust a link from a different course.
path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
  """  if(cards&&isCourseHome()&&j.step!=='المكتبة الرقمية'){
   const action=cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION);""",
  """  if(cards&&isCourseHome()&&j.step!=='المكتبة الرقمية'){
   const record=root.NoorCourseCatalog?.get?.(j.cid);
   const registered=record?.routes?.scorm;
   if(record?.cidNumeric===j.cid&&norm(record.label)===norm(j.label)&&registered){
    let link;try{link=new URL(registered,location.href)}catch(_){}
    if(link?.origin===location.origin&&
      /^\\/teacher\\/attachments\\/index\\/scorm(?:\\/|$)/i.test(link.pathname)&&
      link.pathname.match(/\\/cid:(\\d+)/i)?.[1]===j.cid){
     set({...j,step:'الدروس التفاعلية',phase:'route'});
     notice('جارٍ فتح رابط الدروس التفاعلية الموثق لنفس الصف…');
     location.assign(link.href);return true;
    }
   }
   const action=cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION);""",path)
files[path]=s.encode()

assert "stnHubGenerateOther" in files["noor-hub.js"].decode()
assert "activityCourseOpener?.(p.course)" in files["noor-hub.js"].decode()
assert "activityCourseOpener" in files["noor-class-card.js"].decode()
assert "record?.routes?.scorm" in files["noor-scorm-publisher.js"].decode()


# Fix the ACTUAL SCORM entry point: do not let cards.next(page=3)
# guess a feature or pager before the selected tile has been opened.
# The selected tile (not its first arbitrary child button) gets clicked,
# and we require visible menu/pager evidence before stepping forward.
path="noor-scorm-publisher.js"
s=files[path].decode()
a=s.index("  const cards=root.NoorClassCard;",s.index(" function pickNav(j){"))
b=s.index("  const headings=pageHeaders();",a)
if a<0 or b<0:sys.exit("No SCORM card-navigation section found")
s=s[:a]+"""  const cards=root.NoorClassCard;
  if(cards&&isCourseHome()&&j.step!=='المكتبة الرقمية'){
   const catalog=root.NoorCourseCatalog;
   const record=catalog?.get?.(j.cid);
   // Prefer an existing course-specific link recorded from the teacher's own
   // prior navigation. No fabricated URLs and no cross-course shortcuts.
   const registered=record?.routes?.scorm;
   if(record?.cidNumeric===j.cid&&norm(record.label)===norm(j.label)&&registered){
    let link;try{link=new URL(registered,location.href)}catch(_){}
    const routeCid=link?.pathname?.split('/').find(part=>part.startsWith('cid:'))?.slice(4);
    if(link?.origin===location.origin&&
       link.pathname.toLowerCase().startsWith('/teacher/attachments/index/scorm')&&
       routeCid===j.cid){
      j.phase='route';j.step='الدروس التفاعلية';set(j);
      notice('جارٍ فتح رابط الدروس التفاعلية المعتمد للصف '+j.grade+'…');
      location.assign(link.href);return true;
    }
   }
   const found=(catalog?.cards?.()||[]).filter(c=>norm(c.label)===norm(j.label));
   if(found.length!==1)throw Error('لم أعثر على بطاقة واحدة مطابقة للصف '+j.grade+' والمادة '+j.subject+' على لوحة المعلم.');
   const tile=found[0].element;
   // Noor course tiles are two-sided flip cards (confirmed from teacher video).
   // The back face is *inside* the card, not an external popover.
   const insideHit=el=>{
    if(!el||!visible(el))return false;
    const r=el.getBoundingClientRect();
    if(!r.width||!r.height)return false;
    const hit=document.elementFromPoint(r.left+r.width/2,r.top+r.height/2);
    return Boolean(hit&&(el===hit||el.contains(hit))&&!inHub(hit));
   };
   const pagerElements=[...tile.querySelectorAll('a,button,[role="button"],[role="tab"],[data-slide-to],[data-bs-slide-to],[data-page]')];
   const numericPagers=pagerElements.filter(el=>/^[1-5١-٥]$/.test(String(el.innerText||el.textContent||'').trim())&&insideHit(el));
   const backPanel=tile.querySelector('[class*="flip-card-back"],[class*="card-back"],[class*="back-side"],[class*="backface"]');
   const flippedInner=tile.querySelector('[class*="flip-card-inner"],[class*="card-inner"]');
   const transform=flippedInner?getComputedStyle(flippedInner).transform:'';
   const rotated=/^matrix3d\(/.test(transform)&&Number(transform.slice(9).split(',')[0])<-.5||
    /^matrix\(/.test(transform)&&Number(transform.slice(7).split(',')[0])<-.5;
   const hitBack=Boolean(backPanel&&insideHit(backPanel));
   const backOpen=(numericPagers.length>=2||hitBack||rotated);
   // Don't hide a course's own page controls under the hub's detection logic.
   const directFeature=cards.action(tile,REPOSITORY_ACTION);
   if(backOpen&&directFeature)return takeNavigation(j,directFeature,'المكتبة الرقمية');
   if(!backOpen){
    const attempts=j.cardOpenAttempts||0;
    if(attempts>=3)throw Error('لم تنفتح بطاقة الصف '+j.grade+' بعد 3 محاولات. تحققنا من الوجه الخلفي وأزرار 1-5، ولم نظهرها. لا تضغط استكمال إلا بعد فتح البطاقة يدويًا.');
    const rect=tile.getBoundingClientRect();
    // Click the visible FRONT face at the actual on-screen hit target.
    // A parent tile.click() does not target Noor's nested flip handler.
    const front=tile.querySelector('[class*="flip-card-front"],[class*="card-front"],[class*="front-side"]');
    const box=(front?.getBoundingClientRect()?.width&&front.getBoundingClientRect().height)?front.getBoundingClientRect():rect;
    const hit=document.elementFromPoint(box.left+box.width*.5,box.top+box.height*.48);
    const target=hit&&tile.contains(hit)&&!inHub(hit)?hit:front||tile;
    if(!target||!tile.contains(target))throw Error('تعذر تحديد وجه بطاقة الصف للنقر.');
    j.cardOpenAttempts=attempts+1;
    j.phase='route';j.step='فتح بطاقة الصف';set(j);
    notice('فتح وجه بطاقة الصف '+j.grade+' — محاولة '+j.cardOpenAttempts+' من 3 (التحقق من انقلاب البطاقة)…');
    target.click();
    waitingSince=0;
    scheduleAdvance(j,1250);
    return true;
   }
   // A real flipped back face has appeared; never toggle this tile again.
   if(j.cardOpenAttempts){j.cardOpenAttempts=0;set(j);}
   // Once an actual course menu is visible, page-3 selection is safe.
   const action=cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION);
   if(!action)return false;
   const tries=(j.cardAttempts||0)+1;
   if(tries>9)throw Error('ظهرت بطاقة الصف، لكن تعذر الوصول إلى صفحة المكتبة الرقمية بعد تسع خطوات.');
   j.cardAttempts=tries;
   return takeNavigation(j,action.element,action.step==='feature'?'المكتبة الرقمية':'الصفحة الثالثة من بطاقة الصف '+j.grade+' - خطوة '+tries);
  }
""" +s[b:]
# Eliminate duplicate original block if replacement includes existing later block? b is headings, safe.
files[path]=s.encode()
assert "target.click();" in files["noor-scorm-publisher.js"].decode()
assert "cardOpenAttempts" in files["noor-scorm-publisher.js"].decode()
assert "const backOpen=" in files["noor-scorm-publisher.js"].decode()

assert "numericPagers.length>=2||hitBack||rotated" in files["noor-scorm-publisher.js"].decode()

# DIRECT SCORM route pilot. The teacher pastes the official full "Add new
# interactive lesson" URL for the selected course. Do not hardcode any user's
# CID/tid/tuid or fabricate an opaque ID from a numeric homework CID.
# Saved links are teacher+course scoped and can be reused on subsequent runs.
path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 "  <div id=\"stnHubScormOptions\" hidden>",
 """  <div id="stnHubScormOptions" hidden>
    <label for="stnHubScormDirectUrl">رابط «إضافة درس تفاعلي جديد» المباشر (اختبار للصف المحدد)</label>
    <input type="url" id="stnHubScormDirectUrl" dir="ltr" autocomplete="off" placeholder="https://lms.moe.gov.om/teacher/attachments/upload/Scorm/cid:…/tid:…/tuid:…">
    <p class="stnNote">ألصق الرابط الرسمي الذي فتحته من حسابك للصف المحدد. يُحفظ على جهاز المعلم لهذا المساق فقط، ولا يُستخدم لصف آخر. عند غياب الرابط يستمر مسار نور المعتاد.</p>""",path)
# The service UI reloads on task switches. Keep this field out of generic
# task settings to avoid transferring it to another course.
s=replace_exact(s,
 " async function scorm(opts){",
 """ function validDirectScormUrl(raw){
  try{
   const u=new URL(String(raw||'').trim(),location.href);
   if(u.origin!==location.origin||u.search||u.hash)return null;
   const m=u.pathname.match(/^\\/teacher\\/attachments\\/upload\\/Scorm\\/cid:([A-Za-z0-9_-]+)\\/tid:([A-Za-z0-9_-]+)\\/tuid:([A-Za-z0-9_-]+)\\/?$/i);
   if(!m)return null;
   return {url:u.href,opaqueCid:m[1],tid:m[2],tuid:m[3]};
  }catch(_){return null}
 }
 async function scormDirectLink(opts){
  const input=$('stnHubScormDirectUrl');
  const course=opts.course;
  const key='stnScormDirectLink:v1:'+classTeacherId+':'+course.cid;
  const stored=(await browser.storage.local.get(key))[key];
  const raw=String(input.value||'').trim();
  const selected=raw?validDirectScormUrl(raw):null;
  if(raw&&!selected)throw Error('رابط SCORM غير مطابق لصفحة «إضافة درس تفاعلي جديد» الرسمية في نور.');
  if(selected){
   if(stored?.teacherId===classTeacherId&&stored?.label===course.label&&stored?.cidNumeric===String(course.cid)&&stored?.opaqueCid!==selected.opaqueCid){
    throw Error('رابط SCORM الجديد يختلف عن معرّف المساق المحفوظ لنفس الصف. تحقق منه قبل الاستبدال.');
   }
   await browser.storage.local.set({[key]:{url:selected.url,opaqueCid:selected.opaqueCid,
    teacherId:classTeacherId,cidNumeric:String(course.cid),label:course.label,grade:course.grade,at:Date.now()}});
   return selected.url;
  }
  if(stored?.teacherId===classTeacherId&&stored?.cidNumeric===String(course.cid)&&stored?.label===course.label&&stored?.grade===course.grade){
   const validated=validDirectScormUrl(stored.url);
   return validated?.opaqueCid===stored.opaqueCid?validated.url:'';
  }
  return '';
 }
 async function scorm(opts){""",path)
s=replace_exact(s,
 "  const epoch=operationEpoch;\n  const branch=await orderedBranch(opts);",
 "  const epoch=operationEpoch;\n  const directScormUrl=await scormDirectLink(opts);\n  const branch=await orderedBranch(opts);",path)
s=replace_exact(s,
 "await globalThis.NoorScormPublisher.start(file,{...opts,positionProof:opts.proof,allowUnlinkedLesson:!opts.proof?.lessonId,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",
 "await globalThis.NoorScormPublisher.start(file,{...opts,directScormUrl,positionProof:opts.proof,allowUnlinkedLesson:!opts.proof?.lessonId,mode:scormSaveMode(),fromDashboard:true,teacherId:classTeacherId,publishDate:$('stnHubScormPublishDate').value});",path)
files[path]=s.encode()

path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
 "  if(!opts.unit||!opts.lesson)throw Error('تحديد الوحدة والدرس في شجرة نور مطلوب.');",
 """  if(!opts.unit||!opts.lesson)throw Error('تحديد الوحدة والدرس في شجرة نور مطلوب.');
  let direct=null;
  if(opts.directScormUrl){
   try{
    const u=new URL(String(opts.directScormUrl),location.href);
    const pattern=/^\\/teacher\\/attachments\\/upload\\/Scorm\\/cid:([A-Za-z0-9_-]+)\\/tid:([A-Za-z0-9_-]+)\\/tuid:([A-Za-z0-9_-]+)\\/?$/i;
    if(u.origin!==location.origin||u.search||u.hash||!pattern.test(u.pathname))
     throw Error('invalid');
    direct=u.href;
   }catch(_){throw Error('رابط الدرس التفاعلي المباشر غير صالح؛ لن أستخدم عنوانًا غير موثق.');}
  }""",path)
s=replace_exact(s,
 "   filename:file.name,formPath:'',verifiedLesson:false,attached:false,allowUnlinkedLesson:",
 "   filename:file.name,directScormUrl:direct||'',formPath:'',verifiedLesson:false,attached:false,allowUnlinkedLesson:",path)
s=replace_exact(s,
 "  if(opts.fromDashboard&&!isCourseHome())location.assign(location.origin+'/teacher');\n  else scheduleAdvance(j,250);",
 """  if(direct){
   notice('جارٍ فتح صفحة إضافة الدرس التفاعلي مباشرة دون بطاقة الصف…');
   if(location.href!==direct)location.assign(direct);
   else scheduleAdvance(j,300);
  }else if(opts.fromDashboard&&!isCourseHome())location.assign(location.origin+'/teacher');
  else scheduleAdvance(j,250);""",path)
files[path]=s.encode()
assert "stnHubScormDirectUrl" in files["noor-hub.js"].decode()
assert "stnScormDirectLink:v1:" in files["noor-hub.js"].decode()
assert "directScormUrl:direct||''" in files["noor-scorm-publisher.js"].decode()
assert "location.assign(direct)" in files["noor-scorm-publisher.js"].decode()


# v2.8.92: keep the proven direct SCORM route, but separate Activity and SCORM
# in the task picker again. Neither engine should change the other's UI.
path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 '<option value="activities">نشاط / SCORM</option><option value="scorm" hidden>نشاط / SCORM</option>',
 '<option value="activities">نشاط</option><option value="scorm">SCORM</option>',path)
s=replace_exact(s,
 '<button id="stnHubGenerateOther" type="button" class="stnBtn outline" hidden>توليد SCORM</button>',
 '',path)
s=replace_exact(s,
 """  $('stnHubGenerateOther').hidden=!['activities','scorm'].includes(s);
  if(s==='activities'){$('stnHubGenerate').textContent='✨ توليد نشاط';$('stnHubGenerateOther').textContent='✨ توليد SCORM';}
  if(s==='scorm'){$('stnHubGenerate').textContent='✨ توليد SCORM';$('stnHubGenerateOther').textContent='✨ توليد نشاط';}
""","",path)
start=s.index("  $('stnHubGenerateOther').addEventListener('click',async()=>{")
end=s.index("\n  });",start)+len("\n  });")
if start<0 or end<0:sys.exit("Could not find combined button listener")
s=s[:start]+s[end:]
# For batch SCORM, reuse the same verified per-teacher/per-course direct upload
# URL that worked for single SCORM. Never navigate back to the class card.
s=replace_exact(s,
 "  const entries=needsActivityPage?[]:await confirmedUnitLessons(opts);",
 """  const directScormUrl=opts.service==='scorm'?await scormDirectLink(opts):'';
  const entries=needsActivityPage?[]:await confirmedUnitLessons(opts);""",path)
s=replace_exact(s,
 "semester:opts.semester,unit:opts.unit,unitNo:opts.unitNo,proof:opts.proof,entries,index:0,count:opts.count,quantity,kinds,auto,publishDate,imageMode:scormImageMode(),",
 "semester:opts.semester,unit:opts.unit,unitNo:opts.unitNo,proof:opts.proof,entries,index:0,count:opts.count,quantity,kinds,auto,publishDate,directScormUrl,imageMode:scormImageMode(),",path)
s=replace_exact(s,
 "    const started=await globalThis.NoorScormPublisher.start(file,{...opts,teacherId:j.teacherId,mode:'auto',fromDashboard:true,publishDate:j.publishDate,",
 "    const started=await globalThis.NoorScormPublisher.start(file,{...opts,directScormUrl:j.directScormUrl||'',teacherId:j.teacherId,mode:'auto',fromDashboard:true,publishDate:j.publishDate,",path)
# Keep unverified submits distinct from a confirmed Noor receipt.
s=replace_exact(s,
 "    j.completed.push({unit:j.entries[j.index].unit,lesson:j.entries[j.index].lesson,at:Date.now()});j.index++;j.generationIds=[];j.phase='ready';await setUnitJob(j);",
 """    const unverified=j.service==='scorm'&&Boolean(globalThis.NoorScormPublisher?.inspect?.()?.unverified);
    j.completed.push({unit:j.entries[j.index].unit,lesson:j.entries[j.index].lesson,at:Date.now(),unverified});
    j.index++;j.generationIds=[];j.phase='ready';await setUnitJob(j);""",path)
s=replace_exact(s,
 "j.status=j.auto?'اكتمل حفظ جميع دروس الوحدة التي أكد نور حفظها':'اكتمل توليد جميع دروس الوحدة؛ احفظ الأنشطة يدويًا من المكتبة أو ارفع ملفات SCORM المنزلة';",
 """j.status=j.auto?(j.service==='scorm'&&j.completed.some(x=>x.unverified)?
    'اكتملت محاولة نشر جميع دروس الوحدة، وبعض عمليات الحفظ أُرسلت دون تأكيد من نور؛ راجع القائمة لاحقًا ولا تكرر رفعها':
    'اكتمل حفظ جميع دروس الوحدة التي أكد نور حفظها'):'اكتمل توليد جميع دروس الوحدة؛ احفظ الأنشطة يدويًا من المكتبة أو ارفع ملفات SCORM المنزلة';""",path)
files[path]=s.encode()

# After ONE real click on Noor's save button, never click Save again for this
# file. In an automatic batch only, allow the next file after a reasonable
# verification interval and mark the previous one "submitted, unverified".
# Keep the downloaded local backup and the precise batch status for audit.
path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
 " function notice(message){",
 """ function submittedWithoutReceipt(j){
  if(!j||j.phase!=='submitted_unknown'||!j.batchTag||j.mode!=='auto')return false;
  if(!j.submittedAt||Date.now()-j.submittedAt<14000)return false;
  const current=get();
  if(current?.id!==j.id||current.phase!=='submitted_unknown')return false;
  if(confirmedSaved(j))return true;
  j.phase='done';j.unverified=true;j.assumedAt=Date.now();set(j);
  // Explicitly NOT a confirmation event. The batch advances without retrying
  // the previously submitted upload; the user can inspect Noor later.
  root.dispatchEvent(new CustomEvent('stnNoorScormSubmittedUnverified',
   {detail:{id:j.id,batchTag:j.batchTag,unverified:true}}));
  notice('تم إرسال الحفظ مرة واحدة، ولم يظهر تأكيد نور؛ الانتقال للدرس التالي دون تكرار الحفظ. تحقّق من القائمة لاحقًا.');
  return true;
 }
 function notice(message){""",path)
s=replace_exact(s,
 "  if(j.phase==='submitted_unknown'){if(confirmedSaved(j)){notice('✓ تأكد ظهور SCORM في القائمة.');return;}notice('سبق الضغط على حفظ. افتح قائمة الدروس للتحقق، دون تكرار الإرسال.');return}",
 "  if(j.phase==='submitted_unknown'){if(confirmedSaved(j)){notice('✓ تأكد ظهور SCORM في القائمة.');return;}if(submittedWithoutReceipt(j))return;notice('سبق الضغط على حفظ. ننتظر التحقق دون تكرار الإرسال.');return}",path)
s=replace_exact(s,
 "    if(confirmedSaved(active)){notice('✓ تحقق ظهور الدرس التفاعلي في قائمة نور بعد الحفظ؛ يمكن الانتقال للدرس التالي.');return;}",
 "    if(confirmedSaved(active)){notice('✓ تحقق ظهور الدرس التفاعلي في قائمة نور بعد الحفظ؛ يمكن الانتقال للدرس التالي.');return;}\n     if(submittedWithoutReceipt(active))return;",path)
s=replace_exact(s,
 "     else notice('حالة حفظ SCORM غير مؤكدة. افتح قائمة نور للتحقق؛ لن يُرسل الدرس التالي أو يتكرر الحفظ دون إثبات.');",
 "     else notice('حالة حفظ SCORM غير مؤكدة. افتح قائمة نور للتحقق؛ لن يتكرر الحفظ دون إثبات.');",path)
s=replace_exact(s,
 "batchTag:j.batchTag}:null",
 "batchTag:j.batchTag,unverified:Boolean(j.unverified)}:null",path)
# On every navigation and reload, the batch listener in hub can detect its
# own original publish id and the submitted-unverified completion marker.
files[path]=s.encode()
assert '<option value="activities">نشاط</option><option value="scorm">SCORM</option>' in files["noor-hub.js"].decode()
s=files["noor-hub.js"].decode()
s=replace_exact(s,
 "  window.addEventListener('stnNoorScormConfirmed',()=>checkUnitBatch().catch(()=>{}));",
 "  window.addEventListener('stnNoorScormConfirmed',()=>checkUnitBatch().catch(()=>{}));\n  window.addEventListener('stnNoorScormSubmittedUnverified',()=>checkUnitBatch().catch(()=>{}));",
 "noor-hub.js")
files["noor-hub.js"]=s.encode()
assert "stnHubGenerateOther" not in files["noor-hub.js"].decode()
assert "directScormUrl:j.directScormUrl||''" in files["noor-hub.js"].decode()
assert "submittedWithoutReceipt(active)" in files["noor-scorm-publisher.js"].decode()
assert "unverified:Boolean(j.unverified)" in files["noor-scorm-publisher.js"].decode()


# v2.8.92 - no more card fallback for SCORM: require a verified per-course
# direct upload route. Hide the link field; request one-time setup ONLY if
# this particular teacher/course has no validated saved route.
path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 """    <label for="stnHubScormDirectUrl">رابط «إضافة درس تفاعلي جديد» المباشر (اختبار للصف المحدد)</label>
    <input type="url" id="stnHubScormDirectUrl" dir="ltr" autocomplete="off" placeholder="https://lms.moe.gov.om/teacher/attachments/upload/Scorm/cid:…/tid:…/tuid:…">
    <p class="stnNote">ألصق الرابط الرسمي الذي فتحته من حسابك للصف المحدد. يُحفظ على جهاز المعلم لهذا المساق فقط، ولا يُستخدم لصف آخر. عند غياب الرابط يستمر مسار نور المعتاد.</p>""",
 "",path)
s=replace_exact(s,
 "  const input=$('stnHubScormDirectUrl');\n  const course=opts.course;",
 "  const course=opts.course;",path)
s=replace_exact(s,
 "  const raw=String(input.value||'').trim();\n  const selected=raw?validDirectScormUrl(raw):null;\n  if(raw&&!selected)throw Error('رابط SCORM غير مطابق لصفحة «إضافة درس تفاعلي جديد» الرسمية في نور.');",
 """  // A direct upload URL is opaque: it cannot be derived from the numeric
  // activity CID. On a new course, ask once rather than wrongly opening
  // the course card, which has repeatedly failed in Noor.
  if(stored?.teacherId===classTeacherId&&stored?.cidNumeric===String(course.cid)&&
     stored?.label===course.label&&stored?.grade===course.grade){
   const prior=validDirectScormUrl(stored.url);
   if(prior?.opaqueCid===stored.opaqueCid)return prior.url;
  }
  const raw=String(window.prompt('لم يُحفظ رابط «إضافة درس تفاعلي جديد» لهذا الصف. افتح صفحة الدرس التفاعلي لهذا المساق من نور، ثم الصق رابطها الرسمي مرة واحدة. لن تعود الإضافة إلى محاولة فتح بطاقة الصف تلقائيًا.','')||'').trim();
  if(!raw)throw Error('لم يُسجل رابط SCORM مباشر لهذا المساق. لا يمكن بدء التوليد دون عنوان رسمي خاص به.');
  const selected=validDirectScormUrl(raw);
  if(!selected)throw Error('الرابط غير مطابق لعنوان «إضافة درس تفاعلي جديد» الرسمي في نور. لم يبدأ النشر.');""",path)
s=replace_exact(s,
 """  if(stored?.teacherId===classTeacherId&&stored?.cidNumeric===String(course.cid)&&stored?.label===course.label&&stored?.grade===course.grade){
   const validated=validDirectScormUrl(stored.url);
   return validated?.opaqueCid===stored.opaqueCid?validated.url:'';
  }
  return '';""",
 """  throw Error('لم أستطع الحصول على رابط SCORM الرسمي لهذا المساق.');""",path)
# Single-lesson quantity > 1 must NOT generate download-only files. Create
# a persistent per-file publication queue, reusing the same SCORM batch flow
# that already supports generating after save and page navigation.
s=replace_exact(s,
 " async function beginUnitBatch(opts){",
 " async function beginUnitBatch(opts,lessonCopies=null){",path)
s=replace_exact(s,
 "  if(!opts.proof?.unitId)throw Error('تحقّق من ترتيب الوحدة في شجرة الصف أولًا.');",
 "  if(!lessonCopies&&!opts.proof?.unitId)throw Error('تحقّق من ترتيب الوحدة في شجرة الصف أولًا.');",path)
s=replace_exact(s,
 "  const auto=opts.service==='activities'?$('stnHubActivityUnitAuto').checked:$('stnHubScormUnitAuto').checked;",
 "  const auto=lessonCopies?true:opts.service==='activities'?$('stnHubActivityUnitAuto').checked:$('stnHubScormUnitAuto').checked;",path)
s=replace_exact(s,
 "  const quantity=Number((opts.service==='activities'?$('stnHubActivityQuantity'):$('stnHubScormQuantity')).value);",
 "  const quantity=lessonCopies?1:Number((opts.service==='activities'?$('stnHubActivityQuantity'):$('stnHubScormQuantity')).value);",path)
s=replace_exact(s,
 "  const entries=needsActivityPage?[]:await confirmedUnitLessons(opts);",
 """  const entries=lessonCopies
    ?Array.from({length:lessonCopies},(_,index)=>({
       unit:opts.unit,lesson:opts.lesson,source:'single_lesson',
       unitNo:opts.unitNo,lessonNo:opts.lessonNo,lessonId:opts.proof?.lessonId||'',
       reference:{outcomes:[],objectives:'',concepts:'',practice:'',teacherText:''},
       copyIndex:index+1}))
    :needsActivityPage?[]:await confirmedUnitLessons(opts);""",path)
s=replace_exact(s,
 "  if(opts.service==='scorm'){\n   for(const entry of entries){",
 "  if(opts.service==='scorm'&&!lessonCopies){\n   for(const entry of entries){",path)
# Launch direct queue as soon as a multi-copy single lesson is requested.
s=replace_exact(s,
 "  let started=0;\n  for(let i=0;i<quantity;i++){",
 """  if(quantity>1){
   status('إنشاء ونشر '+quantity+' ملفات SCORM بالتتابع. لن أبدأ الملف التالي حتى يصل أمر حفظ الملف السابق إلى نور.');
   await beginUnitBatch({...opts,unit:target.unit,lesson:target.title},quantity);
   return;
  }
  let started=0;
  for(let i=0;i<quantity;i++){""",path)
s=replace_exact(s,
 "  if(quantity>1)status('تم إنشاء '+quantity+' ملفات SCORM وتنزيلها. اختر ملفًا واحدًا عند نشر كل درس حتى لا يستبدل مساق سابقًا.');",
 "  if(quantity>1)status('تتم معالجة جميع ملفات SCORM في طابور النشر التلقائي.');",path)
# Guard every SCORM queue route before generating anything; never return to
# the known broken flip-card fallback.
s=replace_exact(s,
 "  const directScormUrl=opts.service==='scorm'?await scormDirectLink(opts):'';\n  const entries=",
 "  const directScormUrl=opts.service==='scorm'?await scormDirectLink(opts):'';\n  if(opts.service==='scorm'&&!directScormUrl)throw Error('لا يوجد رابط SCORM مباشر موثق لهذا الصف. لن أفتح البطاقة.');\n  const entries=",path)
s=replace_exact(s,
 "  const directScormUrl=await scormDirectLink(opts);\n  const branch=",
 "  const directScormUrl=await scormDirectLink(opts);\n  if(!directScormUrl)throw Error('رابط SCORM المباشر مطلوب؛ لن تُفتح بطاقة الصف.');\n  const branch=",path)
# The publisher must use only direct URL for both single and serial batches.
path2="noor-scorm-publisher.js"
p=files[path2].decode()
p=replace_exact(p,
 "  }else if(opts.fromDashboard&&!isCourseHome())location.assign(location.origin+'/teacher');\n  else scheduleAdvance(j,250);",
 """  }else{
   throw Error('هذا الإصدار يتطلب رابط «إضافة درس تفاعلي جديد» الرسمي للمساق؛ لن أعود إلى مسار بطاقة الصف.');
  }""",path2)
files[path2]=p.encode()
files[path]=s.encode()
assert "stnHubScormDirectUrl" not in files["noor-hub.js"].decode()
assert "beginUnitBatch(opts,lessonCopies=null)" in files["noor-hub.js"].decode()
assert "await beginUnitBatch({...opts,unit:target.unit,lesson:target.title},quantity)" in files["noor-hub.js"].decode()
assert "هذا الإصدار يتطلب رابط" in files["noor-scorm-publisher.js"].decode()
assert "تم إنشاء '+quantity+' ملفات SCORM وتنزيلها. اختر ملفًا واحدًا" not in files["noor-hub.js"].decode()


# 2.8.92: passively discover *official* Noor SCORM route identities.
# No hardcoded IDs, invented CID translation, cross-teacher IDs or network interception.
path="noor-course-catalog.js"
s=files[path].decode()
s=replace_exact(s,
 " function scan(){let changed=false;",
 r""" function scormDiscovery(course){
  const label=String(course?.label||'');
  const cid=String(course?.cid||'');
  const matches=cache.filter(x=>x.cidNumeric===cid&&norm(x.label)===norm(label));
  const item=matches.length===1?matches[0]:null;
  const source=item?.routes?.scorm||'';
  let direct='';
  if(source){
   try{
    const url=new URL(source,location.href);
    // Accept only the two Noor endpoint families actually observed.
    const match=url.pathname.match(/^\/teacher\/attachments\/(upload|index)\/Scorm\/cid:([A-Za-z0-9_-]+)\/tid:([A-Za-z0-9_-]+)\/tuid:([A-Za-z0-9_-]+)\/?$/i);
    if(url.origin===location.origin&&!url.search&&!url.hash&&match&&
       match[2]===item.cidOpaque){
     url.pathname='/teacher/attachments/upload/Scorm/cid:'+match[2]+'/tid:'+match[3]+'/tuid:'+match[4];
     direct=url.href;
    }
   }catch(_){}
  }
  // Diagnostic counts contain no opaque IDs, teacher IDs or raw URLs.
  const officialLinks=[...document.querySelectorAll('a[href*="cid:"],[data-href*="cid:"]')]
   .filter(el=>Boolean(localURL(el.href||el.getAttribute('data-href'))));
  const scormLinks=officialLinks.filter(el=>service(localURL(el.href||el.getAttribute('data-href')))==='scorm');
  return {direct,recognizedCourse:!!item,hasOpaqueId:!!item?.cidOpaque,
   hasOfficialRoute:!!source,officialLinks:officialLinks.length,scormLinks:scormLinks.length,
   visibleCourseCards:isHome()?discoverCards().length:null};
 }
 function scan(){let changed=false;""",path)
s=replace_exact(s,
 "get:c=>cache.find(x=>x.cidNumeric===String(c)||norm(x.label)===norm(c))||null,gradeOf",
 "get:c=>cache.find(x=>x.cidNumeric===String(c)||norm(x.label)===norm(c))||null,scormDiscovery,gradeOf",path)
files[path]=s.encode()

path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 '  <div id="stnHubScormOptions" hidden>',
 '''  <div id="stnHubScormOptions" hidden>
    <button id="stnHubScormDiagnose" type="button" class="stnBtn outline">فحص المسار التلقائي لـ SCORM</button>''',path)
s=replace_exact(s,
 "  $('stnHubGenerate').addEventListener('click',()=>generate().catch(error=>actionStatus('تعذر بدء التوليد: '+String(error.message||error))));",
 """  $('stnHubGenerate').addEventListener('click',()=>generate().catch(error=>actionStatus('تعذر بدء التوليد: '+String(error.message||error))));
  $('stnHubScormDiagnose').addEventListener('click',()=>{
   const opts=selected();
   const catalog=globalThis.NoorCourseCatalog;
   catalog?.scan?.();
   const diag=catalog?.scormDiscovery?.(opts.course);
   if(!opts.course?.cid){actionStatus('اختر الصف والمادة أولًا لفحص SCORM.');return;}
   if(diag?.direct){actionStatus('✓ تعرفت الإضافة على المسار الرسمي المباشر لـ SCORM لهذا المساق؛ لا حاجة لإدخال رابط.');return;}
   const count=diag?.scormLinks||0;
   actionStatus('لم تكشف صفحة نور رابط SCORM الموثق للمساق المختار بعد. الروابط الرسمية الظاهرة: '+(diag?.officialLinks||0)+'، روابط SCORM المكتشفة: '+count+'، ربط المساق: '+(diag?.recognizedCourse?'موجود':'غير موجود')+'. لن يُخمن رابط أو يستخدم معرّف صف آخر.');
  });""",path)
s=replace_exact(s,
 "  const raw=String(window.prompt('لم يُحفظ رابط «إضافة درس تفاعلي جديد» لهذا الصف. افتح صفحة الدرس التفاعلي لهذا المساق من نور، ثم الصق رابطها الرسمي مرة واحدة. لن تعود الإضافة إلى محاولة فتح بطاقة الصف تلقائيًا.','')||'').trim();",
 """  globalThis.NoorCourseCatalog?.scan?.();
  const discovered=globalThis.NoorCourseCatalog?.scormDiscovery?.(course);
  if(discovered?.direct){
   const match=validDirectScormUrl(discovered.direct);
   if(match){
    await browser.storage.local.set({[key]:{url:match.url,opaqueCid:match.opaqueCid,
     teacherId:classTeacherId,cidNumeric:String(course.cid),label:course.label,grade:course.grade,at:Date.now()}});
    return match.url;
   }
  }
  throw Error('لم أجد رابط SCORM موثقًا لهذا الصف ضمن بيانات نور الحالية. استخدم «فحص المسار التلقائي» لعرض حالة الاكتشاف. لن يُطلب رابط من المعلم أو تُفتح بطاقة الصف.');
  const raw=String('');""",path)
files[path]=s.encode()
assert 'stnHubScormDiagnose' in files["noor-hub.js"].decode()
assert "scormDiscovery" in files["noor-course-catalog.js"].decode()
assert "window.prompt(" not in files["noor-hub.js"].decode()
assert "لم أجد رابط SCORM موثقًا" in files["noor-hub.js"].decode()


# 2.8.92 - robust grade/subject matching, card-scoped URL discovery, and
# diagnostic breakdown. No guessing unknown CID/tid/tuid. Ignore links from
# other course cards, teacher accounts, or unrelated global tables.
path="noor-course-catalog.js"
s=files[path].decode()
a=s.index(" function scormDiscovery(course){")
b=s.index(" function scan(){let changed=false;",a)
if a<0 or b<=a:sys.exit("scormDiscovery section not found")
s=s[:a]+r""" function scormDiscovery(course){
  const selectedLabel=String(course?.label||'');
  const selectedCid=String(course?.cid||'');
  const selectedGrade=Number(course?.grade)||gradeOf(selectedLabel);
  const selectedSubject=subjectOf(selectedLabel);
  const sameCourse=x=>!!x&&
    (selectedCid&&x.cidNumeric===selectedCid||
     selectedLabel&&norm(x.label)===norm(selectedLabel));
  let matches=cache.filter(sameCourse);
  let basis='official_id_or_label';
  if(matches.length!==1&&selectedGrade&&selectedSubject){
   const byCourse=cache.filter(x=>Number(x.grade)===selectedGrade&&
     norm(subjectOf(x.label))===norm(selectedSubject));
   if(byCourse.length===1){matches=byCourse;basis='unique_grade_subject'}
  }
  const item=matches.length===1?matches[0]:null;
  const dashboardCards=isHome()?discoverCards():[];
  const directCards=dashboardCards.filter(c=>norm(c.label)===norm(selectedLabel));
  let card=directCards.length===1?directCards[0]:null;
  if(!card&&selectedGrade&&selectedSubject){
   const byCourse=dashboardCards.filter(c=>gradeOf(c.label)===selectedGrade&&
    norm(subjectOf(c.label))===norm(selectedSubject));
   if(byCourse.length===1)card=byCourse[0];
  }
  const officialLinks=[...document.querySelectorAll('a[href*="cid:"],[data-href*="cid:"]')]
   .filter(el=>Boolean(localURL(el.href||el.getAttribute('data-href'))));
  const scormLinks=officialLinks.filter(el=>service(localURL(el.href||el.getAttribute('data-href')))==='scorm');
  const cardLinks=card?[...card.element.querySelectorAll('a[href],[data-href],[data-url],[data-link]')]:[];
  const cardScorm=cardLinks.map(el=>el.href||el.getAttribute('data-href')||
    el.getAttribute('data-url')||el.getAttribute('data-link'))
   .map(localURL).filter(u=>u&&service(u)==='scorm');
  function directRoute(raw){
   try{
    const u=localURL(raw);if(!u||u.search||u.hash)return null;
    const match=u.pathname.match(/^\/teacher\/attachments\/(upload|index)\/Scorm\/cid:([A-Za-z0-9_-]+)\/tid:([A-Za-z0-9_-]+)\/tuid:([A-Za-z0-9_-]+)\/?$/i);
    if(!match)return null;
    u.pathname='/teacher/attachments/upload/Scorm/cid:'+match[2]+'/tid:'+match[3]+'/tuid:'+match[4];
    return {url:u.href,cid:match[2],tid:match[3],tuid:match[4]};
   }catch(_){return null}
  }
  const saved=item?.routes?.scorm?directRoute(item.routes.scorm):null;
  const candidates=[...(saved?[saved]:[]),...cardScorm.map(x=>directRoute(x.href)).filter(Boolean)]
   .filter(x=>!item?.cidOpaque||x.cid===item.cidOpaque);
  const distinct=new Map(candidates.map(x=>[x.url,x]));
  const safe=distinct.size===1?[...distinct.values()][0]:null;
  if(safe&&card&&(!item||!item.cidOpaque)&&add({label:card.label,cid:safe.cid,
    url:safe.url,service:'scorm'})){
   persist();window.dispatchEvent(new CustomEvent('stnCourseCatalogChanged'));
  }
  return {
   direct:safe?.url||'',recognizedCourse:!!item,hasOpaqueId:!!item?.cidOpaque,
   hasOfficialRoute:!!item?.routes?.scorm,officialLinks:officialLinks.length,
   scormLinks:scormLinks.length,visibleCourseCards:dashboardCards.length,
   matchedCard:!!card,cardScopedLinks:cardLinks.length,cardScormLinks:cardScorm.length,
   ambiguousMatches:matches.length>1||distinct.size>1,matchBasis:basis,
   selectedGrade:!!selectedGrade,selectedSubject:!!selectedSubject
  };
 }
""" +s[b:]
files[path]=s.encode()

path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 """   actionStatus('لم تكشف صفحة نور رابط SCORM الموثق للمساق المختار بعد. الروابط الرسمية الظاهرة: '+(diag?.officialLinks||0)+'، روابط SCORM المكتشفة: '+count+'، ربط المساق: '+(diag?.recognizedCourse?'موجود':'غير موجود')+'. لن يُخمن رابط أو يستخدم معرّف صف آخر.');""",
 """   const details='الروابط العامة: '+(diag?.officialLinks||0)+'، روابط SCORM العامة: '+count+
    '، بطاقة المساق المطابقة: '+(diag?.matchedCard?'نعم':'لا')+
    '، روابط داخل البطاقة: '+(diag?.cardScopedLinks||0)+
    '، روابط SCORM داخل البطاقة: '+(diag?.cardScormLinks||0)+
    '، ربط السجل: '+(diag?.recognizedCourse?'موجود':'غير موجود')+
    (diag?.ambiguousMatches?'، تحذير: وجد أكثر من تطابق':'')+'.';
   actionStatus('لم يظهر رابط SCORM رسمي مرتبط بشكل فريد بالمساق المختار. '+details+' لن تُستخدم معرّفات من صف آخر.');
""",path)
files[path]=s.encode()
assert "const cardScorm=cardLinks" in files["noor-course-catalog.js"].decode()
assert "matchedCard:!!card" in files["noor-course-catalog.js"].decode()
assert "روابط داخل البطاقة" in files["noor-hub.js"].decode()
assert "NoorCourseCatalog?.scormDiscovery?.(course)" in files["noor-hub.js"].decode()


# 2.8.92: use the course CONTENT page shown in the teacher's video, not the
# failed flip-card route and not an opaque SCORM upload link.
# Numeric CID is taken ONLY from an already verified selected teacher course.
path="noor-hub.js"
s=files[path].decode()
a=s.index(" async function scormDirectLink(opts){")
b=s.index(" async function scorm(opts){",a)
if a<0 or b<=a:sys.exit("Cannot find old SCORM opaque-link resolver")
s=s[:a]+""" async function scormDirectLink(opts){
  const c=opts?.course;
  const cid=String(c?.cid||'');
  if(!c?.verified||!/^[0-9]+$/.test(cid)||!c.grade||!c.subject||!c.label)
   throw Error('لا يوجد معرّف مساق رقمي موثّق. اختر المساق من قائمة نور قبل بدء SCORM.');
  // Noor's real course-content route was observed from its sidebar > Home >
  // Show all materials navigation. This avoids the failing course flip card.
  return location.origin+'/teacher/courses/browse_content/cid:'+encodeURIComponent(cid);
 }
""" +s[b:]
s=replace_exact(s,
 "  if(!directScormUrl)throw Error('رابط SCORM المباشر مطلوب؛ لن تُفتح بطاقة الصف.');",
 "  if(!directScormUrl)throw Error('تعذر فتح صفحة محتوى المساق الموثق.');",path)
s=replace_exact(s,
 "  if(opts.service==='scorm'&&!directScormUrl)throw Error('لا يوجد رابط SCORM مباشر موثق لهذا الصف. لن أفتح البطاقة.');",
 "  if(opts.service==='scorm'&&!directScormUrl)throw Error('تعذر استخراج مسار محتوى المساق الرقمي.');",path)
s=replace_exact(s,
 """   if(diag?.direct){actionStatus('✓ تعرفت الإضافة على المسار الرسمي المباشر لـ SCORM لهذا المساق؛ لا حاجة لإدخال رابط.');return;}""",
 """   if(opts.course?.verified&&/^[0-9]+$/.test(String(opts.course.cid||''))){
    actionStatus('✓ معرّف المساق الرقمي متاح. سيُفتح استعراض محتوى المساق أولًا، ثم المكتبات الأخرى وإضافة درس تفاعلي. لا حاجة إلى إدخال رابط.');
    return;
   }
   if(diag?.direct){actionStatus('✓ رابط SCORM الرسمي محفوظ للمساق.');return;}""",path)
files[path]=s.encode()

path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
 """    const pattern=/^\/teacher\/attachments\/upload\/Scorm\/cid:([A-Za-z0-9_-]+)\/tid:([A-Za-z0-9_-]+)\/tuid:([A-Za-z0-9_-]+)\/?$/i;
    if(u.origin!==location.origin||u.search||u.hash||!pattern.test(u.pathname))
     throw Error('invalid');""",
 """    const pattern=/^\/teacher\/courses\/browse_content\/cid:([0-9]+)\/?$/i;
    const found=u.pathname.match(pattern);
    if(u.origin!==location.origin||u.search||u.hash||!found||
       found[1]!==String(c.cid))throw Error('invalid');""",path)
s=replace_exact(s,
 "   }catch(_){throw Error('رابط الدرس التفاعلي المباشر غير صالح؛ لن أستخدم عنوانًا غير موثق.');}",
 "   }catch(_){throw Error('رابط محتوى المساق لا يطابق المعرّف الرقمي للصف المختار.');}",path)
s=replace_exact(s,
 "  set(j);notice('حُفظ ملف SCORM مؤقتًا؛ جارٍ فتح المكتبة الرقمية ثم الدروس التفاعلية للصف المحدد.');",
 "  set(j);notice('حُفظ ملف SCORM؛ جارٍ فتح استعراض محتوى المساق ثم إضافة درس تفاعلي جديد.');",path)
s=replace_exact(s,
 "   notice('جارٍ فتح صفحة إضافة الدرس التفاعلي مباشرة دون بطاقة الصف…');",
 "   notice('جارٍ فتح صفحة محتوى المساق دون بطاقة الصف…');",path)
s=replace_exact(s,
 "   throw Error('هذا الإصدار يتطلب رابط «إضافة درس تفاعلي جديد» الرسمي للمساق؛ لن أعود إلى مسار بطاقة الصف.');",
 "   throw Error('لا يوجد معرّف مساق رقمي موثّق لفتح صفحة المحتوى.');",path)
s=replace_exact(s,
 """  return [e.innerText||e.textContent,e.value,e.getAttribute('aria-label'),e.title].map(norm)""",
 """  return [e.innerText||e.textContent,e.value,e.getAttribute('aria-label'),e.title,
   e.getAttribute('data-original-title'),e.getAttribute('data-bs-original-title'),
   e.getAttribute('data-tooltip')].map(norm)""",path)
# Recognize the actual modal from the video, without requiring a separate
# /attachments/upload page URL. This is the key difference from older versions.
s=replace_exact(s,
 """ const onUploadPage=()=>/\/teacher\/attachments\/upload\/scorm(?:\/|$)/i.test(location.pathname)
   ||pageHeaders().some(h=>UPLOAD_TITLE.test(h));""",
 """ const onUploadPage=()=>/\/teacher\/attachments\/upload\/scorm(?:\/|$)/i.test(location.pathname)
   ||[...document.querySelectorAll('.modal,[role="dialog"],.swal2-popup')]
      .some(el=>visible(el)&&UPLOAD_TITLE.test(norm(el.querySelector('h1,h2,h3,h4,h5,.modal-title,[role="heading"]')?.textContent||'')))
   ||pageHeaders().some(h=>UPLOAD_TITLE.test(h));""",path)
# Routes inside the content page: click the actual OTHER LIBRARIES green
# expansion arrow, then the uniquely named Add interactive lessons action.
# Never use arbitrary colored icon indexes.
s=replace_exact(s,
 " function pickNav(j){",
 """ function contentCoursePath(j){
  const m=location.pathname.match(/^\/teacher\/courses\/browse_content\/cid:([0-9]+)\/?$/i);
  if(!m)return false;
  if(m[1]!==String(j.cid))throw Error('صفحة محتوى نور تخص مساقًا آخر؛ لن نرفع الملف.');
  // If the modal is already visible, advance() will stage it.
  const actions=[...document.querySelectorAll('a,button,[role="button"],[title],[aria-label],[data-original-title],[data-bs-original-title]')]
   .filter(e=>visible(e)&&!inHub(e)&&!e.disabled);
  const add=actions.filter(el=>actionText(el).some(v=>
    /^(?:add interactive lessons?|upload interactive lesson|اضافه درس تفاعلي(?: جديد)?|رفع درس تفاعلي جديد)$/.test(v)));
  const leaf=add.filter(el=>!add.some(other=>other!==el&&el.contains(other)));
  if(leaf.length===1)return takeNavigation(j,leaf[0],'فتح نافذة رفع درس تفاعلي جديد');
  if(leaf.length>1)throw Error('ظهرت عدة أزرار لإضافة درس تفاعلي؛ تعذّر تمييز الزر الصحيح.');
  const labels=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,span,div,p,strong')]
   .filter(el=>visible(el)&&!inHub(el)&&norm(el.textContent)==='المكتبات الاخرى');
  const uniqueLabels=labels.filter(el=>!labels.some(other=>other!==el&&el.contains(other)));
  if(uniqueLabels.length!==1)return false;
  const label=uniqueLabels[0];
  let arrow=null;
  for(let node=label.parentElement,depth=0;node&&depth<4;depth++,node=node.parentElement){
   const candidates=[...node.querySelectorAll('a,button,[role="button"]')].filter(el=>
    visible(el)&&!inHub(el)&&!el.disabled&&
    (el.classList.contains('btn-success')||el.querySelector('.fa-arrow-right,.fa-arrow-circle-right,.fa-angle-right')||
     /expand|فتح|show/i.test(el.getAttribute('aria-label')||el.title||'')));
   if(candidates.length===1){arrow=candidates[0];break;}
   if(candidates.length>1)break;
  }
  return arrow?takeNavigation(j,arrow,'إظهار المكتبات الأخرى'):false;
 }
 function pickNav(j){
  if(/^\/teacher\/courses\/browse_content\/cid:/i.test(location.pathname)){
   return contentCoursePath(j);
  }""",path)
files[path]=s.encode()
assert "contentCoursePath(j)" in files["noor-scorm-publisher.js"].decode()
assert "browse_content\\/cid:([0-9]+)" in files["noor-scorm-publisher.js"].decode()
assert "getAttribute('data-original-title')" in files["noor-scorm-publisher.js"].decode()
assert "return location.origin+'/teacher/courses/browse_content/cid:'" in files["noor-hub.js"].decode()
assert "window.prompt(" not in files["noor-hub.js"].decode()


# v2.8.92 - Remove every previous SCORM card/popover / digital-library
# navigation attempt, retain ONLY the verified course-content route.
# The "Other Libraries" section is a self-contained panel: green arrow
# toggles its icon strip, green PLAY is "Add interactive lessons".
path="noor-scorm-publisher.js"
s=files[path].decode()
a=s.index(" function contentCoursePath(j){")
b=s.index(" function nearText(el){",a)
if a<0 or b<=a:sys.exit("Cannot replace old SCORM navigation engine")
s=s[:a]+r""" // Dedicated SCORM routing engine: no legacy class-card, popover or
 // digital-repository fallbacks are reachable from pickNav.
 function sameCourseContent(j){
  const m=location.pathname.match(/^\/teacher\/courses\/browse_content\/cid:([0-9]+)\/?$/i);
  return m?m[1]===String(j.cid):false;
 }
 function actionMeta(el){
  if(!el)return '';
  return norm([el.textContent,el.title,el.getAttribute('aria-label'),
   el.getAttribute('data-original-title'),el.getAttribute('data-bs-original-title'),
   el.getAttribute('data-tooltip'),el.getAttribute('data-title')]
   .filter(Boolean).join(' '));
 }
 function actionTarget(el){return el?.closest?.('a,button,[role="button"],[onclick]')||el}
 function otherLibrariesPanel(){
  // Find the exact visible heading, not a parent containing all section names.
  const nodes=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,strong,span,div,p,a')]
   .filter(el=>visible(el)&&!inHub(el));
  const headings=nodes.filter(el=>norm(el.textContent)==='المكتبات الاخرى'&&
   ![...el.children].some(child=>norm(child.textContent)==='المكتبات الاخرى'));
  if(headings.length!==1)return null;
  const heading=headings[0];
  for(let el=heading,depth=0;el&&depth<7;el=el.parentElement,depth++){
   if(el===document.body)break;
   const text=norm(el.textContent||'');
   // The selected panel has one heading, its own total, and buttons/icons.
   if(text.length>650||/(?:الاختبارات|المهام الالكترونيه|الفصول الذكيه).*(?:المكتبات الاخرى)/.test(text))continue;
   const controls=[...el.querySelectorAll('a,button,[role="button"],[onclick]')].filter(x=>visible(x)&&!inHub(x));
   if(controls.length&&el.querySelector('[class*="panel"],[class*="card"]'))return el;
   if(controls.length>=2||controls.length===1&&/(?:المجموع|add interactive)/i.test(text))return el;
  }
  return heading.closest('.panel,.card,.box,.widget')||heading.parentElement;
 }
 function onlyUnique(list,description){
  const uniq=[...new Set(list.map(actionTarget).filter(el=>el&&visible(el)&&!inHub(el)&&!el.disabled))];
  const leaf=uniq.filter(el=>!uniq.some(other=>other!==el&&el.contains(other)));
  if(leaf.length>1)throw Error('ظهر أكثر من زر محتمل لـ'+description+' داخل المكتبات الأخرى؛ لن أضغط عشوائيًا.');
  return leaf[0]||null;
 }
 function otherLibrariesAdd(panel){
  const controls=[...panel.querySelectorAll('a,button,[role="button"],[onclick]')].filter(el=>visible(el)&&!inHub(el));
  // 1. Explicit tooltip/name is strongest evidence, including hidden titles.
  let links=controls.filter(el=>/add interactive lessons?|upload interactive lesson|اضافه درس تفاعلي|رفع درس تفاعلي/.test(actionMeta(el)));
  if(links.length)return onlyUnique(links,'إضافة الدرس التفاعلي');
  // 2. On mobile Noor displays a green circular PLAY icon with no
  // text until hover. Scope the icon to this one validated section.
  links=controls.filter(el=>{
   const graphic=el.querySelector('.fa-play-circle,.fa-play,.fa-play-circle-o,.glyphicon-play,[class*="icon-play"]');
   if(!graphic)return false;
   const meta=actionMeta(el);
   if(/video|youtube|فيديو|preview|معاينه/.test(meta))return false;
   const style=getComputedStyle(el),bg=style.backgroundColor||'',childStyle=getComputedStyle(graphic);
   const color=childStyle.color||style.color||'';
   const green=el.classList.contains('btn-success')||
    /rgb\((?:\s*(?:0|[1-9]?\d|1[01]\d)\s*,\s*(?:1[2-9]\d|2[0-5]\d)\s*,)/.test(bg+' '+color)||
    /(green|success)/i.test(el.className+' '+graphic.className);
   return green;
  });
  return onlyUnique(links,'زر التشغيل الأخضر للدروس التفاعلية');
 }
 function otherLibrariesExpand(panel){
  const heading=[...panel.querySelectorAll('h1,h2,h3,h4,h5,h6,span,div,strong')]
   .find(el=>visible(el)&&norm(el.textContent)==='المكتبات الاخرى');
  if(!heading)return null;
  const head=heading.getBoundingClientRect();
  const controls=[...panel.querySelectorAll('a,button,[role="button"],[onclick],[data-toggle],[data-bs-toggle],i,span,svg')]
   .filter(el=>visible(el)&&!el.disabled&&el!==heading&&!el.contains(heading));
  const isGreen=value=>{
   const m=String(value||'').match(/rgba?\\(\\s*(\\d+)[,\\s]+\\s*(\\d+)[,\\s]+\\s*(\\d+)/);
   return !!m&&+m[2]>=80&&+m[2]>+m[1]*1.18&&+m[2]>+m[3]*1.08;
  };
  const candidates=controls.filter(el=>{
   const r=el.getBoundingClientRect();
   // The green circular arrow sits immediately LEFT of the heading,
   // aligned with its row. Do not confuse it with the section's add buttons.
   if(r.width<22||r.width>88||r.height<22||r.height>88)return false;
   if(r.right>head.left+8||Math.abs((r.top+r.bottom-head.top-head.bottom)/2)>Math.max(28,head.height*.8))return false;
   const target=actionTarget(el);
   if(/add|اضافه|درس|interactive|play|فيديو/i.test(actionMeta(target)))return false;
   const paint=[el,target,el.parentElement,target.parentElement].filter((x,i,a)=>x&&panel.contains(x)&&a.indexOf(x)===i);
   const green=paint.some(x=>{
    const cs=getComputedStyle(x),before=getComputedStyle(x,'::before'),after=getComputedStyle(x,'::after');
    return /success|green/i.test(String(x.className))||isGreen(cs.backgroundColor)||isGreen(cs.borderColor)||isGreen(before.backgroundColor)||isGreen(after.backgroundColor);
   });
   const hasArrow=paint.some(x=>x.matches?.('svg,i,[class*="arrow"],[class*="right"]')||
    x.querySelector?.('svg,i,[class*="arrow"],[class*="right"]'))||
    /arrow|right/i.test(String(el.className));
   return green&&(hasArrow||el.matches('a,button,[role="button"],[onclick],[data-toggle],[data-bs-toggle]'));
  });
  return onlyUnique(candidates,'الدائرة الخضراء ذات السهم الأبيض بجانب المكتبات الأخرى');
 }
 function pickNav(j){
  if(!/^\/teacher\/courses\/browse_content\/cid:/i.test(location.pathname)){
   throw Error('مسار SCORM الجديد لا يعمل إلا من صفحة استعراض محتوى المساق الموثقة، وليس من بطاقة الصف.');
  }
  if(!sameCourseContent(j))throw Error('توقفت العملية لأن معرّف صفحة المحتوى لا يطابق المساق المختار.');
  const panel=otherLibrariesPanel();
  if(!panel)return false; // Wait for Noor to render the Other Libraries section.
  const add=otherLibrariesAdd(panel);
  if(add)return takeNavigation(j,add,'فتح نافذة إضافة درس تفاعلي');
  if(j.step==='إظهار المكتبات الأخرى')return false; // Wait for expansion; never toggle it shut.
  const expand=otherLibrariesExpand(panel);
  return expand?takeNavigation(j,expand,'إظهار المكتبات الأخرى'):false;
 }
""" +s[b:]
# Historical route assertions must now assert deletion, not preservation.
files[path]=s.encode()
assert "function otherLibrariesPanel()" in s
assert "function otherLibrariesExpand(panel)" in s
assert "function otherLibrariesAdd(panel)" in s
assert "cards.next(" not in s
assert "cardOpenAttempts" not in s
assert "function contentCoursePath(j)" not in s
assert "function pickNav(j)" in s


# v2.8.92: Correct the genuine Noor in-page modal and link tooltip recognition.
# When teacher manually opens the modal, Resume MUST stage the file rather
# than running navigation again. Never click Submit until all required fields
# are filled. Keep all course and teacher identity checks.
path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
 """ const onUploadPage=()=>/\/teacher\/attachments\/upload\/scorm(?:\/|$)/i.test(location.pathname)
   ||[...document.querySelectorAll('.modal,[role="dialog"],.swal2-popup')]
      .some(el=>visible(el)&&UPLOAD_TITLE.test(norm(el.querySelector('h1,h2,h3,h4,h5,.modal-title,[role="heading"]')?.textContent||'')))
   ||pageHeaders().some(h=>UPLOAD_TITLE.test(h));""",
 """ const uploadDialogs=()=>[...document.querySelectorAll('.modal,[role="dialog"],.swal2-popup,[class*="modal-content"]')]
   .filter(el=>visible(el)&&!inHub(el));
 function openScormDialog(){
  const matches=uploadDialogs().filter(el=>{
   const header=el.querySelector('.modal-title,h1,h2,h3,h4,h5,[role="heading"],.modal-header');
   const name=norm(header?.textContent||'');
   const text=norm(el.textContent||'').slice(0,350);
   const title=/رفع درس تفاعلي جديد|اضافه درس تفاعلي جديد|new interactive lesson|add interactive lesson/i;
   // Noor may use a plain DIV title, not a semantic heading.
   return title.test(name)||title.test(text);
  });
  if(matches.length===1)return matches[0];
  const leaf=matches.filter(el=>!matches.some(other=>other!==el&&el.contains(other)));
  return leaf.length===1?leaf[0]:null;
 }
 const onUploadPage=()=>/\/teacher\/attachments\/upload\/scorm(?:\/|$)/i.test(location.pathname)
   ||Boolean(openScormDialog())||pageHeaders().some(h=>UPLOAD_TITLE.test(h));""",path)
s=replace_exact(s,
 " const isScormForm=()=>onUploadPage()&&Boolean(optionOfRadio('SCORM'));",
 """ const isScormForm=()=>onUploadPage()&&Boolean(optionOfRadio('SCORM'));""",path)
# Inside modal, the heading label may be on a nested icon and styled
# by the popover library. Find exact tooltip across descendants.
s=replace_exact(s,
 """  let links=controls.filter(el=>/add interactive lessons?|upload interactive lesson|اضافه درس تفاعلي|رفع درس تفاعلي/.test(actionMeta(el)));""",
 """  let links=controls.filter(el=>{
   const tooltip=actionMeta(el)+' '+[...el.querySelectorAll('[title],[aria-label],[data-original-title],[data-bs-original-title]')]
    .slice(0,12).map(x=>actionMeta(x)).join(' ');
   return /add interactive lessons?|upload interactive lesson|اضافه درس تفاعلي|رفع درس تفاعلي/.test(tooltip);
  });""",path)
# Most importantly: when the real modal is visible, never try to open any
# other library widget again. A paused task can resume directly into staging.
s=replace_exact(s,
 """   if(!isScormForm()){
    if(!onUploadPage()&&pickNav(j))return;""",
 """   if(!isScormForm()){
    if(openScormDialog()){
     if(waitForPage(j))return;
     throw Error('نافذة رفع الدرس التفاعلي مفتوحة، لكن خيار SCORM لم يُكتشف داخلها. تحقق من وجود خيار SCORM.');
    }
    if(!onUploadPage()&&pickNav(j))return;""",path)
files[path]=s.encode()
assert "function openScormDialog()" in s
assert "if(openScormDialog()){" in s
assert "querySelectorAll('[title],[aria-label]" in s


# v2.8.92 -- ISOLATED SCORM NAVIGATION PILOT. This button never generates,
# attaches, clicks Save, or modifies the existing publishing job.
path="noor-hub.js"
s=files[path].decode()
s=replace_exact(s,
 '    <button id="stnHubScormDiagnose" type="button" class="stnBtn outline">فحص المسار التلقائي لـ SCORM</button>',
 '    <button id="stnHubScormDiagnose" type="button" class="stnBtn outline">فحص المسار التلقائي لـ SCORM</button><button id="stnHubScormTestModal" type="button" class="stnBtn outline">اختبار فتح نافذة الدرس التفاعلي فقط</button>',path)
s=replace_exact(s,
 """  $('stnHubScormDiagnose').addEventListener('click',()=>{""",
 """  $('stnHubScormTestModal').addEventListener('click',async()=>{
   try{
    const choice=selected(),course=choice.course;
    if(!course?.verified||!/^[0-9]+$/.test(String(course.cid||'')))throw Error('اختر أولًا مساقًا موثّقًا من نور.');
    if(!globalThis.NoorScormPublisher?.testModal)throw Error('اختبار الوصول غير محمّل.');
    const result=await globalThis.NoorScormPublisher.testModal(course);
    if(!result?.ok)throw Error('تعذر تشغيل اختبار الوصول.');
    actionStatus('بدأ اختبار الوصول إلى نافذة إضافة درس تفاعلي دون توليد أو حفظ.');
   }catch(e){actionStatus('تعذر اختبار الوصول: '+String(e.message||e));}
  });
  $('stnHubScormDiagnose').addEventListener('click',()=>{""",path)
files[path]=s.encode()

path="noor-scorm-publisher.js"
s=files[path].decode()
s=replace_exact(s,
 """ root.NoorScormPublisher=Object.freeze({start,resume,cancel,onUploadPage,inspect:""",
 """ const MODAL_TEST_KEY='stnScormModalTest:v1';
 const testGet=()=>{try{
  const j=JSON.parse(sessionStorage.getItem(MODAL_TEST_KEY)||'null');
  if(j&&Date.now()-j.at<120000)return j;
 }catch(_){}
  sessionStorage.removeItem(MODAL_TEST_KEY);return null;
 };
 const testSet=j=>sessionStorage.setItem(MODAL_TEST_KEY,JSON.stringify(j));
 const testDone=message=>{sessionStorage.removeItem(MODAL_TEST_KEY);notice(message);};
 async function testModal(course){
  const t=await teacher();
  if(!t||!course?.verified||!/^[0-9]+$/.test(String(course.cid||''))||!course.label)
   throw Error('الصف أو حساب المعلم غير موثّق.');
  const active=get();
  if(active&&active.phase!=='done'&&active.phase!=='paused')
   throw Error('توجد عملية نشر SCORM نشطة. أوقفها أو انتظر اكتمالها قبل الاختبار.');
  const j={cid:String(course.cid),label:course.label,teacherId:t,at:Date.now(),
   tries:0,expandTries:0,addTries:0,step:'فتح محتوى المساق'};
  testSet(j);
  const url=location.origin+'/teacher/courses/browse_content/cid:'+encodeURIComponent(j.cid);
  if(location.href!==url){notice('اختبار فقط: فتح صفحة محتوى المساق…');location.assign(url);}
  else setTimeout(testAdvance,450);
  return {ok:true};
 }
 let testTimer=null;
 async function testAdvance(){
  const j=testGet();if(!j)return;
  clearTimeout(testTimer);
  try{
   if(await teacher()!==j.teacherId)throw Error('تغير حساب المعلم أثناء الاختبار.');
   if(openScormDialog()){testDone('✓ نجح اختبار الوصول: نافذة رفع درس تفاعلي جديد مفتوحة. لم يتم توليد أو رفع أو حفظ أي ملف.');return;}
   const match=location.pathname.match(/^\/teacher\/courses\/browse_content\/cid:([0-9]+)\/?$/i);
   if(!match||match[1]!==j.cid)throw Error('لم نصل إلى صفحة محتوى المساق المحدد.');
   const panel=otherLibrariesPanel();
   if(!panel){
    if(++j.tries<7){testSet(j);testTimer=setTimeout(testAdvance,900);return;}
    throw Error('لم أتعرف على قسم «المكتبات الأخرى» في صفحة المساق بعد التحميل.');
   }
   const add=otherLibrariesAdd(panel);
   if(add){
    if(j.addTries>0){
     if(++j.tries<8){testSet(j);testTimer=setTimeout(testAdvance,950);return;}
     throw Error('ضغطت أيقونة الدروس التفاعلية ولم تظهر نافذة الرفع.');
    }
    j.addTries++;j.step='الضغط على أيقونة الدروس التفاعلية';testSet(j);
    notice('اختبار فقط: الضغط على أيقونة الدروس التفاعلية…');
    add.click();testTimer=setTimeout(testAdvance,1250);return;
   }
   if(!j.expandTries){
    const expand=otherLibrariesExpand(panel);
    if(!expand)throw Error('وجدت «المكتبات الأخرى» ولكن لم أتعرف على سهم توسيعها الأخضر.');
    j.expandTries++;j.step='توسيع المكتبات الأخرى';testSet(j);
    notice('اختبار فقط: فتح أيقونات «المكتبات الأخرى»…');
    expand.click();testTimer=setTimeout(testAdvance,1000);return;
   }
   if(++j.tries<6){testSet(j);testTimer=setTimeout(testAdvance,950);return;}
   throw Error('ضغطت سهم «المكتبات الأخرى» لكن لم أتعرف على أيقونة الدروس التفاعلية.');
  }catch(e){testDone('توقف اختبار فتح النافذة: '+String(e.message||e)+' — لا يوجد توليد أو حفظ.');}
 }
 root.NoorScormPublisher=Object.freeze({start,resume,cancel,testModal,onUploadPage,inspect:""",path)
s=replace_exact(s,
 """ setTimeout(()=>{const j=get();if(j&&!activityInUse()){""",
 """ setTimeout(()=>{if(testGet()){testAdvance();return;}
  const j=get();if(j&&!activityInUse()){""",path)
files[path]=s.encode()
assert "stnHubScormTestModal" in files["noor-hub.js"].decode()
assert "async function testModal(course)" in files["noor-scorm-publisher.js"].decode()
assert "function pickNav(j)" in files["noor-scorm-publisher.js"].decode()
assert "testAdvance()" in files["noor-scorm-publisher.js"].decode()


# v2.8.92: Fix observed "Other Libraries section not found" on actual Noor
# browse_content. The 2.8.85 exact normalized string equality rejected
# real headings with Arabic hamza, whitespace, and nested icon labels.
path="noor-scorm-publisher.js"
s=files[path].decode()
a=s.index(" function otherLibrariesPanel(){")
b=s.index(" function onlyUnique(",a)
if a<0 or b<0:sys.exit("Missing v2.8.85 section recognizer")
s=s[:a]+r""" function otherLibraryArabic(text){
  return String(text||'').normalize('NFKC').replace(/[\u064B-\u065F\u0670\u0640]/g,'')
   .replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي').replace(/\s+/g,' ').trim();
 }
 function isOtherLibraryHeading(text){
  return /^المكتبات الاخري(?:\s*[:：])?$/.test(otherLibraryArabic(text))
   ||/^المكتبات الاخرى(?:\s*[:：])?$/.test(otherLibraryArabic(text));
 }
 function otherLibrariesPanel(){
  // Use the actual TEXT NODE of the section header; Noor may wrap the
  // title in icons or formatted elements. Avoid matching the entire page.
  const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);
  const raw=[];
  for(let node; (node=walker.nextNode());){
   if(!isOtherLibraryHeading(node.nodeValue))continue;
   const el=node.parentElement;
   if(el&&visible(el)&&!inHub(el))raw.push(el);
  }
  const candidates=[...new Set(raw)];
  if(candidates.length!==1)return null;
  const heading=candidates[0];
  for(let el=heading,depth=0;el&&depth<9;el=el.parentElement,depth++){
   if(el===document.body)break;
   const text=otherLibraryArabic(el.textContent);
   // Isolated section = section header + total count, not adjacent panels.
   if(text.length>1100||/(?:الاختبارات|المهام الالكترونيه|الفصول الذكيه).*(?:المكتبات الاخري)/.test(text))continue;
   const count=/المجموع\s*[:：]/.test(text);
   const actions=[...el.querySelectorAll('a,button,[role="button"],[onclick],.fa-arrow-circle-right,.fa-arrow-right')]
     .filter(x=>visible(x)&&!inHub(x));
   if(count&&actions.length)return el;
  }
  // A collapsed Noor panel might not display its counter yet; use the
  // heading's nearest distinct content panel, not the entire document.
  return heading.closest('.panel,.card,[class*="widget"],[class*="panel"]')||
   heading.parentElement?.parentElement||null;
 }
""" +s[b:]
# Expansion detection uses heading regex and chooses green circle; arrows
# frequently are <i> children of a DIV with an onclick handler.
s=s.replace("norm(el.textContent)==='المكتبات الاخرى'","isOtherLibraryHeading(el.textContent)")
s=s.replace("const controls=[...panel.querySelectorAll('a,button,[role=\"button\"],[onclick]')].filter(el=>visible(el)&&!el.disabled);",
"""const controls=[...panel.querySelectorAll('a,button,[role="button"],[onclick],.fa-arrow-circle-right,.fa-arrow-circle-o-right,.fa-arrow-right')]
   .filter(el=>visible(el)&&!el.disabled);""")
files[path]=s.encode()
assert "function otherLibraryArabic(text)" in s
assert "NodeFilter.SHOW_TEXT" in s
assert "function otherLibrariesPanel()" in s


# v2.8.92 - Noor Other Libraries navigation: click expand FIRST,
# wait for revealed icons, then click green PLAY. Do not generate or save.
path="noor-scorm-publisher.js"
s=files[path].decode()
a=s.index(" function otherLibrariesExpand(panel){")
b=s.index(" function pickNav(j){",a)
if a<0 or b<=a:sys.exit("otherLibrariesExpand source not found")
s=s[:a]+r""" function otherLibrariesExpand(panel){
  // The actual Noor control is a green right-arrow circle at the LEFT
  // of the "المكتبات الأخرى" heading. It is not a generic Add button.
  const raw=[...panel.querySelectorAll('*')].filter(el=>
   visible(el)&&!inHub(el)&&isOtherLibraryHeading(el.textContent||'')&&
   ![...el.children].some(c=>isOtherLibraryHeading(c.textContent||'')));
  if(raw.length===0)return null;
  const heading=raw[0];
  const ownHeader=heading.closest('.panel-heading,.card-header,[class*="header"]');
  let header=ownHeader||heading.parentElement;
  for(let i=0;i<3&&header&&!header.querySelector('.fa-arrow-circle-right,.fa-arrow-right,.fa-arrow-circle-o-right,[class*="arrow-circle"],[class*="circle-arrow"],.glyphicon-circle-arrow-right');i++)header=header.parentElement;
  if(!header||header===document.body)return null;
  const arrows=[...header.querySelectorAll(
    '.fa-arrow-circle-right,.fa-arrow-circle-o-right,.fa-arrow-right,.fa-long-arrow-right,.glyphicon-circle-arrow-right,[class*="arrow-circle"],[class*="circle-arrow"],svg[class*="arrow"]'
  )].filter(el=>visible(el)&&!inHub(el));
  // A green arrow may be styled on the anchor itself, not on a child icon.
  const greenButtons=[...header.querySelectorAll('a,button,[role="button"],[onclick]')].filter(el=>
    visible(el)&&!inHub(el)&&
    (/(?:green|success)/i.test(String(el.className))||
     el.querySelector('i[class*="arrow"],svg[class*="arrow"]')));
  const targets=[...new Set([...arrows,...greenButtons].map(el=>el.closest('a,button,[role="button"],[onclick]')||el))]
    .filter(el=>visible(el)&&!inHub(el));
  // Prefer a true arrow-bearing target, and avoid ancestor duplicates.
  const explicit=targets.filter(el=>el.matches('.fa-arrow-circle-right,.fa-arrow-circle-o-right,.fa-arrow-right,.glyphicon-circle-arrow-right')||
   el.querySelector('.fa-arrow-circle-right,.fa-arrow-circle-o-right,.fa-arrow-right,.glyphicon-circle-arrow-right,[class*="arrow-circle"]'));
  const candidate=explicit.length===1?explicit[0]:targets.length===1?targets[0]:null;
  if(candidate&&!/اضافه|add\s/i.test(actionMeta(candidate)))return candidate;
  // Noor's arrow is a white arrow in a green circular background,
  // positioned to the LEFT of the Other Libraries heading.
  const box=heading.getBoundingClientRect();
  const nearby=[...header.querySelectorAll('a,button,[role="button"],[onclick],[data-toggle],[data-bs-toggle],i,span,svg')]
   .filter(el=>{
    if(!visible(el)||inHub(el)||el===heading||el.contains(heading))return false;
    const r=el.getBoundingClientRect();
    if(r.width<22||r.width>88||r.height<22||r.height>88||r.right>box.left+8)return false;
    if(Math.abs((r.top+r.bottom-box.top-box.bottom)/2)>Math.max(30,box.height))return false;
    const target=el.closest('a,button,[role="button"],[onclick],[data-toggle],[data-bs-toggle]')||el;
    if(/اضافه|add\s|play|درس|interactive|video/i.test(actionMeta(target)))return false;
    const paint=[el,target,el.parentElement,target.parentElement].filter((x,i,a)=>x&&header.contains(x)&&a.indexOf(x)===i);
    const green=paint.some(x=>{
     const cs=getComputedStyle(x),before=getComputedStyle(x,'::before'),after=getComputedStyle(x,'::after');
     const vals=[cs.backgroundColor,cs.borderColor,before.backgroundColor,after.backgroundColor];
     return /success|green/i.test(String(x.className))||vals.some(v=>{
      const m=String(v).match(/rgba?\(\s*(\d+)[,\s]+\s*(\d+)[,\s]+\s*(\d+)/);
      return m&&+m[2]>=80&&+m[2]>+m[1]*1.18&&+m[2]>+m[3]*1.08;
     });
    });
    const arrow=paint.some(x=>x.matches?.('svg,i,[class*="arrow"],[class*="right"]')||
     x.querySelector?.('svg,i,[class*="arrow"],[class*="right"]'))||
     /arrow|right/i.test(String(el.className));
    return green&&arrow;
   });
  const nearbyTargets=[...new Set(nearby.map(el=>el.closest('a,button,[role="button"],[onclick],[data-toggle],[data-bs-toggle]')||el))];
  const leaves=nearbyTargets.filter(el=>!nearbyTargets.some(other=>other!==el&&el.contains(other)));
  return leaves.length===1?leaves[0]:null;
 }
 function revealedLessonPlay(panel){
  // Call ONLY after the green section arrow was clicked. The play icon
  // appears in the revealed toolbar and is labeled on hover in Noor.
  const all=[...panel.querySelectorAll('a,button,[role="button"],[onclick],[title],[data-original-title]')]
   .filter(el=>visible(el)&&!inHub(el));
  let candidates=all.filter(el=>{
   const meta=actionMeta(el)+' '+[...el.querySelectorAll('[title],[data-original-title],[data-bs-original-title]')].map(actionMeta).join(' ');
   return /add interactive lessons?|اضافه درس تفاعلي|رفع درس تفاعلي/.test(meta);
  });
  if(candidates.length){
   const leaf=candidates.filter(el=>!candidates.some(other=>other!==el&&el.contains(other)));
   const targets=[...new Set(leaf.map(actionTarget))];
   if(targets.length===1)return targets[0];
  }
  candidates=all.filter(el=>el.querySelector('.fa-play-circle,.fa-play-circle-o,.fa-play,.glyphicon-play,[class*="icon-play"]')&&
   (/(?:green|success)/i.test(String(el.className))||/rgb\(\s*(?:[0-9]{1,2}|1[0-2][0-9])\s*,\s*(?:1[2-9][0-9]|2[0-5][0-9])\s*,/.test(getComputedStyle(el).color)));
  const targets=[...new Set(candidates.map(actionTarget))];
  return targets.length===1?targets[0]:null;
 }
""" +s[b:]
# Pilot must never try the play icon until it has EXPANDED via green arrow.
a=s.index("   const add=otherLibrariesAdd(panel);",s.index(" async function testAdvance(){"))
b=s.index("  }catch(e){testDone(",a)
if a<0 or b<=a:sys.exit("testAdvance block not found")
s=s[:a]+r"""   if(!j.expandTries){
    const expand=otherLibrariesExpand(panel);
    if(!expand)throw Error('وجدت المكتبات الأخرى، لكن لم أجد السهم الأخضر الدائري بجوار عنوان القسم.');
    j.expandTries=1;j.step='تم الضغط على سهم المكتبات الأخرى';j.tries=0;testSet(j);
    notice('المرحلة 1/3: الضغط على السهم الأخضر لتوسيع المكتبات الأخرى…');
    expand.click();
    testTimer=setTimeout(testAdvance,1100);
    return;
   }
   const add=revealedLessonPlay(panel);
   if(!add){
    if(++j.tries<8){
     testSet(j);testTimer=setTimeout(testAdvance,850);return;
    }
    throw Error('تم الضغط على السهم الأخضر، لكن أيقونات المكتبات الأخرى لم تظهر أو تعذر تحديد زر التشغيل الأخضر.');
   }
   if(!j.addTries){
    j.addTries=1;j.step='تم الضغط على أيقونة الدروس التفاعلية';j.tries=0;testSet(j);
    notice('المرحلة 2/3: ظهرت الأيقونات؛ الضغط على التشغيل الأخضر للدروس التفاعلية…');
    add.click();testTimer=setTimeout(testAdvance,1150);return;
   }
   if(++j.tries<8){testSet(j);testTimer=setTimeout(testAdvance,850);return;}
   throw Error('تم الضغط على أيقونة الدروس التفاعلية لكن لم تظهر نافذة رفع درس تفاعلي جديد.');
""" +s[b:]
# Production SCORM route should also enforce arrow before play, reusing same helpers
a=s.index(" function pickNav(j){");b=s.index(" function nearText(el){",a)
if a<0 or b<=a:sys.exit("pickNav section not found")
s=s[:a]+r""" function pickNav(j){
  if(!/^\/teacher\/courses\/browse_content\/cid:/i.test(location.pathname))
   throw Error('مسار SCORM الجديد يتطلب صفحة محتوى المساق الموثقة.');
  if(!sameCourseContent(j))throw Error('صفحة المحتوى لا تطابق المساق المختار.');
  const panel=otherLibrariesPanel();if(!panel)return false;
  if(j.step!=='إظهار المكتبات الأخرى'&&j.step!=='فتح نافذة إضافة درس تفاعلي'){
   const expand=otherLibrariesExpand(panel);
   return expand?takeNavigation(j,expand,'إظهار المكتبات الأخرى'):false;
  }
  const add=revealedLessonPlay(panel);
  if(add&&j.step!=='فتح نافذة إضافة درس تفاعلي')
   return takeNavigation(j,add,'فتح نافذة إضافة درس تفاعلي');
  return false;
 }
""" +s[b:]
files[path]=s.encode()
assert "function revealedLessonPlay(panel)" in s
assert "if(!j.expandTries){" in s
assert "المرحلة 1/3" in s


# v2.8.92: interactive lessons icon is a TWO-CLICK Noor control.
# First click reveals "Add interactive lessons", second opens modal.
path="noor-scorm-publisher.js"
s=files[path].decode()
needle="""   if(!j.addTries){
    j.addTries=1;j.step='تم الضغط على أيقونة الدروس التفاعلية';j.tries=0;testSet(j);
    notice('المرحلة 2/3: ظهرت الأيقونات؛ الضغط على التشغيل الأخضر للدروس التفاعلية…');
    add.click();testTimer=setTimeout(testAdvance,1150);return;
   }
   if(++j.tries<8){testSet(j);testTimer=setTimeout(testAdvance,850);return;}
   throw Error('تم الضغط على أيقونة الدروس التفاعلية لكن لم تظهر نافذة رفع درس تفاعلي جديد.');"""
replacement=r"""   if(j.addTries<2){
    // In Noor the first click reveals the "Add interactive lessons"
    // caption/tooltip. The second click actually opens the modal.
    const first=j.addTries===0;
    j.addTries++;j.step=first?'إظهار اسم أيقونة الدروس التفاعلية':'فتح نافذة الدرس التفاعلي';
    j.tries=0;testSet(j);
    notice(first?'المرحلة 2/3: إظهار اسم Add interactive lessons…':
      'المرحلة 3/3: الضغط مرة ثانية لفتح نافذة الدرس التفاعلي…');
    add.click();testTimer=setTimeout(testAdvance,1000);return;
   }
   if(++j.tries<8){testSet(j);testTimer=setTimeout(testAdvance,850);return;}
   throw Error('تم الضغط مرتين على أيقونة الدروس التفاعلية لكن لم تظهر نافذة رفع درس تفاعلي جديد.');"""
s=replace_exact(s,needle,replacement,path)
files[path]=s.encode()
assert "if(j.addTries<2)" in s
assert "الضغط مرة ثانية" in s

# v2.8.92: restore the proven card -> page 3 -> Digital Library SCORM publisher.
# The current task is generated first; the teacher opens the matching course card,
# then presses Resume. Restore the publisher from the clean 2.8.64 base, whose
# pickNav follows the card pager and original Digital Library path.
files["noor-scorm-publisher.js"] = base_scorm_publisher

# Remove all direct opaque-URL routing from the SCORM launch path.
path = "noor-hub.js"
s = files[path].decode()
s = s.replace("  const directScormUrl=await scormDirectLink(opts);\\n", "")
s = s.replace("  const directScormUrl=opts.service==='scorm'?await scormDirectLink(opts):'';\\n", "")
s = s.replace("publishDate,directScormUrl,imageMode:scormImageMode(),", "publishDate,imageMode:scormImageMode(),")
s = s.replace("...opts,directScormUrl:j.directScormUrl||'',teacherId:j.teacherId", "...opts,teacherId:j.teacherId")
files[path] = s.encode()

# Hide the image-mode selector. The add-on now tries the configured Gemini
# image models in order automatically, then uses the existing SVG fallback.
s = files[path].decode()
old = """    <label for="stnHubScormImageMode">الصورة المصاحبة للنشاط</label>
    <select id="stnHubScormImageMode">
      <option value="gemini_svg">صورة Gemini ثلاثية الأبعاد؛ عند تعذرها استخدم SVG</option>
      <option value="gemini_none">صورة Gemini ثلاثية الأبعاد؛ عند تعذرها بدون صورة</option>
      <option value="svg">رسم SVG تعليمي دون استدعاء Gemini للصور</option>
      <option value="none">بدون صورة (مباشرة)</option>
    </select>
    <p class="stnNote">عند نفاد رصيد صور Gemini أو رفض الخطة (مثل 429)، يستمر إنشاء SCORM بالخيار المحدد. SVG رسم متجهي محلي، وليس صورة ثلاثية الأبعاد من Gemini.</p>"""
new = """    <input type="hidden" id="stnHubScormImageMode" value="gemini_svg">
    <p class="stnNote">تُجرّب نماذج صور Gemini المتاحة تلقائيًا بالترتيب؛ وإذا تعذرت جميعها يُستخدم رسم SVG محلي حتى لا يتوقف إنشاء الدرس.</p>"""
if old not in s: raise SystemExit("image selector HTML anchor missing")
s = s.replace(old,new,1)
# Force automatic Gemini -> SVG mode regardless of any older saved preference.
oldmode = """ function scormImageMode(){
  const mode=$('stnHubScormImageMode').value;
  return ['gemini_svg','gemini_none','svg','none'].includes(mode)?mode:'gemini_svg';
 }"""
newmode = """ function scormImageMode(){
  return 'gemini_svg';
 }"""
if oldmode not in s: raise SystemExit("image mode function anchor missing")
s = s.replace(oldmode,newmode,1)
files[path] = s.encode()

# Try each supported image model in order. Model-specific unavailability,
# overload, quota and transient server failures advance to the next model.
path = "gemini-background.js"
s = files[path].decode()
old = """   }catch(e){return {ok:false,error:'تعذر الاتصال بخدمة صور Gemini: '+String(e?.message||e).slice(0,140)}}
   if(!response.ok){
    const status=response.status;
    if(status===404||status===400){if(model==='gemini-2.5-flash-image')continue;}
    const data=await response.json().catch(()=>({}));
    const detail=String(data?.error?.message||'Google HTTP '+status).replaceAll(key,'[hidden]').slice(0,170);
    return {ok:false,error:'تعذر توليد صورة Gemini ('+status+'): '+detail};
   }"""
new = """   }catch(e){
    if(model!=='gemini-3.1-flash-image')continue;
    return {ok:false,error:'تعذر الاتصال بنماذج صور Gemini المتاحة: '+String(e?.message||e).slice(0,140)};
   }
   if(!response.ok){
    const status=response.status;
    if([400,404,429,500,502,503,504].includes(status))continue;
    const data=await response.json().catch(()=>({}));
    const detail=String(data?.error?.message||'Google HTTP '+status).replaceAll(key,'[hidden]').slice(0,170);
    return {ok:false,error:'تعذر توليد صورة Gemini ('+status+'): '+detail};
   }"""
if old not in s: raise SystemExit("Gemini image response handling anchor missing")
s=s.replace(old,new,1)
old2="""   return {ok:false,error:'لم يرجع نموذج Gemini صورة فعلية. لم أستخدم رسم SVG بديلًا.'};
  }
  return {ok:false,error:'لا يتوفر نموذج توليد صور Gemini لهذا المفتاح.'};"""
new2="""   // A model may return text or an empty candidate instead of image bytes.
   // Continue to the next configured image model before using the local fallback.
   continue;
  }
  return {ok:false,error:'تعذرت نماذج صور Gemini المتاحة بالتتابع؛ سيُستخدم SVG المحلي كخيار احتياطي.'};"""
if old2 not in s: raise SystemExit("Gemini no-image response anchor missing")
s=s.replace(old2,new2,1)
files[path]=s.encode()

# The hidden mode field is fixed to automatic mode; remove legacy user preference restore.
path = "noor-hub.js"
s = files[path].decode()
s = s.replace("  $('stnHubScormImageMode').addEventListener('change',()=>{try{sessionStorage.setItem('stnNoorScormImageMode:v1',scormImageMode())}catch(_){}});", "")
s = s.replace("  try{const mode=sessionStorage.getItem('stnNoorScormImageMode:v1');if(['gemini_svg','gemini_none','svg','none'].includes(mode))$('stnHubScormImageMode').value=mode}catch(_){}", "")
files[path]=s.encode()

assert base_scorm_publisher is not None
assert "return 'gemini_svg';" in s
assert "gemini-3.1-flash-image')continue" in files["gemini-background.js"].decode()
assert "cards.next({label:j.label},3,REPOSITORY_ACTION)" in files["noor-scorm-publisher.js"].decode()

# Regression checks: retain the original digital-library publisher exactly.
with ZipFile(sources[0]) as original:
    assert files["noor-scorm-publisher.js"]==original.read("noor-scorm-publisher.js")
assert "stnHubScormReference" not in files["noor-hub.js"].decode()
assert "await curriculum.start({...inputs(),cid:opts.course.cid,label:opts.course.label,purpose:'scorm'})" not in files["noor-hub.js"].decode()
assert "cards.next(" in files["noor-scorm-publisher.js"].decode()
assert "function treeCandidate(j)" in files["noor-scorm-publisher.js"].decode()
assert "const gradeMatches=Number.isInteger(selectedGrade)" in files["noor-hub.js"].decode()


# 2.8.93 -- compact, low-obstruction teacher UI. Keep every workflow and
# control functional; remove only redundant navigation/diagnostic buttons.
path = "noor-hub.css"
s = files[path].decode()
s += """
/* 2.8.93 compact teacher panel */
#stnNoorHub .stnHubPanel{
 width:min(318px,calc(100vw - 16px));
 max-height:min(58dvh,520px);
 padding:8px;
 border-radius:12px;
 box-shadow:0 5px 18px #061e1733;
}
#stnNoorHub .stnHead{font-size:13px;margin-bottom:5px;padding:3px 2px}
#stnNoorHub .stnHeadButtons{gap:3px}
#stnNoorHub .stnHeadButtons button{min-width:27px;min-height:27px;font-size:20px}
#stnNoorHub .stnHubTaskPicker{gap:6px;margin:2px 0 5px}
#stnNoorHub .stnHubTaskPicker label{margin:0;font-size:11px;white-space:nowrap}
#stnNoorHub .stnHubTaskPicker select{min-height:31px;padding:4px 7px}
#stnNoorHub #stnHubDetails{padding-top:2px}
#stnNoorHub #stnHubOtherTab,
#stnNoorHub #stnHubScormDiagnose,
#stnNoorHub #stnHubScormTestModal{display:none!important}
#stnNoorHub label{font-size:11px;margin:5px 0 2px}
#stnNoorHub select,
#stnNoorHub input:not([type=file]),
#stnNoorHub textarea{min-height:31px;padding:5px 7px;border-radius:7px}
#stnNoorHub .stnTeacherTree{padding:6px;margin:5px 0;border-radius:8px}
#stnNoorHub .stnTeacherTree .stnBtn{margin-top:5px}
#stnNoorHub .stnHubChecks{grid-template-columns:repeat(2,minmax(0,1fr));gap:2px 6px;margin:3px 0 6px;padding:5px 7px;border-radius:8px}
#stnNoorHub .stnHubChecks label{font-size:10px;line-height:1.45;margin:0;gap:4px}
#stnNoorHub .stnActions{gap:5px;margin-top:6px}
#stnNoorHub .stnBtn{padding:7px 6px;border-radius:7px;font-size:11px}
#stnNoorHub .stnNote{display:none!important}
#stnNoorHub .stnStatus{font-size:11px;line-height:1.45;padding:5px 7px;margin-top:6px;border-radius:7px}
#stnNoorHub .stnStatus:empty{display:none}
#stnNoorHub .stnPreview{max-height:100px;margin-top:5px;font-size:11px}
#stnNoorHub .stnHubTabs{gap:4px;margin:2px 0 5px;padding:4px 0}
#stnNoorHub .stnHubTabs button{min-height:30px;font-size:11px;border-radius:7px}
#stnNoorHub .stnHubLanguage{padding:2px 0;font-size:10px}
#stnNoorHub .stnHubLanguage select{min-height:27px;min-width:5.5rem;padding:3px 5px}
#stnNoorHub .stnHubMinimized{width:min(250px,calc(100vw - 16px));max-height:72px}
@media(max-width:520px){
 #stnNoorHub .stnHubPanel{width:min(310px,calc(100vw - 16px));max-height:56dvh;padding:7px}
 #stnNoorHub .stnHubChecks{grid-template-columns:repeat(2,minmax(0,1fr))}
 #stnNoorHub .stnHead{font-size:12px}
}
"""
files[path] = s.encode()

# 2.8.97: restore a readable single-column task form and responsive panel sizing.
# Keep compact controls without turning the entire details container into a grid.
s = files[path].decode()
s += """

/* 2.8.102 compact teacher controls and language switch */
#stnNoorHub .stnLangToggle{min-width:34px!important;height:30px!important;min-height:30px!important;padding:3px 7px!important;border:1px solid #ffffff55!important;border-radius:9px!important;background:#ffffff18!important;color:#fff!important;font-size:11px!important;font-weight:800!important;line-height:1!important}
#stnNoorHub .stnHubLanguage[hidden]{display:none!important}
#stnNoorHub .stnHubChecks{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:5px 10px!important;padding:7px!important;margin:5px 0 7px!important}
#stnNoorHub .stnHubChecks label{display:flex!important;align-items:center!important;gap:6px!important;min-height:28px!important;margin:0!important;padding:2px 4px!important;font-size:11px!important;line-height:1.3!important}
#stnNoorHub .stnHubChecks input[type=checkbox],#stnNoorHub .stnHubChecks input[type=radio]{appearance:auto!important;-webkit-appearance:auto!important;width:17px!important;height:17px!important;min-width:17px!important;min-height:17px!important;margin:0 2px!important;padding:0!important;accent-color:#08745a!important;transform:none!important}
#stnNoorHub .stnActions{gap:6px!important;margin-top:8px!important}
#stnNoorHub .stnActions .stnBtn{min-height:34px!important;height:auto!important;padding:6px 8px!important;border-radius:9px!important;font-size:11px!important;line-height:1.35!important}
#stnNoorHub #stnHubDetails label{font-size:11px!important;margin:5px 0 3px!important}
#stnNoorHub #stnHubDetails select,#stnNoorHub #stnHubDetails input:not([type=file]),#stnNoorHub #stnHubDetails textarea{min-height:36px!important;padding:6px 9px!important;border-radius:9px!important;font-size:12px!important}
#stnNoorHub #stnHubDetails .stnTeacherTree .stnBtn,#stnNoorHub #stnHubDetails button{min-height:34px!important;padding:6px 9px!important;font-size:11px!important}
@media(max-width:520px){#stnNoorHub .stnHubPanel{max-height:78dvh!important;padding:9px!important}#stnNoorHub .stnHubChecks{grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:4px!important}#stnNoorHub .stnHubChecks label{font-size:10px!important}}

/* 2.8.102 responsive panel and readable task form */
#stnNoorHub .stnHubPanel{
 width:min(520px,calc(100vw - 24px))!important;
 max-width:calc(100vw - 24px)!important;
 max-height:82dvh!important;
 padding:12px!important;
}
#stnNoorHub .stnHubPanel #stnHubDetails{
 display:block!important;
 width:100%!important;
 min-width:0!important;
}
#stnNoorHub #stnHubDetails > *{
 box-sizing:border-box!important;
 min-width:0!important;
 max-width:100%!important;
}
#stnNoorHub #stnHubDetails > div,
#stnNoorHub #stnHubClassFields,
#stnNoorHub #stnHubLessonChoiceBox,
#stnNoorHub #stnHubScormOptions,
#stnNoorHub #stnHubActivityOptions,
#stnNoorHub #stnHubExamOptions{
 width:100%!important;
 min-width:0!important;
}
#stnNoorHub #stnHubDetails label{
 display:block!important;
 max-width:100%!important;
 margin:8px 0 4px!important;
 font-size:12px!important;
 line-height:1.45!important;
 white-space:normal!important;
 overflow-wrap:anywhere!important;
}
#stnNoorHub #stnHubDetails input:not([type=hidden]):not([type=checkbox]):not([type=radio]),
#stnNoorHub #stnHubDetails select,
#stnNoorHub #stnHubDetails textarea{
 display:block!important;
 width:100%!important;
 min-width:0!important;
 max-width:100%!important;
 min-height:38px!important;
 height:auto!important;
 padding:7px 9px!important;
 font-size:13px!important;
}
#stnNoorHub #stnHubDetails .stnRow{
 display:grid!important;
 grid-template-columns:repeat(2,minmax(0,1fr))!important;
 gap:8px!important;
 width:100%!important;
}
#stnNoorHub .stnActions{
 display:flex!important;
 flex-flow:row wrap!important;
 align-items:stretch!important;
 gap:7px!important;
}
#stnNoorHub .stnActions > *,
#stnNoorHub .stnActions .stnBtn{
 flex:1 1 125px!important;
 min-width:0!important;
 max-width:100%!important;
}
#stnNoorHub .stnBtn{
 box-sizing:border-box!important;
 min-height:38px!important;
 height:auto!important;
 max-height:none!important;
 padding:7px 9px!important;
 font-size:12px!important;
 line-height:1.35!important;
 white-space:normal!important;
 overflow:visible!important;
 overflow-wrap:anywhere!important;
}
#stnNoorHub button{font-size:12px!important}
#stnNoorHub input[type=checkbox],
#stnNoorHub input[type=radio]{
 width:17px!important;
 height:17px!important;
 min-height:17px!important;
 flex:0 0 auto!important;
}
@media(max-width:520px){
 #stnNoorHub .stnHubPanel{
  width:calc(100vw - 24px)!important;
  max-width:calc(100vw - 24px)!important;
  max-height:82dvh!important;
  padding:10px!important;
 }
 #stnNoorHub #stnHubDetails .stnRow{
  grid-template-columns:repeat(2,minmax(0,1fr))!important;
 }
 #stnNoorHub #stnHubDetails label{font-size:11px!important}
 #stnNoorHub .stnBtn{font-size:11px!important}
}
"""
files[path] = s.encode()


# Lesson-grounded activity generation: retrieve the saved preparation for the
# exact verified Noor lesson and combine it with Google Search curriculum sources.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s,
"""  const generated=await globalThis.NoorSmartHub.generate({unit:opts.unit,lesson:opts.lesson,count:opts.count,courseProof,kinds});""",
"""   const refKey=resolved.lessonId?lessonReferenceKey(opts.course.cid,resolved.lessonId):'';
   const savedPrep=refKey?(await browser.storage.local.get(refKey))[refKey]:null;
   const prepFields=[
    ['الأهداف التعليمية',savedPrep?.objectives],
    ['المفاهيم والمصطلحات',savedPrep?.concepts],
    ['التمهيد',savedPrep?.warmUp],
    ['خطوات وإجراءات التدريس',savedPrep?.procedures],
    ['التقويم والتدريب',savedPrep?.formative],
    ['التقويم الختامي',savedPrep?.closing],
    ['ملاحظات المعلم',savedPrep?.details]
   ].filter(([,value])=>String(value||'').trim())
    .map(([label,value])=>label+': '+String(value).trim()).join('\\n');
   const prepText=prepFields.slice(0,2600);
   const sourceFocus=[
    'STRICT LESSON IDENTITY — do not change, broaden or replace this lesson.',
    'Subject: '+opts.subject+'; Grade: '+opts.course.grade+'; Unit: '+opts.unit+'; Exact lesson: '+opts.lesson+'.',
    'The selected Noor lesson is the only assessment scope. Do not use a neighboring lesson or another topic from the same unit.',
    'RESEARCH REQUIRED: search online for the Oman Ministry of Education curriculum sources for this exact grade, subject, unit and lesson. Search separately for the Student Book, Activity Book/Workbook, and Teacher Guide. Prefer official Oman Ministry sources and documents. Use only sources whose grade, subject and lesson match. Use the Student Book for taught concepts/examples, the Activity Book for practice formats, and the Teacher Guide for objectives, misconceptions and pedagogy.',
    'SOURCE SAFETY: cite the actual source title and URL in warnings. If one source type cannot be found, say so. Never invent page numbers, quotations, exercises, answer keys or textbook content. If a source is missing, use only the saved preparation and verifiable search material.',
    'QUESTION QUALITY: every question must assess the exact lesson concept, not merely the unit theme. Reject any generated question about another topic.',
    savedPrep?'SAVED TEACHER PREPARATION — PRIMARY SOURCE (use before web sources):\\n'+prepText:
     'No saved teacher preparation was found for this exact lesson. Do not pretend one exists.'
   ].join('\\n').slice(0,4800);
   const generated=await globalThis.NoorSmartHub.generate({unit:opts.unit,lesson:opts.lesson,count:opts.count,courseProof,kinds,focus:sourceFocus});""",
 path)
files[path] = s.encode()

path = "smart/src/noor-panel.js"
s = files[path].decode()
s = replace_exact(s,
  'maxlength="800" placeholder="مثال: Renewable Energy – solar and wind"',
  'maxlength="5200" placeholder="موضوع النشاط أو تعليمات المعلم (اختياري)"', path)
s = replace_exact(s,
  "$('geminiFocus').value=String(options.focus||'').slice(0,800);",
  "$('geminiFocus').value=String(options.focus||'').slice(0,4800);", path)
files[path] = s.encode()

path = "smart/src/noor-gemini.js"
s = files[path].decode()
s = replace_exact(s,
  "const instructions=trim(input.description,1800);",
  "const instructions=trim(input.description,5000);", path)
files[path] = s.encode()

path = "smart-background.js"
s = files[path].decode()
if s.count("Focus: ${c.description}.") != 1:
    raise SystemExit("Could not locate activity focus prompt")
s = s.replace("Focus: ${c.description}.", "Teacher source brief and exact lesson lock: ${c.description}.", 1)
research_anchor = "   const schema="
research_code = """   const research=`MANDATORY CURRICULUM RESEARCH USING THE ENABLED GOOGLE SEARCH TOOL:
Search for the exact Oman Ministry of Education curriculum materials for Grade ${c.grade}, subject ${c.subject}, Unit ${c.unit}, Lesson ${c.lesson}. Run separate searches for:
1) Oman Grade ${c.grade} ${c.subject} Student Book ${c.unit} ${c.lesson};
2) Oman Grade ${c.grade} ${c.subject} Activity Book or Workbook ${c.unit} ${c.lesson};
3) Oman Grade ${c.grade} ${c.subject} Teacher Guide ${c.unit} ${c.lesson}.
Prefer official Ministry of Education sources and exact matching editions. Use Student Book content to establish what was taught, Activity Book content for age-appropriate practice, and Teacher Guide content for lesson objectives, misconceptions and teaching emphasis. Verify the grade, subject and lesson before using a source. The exact lesson title is a strict boundary: never replace it with a different topic merely because that topic appears elsewhere in the same unit. If a source cannot be located or verified, report that fact in warnings and do not invent its contents, pages, quotations or answer keys. If the teacher brief contains a saved preparation, it is the primary source and web material only supplements it.`;
"""
if "const schema=" not in s:
    raise SystemExit("Could not locate activity schema insertion point")
s = s.replace("const schema=", research_code + "const schema=", 1)
old_return = r"return rules+'\n'+schema"
new_return = r"return rules+'\n'+(mode==='generate'?research+'\n':'')+schema"
if s.count(old_return) != 1:
    raise SystemExit("Could not locate activity prompt return")
s = s.replace(old_return,new_return,1)
old_body = "const body={contents:[{role:'user',parts}],generationConfig:{responseMimeType:'application/json',temperature:mode==='pdf'?0.1:0.4,maxOutputTokens:16000}};"
new_body = "const body={contents:[{role:'user',parts}],generationConfig:{responseMimeType:'application/json',temperature:mode==='pdf'?0.1:0.4,maxOutputTokens:16000},...(mode==='generate'?{tools:[{googleSearch:{}}]}:{})};"
if s.count(old_body) != 1:
    raise SystemExit("Could not locate Gemini generateContent body")
s = s.replace(old_body,new_body,1)
old_result = "return {ok:true,questions:parsed.questions.slice(0,mode==='pdf'?60:30),warnings:Array.isArray(parsed.warnings)?parsed.warnings.map(x=>trim(x,250)).slice(0,20):[],needsReview:true,modelUsed:generated.model};"
new_result = """const candidate=result?.candidates?.[0]||{};
   const grounding=candidate.groundingMetadata||candidate.grounding_metadata||{};
   const chunks=Array.isArray(grounding.groundingChunks)?grounding.groundingChunks:[];
   const sources=[...new Map(chunks.map(chunk=>chunk.web||chunk).filter(source=>source?.uri)
    .map(source=>[source.uri,{title:trim(source.title||source.uri,180),uri:trim(source.uri,500)}])).values()].slice(0,12);
   const queries=Array.isArray(grounding.webSearchQueries)?grounding.webSearchQueries.map(x=>trim(x,180)).slice(0,8):[];
   const warnings=Array.isArray(parsed.warnings)?parsed.warnings.map(x=>trim(x,250)).slice(0,16):[];
   if(sources.length)warnings.push('مصادر Google Search المستخدمة: '+sources.map(x=>x.title+' — '+x.uri).join(' | ').slice(0,1800));
   else if(mode==='generate')warnings.push('لم يُرجع بحث Google مصادر ويب قابلة للتوثيق لهذا الطلب؛ راجع الأسئلة مع التحضير قبل اعتمادها.');
   if(queries.length)warnings.push('عبارات البحث: '+queries.join(' | ').slice(0,700));
   return {ok:true,questions:parsed.questions.slice(0,mode==='pdf'?60:30),warnings:warnings.slice(0,20),sources,searchQueries:queries,needsReview:true,modelUsed:generated.model};"""
if s.count(old_result) != 1:
    raise SystemExit("Could not locate Gemini activity result")
s = s.replace(old_result,new_result,1)
files[path] = s.encode()

hub=files["noor-hub.js"].decode()
smart=files["smart-background.js"].decode()
panel=files["smart/src/noor-panel.js"].decode()
gemini=files["smart/src/noor-gemini.js"].decode()
assert "SAVED TEACHER PREPARATION — PRIMARY SOURCE" in hub
assert "lessonReferenceKey(opts.course.cid,resolved.lessonId)" in hub
assert "focus:sourceFocus" in hub
assert "MANDATORY CURRICULUM RESEARCH USING THE ENABLED GOOGLE SEARCH TOOL" in smart
assert "tools:[{googleSearch:{}}]" in smart
assert "groundingChunks" in smart and "webSearchQueries" in smart
assert "slice(0,4800)" in panel and "trim(input.description,5000)" in gemini

# Compact build invariants: retain the primary actions and task-specific fields.
hub = files["noor-hub.js"].decode()
for required in ['id="stnHubService"','id="stnHubClass"','id="stnHubUnit"','id="stnHubLesson"','id="stnHubGenerate"']:
    if required not in hub:
        raise SystemExit("Compact UI would remove a required control: " + required)
css = files["noor-hub.css"].decode()
for required in ['#stnHubOtherTab','#stnHubScormDiagnose','#stnHubScormTestModal','max-height:min(58dvh,520px)']:
    if required not in css:
        raise SystemExit("Compact CSS missing " + required)


# 2.8.102 approved identity and mobile task-card workspace.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s, 'title="اضغط للفتح، واسحب لنقل الزر">🧩 أدوات نور</button>',
    'title="دفتر نور — اضغط للفتح واسحب لتغيير المكان">📘 دفتر نور</button>', path)
s = replace_exact(s, 'aria-label="أدوات نور الموحدة"', 'aria-label="دفتر نور"', path)
s = replace_exact(s, 'أدوات نور · دفتر المعلم <bdi class="stnHubVersion">', 'دفتر نور <bdi class="stnHubVersion">', path)
s = replace_exact(s, '<div class="stnHubTaskPicker"><label for="stnHubService">المهمة</label><select id="stnHubService">',
    '<div class="stnHubTaskPicker" aria-label="اختر المهمة"><button type="button" class="stnTaskCard" data-service="preparation"><span>✎</span>التحضير</button><button type="button" class="stnTaskCard" data-service="activities"><span>▦</span>النشاط</button><button type="button" class="stnTaskCard" data-service="scorm"><span>▣</span>SCORM</button><select id="stnHubService" aria-hidden="true" tabindex="-1">', path)
anchor = " const taskService=()=>$('stnHubService').value;"
if anchor not in s: raise SystemExit("Task service helper anchor missing")
s = replace_exact(s, anchor, anchor + """
 root.querySelectorAll('.stnTaskCard').forEach(button=>{
  button.addEventListener('click',async()=>{
   const service=$('stnHubService'),task=button.dataset.service;
   if(!['preparation','activities','scorm'].includes(task))return;
   service.value=task;
   sessionStorage.setItem(serviceStorageKey(),task);
   root.querySelectorAll('.stnTaskCard').forEach(item=>item.classList.toggle('active',item===button));
   try{await switchTask(task);}
   catch(error){actionStatus('تعذر فتح المهمة: '+String(error?.message||error));}
  });
 });

 // Compact language toggle: reuse the existing localization engine.
 const languageWrap=root.querySelector('.stnHubLanguage');
 const languageSelect=languageWrap?.querySelector('select');
 const headButtons=root.querySelector('.stnHeadButtons');
 if(languageSelect&&headButtons&&!headButtons.querySelector('.stnLangToggle')){
  languageWrap.hidden=true;
  const toggle=document.createElement('button');
  toggle.type='button';toggle.className='stnLangToggle';
  const languageLabel=()=>{const v=String(languageSelect.value||'').toLowerCase();return /^(en|english)/.test(v)?'EN':'عربي';};
  toggle.textContent=languageLabel();
  toggle.setAttribute('aria-label','تغيير لغة الواجهة');
  toggle.addEventListener('click',()=>{
   const options=[...languageSelect.options],current=languageSelect.selectedIndex;
   const target=options.findIndex((o,i)=>i!==current&&(/english|\\ben\\b/i.test(o.textContent+' '+o.value)));
   languageSelect.selectedIndex=target>=0?target:(current+1)%Math.max(1,options.length);
   languageSelect.dispatchEvent(new Event('change',{bubbles:true}));
   toggle.textContent=languageLabel();
  });
  headButtons.append(toggle);
 }


 // 2.8.104: class + numeric unit/lesson selectors precede task cards.
 const taskPicker=root.querySelector('.stnHubTaskPicker');
 const selectionClassSelect=$('stnHubClass');
 const classLabel=root.querySelector('label[for="stnHubClass"]');
 const unitLessonRow=root.querySelector('#stnHubLessonChoiceBox .stnRow');
 if(!taskPicker||!selectionClassSelect||!classLabel||!unitLessonRow)throw new Error('تعذر تجهيز شريط اختيار الصف والدرس.');
 const selectionDock=document.createElement('section');
 selectionDock.className='stnSelectionDock';
 selectionDock.setAttribute('aria-label','تحديد الصف والدرس قبل اختيار المهمة');
 const classField=document.createElement('div');classField.className='stnSelectionField';
 classField.append(classLabel,selectionClassSelect);
 const classRow=document.createElement('div');classRow.className='stnSelectionClass';
 classRow.append(classField);
 const selectionTitle=document.createElement('div');
 selectionTitle.className='stnSelectionCaption';selectionTitle.textContent='أولًا: اختر الصف ورقم الوحدة والدرس';
 selectionDock.append(selectionTitle,classRow,unitLessonRow);
 taskPicker.before(selectionDock);
 selectionClassSelect.required=true;
 for(const id of ['stnHubOpenCurriculumTree','stnHubSelectedPath','stnHubRefreshTree','stnHubLessonPreview']){
  const el=$(id);if(el)el.hidden=true;
 }
 const semesterLabel=root.querySelector('label[for="stnHubSemester"]');
 if(semesterLabel)semesterLabel.hidden=true;
 $('stnHubSemester').hidden=true;
 const syncTaskAvailability=()=>{
  const ready=Boolean(selectionClassSelect.value&&position($('stnHubUnit').value)&&position($('stnHubLesson').value));
  root.querySelectorAll('.stnTaskCard').forEach(card=>{
   card.disabled=!ready;card.setAttribute('aria-disabled',String(!ready));
   card.title=ready?'':'اختر الصف ورقم الوحدة والدرس أولًا';
  });
 };
 selectionClassSelect.addEventListener('change',syncTaskAvailability);
 $('stnHubUnit').addEventListener('input',syncTaskAvailability);
 $('stnHubLesson').addEventListener('input',syncTaskAvailability);
 syncTaskAvailability();
 // 2.8.105: class first, then numeric unit and lesson coordinates.
 const unitInput=$('stnHubUnit'),lessonInput=$('stnHubLesson');
 const unitLabel=root.querySelector('label[for="stnHubUnit"]');
 const lessonLabel=root.querySelector('label[for="stnHubLesson"]');
 if(!unitInput||!lessonInput||!unitLabel||!lessonLabel)throw new Error('حقلا رقم الوحدة ورقم الدرس غير متاحين.');
 for(const [input,label,text] of [[unitInput,unitLabel,'رقم الوحدة'],[lessonInput,lessonLabel,'رقم الدرس']]){
  input.type='number';input.inputMode='numeric';input.min='1';input.max='99';input.step='1';
  input.placeholder=text;input.setAttribute('aria-label',text);label.textContent=text;input.required=true;
 }
 const legacyTree=root.querySelector('#stnHubLessonChoiceBox');if(legacyTree)legacyTree.hidden=true;
 const selectionSummary=root.querySelector('#stnHubSelectedPath');if(selectionSummary)selectionSummary.hidden=true;
 const lessonPreview=root.querySelector('#stnHubLessonPreview');if(lessonPreview)lessonPreview.hidden=true;
 if(taskPicker.previousElementSibling!==selectionDock)taskPicker.before(selectionDock);
 selectionDock.querySelector('.stnSelectionCaption').textContent='اختر الصف ثم أدخل رقم الوحدة والدرس';
 const taskCards=[...root.querySelectorAll('.stnTaskCard')];
 const updateTaskReady=()=>{
  const ready=Boolean(selectionClassSelect.value&&Number.isInteger(Number(unitInput.value))&&Number(unitInput.value)>0&&Number.isInteger(Number(lessonInput.value))&&Number(lessonInput.value)>0);
  taskCards.forEach(card=>{card.disabled=!ready;card.setAttribute('aria-disabled',String(!ready));});
 };
 for(const input of [selectionClassSelect,unitInput,lessonInput])input.addEventListener('input',updateTaskReady);
 updateTaskReady();
 const initialTask=taskService();
 root.querySelectorAll('.stnTaskCard').forEach(item=>item.classList.toggle('active',item.dataset.service===initialTask));
""", path)
files[path] = s.encode()

# 2.8.102: select the official Oman 2026/2027 semester automatically.
path = "noor-hub.js"
s = files[path].decode()
anchor = " const initialTask=taskService();"
if s.count(anchor) != 1:
    raise SystemExit("Could not locate task initialization for Oman term logic")
s = replace_exact(s, anchor, """
 function applyOfficialOmanSemester(){
  const parts=new Intl.DateTimeFormat('en-CA',{
   timeZone:'Asia/Muscat',year:'numeric',month:'2-digit',day:'2-digit'
  }).formatToParts(new Date());
  const part=name=>parts.find(item=>item.type===name)?.value||'';
  const today=part('year')+'-'+part('month')+'-'+part('day');
  // Ministry calendar 2026/2027: semester 1 begins 6 Sep 2026;
  // semester 2 begins 31 Jan 2027; school year ends 13 Jul 2027.
  const semester=today>='2027-01-31'&&today<'2027-07-14'?'2':'1';
  const select=$('stnHubSemester');
  if(select&&select.value!==semester)select.value=semester;
  const label=root.querySelector('label[for="stnHubSemester"]');
  if(label)label.style.setProperty('display','none','important');
  if(select)select.style.setProperty('display','none','important');
  return semester;
 }
 applyOfficialOmanSemester();
""" + anchor, path)
# Semester is refreshed at initialization and every task switch; no manual selector remains.
s = replace_exact(s, "  $('stnHubSemester').value=data?.semester||'1';", "  applyOfficialOmanSemester();", path)
s = replace_exact(s, " function bind(){\n  bindPrimaryActions();", " function bind(){\n  applyOfficialOmanSemester();\n  bindPrimaryActions();", path)
files[path] = s.encode()

path = "noor-hub.css"
s = files[path].decode()
s += """
/* 2.8.102 hide manual semester selector; term is calendar-driven */
#stnNoorHub label[for="stnHubSemester"],
#stnNoorHub #stnHubSemester{display:none!important}
"""
files[path] = s.encode()

path = "noor-hub.css"
s = files[path].decode()
s += """
/* 2.8.102 Daftar Noor approved task-card workspace */
#stnNoorHub{font-family:Tahoma,Arial,sans-serif;color:#214b3e}
#stnNoorHub #stnHubOpen{background:linear-gradient(135deg,#08745a,#075744)!important;border:1px solid #d5c28a!important;border-radius:28px!important;padding:12px 18px!important;font-size:14px!important;font-weight:800!important}
#stnNoorHub .stnHubPanel{width:min(440px,calc(100vw - 18px))!important;max-height:min(84dvh,780px)!important;overflow:auto!important;background:#fffefa!important;border:1px solid #d8c89c!important;border-radius:18px!important;padding:12px!important;box-shadow:0 14px 40px #082c2055!important}
#stnNoorHub .stnHead{background:linear-gradient(115deg,#075b49,#0a765d)!important;color:#fff!important;border-radius:13px!important;padding:13px 12px!important;margin:-12px -12px 10px!important;min-height:64px!important}
#stnNoorHub .stnHeadButtons button{color:#fff!important;background:#ffffff1b!important;border-radius:9px!important}
#stnNoorHub .stnHubTaskPicker{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:8px!important;margin:10px 0 12px!important}
#stnNoorHub .stnHubTaskPicker label{display:none!important}
#stnNoorHub .stnHubTaskPicker select{position:absolute!important;width:1px!important;height:1px!important;opacity:0!important;pointer-events:none!important;overflow:hidden!important}
#stnNoorHub .stnTaskCard{display:flex!important;flex-direction:column!important;align-items:center!important;justify-content:center!important;gap:5px!important;min-width:0!important;min-height:68px!important;border:1px solid #dce6df!important;border-radius:12px!important;background:#fff!important;color:#526e62!important;font-size:12px!important;font-weight:800!important;padding:8px 4px!important;cursor:pointer!important}
#stnNoorHub .stnTaskCard span{font-size:20px!important;line-height:1.1!important}
#stnNoorHub .stnTaskCard.active{background:#eaf5ef!important;border:2px solid #168267!important;color:#075b49!important}
#stnNoorHub #stnHubDetails{display:block!important;min-width:0!important;padding-top:3px!important}
#stnNoorHub .stnRow{display:grid!important;grid-template-columns:1.35fr .75fr!important;gap:8px!important}
#stnNoorHub label{font-size:12px!important;margin:8px 0 4px!important}
#stnNoorHub select,#stnNoorHub input:not([type=file]),#stnNoorHub textarea{width:100%!important;min-width:0!important;min-height:42px!important;border:1px solid #d4dfd8!important;border-radius:10px!important;background:#fff!important;padding:8px 10px!important;font-size:13px!important}
#stnNoorHub .stnHubChecks{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important;padding:10px!important;border:1px solid #e0e8e2!important;border-radius:12px!important;background:#f7faf7!important}
#stnNoorHub .stnActions{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;margin-top:12px!important}
#stnNoorHub .stnBtn{min-height:42px!important;max-height:none!important;height:auto!important;border-radius:10px!important;padding:9px 10px!important;font-size:12px!important;line-height:1.45!important;white-space:normal!important;overflow:visible!important}
#stnNoorHub .stnNote{display:block!important;font-size:11px!important;line-height:1.55!important}
#stnNoorHub .stnStatus{font-size:12px!important;line-height:1.6!important;padding:9px!important}
@media(max-width:520px){#stnNoorHub{left:8px!important;bottom:8px!important}#stnNoorHub .stnHubPanel{width:calc(100vw - 16px)!important;max-height:82dvh!important}#stnNoorHub .stnTaskCard{min-height:62px!important;font-size:11px!important}}
"""
files[path] = s.encode()


# 2.8.102: true minimize hides the entire panel and leaves only the floating launcher.
path = "noor-hub.js"
s = files[path].decode()
s = replace_exact(s,
"""  $('stnHubMinimize').addEventListener('click',()=>{const pane=$('stnHubPanel'),mini=pane.classList.toggle('stnHubMinimized');
   $('stnHubMinimize').textContent=mini?'▢':'−';$('stnHubMinimize').setAttribute('aria-expanded',String(!mini));
   if(!mini)requestAnimationFrame(()=>{if(panelPosition)placePanel(panelPosition.x,panelPosition.y)});
  });""",
"""  $('stnHubMinimize').addEventListener('click',()=>{
   const pane=$('stnHubPanel');
   pane.classList.remove('stnHubMinimized');
   pane.hidden=true;
   $('stnHubMinimize').textContent='−';
   $('stnHubMinimize').setAttribute('aria-expanded','false');
  });""",path)
s = replace_exact(s,
"""  $('stnHubOpen').addEventListener('click',()=>{if(draggedOpener)return;const p=$('stnHubPanel');if(p.hidden)showPanel();else p.hidden=true});""",
"""  $('stnHubOpen').addEventListener('click',()=>{if(draggedOpener)return;const p=$('stnHubPanel');if(p.hidden){p.classList.remove('stnHubMinimized');$('stnHubMinimize').textContent='−';$('stnHubMinimize').setAttribute('aria-expanded','true');showPanel();}else p.hidden=true});""",path)
s = replace_exact(s,
"""    <button type="button" class="stnBtn outline" id="stnHubRefreshTree">تحقّق من الاختيار في نور</button>""",
"""    <button type="button" class="stnBtn outline" id="stnHubRefreshTree" hidden aria-hidden="true" tabindex="-1">تحقّق من الاختيار في نور</button>""",path)
s = replace_exact(s,
""" let stoppingAll=false;""",
""" let lastAutoTreeSignature='';
 let stoppingAll=false;""",path)
s = replace_exact(s,
"""   if(useCache)previewNumberSelection({useCache:true}).catch(()=>{});
  }""",
"""   if(useCache)previewNumberSelection({useCache:true}).catch(()=>{});
   const course=selectedClass(),coordinates=inputs();
   if(course&&coordinates.unitNo&&(!$('stnHubLesson').value||coordinates.lessonNo)&&
      !curriculumScanning()&&!busy&&!unitBatchBusy){
    const epoch=operationEpoch,signature=[course.cid,coordinates.semester,coordinates.unitNo,coordinates.lessonNo].join(':');
    if(lastAutoTreeSignature!==signature){
     lastAutoTreeSignature=signature;
     setTimeout(async()=>{
      if(epoch!==operationEpoch||curriculumScanning()||busy||unitBatchBusy)return;
      const current=selectedClass(),now=inputs();
      if(!current||current.cid!==course.cid||!samePositions(coordinates,now))return;
      if(!await curriculumAllowed())return;
      clearPreview();persistSelection({course});
      try{await curriculum.start({...coordinates,cid:course.cid,label:course.label});}
      catch(error){curriculumStatus('تعذرت قراءة شجرة الصف تلقائيًا: '+String(error.message||error));}
     },260);
    }
   }
  }""",path)
files[path]=s.encode()
path="noor-hub.css"
s=files[path].decode()+"""


/* 2.8.105 class + numeric lesson coordinates, shown before task selection */
#stnNoorHub .stnSelectionDock{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:7px!important;margin:8px 0 10px!important;padding:9px!important;border:1px solid #d9e5dc!important;border-radius:11px!important;background:#f5faf6!important}
#stnNoorHub .stnSelectionCaption{font-size:12px!important;font-weight:800!important;color:#075b49!important}
#stnNoorHub .stnSelectionClass{display:grid!important;grid-template-columns:58px minmax(0,1fr)!important;align-items:center!important;gap:7px!important}
#stnNoorHub .stnSelectionClass label{margin:0!important}
#stnNoorHub .stnSelectionDock .stnLegacyTreeFields{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important;margin:0!important}
#stnNoorHub .stnSelectionDock .stnLegacyTreeFields>div{min-width:0!important}
#stnNoorHub .stnSelectionDock input[type=number]{width:100%!important;min-height:38px!important;text-align:center!important;font-size:14px!important;font-weight:700!important}
#stnNoorHub .stnHubTaskPicker{margin:7px 0 9px!important;gap:6px!important}
#stnNoorHub .stnTaskCard{min-height:54px!important;padding:6px 3px!important;font-size:11px!important;gap:3px!important}
#stnNoorHub .stnTaskCard span{font-size:17px!important}
#stnNoorHub .stnTaskCard:disabled{opacity:.4!important;cursor:not-allowed!important}
#stnNoorHub #stnHubLessonChoiceBox[hidden],#stnNoorHub #stnHubLessonPreview[hidden],#stnNoorHub #stnHubSelectedPath[hidden]{display:none!important}
@media(max-width:520px){#stnNoorHub .stnSelectionDock{padding:7px!important;gap:6px!important}#stnNoorHub .stnSelectionDock .stnLegacyTreeFields{gap:6px!important}}


/* 2.8.108: keep grade, unit and lesson in one horizontal row */
#stnNoorHub .stnSelectionDock{
 display:grid!important;
 grid-template-columns:repeat(3,minmax(0,1fr))!important;
 align-items:end!important;
 gap:8px!important;
}
#stnNoorHub .stnSelectionCaption{grid-column:1/-1!important}
#stnNoorHub .stnSelectionClass{display:contents!important}
#stnNoorHub .stnSelectionField{display:grid!important;grid-template-columns:minmax(0,1fr)!important;min-width:0!important;gap:4px!important}
#stnNoorHub .stnSelectionDock .stnRow{display:contents!important}
#stnNoorHub .stnSelectionDock .stnRow>div{display:grid!important;grid-template-columns:minmax(0,1fr)!important;min-width:0!important;gap:4px!important}
#stnNoorHub .stnSelectionDock label{font-size:11px!important;white-space:nowrap!important;overflow:hidden!important;text-overflow:ellipsis!important;margin:0!important}
#stnNoorHub .stnSelectionDock select,#stnNoorHub .stnSelectionDock input{min-width:0!important;width:100%!important;min-height:40px!important;padding:6px 5px!important;font-size:12px!important;text-align:center!important}
@media(max-width:520px){
 #stnNoorHub .stnSelectionDock{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important;padding:7px!important}
 #stnNoorHub .stnSelectionDock label{font-size:10px!important}
 #stnNoorHub .stnSelectionDock select,#stnNoorHub .stnSelectionDock input{font-size:11px!important;min-height:38px!important}
}

/* 2.8.104 selection-first layout */
#stnNoorHub .stnSelectionDock{display:grid!important;grid-template-columns:minmax(0,1fr)!important;gap:7px!important;margin:8px 0 10px!important;padding:10px!important;border:1px solid #d9e5dc!important;border-radius:12px!important;background:#f5faf6!important}
#stnNoorHub .stnSelectionCaption{font-size:12px!important;font-weight:800!important;color:#075b49!important}
#stnNoorHub .stnSelectionClass{display:grid!important;grid-template-columns:76px minmax(0,1fr)!important;align-items:center!important;gap:8px!important}
#stnNoorHub .stnSelectionClass label{margin:0!important}
#stnNoorHub .stnSelectionDock .stnLegacyTreeFields{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:8px!important;margin:0!important}
#stnNoorHub .stnSelectionDock .stnLegacyTreeFields>div{min-width:0!important}
#stnNoorHub .stnSelectionDock .stnLegacyTreeFields input{width:100%!important;text-align:center!important;font-size:15px!important;font-weight:700!important}
#stnNoorHub .stnHubTaskPicker{margin-top:8px!important}
#stnNoorHub .stnTaskCard:disabled{opacity:.42!important;filter:grayscale(1)!important;cursor:not-allowed!important}
#stnNoorHub #stnHubOpenCurriculumTree[hidden],#stnNoorHub #stnHubRefreshTree[hidden],#stnNoorHub #stnHubLessonPreview[hidden]{display:none!important}
@media(max-width:520px){#stnNoorHub .stnSelectionDock{padding:8px!important;gap:6px!important}#stnNoorHub .stnSelectionClass{grid-template-columns:62px minmax(0,1fr)!important}#stnNoorHub .stnSelectionDock .stnLegacyTreeFields{gap:6px!important}}
/* 2.8.102: minimize the complete workspace, not only its task tabs */
#stnNoorHub .stnHubPanel.stnHubMinimized{display:none!important}
#stnNoorHub #stnHubRefreshTree[hidden]{display:none!important}
"""
files[path]=s.replace(".stnLegacyTreeFields",".stnRow").encode()

# 2.8.104: teacher-facing terminology — keep the internal service key "scorm".
# Release gate: this label-only patch does not alter Noor SCORM routing or upload semantics.
hub = files["noor-hub.js"].decode()
hub = hub.replace(">SCORM</button>", ">درس تفاعلي</button>")
hub = hub.replace("توليد SCORM", "إنشاء درس تفاعلي")
hub = hub.replace("ملفات SCORM", "ملفات الدروس التفاعلية")
hub = hub.replace("رفع ملفات SCORM", "رفع ملفات الدروس التفاعلية")
hub = hub.replace("منزلة SCORM", "منزلة الدرس التفاعلي")
files["noor-hub.js"] = hub.encode()

publisher = files["noor-scorm-publisher.js"].decode()
publisher = publisher.replace("حفظ ملف SCORM", "حفظ ملف الدرس التفاعلي")
publisher = publisher.replace("حالة حفظ SCORM", "حالة حفظ الدرس التفاعلي")
publisher = publisher.replace("ظهور SCORM في القائمة", "ظهور الدرس التفاعلي في القائمة")
files["noor-scorm-publisher.js"] = publisher.encode()

assert ">درس تفاعلي</button>" in hub
assert "إنشاء درس تفاعلي" in hub
assert "data-service=\"scorm\"" in hub
assert "const isScormForm=()=>onUploadPage()&&Boolean(optionOfRadio('SCORM'));" in publisher


# 2.8.108: build the membership notice with DOM APIs rather than HTML parsing.
# This removes the Mozilla unsafe-innerHTML warning without changing the UI flow.
path = "noor-license-ui.js"
s = files[path].decode()
old = "widget.innerHTML='<strong>🧩 أدوات نور | دفتر المعلم</strong><p style=\"margin:5px 0 8px\" id=\"stnMembershipMessage\">جارٍ التحقق من العضوية...</p><a href=\"https://rouhous.github.io/School-Teacher-Notebook-App/school-edition/school-notebook.html\" target=\"_blank\" rel=\"noopener noreferrer\" style=\"color:#087a5b\">فتح دفتر المعلم للتحقق</a>　<button type=\"button\" id=\"stnMembershipRetry\" style=\"cursor:pointer;border:1px solid #087a5b;border-radius:7px;color:#087a5b;background:#fff;padding:4px 8px\">إعادة الفحص</button>';"
new = """const heading=document.createElement('strong');
heading.textContent='🧩 أدوات نور | دفتر المعلم';
const message=document.createElement('p');
message.id='stnMembershipMessage';
message.style.cssText='margin:5px 0 8px';
message.textContent='جارٍ التحقق من العضوية...';
const link=document.createElement('a');
link.href='https://rouhous.github.io/School-Teacher-Notebook-App/school-edition/school-notebook.html';
link.target='_blank';link.rel='noopener noreferrer';
link.style.color='#087a5b';link.textContent='فتح دفتر المعلم للتحقق';
const retry=document.createElement('button');
retry.type='button';retry.id='stnMembershipRetry';retry.textContent='إعادة الفحص';
retry.style.cssText='cursor:pointer;border:1px solid #087a5b;border-radius:7px;color:#087a5b;background:#fff;padding:4px 8px';
widget.append(heading,message,link,document.createTextNode('　'),retry);"""
s = replace_exact(s, old, new, path)
if "innerHTML" in s:
    sys.exit("Unsafe innerHTML remains in membership UI")
files[path] = s.encode()

# Keep the packaged documentation aligned with the actual manifest version.
if "README.md" in files:
    readme=files["README.md"].decode()
    readme=readme.replace("Noor Unified Firefox Extension 2.8.64","Noor Unified Firefox Extension 2.8.110",1)
    files["README.md"]=readme.encode()



# 2.8.109: restore automatic Gemini model fallback on quota/rate-limit responses.
# The shared model router previously stopped immediately on HTTP 429, so the
# configured lower-tier model was never attempted. Keep key handling and
# generation/publishing flows unchanged; only repair model selection.
path = "noor-gemini-models.js"
models = files[path].decode()
models = replace_exact(models,
    "if(status===429)return 'تجاوز مشروع Gemini حد الطلبات أو الحصة (429). انتظر تجدد الحصة؛ لن نُعيد الطلب تلقائيًا.';",
    "if(status===429)return 'تجاوز النموذج الأساسي حد الطلبات أو الحصة (429)، وتمت تجربة النموذج الاحتياطي تلقائيًا إن كان متاحًا.';",
    path)
models = replace_exact(models,
    """   const discovered=await available(key);
   if(!discovered.length)throw Error('لا يعرض مشروع Google نموذجًا حديثًا من Gemini Flash-Lite قادرًا على التوليد. تحقق من المشروع والمفتاح في AI Studio.');""",
    """   let discovered=[];
   try{discovered=await available(key);}
   catch(error){
     // A transient quota/rate-limit on the model-list endpoint must not
     // prevent a direct attempt with the configured primary and fallback.
     const message=String(error?.message||error);
     if(!/429|HTTP 5\\d\\d|غير متاحة حاليًا|تعذر الاتصال/.test(message))throw error;
     discovered=SUPPORTED.slice();
   }
   if(!discovered.length)throw Error('لا يعرض مشروع Google نموذجًا حديثًا من Gemini Flash-Lite قادرًا على التوليد. تحقق من المشروع والمفتاح في AI Studio.');""",
    path)
models = replace_exact(models,
    """   let overloaded=false;
   const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));""",
    """   let overloaded=false,quotaLimited=false;
   const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));""",
    path)
models = replace_exact(models,
    """       if(r.status===404){failures.push(model);break;}
       if(r.status===503){
         overloaded=true;
         if(attempt===0){await sleep(1800+Math.floor(Math.random()*500));continue;}
         break; // Try another discovered Lite model only after bounded backoff.
       }
       // Never retry quota, permission, invalid request or other server failures.
       throw Error(safeError(r.status));""",
    """       if(r.status===404){failures.push(model);break;}
       if(r.status===429){
         // Quota/rate limit can be model-specific. Do not repeat the exhausted
         // model; move immediately to the next configured lower-tier model.
         quotaLimited=true;failures.push(model);break;
       }
       if(r.status===503){
         overloaded=true;
         if(attempt===0){await sleep(1800+Math.floor(Math.random()*500));continue;}
         break; // Try another discovered Lite model only after bounded backoff.
       }
       if([500,502,504].includes(r.status)){
         overloaded=true;failures.push(model);break;
       }
       // Permission and invalid-request failures are not solved by switching models.
       throw Error(safeError(r.status));""",
    path)
models = replace_exact(models,
    """   if(overloaded)throw Error(safeError(503));
   throw Error('نماذج Gemini Flash-Lite غير متاحة للتوليد بهذا المفتاح ('+failures.join('، ')+'). قد تظهر في قائمة Google رغم تقييد الاستخدام. جرّب مفتاح مشروع يدعم النماذج الحديثة.');""",
    """   if(quotaLimited)throw Error(safeError(429));
   if(overloaded)throw Error(safeError(503));
   throw Error('نماذج Gemini Flash-Lite غير متاحة للتوليد بهذا المفتاح ('+failures.join('، ')+'). قد تظهر في قائمة Google رغم تقييد الاستخدام. جرّب مفتاح مشروع يدعم النماذج الحديثة.');""",
    path)
assert "quotaLimited=true;failures.push(model);break;" in models
assert "discovered=SUPPORTED.slice();" in models
files[path]=models.encode()

# Persistent Gemini-key entry point: allow opening the key field even when a key is already saved.
path = "noor-hub.js"
hub = files[path].decode()
hub = replace_exact(hub,
    '<div id="stnHubKeyBox" hidden>',
    '<div class="stnActions"><button type="button" id="stnHubManageKey" class="stnBtn outline">🔑 إعداد مفتاح Gemini</button></div><div id="stnHubKeyBox" hidden>',
    path)
hub = replace_exact(hub,
    "$('stnHubCreateKey').addEventListener('click',()=>window.open('https://aistudio.google.com/api-keys','_blank','noopener,noreferrer'));",
    "$('stnHubManageKey').addEventListener('click',()=>{ $('stnHubKeyBox').hidden=false; $('stnHubKey').focus(); status(keyReady?'يمكنك لصق مفتاح Gemini جديد لاستبدال المفتاح الحالي.':'أضف مفتاح Gemini ثم اضغط «لصق وحفظ».'); }); $('stnHubCreateKey').addEventListener('click',()=>window.open('https://aistudio.google.com/api-keys','_blank','noopener,noreferrer'));",
    path)
files[path] = hub.encode()


# 2.8.110: compact header Gemini key dialog and one-row action controls.
path = "noor-hub.js"
s = files[path].decode()
# Put the key entry point in the title toolbar; reuse the existing key box and save handlers.
s = replace_exact(s,
  " const panelRoot=root.querySelector('#stnHubPanel');",
  """  const panelRoot=root.querySelector('#stnHubPanel');
  const geminiHeadButtons=panelRoot.querySelector('.stnHeadButtons');
  const geminiButton=document.createElement('button');
  geminiButton.type='button';geminiButton.id='stnHubGeminiHeader';
  geminiButton.className='stnHeadGemini';geminiButton.title='إعداد مفتاح Gemini';
  geminiButton.setAttribute('aria-label','إعداد مفتاح Gemini');
  geminiButton.textContent='🔑 Gemini';
  geminiHeadButtons?.insertBefore(geminiButton,geminiHeadButtons.firstChild);
  const keyBox=panelRoot.querySelector('#stnHubKeyBox');
  const keyDialog=document.createElement('div');
  keyDialog.id='stnHubKeyDialog';keyDialog.hidden=true;
  keyDialog.setAttribute('role','dialog');keyDialog.setAttribute('aria-modal','true');
  keyDialog.setAttribute('aria-label','إعداد مفتاح Gemini');
  const keyDialogHead=document.createElement('div');keyDialogHead.className='stnKeyDialogHead';
  const keyDialogTitle=document.createElement('strong');keyDialogTitle.textContent='🔑 إعداد مفتاح Gemini';
  const keyDialogClose=document.createElement('button');keyDialogClose.type='button';
  keyDialogClose.textContent='×';keyDialogClose.setAttribute('aria-label','إغلاق');
  keyDialogHead.append(keyDialogTitle,keyDialogClose);
  keyDialog.append(keyDialogHead,keyBox);
  panelRoot.append(keyDialog);
  geminiButton.addEventListener('click',()=>{keyDialog.hidden=false;keyBox.hidden=false;});
  keyDialogClose.addEventListener('click',()=>{keyDialog.hidden=true;});
  keyDialog.addEventListener('click',event=>{if(event.target===keyDialog)keyDialog.hidden=true;});
  const legacyActions=panelRoot.querySelector('#stnHubLegacyActions');
  const stopButton=panelRoot.querySelector('#stnHubBatchCancel');
  if(legacyActions&&stopButton)legacyActions.append(stopButton);""",
  path)
# Use a 3-column action row; do not leave the stop action on its own line.
files[path]=s.encode()

path = "noor-hub.css"
s=files[path].decode()
s += """
/* 2.8.110 compact Gemini header and single-line task actions */
#stnNoorHub .stnHeadButtons{display:flex!important;align-items:center!important;gap:5px!important;flex-wrap:nowrap!important}
#stnNoorHub .stnHeadGemini{display:inline-flex!important;align-items:center!important;justify-content:center!important;gap:3px!important;min-width:76px!important;height:34px!important;padding:0 8px!important;border:1px solid #ffffff55!important;border-radius:10px!important;background:#ffffff18!important;color:#fff!important;font-size:11px!important;font-weight:800!important}
#stnNoorHub #stnHubKeyDialog[hidden]{display:none!important}
#stnNoorHub #stnHubKeyDialog{position:absolute!important;z-index:100000!important;inset:0!important;display:flex!important;flex-direction:column!important;justify-content:center!important;align-items:stretch!important;gap:12px!important;padding:18px!important;background:#102b25d9!important;border-radius:18px!important}
#stnNoorHub .stnKeyDialogHead{display:flex!important;align-items:center!important;justify-content:space-between!important;color:#fff!important;font-size:15px!important}
#stnNoorHub .stnKeyDialogHead button{width:34px!important;height:34px!important;border:0!important;border-radius:9px!important;background:#ffffff22!important;color:#fff!important;font-size:23px!important}
#stnNoorHub #stnHubKeyBox{display:block!important;padding:14px!important;border:1px solid #d9e5dc!important;border-radius:13px!important;background:#fffefa!important}
#stnNoorHub #stnHubKeyBox[hidden]{display:block!important}
#stnNoorHub #stnHubKeyBox .stnActions{display:grid!important;grid-template-columns:repeat(2,minmax(0,1fr))!important;gap:7px!important}
#stnNoorHub #stnHubLegacyActions{display:grid!important;grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:6px!important;align-items:stretch!important;margin-top:10px!important}
#stnNoorHub #stnHubLegacyActions .stnBtn,#stnNoorHub #stnHubLegacyActions .stnFilePicker{min-width:0!important;min-height:38px!important;padding:6px 5px!important;font-size:10px!important;line-height:1.25!important;white-space:normal!important;text-align:center!important}
#stnNoorHub #stnHubLegacyActions #stnHubBatchCancel{margin:0!important}
@media(max-width:520px){
 #stnNoorHub .stnHeadButtons{gap:3px!important}
 #stnNoorHub .stnHeadGemini{min-width:67px!important;padding:0 5px!important;font-size:10px!important}
 #stnNoorHub #stnHubLegacyActions{grid-template-columns:repeat(3,minmax(0,1fr))!important;gap:5px!important}
 #stnNoorHub #stnHubLegacyActions .stnBtn,#stnNoorHub #stnHubLegacyActions .stnFilePicker{font-size:9px!important;padding:5px 3px!important}
}
"""
files[path]=s.encode()
assert "stnHubGeminiHeader" in files["noor-hub.js"].decode()
assert "keyDialogClose.addEventListener" in files["noor-hub.js"].decode()
assert "#stnNoorHub #stnHubLegacyActions{display:grid!important;grid-template-columns:repeat(3" in files["noor-hub.css"].decode()


# Unit/lesson dropdown work is deferred for this release.

# 2.8.110: never auto-navigate during grade transfer; require the teacher-opened gradebook.
path = "noor-hub.js"
s = files[path].decode()
route_start = s.find(" async function routeIfNeeded(opts){")
if route_start < 0: sys.exit("Could not find grade route handler in noor-hub.js")
route_end = s.find("\n }", route_start)
if route_end < 0: sys.exit("Could not find end of grade route handler in noor-hub.js")
route_end += 3
new_route = """ async function routeIfNeeded(opts){
  if(opts.service!=='grades')return false;
  // The teacher opens the gradebook manually; never follow a cached route.
  if(routetype()!=='grades')
   throw Error('افتح صفحة رصد الدرجات في نور بنفسك، ثم أعد المطابقة. لم يتم فتح أي صفحة تلقائيًا.');
  if(csvFileInfo){
   try{gradePageScan();}
   catch(error){throw Error('الصفحة الحالية ليست صفحة رصد درجات قابلة للمطابقة. افتح صفحة الدرجات بنفسك ثم أعد المحاولة.');}
  }else if(!document.querySelector('#stnGradeAssessment')){
   throw Error('لم أتعرف على نموذج رصد الدرجات في الصفحة الحالية. افتح صفحة الدرجات بنفسك ثم أعد المحاولة.');
  }
  return false;
 }"""
s = s[:route_start] + new_route + s[route_end:]
files[path] = s.encode()
assert "لم يتم فتح أي صفحة تلقائيًا" in s

with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dest:
    for path,data in files.items():
        dest.writestr(path,data)
print(f"Generated {output} ({output.stat().st_size} bytes)")

