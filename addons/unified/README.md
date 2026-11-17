## 2.8.31 — إصلاح اكتشاف صفوف المعلم (17 نوفمبر 2026)

- يستخرج الصفوف مباشرة من **بطاقات المواد** في صفحة المعلم، حتى لو كانت مبنية بعناصر Bootstrap عادية وليست عناصر `.card`.
- يقرأ الصف من **عنوان المادة** عند فتح صفحة المحتوى الخاصة به باستخدام معرّف CID الرقمي الظاهر في الرابط.
- يمنع استعمال روابط وعناوين التحاضير السابقة في معرفة صفوف المعلم أو ربطها بمعرّفات خاطئة.
- يدعم تحميل بطاقات المواد المتأخر بواسطة نور، وتحديث القائمة دون إغلاقها أثناء الاختيار.
- يحتفظ بآلية الضغط على بطاقة الصف لجلب روابطها الرسمية، ويبقي الحفظ والنشر متوقفين حين لا يتوفر معرّف موثوق.
- اجتاز اختبارات محاكاة في متصفح Chromium لصفوف التاسع والعاشر والحادي عشر والثاني عشر، مع اختبار رابط الصف وتلوث الجداول والتحديث المتأخر.
- **تنبيه:** لا تزال التجربة العملية داخل جلسة نور الحقيقية مطلوبة؛ لم نؤكد بها عمل جميع المراحل بعد.

[مصدر الإصدار 2.8.31](./Noor-Unified-v2.8.31-ClassDiscovery-source.zip)

---

## الإصدار التصحيحي 2.8.30 — تصحيح الصفوف والتنقل وتحريك الواجهة

- [مصدر الإصدار 2.8.30](./Noor-Unified-v2.8.30-Stability-Drag-source.zip)
- يقرأ الصفوف من بطاقات المعلم فقط، ويستبعد نصوص تحاضير Grade 10 القديمة وجداول الاختبارات
- سجل جديد v3 لكل حساب معلم يمنع عرض سجلات الصفوف الملوثة سابقًا
- يلتقط CID الرسمي عند اختيار الصف من قائمة خدمات بطاقة المادة إن كان متاحًا
- يعالج اختلاف CID بين فهرس التحضير الرقمي ورابط نموذج إضافة تحضير غير الرقمي مع تحقق قصير العمر
- سحب نافذة «أدوات نور» من شريط العنوان وسحب زر الإظهار نفسه مع حفظ الموضع محليًا وزر ⟲ لإعادته
- يبقي التوليد، الأنشطة، SCORM، نقل الدرجات والاستيراد كما هي مع تجنب الحفظ عند عدم التحقق من الصف
- **التحقق:** Node + Chromium محاكى + GitHub Actions؛ لم تتم تجربة الحفظ على جلسة نور حقيقية

**التوقيع:** لا يُدرج الإصدار في `addons/updates.json` إلا بعد نجاح توقيعه من Mozilla وإعادة استيراد XPI الموقّع.

---

# Noor Unified Tools 2.8.29 — إصلاح اختيار الصف (موقّع ومنشور)

**إصلاح مشكلة Firefox في نافذة اختيار الصف:** كانت قائمة الصفوف يعيد بناءها محركان منفصلان، وهو ما يؤدي إلى اختفاء قائمة Firefox الأصلية أثناء اختيار الصف. أصبح `noor-hub.js` هو المسؤول الوحيد عن القائمة، و`noor-pipeline.js` يطلب التحديث دون تعديل الخيارات بنفسه.

- لا تُغيَّر الخيارات حين تكون قائمة الصفوف مفتوحة، ولا تُنشأ من جديد إن لم يتغير محتواها.
- يحتفظ المعلم بالصف الذي اختاره، بما في ذلك الانتقال بين صفحات نور ضمن الجلسة، مع فصل الاختيار بحسب حسابه.
- يكتشف الصفوف من بطاقات صفحة المعلم حتى عندما يظهر اسم الصف في متن البطاقة بدل عنوانها.
- يطالب بفتح بطاقة الصف في نور إذا لم يظهر معرف Course ID رسمي؛ لا يخترع معرفات ولا يُدخل بيانات في صف خاطئ.
- لم تتغير وظائف Gemini والتحضير الجماعي والأنشطة وSCORM ونقل الدرجات من 2.8.28.

**الاختبار:** اجتاز اختبار إعادة فتح القائمة وتحديثها وفصل الصفوف وحماية المعرفات عبر محاكاة DOM، وفحص ملفات JavaScript وسلامة ZIP. **اختبار Noor الحي لم يتم بعد**.

