/* Noor Unified 2.8.119 — context-aware resumable course-attachment uploader.
 * Uses only links and controls observed in the teacher's live Noor page.
 * Unknown or ambiguous page structures stop safely; no guessed endpoints.
 */
(function(root){'use strict';
 if(window.top!==window||root.NoorAttachmentPublisher)return;
 const JOB='stnNoorAttachmentJob:v1',FILES='stnNoorAttachmentFiles:v1:',MAX_FILE=20*1024*1024,MAX_TOTAL=40*1024*1024,TTL=45*60*1000;
 const clean=s=>String(s||'').replace(/\s+/g,' ').trim();
 const norm=s=>clean(s).normalize('NFKC').replace(/[إأآ]/g,'ا').replace(/ة/g,'ه').replace(/[\u064b-\u065f\u0640]/g,'').toLowerCase();
 const visible=e=>Boolean(e&&e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden');
 const sleep=t=>new Promise(r=>setTimeout(r,t));
 const inHub=e=>Boolean(e?.closest?.('#stnNoorHub'));
 const get=()=>{try{const j=JSON.parse(sessionStorage.getItem(JOB)||'null');if(!j)return null;if(Date.now()-j.at>TTL){sessionStorage.removeItem(JOB);return null}return j}catch(_){return null}};
 const set=j=>sessionStorage.setItem(JOB,JSON.stringify({...j,updated:Date.now()}));
 const fileKey=j=>FILES+j.id;
 function notice(message){const panel=document.getElementById('stnHubPanel'),s=document.getElementById('stnHubStatus');if(panel)panel.hidden=false;if(s)s.textContent=String(message||'');}
 async function teacher(){try{return String(await root.NOOR_TEACHER_PROFILE?.active?.()||'')}catch(_){return ''}}
 function textOf(e){return norm([e.innerText,e.textContent,e.value,e.getAttribute('aria-label'),e.title].filter(Boolean).join(' '));}
 function actions(re,scope=document){return [...scope.querySelectorAll('a,button,[role="button"],[onclick],input[type="button"],input[type="submit"]')].filter(e=>visible(e)&&!e.disabled&&!inHub(e)&&re.test(textOf(e)));}
 function clickUnique(re,scope=document){const list=actions(re,scope);const unique=[...new Set(list.map(e=>e.closest('a,button,[role="button"]')||e))];return unique.length===1?unique[0]:null;}
 const isTeacherHome=()=>/^\/teacher\/?$/i.test(location.pathname);
 function routeCid(){const m=location.pathname.match(/(?:^|\/)cid:(\d+)(?:\/|$)/i);return m?m[1]:'';}
 const selectedRoute=cid=>routeCid()===String(cid||'');

 function attachmentRow(){
  const rows=[...document.querySelectorAll('tr,li,.row,.list-group-item,[role=\"row\"],.media-row,.content-row,div')].filter(e=>visible(e)&&!inHub(e)&&norm(e.innerText||e.textContent).length<260&&/مرفقات(?:\s+الماده)?|course attachments/i.test(norm(e.innerText||e.textContent)));
  const top=rows.filter(e=>!rows.some(p=>p!==e&&p.contains(e)));
  if(top.length!==1)return null;
  const add=clickUnique(/^(?:\+?\s*)?(?:اضافه|إضافة|add)$/i,top[0]);
  return add?{row:top[0],add}:null;
 }
 function attachmentForm(){return /attachment|resource|مرفق|مستودع/i.test(norm(document.body.innerText.slice(0,12000)))&&Boolean(document.querySelector('input[type="file"]'));}
 function setNative(el,value){const proto=el.tagName==='TEXTAREA'?HTMLTextAreaElement.prototype:HTMLInputElement.prototype;const setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;if(setter)setter.call(el,value);else el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}
 function lessonAction(j){const pool=[...document.querySelectorAll('a,button,[role="button"],[role="treeitem"],.lesson,.lesson-item,li')].filter(e=>visible(e)&&!inHub(e));const compact=v=>norm(v).replace(/[\s:：._-]/g,'');const wanted=compact(j.lesson);const tail=compact(String(j.lesson||'').split(/[»›>]/).pop().replace(/^media\s*:/i,''));const id=String(j.lessonId||'');const byId=id?pool.filter(e=>[e.getAttribute('data-id'),e.getAttribute('data-node-id'),e.getAttribute('data-lesson-id'),e.getAttribute('aria-controls')].some(v=>v&&String(v)===id)||[e.getAttribute('href')].some(v=>v&&new RegExp('(?:^|[/=:])'+id.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+'(?:$|[/?#&])').test(v))):[];const exact=pool.filter(e=>compact(e.textContent)===wanted||compact(e.textContent)===tail);let matches=byId.length?byId:exact;if(!matches.length&&tail)matches=pool.filter(e=>{const t=compact(e.textContent);return t===tail||t.endsWith(tail)});const top=matches.filter(e=>!matches.some(p=>p!==e&&p.contains(e)));return top.length===1?top[0]:null;}
 function attachmentSection(){const headings=[...document.querySelectorAll('h1,h2,h3,h4,h5,h6,strong,b,legend,[role="heading"],.card-title')].filter(e=>visible(e)&&!inHub(e)&&/^(?:مرفقات(?:\s+الماده)?|course attachments|attachments)$/i.test(norm(e.textContent)));if(headings.length!==1)return null;let node=headings[0];for(let i=0;i<5&&node;i++,node=node.parentElement){const add=clickUnique(/^(?:\+?\s*)?(?:اضافه|إضافة|add)$/i,node);if(add)return {node,add};}return null;}
 function uploadInput(){
  const all=[...document.querySelectorAll('input[type="file"]')].filter(e=>!e.disabled&&!inHub(e));
  const describe=e=>norm([e.id,e.name,e.accept,e.getAttribute('aria-label'),[...(e.labels||[])].map(l=>l.textContent).join(' '),e.closest('.form-group,.form-row,.custom-file,.upload-area')?.textContent].join(' '));
  const cover=/(?:غلاف|صوره|صورة|cover|image|jpe?g|png|webp|avatar)/;
  const main=all.filter(e=>!cover.test(describe(e))&&(/pdf|doc|ppt|xls|zip|rar|ibooks|html/i.test(describe(e))||/اختر ملفا|اختر ملف|drop a file|file/i.test(describe(e))));
  if(main.length===1)return main[0];
  if(all.length===1)return all[0];
  // Fallback: drop cover/image inputs; then prefer the input inside the open dialog.
  const nonCover=all.filter(e=>!cover.test(describe(e)));
  if(nonCover.length===1)return nonCover[0];
  const dlg=(nonCover.length?nonCover:all).filter(e=>e.closest('.modal.show,.modal.in,.modal[style*="block"],[role="dialog"]'));
  if(dlg.length===1)return dlg[0];
  const vis=(nonCover.length?nonCover:all).filter(visible);
  return vis.length===1?vis[0]:null;
 }
 function titleField(form){const all=[...form.querySelectorAll('input[type="text"],textarea')].filter(e=>visible(e)&&!e.disabled);const hits=all.filter(e=>/title|name|العنوان|اسم المرفق/i.test([e.name,e.id,e.placeholder,e.getAttribute('aria-label'),e.labels?.[0]?.textContent].join(' ')));return hits.length===1?hits[0]:null;}
 function saveButton(form){const matches=[...form.querySelectorAll('button,input[type="submit"],input[type="button"],a.btn')].filter(e=>visible(e)&&!e.disabled&&/^(?:حفظ|اضافه|إضافة|رفع|نشر|save|upload|add|submit)$/i.test(norm(e.textContent||e.value||e.title)));return matches.length===1?matches[0]:null;}
 function fillLessonAndDate(form,j){
  const selects=[...form.querySelectorAll('select')].filter(e=>visible(e)&&!e.disabled);
  const lessonSelects=selects.filter(sel=>{const meta=norm([sel.name,sel.id,sel.getAttribute('aria-label'),sel.closest('.form-group,.form-row')?.textContent].join(' '));return /درس|lesson/.test(meta)||[...sel.options].some(o=>norm(o.textContent).includes(norm(j.lesson)));});
  if(lessonSelects.length===1){const sel=lessonSelects[0];const hits=[...sel.options].filter(o=>norm(o.textContent)===norm(j.lesson)||norm(o.textContent).endsWith(norm(j.lesson))||norm(j.lesson).endsWith(norm(o.textContent)));if(hits.length===1){sel.value=hits[0].value;sel.dispatchEvent(new Event('input',{bubbles:true}));sel.dispatchEvent(new Event('change',{bubbles:true}));}}
  const dates=[...form.querySelectorAll('input[type=date],input[name*=date i],input[id*=date i]')].filter(e=>visible(e)&&!e.disabled);
  const dateHits=dates.filter(e=>/تاريخ النشر|publish date|publication date/.test(norm([e.name,e.id,e.getAttribute('aria-label'),e.closest('.form-group,.form-row')?.textContent].join(' '))));
  if(dateHits.length===1&&!dateHits[0].value){const d=new Date(),v=d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');setNative(dateHits[0],v);}
 }
 function requiredMissing(form){return [...form.querySelectorAll('input[required],select[required],textarea[required]')].filter(e=>visible(e)&&!e.disabled&&e.type!=='file'&&e.type!=='checkbox'&&e.type!=='radio'&&!String(e.value||'').trim());}
 async function cleanup(j){try{await browser.storage.local.remove(fileKey(j))}catch(_){}sessionStorage.removeItem(JOB)}
 async function start(opts){
  if(get()&&get().phase!=='done')throw Error('توجد عملية مرفقات سابقة غير محسومة. تحقق منها أو استكملها قبل بدء عملية أخرى.');
  const t=await teacher();if(!t||String(opts.teacherId||'')!==t)throw Error('تعذر تأكيد حساب المعلم الحالي.');
  const c=opts.course;if(!c?.verified||!/^[0-9]+$/.test(String(c.cid||''))||!c.grade||!c.subject||!opts.unit||!opts.lesson||!opts.lessonId)throw Error('اختر صفًا ودرسًا موثقين من نور أولًا.');
  // Continue from the page already open instead of restarting the card workflow.
  const onSelectedCourse=selectedRoute(c.cid);
  const initialPhase=attachmentForm()&&onSelectedCourse?'form':
   onSelectedCourse&&attachmentSection()?'section':
   onSelectedCourse&&attachmentRow()?'content':'card';
  const j={id:'a'+Date.now()+'-'+Math.random().toString(36).slice(2,8),at:Date.now(),teacherId:t,cid:String(c.cid),grade:Number(c.grade),label:c.label,subject:c.subject,unit:clean(opts.unit),lesson:clean(opts.lesson),lessonId:String(opts.lessonId),files:[],index:0,targetPhase:initialPhase,phase:'awaiting_files',navigation:[],savedContext:true};
  await browser.storage.local.set({[fileKey(j)]:{teacherId:t,files:[]},['stnNoorAttachmentContext:v1:'+t]:{cid:j.cid,grade:j.grade,label:j.label,subject:j.subject,unit:j.unit,lesson:j.lesson,lessonId:j.lessonId,at:Date.now()}});set(j);
  notice('تم حفظ الصف والوحدة والدرس. اختر ملف المرفق أولًا؛ لن يبدأ التنقل قبل استلام الملف.');

  return {ok:true,queued:true,count:0};
 }
 async function attach(files){
  const j=get();if(!j||j.phase!=='awaiting_files')throw Error('لم نصل بعد إلى نموذج مرفقات المادة. استكمل التنقل أولاً.');
  if(!Array.isArray(files)||!files.length)throw Error('لم يتم اختيار أي ملف.');
  const allowed=/\.(?:pdf|doc|docx|ppt|pptx|xls|xlsx|pps|ppsx|ibooks|html|zip|rar)$/i;
  const encode=bytes=>{const parts=[];let chunk='';for(let i=0;i<bytes.length;i++){chunk+=String.fromCharCode(bytes[i]);if(chunk.length===8192){parts.push(chunk);chunk='';}}if(chunk)parts.push(chunk);return btoa(parts.join(''))};
  let total=0;const packed=[];
  for(const f of files){if(!allowed.test(f.name))throw Error('نوع الملف غير مدعوم: '+f.name);if(!f.size||f.size>MAX_FILE)throw Error('حجم الملف غير صالح أو يتجاوز 20 ميغابايت: '+f.name);total+=f.size;if(total>MAX_TOTAL)throw Error('مجموع الملفات يتجاوز 40 ميغابايت. قسّمها إلى دفعتين.');packed.push({name:f.name,type:f.type||'application/octet-stream',base64:encode(new Uint8Array(await f.arrayBuffer()))})}
  await browser.storage.local.set({[fileKey(j)]:{teacherId:j.teacherId,files:packed}});j.files=packed.map(x=>x.name);j.index=0;j.phase=j.targetPhase||'card';set(j);const pick=document.getElementById('stnHubAttachFiles');if(pick)pick.textContent='📎 إضافة مرفقات';notice('تم حفظ الملفات. جارٍ الآن فتح بطاقة الصف المحددة والوصول إلى مرفقاتها.');if(j.phase==='card'&&!isTeacherHome())location.assign(location.origin+'/teacher');else advance();return {ok:true,count:packed.length};
 }
 let running=false,timer;
 function schedule(){clearTimeout(timer);timer=setTimeout(advance,450)}
 async function advance(){if(running)return;const j=get();if(!j||!['card','page3','content','lesson','section','form','awaiting_files','staged','submitted_unknown'].includes(j.phase))return;running=true;
  try{
   const t=await teacher();if(t!==j.teacherId)throw Error('تغير حساب المعلم؛ أوقفت العملية لحماية الملفات.');
   if(j.phase==='awaiting_files'){notice('نموذج مرفقات المادة جاهز. اختر الملفات من زر الإضافة في لوحة الإضافة.');return;}
   if(j.phase==='submitted_unknown'){notice('تم إرسال الملف إلى نور لكن لم يثبت ظهوره بعد. تحقق من قائمة المرفقات قبل إعادة المحاولة.');return;}
   if(j.phase!=='form'&&!isTeacherHome()&&j.phase!=='content'&&j.phase!=='lesson'&&j.phase!=='section'){notice('افتح الصفحة الرئيسية لبوابة المعلم لاستكمال الوصول إلى بطاقة الصف.');return;}
   if(j.phase==='card'||j.phase==='page3'){
    if(!isTeacherHome()){notice('جارٍ العودة إلى بطاقات الصفوف في بوابة المعلم.');location.assign(location.origin+'/teacher');return;}
    const catalog=root.NoorCourseCatalog;
    let nav=null;
    // Repeatedly ask the shared navigator for the next verified step. It
    // recognizes an already-open card menu and never toggles it closed.
    for(let attempt=0;attempt<36&&!nav;attempt++){
     catalog?.scan?.();
     nav=root.NoorClassCard?.next?.({label:j.label,cid:j.cid,grade:j.grade,subject:j.subject},3,/^__no_attachment_shortcut__$/i);
     if(!nav)await sleep(250);
    }
    if(!nav)throw Error('لم أتعرف على بطاقة الصف المحددة أو الصفحة الثالثة. تحقق من ظهور البطاقة وقائمة خدماتها؛ لم أفتح صفًا آخر ولم أرفع أي ملف.');
    const key=location.href+'|'+nav.step+'|'+j.label;
    if((j.navigation||[]).includes(key)&&nav.step!=='open')throw Error('توقف التنقل لتجنب تكرار الضغط على بطاقة الصف.');
    j.navigation=[...(j.navigation||[]),key];
    j.phase=nav.step==='open'?'page3':'content';set(j);
    nav.element.click();
    notice(nav.step==='open'?'تم تحديد بطاقة الصف الصحيحة. جارٍ فتح القائمة ثم الانتقال إلى الصفحة الثالثة…':'تم تحديد خطوة الصفحة الثالثة في بطاقة الصف. جارٍ الوصول إلى قسم المرفقات…');
    await sleep(700);schedule();return;
   }
   if(j.phase==='content'){
    let row=null;
    for(let attempt=0;attempt<24&&!row;attempt++){row=attachmentRow();if(!row)await sleep(250);}
    if(!row)throw Error('وصلت إلى بطاقة الصف، لكن لم يظهر صف «مرفقات المادة» وزر «إضافة» في الصفحة الثالثة. لم أضغط زرًا آخر ولم أرفع أي ملف.');
    j.phase='form';set(j);row.add.click();await sleep(650);
   }
   if(j.phase==='lesson'||j.phase==='navigate'||j.phase==='section'){
    const lesson=lessonAction(j);if(!lesson)throw Error('لم أتعرف على عنصر الدرس «'+j.lesson+'» بصورة فريدة في صفحة محتوى الصف. لم أرفع أي ملف.');
    if(!lesson.matches('[aria-current="true"],.active,.selected')&&!lesson.querySelector('[aria-current="true"],.active,.selected')){j.phase='lesson';set(j);lesson.click();await sleep(500);}
    j.phase='section';set(j);
   }
   if(j.phase==='section'){
    const section=attachmentSection();if(!section)throw Error('لم أجد زر «إضافة» داخل قسم «مرفقات المادة» للدرس المحدد. لم أرفع أي ملف.');
    j.phase='form';set(j);section.add.click();await sleep(450);
   }
   if(j.phase==='form'){
    if(!attachmentForm())throw Error('لم يظهر نموذج رفع مرفقات المادة بعد فتحه.');
    const input=uploadInput();if(!input)throw Error('خانة اختيار الملف غير واضحة أو توجد عدة خانات؛ أوقفت الرفع لتجنب وضع الملف في حقل الغلاف.');
    const data=(await browser.storage.local.get(fileKey(j)))[fileKey(j)];if(!data||data.teacherId!==j.teacherId)throw Error('لم أجد سجل عملية المرفقات.');
    if(!data.files?.length){j.phase='awaiting_files';set(j);const pick=document.getElementById('stnHubAttachFiles');if(pick)pick.textContent='📎 اختيار الملف الآن';notice('وصلنا إلى نموذج «مرفقات المادة». اضغط زر «اختيار الملف الآن» لإرفاق الملفات، وسأكمل الرفع تلقائيًا.');return;}
    const remaining=data.files.slice(j.index);if(!input.multiple&&remaining.length>1)throw Error('نموذج نور لا يدعم رفع المجموعة في حقل واحد. لم أرسل أي ملف؛ اختر الملفات على دفعات فردية بعد التحقق من دعم النموذج.');const chosen=remaining;
    const transfer=new DataTransfer();for(const item of chosen){const bytes=Uint8Array.from(atob(item.base64),c=>c.charCodeAt(0));transfer.items.add(new File([bytes],item.name,{type:item.type}));}
    input.files=transfer.files;input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));
    if(input.files.length!==chosen.length||chosen.some((f,i)=>input.files[i]?.name!==f.name))throw Error('لم يتأكد إرفاق جميع الملفات المحددة.');
    let form=input.form||input.closest('form');
    if(!form){for(let n=input.parentElement,d=0;n&&d<10&&n!==document.body;n=n.parentElement,d++){if(saveButton(n)){form=n;break;}}}
    if(!form)form=input.closest('.modal-content,.modal,[role="dialog"],.card,fieldset')||input.parentElement;
    if(!form)throw Error('لم أتعرف على نموذج رفع الملفات.');
    const title=titleField(form);if(title&&chosen.length===1&&!String(title.value||'').trim())setNative(title,chosen[0].name.replace(/\.[^.]+$/,''));
    fillLessonAndDate(form,j);
    if(requiredMissing(form).length)throw Error('توجد حقول مطلوبة في نموذج نور لم تُملأ. أكملها يدويًا ثم أعد المحاولة.');
    const save=saveButton(form);if(!save)throw Error('لم أتعرف على زر الحفظ الرسمي بصورة فريدة؛ الملفات مرفقة في النموذج ولم أضغط حفظ.');
    j.phase='submitted_unknown';j.submitted=chosen.map(f=>f.name);set(j);notice('تم إرفاق '+chosen.length+' ملفًا والضغط على زر نور مرة واحدة. جارٍ التحقق من نتيجة الحفظ.');save.click();
   }
  }catch(e){console.error('[Noor attach]',e);j.phase='paused';j.reason=String(e.message||e)+(e instanceof TypeError?' @ '+String(e.stack||'').split('\n').slice(0,2).join(' | '):'');set(j);notice('توقفت عملية المرفقات: '+j.reason);}
  finally{running=false;}
 }
 async function resume(){const j=get();if(!j){notice('لا توجد عملية مرفقات معلقة.');return;}if(j.phase==='awaiting_files'){notice('نموذج مرفقات المادة جاهز. اختر الملفات من زر الإضافة في لوحة الإضافة.');return;}
   if(j.phase==='submitted_unknown'){notice('حالة الحفظ غير مؤكدة. تحقق من ظهور أسماء الملفات في مرفقات الدرس قبل أي إعادة إرسال.');return;}
   if(j.phase==='paused'){if(attachmentForm())j.phase='form';else if(attachmentSection())j.phase='section';else if(attachmentRow())j.phase='content';else if(isTeacherHome())j.phase='card';else if(j.lesson&&lessonAction(j))j.phase='lesson';else j.phase='card';j.reason='';}
   if(j.phase==='card'&&!isTeacherHome()){notice('لم أتعرف على صفحة المرفقات الحالية؛ سأعود إلى بطاقات الصف لاستكمال المسار المحفوظ.');location.assign(location.origin+'/teacher');return;}
   set(j);advance();}
 async function cancel(){const j=get();if(j?.phase==='submitted_unknown')throw Error('سبق إرسال الملفات؛ تحقق من نور قبل الإلغاء أو إعادة الرفع.');await cleanup(j);notice('ألغيت عملية المرفقات المعلقة.');}
 root.NoorAttachmentPublisher=Object.freeze({start,attach,resume,cancel,inspect:()=>{const j=get();return j?{phase:j.phase,lesson:j.lesson,files:j.files,reason:j.reason}:null}});
 setTimeout(()=>{const j=get();if(j&&j.phase!=='done')advance();},900);
})(typeof globalThis==='object'?globalThis:this);