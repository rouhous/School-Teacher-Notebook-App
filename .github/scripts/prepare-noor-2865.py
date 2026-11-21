#!/usr/bin/env python3
"""Generate Noor 2.8.83 source ZIP from the tested 2.8.64 source archive.
Keeps the v2.8.65 card recognizer and original SCORM publisher; fixes only task-side card resolution."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.83-ClassCard-source.zip"

def replace_exact(content, old, new, path):
    if content.count(old) != 1:
        sys.exit(f"Could not find unique patch anchor in {path}: {repr(old[:125])}; count={content.count(old)}")
    return content.replace(old, new, 1)

with ZipFile(sources[0]) as original:
    files = {i.filename: original.read(i.filename) for i in original.infolist() if not i.is_dir()}
if any(p.startswith("META-INF/") for p in files):
    sys.exit("Refusing to use already signed source")
manifest = json.loads(files["manifest.json"])
if manifest["version"] != "2.8.64":
    sys.exit("Unexpected base version")
manifest["version"] = "2.8.83"
manifest["description"] = "Noor Unified 2.8.83: SCORM course card verification with original publisher and library navigation preserved."
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


# v2.8.83: keep the proven direct SCORM route, but separate Activity and SCORM
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


# v2.8.83 - no more card fallback for SCORM: require a verified per-course
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


# 2.8.83: passively discover *official* Noor SCORM route identities.
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


# 2.8.83 - robust grade/subject matching, card-scoped URL discovery, and
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


# 2.8.83: use the course CONTENT page shown in the teacher's video, not the
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


# v2.8.83 - Remove every previous SCORM card/popover / digital-library
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
  const controls=[...panel.querySelectorAll('a,button,[role="button"],[onclick]')].filter(el=>visible(el)&&!el.disabled);
  const candidates=controls.filter(el=>{
   const icon=el.querySelector('.fa-arrow-right,.fa-arrow-circle-right,.fa-long-arrow-right,.glyphicon-arrow-right,[class*="arrow-right"]');
   const label=actionMeta(el);
   return !!icon||(/^(?:expand|show other libraries|open libraries)$/.test(label)&&!/(?:lesson|interactive)/.test(label));
  });
  if(candidates.length)return onlyUnique(candidates,'السهم الأخضر الخاص بالمكتبات الأخرى');
  // If Noor uses a CSS-drawn green arrow, choose only the one adjacent
  // to the exact heading in the panel header, not a random card button.
  const header=heading.closest('.panel-heading,.card-header,[class*="header"]')||heading.parentElement;
  const adjacent=[...header.querySelectorAll('a,button,[role="button"],[onclick]')]
   .filter(el=>visible(el)&&el!==heading&&(
     el.classList.contains('btn-success')||/(green|success)/i.test(String(el.className))||
     el.querySelector('svg use[href*="arrow"],svg[class*="arrow"]')));
  return onlyUnique(adjacent,'زر توسيع المكتبات الأخرى');
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

# Regression checks: retain the original digital-library publisher exactly.
with ZipFile(sources[0]) as original:
    assert files["noor-scorm-publisher.js"]!=original.read("noor-scorm-publisher.js")
assert "stnHubScormReference" not in files["noor-hub.js"].decode()
assert "await curriculum.start({...inputs(),cid:opts.course.cid,label:opts.course.label,purpose:'scorm'})" not in files["noor-hub.js"].decode()
assert "cards.next({label:j.label,grade:j.grade,cid:j.cid},3,REPOSITORY_ACTION)" in files["noor-scorm-publisher.js"].decode()
assert "function treeCandidate(j)" in files["noor-scorm-publisher.js"].decode()
assert "const gradeMatches=Number.isInteger(selectedGrade)" in files["noor-hub.js"].decode()

with ZipFile(output, "w", ZIP_DEFLATED, compresslevel=6) as dest:
    for path,data in files.items():
        dest.writestr(path,data)
print(f"Generated {output} ({output.stat().st_size} bytes)")