[تنزيل XPI الموقّع 2.8.29](../files/Noor-Unified-v2.8.29-signed.xpi) · [تنزيل مصدر 2.8.29](./Noor-Unified-v2.8.29-ClassDropdown-source.zip) · [مكتبة الإضافات](../index.html)

---

# ✅ Noor Unified Tools 2.8.28 — Mozilla signed and published

The signed extension was imported directly from Mozilla and published as `addons/files/Noor-Unified-v2.8.28-signed.xpi`. `addons/updates.json` now includes version 2.8.28, and the Notebook's installation link points to the new signed package. Automatic publishing does not constitute a live end-to-end Noor workflow test; teacher sessions should first run one lesson and verify its three saved resources before a large batch.

# Noor Unified 2.8.28 — Combined lesson publication

The development source includes an integrated, teacher-initiated process that generates a preparation, assessment/questions, and interactive SCORM 1.2 course for each selected lesson, with lesson/unit/semester scope. The tool carries start date and number of periods, reads Noor's own curriculum tree and verified course links, and stores a teacher-specific progress log across page navigation. A personal Gemini API key is shared by the three generation services; grades remain a separate, preview-first process.

**Safety and verification:** The workflow refuses to guess class or attachment CID/TID identifiers, refuses to publish an unverified lesson-tree selection, verifies preparation period choices, and avoids repeating a Save after an uncertain response. The original grade matching and quiz insertion engines remain available. Lesson preparation → activity → SCORM uses the first date actually selected by Noor's preparation timetable for all three services.

**Testing status:** JavaScript syntax, archive/manifest integrity, class label parsing, curriculum matching, and mock Gemini bundle validation passed. Live authenticated Noor end-to-end save, question insertion, and SCORM upload controls have NOT been verified. If Noor's DOM is different, the extension pauses with a reason rather than claiming success. Manual teacher review is strongly advised for the initial rollout.

[Source 2.8.28](./Noor-Unified-v2.8.28-Release-source.zip) | [Firefox signed downloads](../index.html) | [Automatic update manifest](../updates.json)

---

# أدوات نور الموحدة — الإصدار الموقّع 2.8.26

تم استلام حزمة **Noor Unified Tools 2.8.26** الموقّعة من Mozilla آليًا عبر API حساب المطوّر، والتحقق من تطابق رقم الإصدار ومعرف الإضافة وملفات التوقيع وبنية الحزمة قبل وضعها في المستودع.

- [تثبيت أو تنزيل ملف XPI الموقّع 2.8.26](../files/Noor-Unified-v2.8.26-signed.xpi)
- [مكتبة إضافات دفتر المعلم](../index.html)
- [ملف التحديثات التلقائية](../updates.json)
- [ملف المصدر الموحد](./Noor-Unified-v2.8.26-Integrated-source.zip)

**التحديثات:** يظهر الإصدار 2.8.26 في `addons/updates.json` و`addons/latest.json`. يستطيع Firefox تحديث الإصدار 2.8.24 المثبت مسبقًا متى أجرى التحقق من الإصدارات وسمحت إعداداته. التحديثات تتطلب إصدارًا موقعًا بمعرف الإضافة الثابت.

**حالة الاختبار:** نجحت عملية الاستلام الآلي والتوقيع وفحص الحزمة، لكن لا يزال نجاح إرسال كل أنواع الأسئلة والدرجات وملفات SCORM في جلسة نور الحقيقية بحاجة إلى اختبار عملي. لا ينبغي اعتبار التوقيع وحده ضمانًا لعمل تلك الوظائف.

---

## أرشيف الإصدارات السابقة

# أدوات نور الموحدة — 2.8.24 (موقّعة)

تم استلام حزمة XPI الموقّعة من Mozilla والتأكد من بنيتها، ورقم إصدارها ومعرّفها `noor-prep-filler-private-2026@rouhous.github.io`، ووجود ملفات `META-INF`. التحقق النهائي من توقيع Mozilla يتم بواسطة Firefox عند التثبيت.

- [تحميل XPI الموقّع](../files/Noor-Unified-v2.8.24-Gemini-AQ-signed.xpi)
- [ملف التحديث التلقائي](../updates.json)
- SHA-256: `29be232ea4f76b0436f7f1302497459e15d6cd4a1a2cb84cbcbfcbddab888cb1`

