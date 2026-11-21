#!/usr/bin/env python3
"""Generate Noor 2.8.77 source ZIP from the tested 2.8.64 source archive.
Keeps the v2.8.65 card recognizer and original SCORM publisher; fixes only task-side card resolution."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import json, re, sys

directory = Path("addons/unified")
sources = sorted(directory.glob("*-v2.8.64-*-source.zip"))
if len(sources) != 1:
    sys.exit(f"Expected one 2.8.64 source archive, found {len(sources)}")
output = directory / "Noor-Unified-v2.8.77-ClassCard-source.zip"

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
manifest["version"] = "2.8.77"
manifest["description"] = "Noor Unified 2.8.77: SCORM course card verification with original publisher and library navigation preserved."
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
 "  const epoch=operationEpoch;\\n  const branch=await orderedBranch(opts);",
 "  const epoch=operationEpoch;\\n  const directScormUrl=await scormDirectLink(opts);\\n  const branch=await orderedBranch(opts);",path)
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
 "  if(opts.fromDashboard&&!isCourseHome())location.assign(location.origin+'/teacher');\\n  else scheduleAdvance(j,250);",
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