أهم التغييرات: حُذفت التحاضير القديمة المضمّنة، ودعم مفاتيح Gemini الجديدة `AQ.` والقديمة `AIza`، وفصل البيانات بحسب حساب المعلم. ولا يعني ذلك اكتمال اختبارات رفع أنشطة نور أو نقل الدرجات تلقائيًا؛ يجب مراجعة كل إدراج قبل الحفظ.

**التحديثات**: الإصدار 2.8.24 يتضمن رابط `update_url` في manifest ويدعمه ملف `updates.json`، ويمكن أن يستقبل الإصدارات الموقّعة التالية تلقائيًا عند نشرها. من ثبت نسخة أقدم لم تكن تتضمن رابط التحديث، عليه تحديثها يدويًا مرة واحدة.

## نسخة التطوير 2.8.25 — قيد توقيع Mozilla

أُعدت هذه النسخة بناءً على الملاحظات المصورة من واجهة نور: يقرأ مسار الدرس المحدد من شجرة jsTree مباشرة، بما في ذلك الوحدة والفصل الدراسي. يمكن اختيار الفصل الدراسي يدويًا. إذا لم تُقرأ المعلومات، تظهر مساحة تصحيح بسيطة فقط عند الحاجة.

**واجهة التحضير الجديدة:** قبل إعداد المفتاح يظهر «إنشاء مفتاح» وحقل المفتاح وزر «لصق وحفظ». بعد حفظ المفتاح والتحقق منه تختفي هذه المرحلة، ويبقى زران: «تحضير الدرس»، «نسخ التحضير / تعبئته في نور». لا يتم الضغط على حفظ في نور تلقائيًا. تظل أدوات الدرجات والاختبارات متاحة في الصفحات ذات العلاقة، بدل أن تطغى على لوحة التحضير.

التحسينات بُنيت وفُحصت على شجرة محاكاة لدرس محدد داخل وحدة وفصل. **لم تختبر بعد على حساب نور فعلي**؛ اختلافات الواجهة قد تتطلب تعديلًا لاحقًا.

- [المصدر الجاهز للتوقيع 2.8.25](./Noor-Unified-v2.8.25-Simplified-source.zip)
- المعرف ثابت: `noor-prep-filler-private-2026@rouhous.github.io`.
- إلى حين توقيعه، يبقى الإصدار 2.8.24 الموقّع هو نسخة التثبيت المنشورة ويظل `updates.json` يشير إليه.
- بعد الحصول على ملف XPI الموقّع للإصدار 2.8.25، ارفعه إلى مكتبة التطبيق وأضفه إلى `updates.json` لتفعيل التحديث التلقائي.


## نسخة التطوير 2.8.26 — دمج أنشطة نور الذكية والمساق التفاعلي

- [تحميل المصدر الموحد (ZIP)](./Noor-Unified-v2.8.26-Integrated-source.zip)
- **نفس معرف Firefox** `noor-prep-filler-private-2026@rouhous.github.io` مع التحديث التلقائي إلى إصدار **موقّع فقط**.
- تم دمج نشاطات Noor Smart Activities `0.6.11` مع المحرك السابق، وتوحيد مفتاح Gemini لكل معلم عند `stnGeminiKey:<teacherId>`؛ لا يتم مشاركة مفتاح بين المعلمين.
- لوحة واحدة للخدمات: التحضير، النشاط/الاختبار، نقل الدرجات، SCORM. تقرأ شجرة نور وتطلب اختيار الفصل بدقة من معلومات نور المعروضة؛ لا تستنتج رقم الصف من معرف CID.
- سكربت SCORM يولّد ZIP يحتوي `imsmanifest.xml`,`index.html`,`questions.js`,`runtime.js`، ويستخدم SCORM 1.2 LMS API.
- التحضير يملأ حقول نور بعد موافقة المعلم ولا يضغط حفظ نهائي، والدرجات تُطابق قبل التعبئة، والأنشطة تستخدم محرك «إضافة مفردة» القائم وتتوقف عند أي اختلاف، والمساق SCORM يُنشأ محليًا ثم يُرفق إن تعرّفت الإضافة على خانة رفع ملف واحدة بدقة.
- **حدود التحقق:** روابط المستخدم توضح صفحة المعلم وتحضير الدروس والأنشطة والمرفقات SCORM، لكننا لم نستطع قراءة DOM الخاص بجلسة Noor المحمية أو إكمال نشر نشاط فعلي. بعض الخطوات قد تتوقف حتى توفير اختبار فعلي بالصفحة.
- هذه نسخة مصدر غير موقّعة. **لا تغير `updates.json` إلى 2.8.26** حتى يوقع Mozilla نسخة XPI النهائية وتُختبر.
