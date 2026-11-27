# الدليل الشامل لشرح مشروع **AegisVAPT** وخطة المناقشة الكاملة مع المحاضر

**المشروع:** DEPI Graduation Program — Project 5: *AI-Assisted VAPT Automation & Reporting Workflow*  
**الاسم التجاري للنظام:** **AegisVAPT** — *Local AI Security Workbench*  
**المُنفِّذ:** محمد رضا الحداد (`@7adadd`) · **التاريخ:** 2026-11-27  
**نطاق الاستخدام:** ملف مرجعي مبسّط باللغة العربية (مع المصطلحات التقنية كما تُنطق في المناقشة) لشرح كل خطوة من الأسابيع الأربعة + كل التطويرات الإضافية + سيناريو العرض العملي وأسئلة المحاضر المتوقعة.

---

## الفصل 1: فكرة المشروع في دقيقة (Elevator Pitch)

في أي شغل اختبار اختراق (**VAPT**)، المهندس بيضيع من **40% إلى 60%** من وقته مش في الاختراق نفسه، لكن في قراءة مخرجات طويلة جدًا (`Nmap XML`، `BloodHound JSON`، طلبات `Burp HTTP`، كود موبايل مفكوك بـ `jadx`) وفي كتابة نفس التقرير والـ CVSS يدويًا.

لو رميت البيانات دي على ChatGPT أو أي Cloud AI:
1. **كارثة خصوصية (Privacy Leak):** بتسرّب بيانات عميل حقيقية أو ثغرات لشركات خارجية.
2. **هلوسة خطيرة (Hallucinations):** الـ AI ممكن يألف ثغرة مش موجودة، أو يخترع مسار Active Directory، أو يحسب CVSS غلط.

**الحل بتاعنا في AegisVAPT:**
بنينا بيئة عمل متكاملة شغالة **100% محليًا على الجهاز (`127.0.0.1`)** باستخدام **Ollama** و **Dual 3B Models** (`qwen2.5:3b` + `llama3.2:3b`) على كارت شاشة **4 GB VRAM**، وحوّلنا الشغل لـ **Pipeline مضبوطة بـ 5 طبقات**:
- **قاعدة ذهبية:** *الذكاء الاصطناعي بيساعد المحلل ويسرّع التحليل، لكن الإنسان والأدوات الحتمية هما أصحاب القرار النهائي — مفيش أي AI claim بيدخل التقرير من غير التحقق في اللاب (`L1–L4`).*

### ليه استخدمنا Two Models (`qwen2.5:3b` + `llama3.2:3b`) مش موديل واحد؟

| الموديل | حجمه وسرعته عندنا | شاطر في إيه؟ | بنستخدمه إمتى في المشروع؟ |
|---|---|---|---|
| **`llama3.2:3b`** | سريع جدًا (~72–81 tok/s) | كتابة إنجليزية مرتبة وتلخيص سريع (`Prose & Triage`) | ملخصات الاستطلاع (`R1/R4`)، صياغة `Executive Summary` (`RP3`)، وفحص الأمان السريع (`W5`) |
| **`qwen2.5:3b`** | دقيق ومنظم (~57–70 tok/s) | الالتزام بالقواعد، `JSON`، استخراج `Citations`، وكتابة كود `Python/PowerShell/Frida` | مسارات `BloodHound` (`AD1`)، مراجعة الصلاحيات (`AD2`)، توليد السكربتات (`AD3/M2`)، وتحديات الويب (`W1/PS1`) |
| **الاتنين مع بعض (`--cross-check`)** | مقارنة ثنائية | كشف الهلوسة بدري (`L3 Gate`) | لو موديلين على نفس الداتا اختلفوا في المسار أو الثغرة → نعرف فورًا إن فيه هلوسة ونفحص يدويًا |

---

## الفصل 2: المعمارية كاملة (5 Layers + AegisVAPT Workbench)

```text
+-------------------------------------------------------------------------+
| UI Layer   AegisVAPT Web Workbench (http://127.0.0.1:8000)              |
|            Analyzer | Port Solver | Dashboard | AD Graph | Reports      |
+-------------------------------------------------------------------------+
| Layer 5    Reporting & Math Assurance                                   |
|            calc_cvss.py (exact CVSS 3.1) + diff_draft.py + PDF/DOCX/PPT |
+-------------------------------------------------------------------------+
| Layer 4    Human-in-the-Loop Validation Gate (L1-L4)                    |
|            L1 Data-Check | L2 Lab-Execution | L3 Cross-Check | L4 QA    |
+-------------------------------------------------------------------------+
| Layer 3    24 Versioned Prompt Templates (prompts/<phase>/)             |
|            7-Field Standard + Citation Tags [source:line] + UNKNOWN rule|
+-------------------------------------------------------------------------+
| Layer 2    Deterministic Ingest Adapters (scripts/ingest/*.py)          |
|            Strip XML/JSON noise + BFS Math Solver for BloodHound AD     |
+-------------------------------------------------------------------------+
| Layer 1    Local AI Runtime (Ollama @ http://127.0.0.1:11434)           |
|            llama3.2:3b + qwen2.5:3b (VRAM 4 GB, RTX 3050 Ti)            |
+-------------------------------------------------------------------------+
```

### أهم مجلدات الريبو (عشان لو المحاضر سأل فين إيه)
- `docs/`: خطة الـ 4 أسابيع (`00`)، دليل اللاب (`01`)، معيار البرومبتات (`02`)، قواعد الخصوصية والأخلاق (`03`)، وإطار التحقق (`04`).
- `prompts/`: **24 برومبت** متقسمين على 5 مراحل (`recon R1–R4`، `active-directory AD1–AD5`، `web W1–W5 + PS1`، `mobile M1–M4`، `reporting RP1–RP5`).
- `scripts/ingest/`: 5 محولات حتمية (`nmap_to_context.py`, `enum_to_context.py`, `bloodhound_to_context.py`, `burp_to_context.py`, `mobile_to_context.py`).
- `scripts/`: المحرك المحلي `vapt_ai.py` + التقييم `run_benchmarks.py` / `evaluate_challenges.py` + `lab_inspect.py` + `port_solver.py` + `agentic_solver.py` + `safe_lab_http.py`.
- `scripts/reporting/`: `calc_cvss.py`, `diff_draft.py`, `build_vapt_report.py`, `build_presentation.py`, `build_docs_pdf.py`, `build_defense_guide_pdf.py`.
- `app/` + `run_gui.py`: واجهة الويب **AegisVAPT** (FastAPI + HTML/CSS/JS + Chart.js + Cytoscape.js محليين بالكامل).
- `tests/`: **24 اختبار آلي Offline** (`18` في `test_solver_unit.py` + `6` في `test_gui_api.py`) + اختبار متصفح Playwright (`verify_gui_playwright.py`).
- `deliverables/`: كل التسليمات النهائية (التقرير البشري، مسودة الـ AI، ملف الفرق diff، الـ SOP، العرض التقديمي، نتائج التحديات، وسجل التحقق `validation-log.md`).

---

## الفصل 3: شرح مبسّط لكل خطوة في الأسابيع الأربعة

### الأسبوع الأول (Week 1): تأسيس اللاب وهندسة البرومبتات
**عملنا إيه ببساطة؟**
1. جهّزنا البيئة على ويندوز + **Kali WSL** ونضفنا مساحة فاضية على القرص (`23.38 GB` متاحة) وثبّتنا **Ollama** محليًا على `127.0.0.1:11434` مع موديلين `3B`: `qwen2.5:3b` و `llama3.2:3b` عشان يشتغلوا بسلاسة في `4 GB VRAM`.
2. كتبنا **قواعد الخصوصية والأخلاق (`docs/03`)**: مفيش أي داتا تطلع لـ Cloud AI، ممنوع استهداف أي موقع مش بتاعنا، والبيانات الخام في `evidence/` مقفولة بـ `.gitignore`.
3. صمّمنا **معيار البرومبتات (`docs/02`)**: كل برومبت متكون من 7 خانات وفيه **"Grounding Block"** بيجبر الموديل:
   - يستشهد برقم السطر أو الـ Tag زي `[nmap:port 80/tcp]` أو `[bh:edge E01]`.
   - يكتب **`UNKNOWN`** لو الداتا مش كافية — ممنوع يخمن.
   - يحط فاصل صارم `<DATA> ... </DATA>` عشان الموديل ميتخدعش بـ Prompt Injection لو فيه كلام غريب جوا الترافيك.
4. بنينا **5 محولات تنضيف (`Ingest Adapters`)**: قبل ما نبعت أي ملف للـ AI، السكربتات بتشيل الـ XML/JSON الزيادة وتحط أرقام سطور واضحة عشان الموديل الصغير (`3B`) يركز في المفيد وميتهش.
5. عملنا **Benchmark حقيقي (`scripts/run_benchmarks.py`)** على **6 مهام ثابتة × 2 موديل = 12 تجربة** واتسجلت النتيجة في `lab/model-benchmarks.md` (`91.7% usable`، `qwen` تفوق في البنية والكود و `llama` تفوق في السرعة والملخصات).

---

### الأسبوع الثاني (Week 2): الاستطلاع (Recon) و Active Directory
**عملنا إيه ببساطة؟**
1. **الاستطلاع الحقيقي على Kali WSL:** عملنا فحص Nmap فعلي طلع `nmap-lab.xml` (`80/tcp` Apache, `3306/tcp` MariaDB, `8888/tcp` Werkzeug) وسحبنا الهيدرز في `enum-lab.txt`، وشغلنا برومبتات `R1/R2` على الداتا بعد تنضيفها.
2. **تحليل Active Directory بذكاء رياضي (`BloodHound + BFS Ground Truth`):**
   - عندنا شبكة AD معملية موثقة `LAB.LOCAL` (`11` Node و `8` Edges في `lab/ad-lab-dataset/bloodhound_lab.json`).
   - سكربت `bloodhound_to_context.py` مش بس بيبعت الجراف للـ AI — ده بيحسب أولًا أقصر مسار اختراق بخوارزمية **BFS (Breadth-First Search)** ويطلع ملف حقيقة رياضية اسمه `bloodhound_ground_truth.json`:
     - **المسار الأول (3 خطوات):** `m.ali --(GenericAll)--> svc-backup --(MemberOf)--> IT-Admins --(WriteDacl)--> Domain Admins`
     - **المسار الثاني (3 خطوات):** `j.smith --(ForceChangePassword)--> svc-sync --(GetChanges + GetChangesAll / DCSync)--> LAB.LOCAL`
   - بعدها بندي الكونتكست للـ AI ببرومبت `AD1` و `AD2` (تحليل ACL) و `AD4` (enum4linux) و `AD5` (Kerberoasting/AS-REP) ونقارن كلام الـ AI بالحقيقة الرياضية اللي حسبها الـ BFS!
3. **توليد السكربتات والتحقق منها (`scripts/generated/`):** الموديل ولّد 4 سكربتات (`nmap_triage_verifier.py`, `bh_path_auditor.py`, `ad_spn_audit.ps1`, `bloodhound_analyzer.py`) وفحصنا الباورشيل بـ **PowerShell AST Parser** وشغلنا بايثون على الداتا الفعلية.
4. **هلوسات حقيقية مسكناها وسجلناها (`validation-log.md`):**
   - `W2-03` (`llama3.2:3b`): لخبط بين بورت `8888` (`Werkzeug`) وبورت `80` (`Apache`) وقال الصفحة الافتراضية "معرضة للاستغلال" ← اترفضت كـ **Hallucination**.
   - `W2-05` (`qwen2.5:3b`): شبّك حافة `E02` في مسار غير مسارها ← اتمسكت بالـ BFS Ground Truth.
   - `W2-07` (`llama3.2:3b`): بدّل بين هجوم Kerberoasting و AS-REP واخترع Flags وهمية لـ `klist` ← اترفضت كـ **Hallucination**.
- **خلاصة الأسبوع التاني:** من أصل 12 ادعاءات AI: **6 مؤكدين (50.0%)**، **3 جزئيين اتصححوا (25.0%)**، **3 هلاوس اترفضوا (25.0%)**.
- **نقطة أمانة مهمة للمناقشة:** مرحلة AD اتعملت على **Structured Lab Graph (`LAB.LOCAL`)** واتحسبت حتميًا بالـ BFS لأن تشغيل Samba AD DC كامل مش مطلوب على لابتوب 16GB، وإحنا موضحين ده بصراحة في كل المستندات.

---

### الأسبوع الثالث (Week 3): الويب الحي (DVWA) والموبايل (DIVA APK)
**عملنا إيه ببساطة؟**
1. **تطبيقات الويب (Live DVWA في Kali WSL):**
   - شغّلنا DVWA حقيقي على Apache2 + PHP + MariaDB جوا Kali WSL (`scripts/run_dvwa_pocs.py`).
   - مشينا بالترتيب الآمن: التقاط الطلب (`burp_to_context.py`) ← تحليل الثغرة (`W1`) ← اقتراح بايلودز غير مدمرة (`W2`) ← **بوابة مراجعة الأمان الإجبارية `W5`** (عشان نمنع أي `DROP TABLE` قبل ما يتجرب!) ← تنفيذ بالمتصفح الحقيقي وتصوير الـ PoC!
   - **نجحنا في إثبات 5 من 5 ثغرات حية بالصور (`deliverables/assets/poc-01..05.png`):**
     1. **SQL Injection (UNION)** على `id`: استخراج هاشات MD5 للمستخدمين.
     2. **Reflected XSS** على `name`: ظهور alert فعلي في Playwright.
     3. **Stored XSS** على `mtxMessage`: تخزين وتشغيل السكربت في سجل الزوار.
     4. **OS Command Injection** على `ip`: تنفيذ `id` وإرجاع `uid=33(www-data)`.
     5. **Local File Inclusion (LFI)** على `page`: قراءة `/etc/passwd`.
2. **تطبيقات الموبايل (`diva-beta.apk`):**
   - فكّينا التطبيق فعليًا بأداة **`jadx` v1.5.6** فطلع `718` كلاس جافا و `AndroidManifest.xml`.
   - الـ AI (`M1/M3`) استخرج 4 ثغرات بأرقام سطور دقيقة جدًا في ملفات `HardcodeActivity.java:19` (`"vendorsecretkey"`), `LogActivity.java:23` (تسريب كريدت كارد في الـ Logcat), `InsecureDataStorage1Activity.java:20`, و `AndroidManifest.xml` (`debuggable="true"`, `allowBackup="true"`).
   - ولّدنا **2 Frida JS Scripts** (`frida_ssl_pinning_bypass.js` و `frida_diva_hardcode_hook.js`) واتأكدنا من صحة الـ JS Syntax وأسماء الـ Classes/Methods (`jakhar.aseem.diva.HardcodeActivity.access`) قصاد كود `jadx`.
   - **نقطة أمانة مهمة للمناقشة:** التحقق في الموبايل هنا **Static & Signature-Verified** (فحص كود و Syntax ومطابقة أسماء الدوال)، مش تشغيل على موبايل أو Emulator فعلي، وده مكتوب بوضوح في التقارير.
3. **هلوسات حقيقية مسكناها في الأسبوع التالت:**
   - `W3-03`: اقترح XSS جوا HTML Comment `<!-- <script> -->` (وده عمره ما بيتنفذ!) واخترع باراميتر اسمه `username` مش موجود.
   - `W3-08`: سمّى `new RuntimeException()` ثغرة "تشفير ضعيف Critical".
   - `W3-10`: الموديل ألف أسماء Classes وهمية في أندرويد زي `OkHttp$CertificatePinner.pinToKeyStore` ← اتمسكت فورًا بالمقارنة مع AOSP/OkHttp3!
- **خلاصة الأسبوع التالت:** من 12 ادعاءات AI: **7 مؤكدين (58.3%)**، **2 جزئيين (16.7%)**، **3 هلاوس (25.0%)**.
- **إجمالي الأسبوعين مع بعض (`24` ادعاءات في `validation-log.md`):** **13 مؤكدين (54.2%)**، **5 جزئيين اتصححوا (20.8%)**، **6 هلاوس اترفضوا (25.0%)** — يعني **75.0% مخرجات مفيدة** مع التزام كامل إننا منسيبش ولا هلوسة تعدي للتقرير.

---

### الأسبوع الرابع (Week 4): التقرير النهائي، حساب CVSS، وتدقيق الفرق (QA Diff)
**عملنا إيه ببساطة؟**
1. الموديلات كتبت مسودة أولية كاملة للـ 9 ثغرات (`deliverables/vapt-report-ai-draft.md`: **398 سطر / 3,050 كلمة**) باستخدام برومبتات `RP1–RP4`.
2. **التدخل البشري والأدوات الحتمية (`Human QA + calc_cvss.py`):**
   - لغينا أي ثغرة أو سطر مش مثبوت في الداتا، وكتبنا النسخة النهائية النظيفة (`deliverables/vapt-report-human-edited.md`: **190 سطر / 2,208 كلمة**).
   - حسبنا كل الـ **9 ثغرات** (`1 Critical 9.8`، `4 High 7.1–8.8`، `4 Medium 5.1–6.5`) بمعادلات **`scripts/reporting/calc_cvss.py`** (حساب CVSS v3.1 برمجي 100% — مفيش AI بيألف أرقام خطورة!).
   - ركّبنا صور الـ PoC الحقيقية وضفنا إفصاح استخدام الـ AI (قاعدة `E7`).
3. **إثبات المراجعة البشرية بالأرقام (`scripts/reporting/diff_draft.py`):**
   - قارنّا مسودة الـ AI بالنسخة البشرية كلمة بكلمة: التشابه كان **10.3%** فقط على مستوى الكلمات (و **18.4%** على مستوى السطور) وتم حذف **339 كلمة** وإعادة صياغة وتدقيق **2439 -> 1896 كلمة** — ده دليل قاطع للمحاضر إن التقرير مش Copy-Paste من ChatGPT/Ollama!
4. **التسليمات المصممة (`build_vapt_report.py`, `build_presentation.py`, `build_docs_pdf.py`):**
   - تصدير PDF و DOCX بهوية DEPI & MCIT لكل من **التقرير النهائي** و **دليل العمل القياسي (`REUSABLE-VAPT-AI-SOP`)** + **توثيق المشروع الكامل** + **العرض التقديمي (15 شريحة)**.

---

## الفصل 4: التطويرات والإضافات اللي عملناها بعد الخطة الأصلية (Post-Week-4)

بعد ما خلصنا الأسابيع الأربعة الأساسية، طورنا المشروع لنسخة متكاملة جاهزة للاستخدام الفعلي والتقييم:

### 1. واجهة ويب محلية احترافية — **AegisVAPT** (`run_gui.py` + `app/`)
- بدل ما يشتغل بالـ CLI بس، بنينا واجهة ويب **FastAPI** خفيفة وشيك مربوطة حصريًا بـ `http://127.0.0.1:8000` بدون أي اعتماد على الإنترنت (مكتبات `Chart.js` و `Cytoscape.js` متخزنة محليًا في `app/static/vendor/`).
- **5 تبويبات متخصصة بأيقونات واقعية وشعار خاص (`AegisVAPT`):**
  1. **Artifact Analyzer:** لصق أو رفع ملفات (`Nmap XML`, `BloodHound JSON`, `HTTP`, `Java`) أو فحص رابط لاب سلبيًا، وتشغيل تحليل فردي أو **مقارنة مباشرة بين الموديلين** مع أزرار تقييم (`Verified`, `Corrected`, `Hallucination`) تكتب في `validation-log.md`.
  2. **Port Solver:** مساعد تفاعلي لحل تدريبات PortSwigger بمنهجية علمية منضبطة.
  3. **Dashboard:** حالة Ollama والموديلات، الـ KPIs المباشرة، رسمين بيانيين لسرعة ودقة الموديلين، وجدول تحديات الـ 12 ثغرة مع زر `Load`.
  4. **AD Attack Paths:** رسم بياني تفاعلي لشبكة `LAB.LOCAL` يميّز مسارات الـ BFS باللون الأخضر والبرتقالي ويعرض تفاصيل كل Node واتصالاته عند الضغط عليه.
  5. **Reports & Export:** حاسبة `CVSS 3.1` فورية، إحصائيات الفرق بين مسودة الـ AI والتقرير البشري، معرض صور الـ PoC الخمسة، وأزرار التصدير الفوري (`PDF / DOCX / PPTX`).
- **تأمين الواجهة (`Security Hardening`):**
  - حماية كل طلبات `POST` بـ **Session Token عشوائي (`X-VAPT-Session`)** يتولّد مع كل تشغيل.
  - التحقق من `Host` و `Origin` إنه `127.0.0.1` أو `localhost` فقط (منع هجمات DNS Rebinding و CSRF).
  - حد أقصى لحجم الملفات `2 MiB`.

### 2. مجموعة تحديات الويب الـ 12 (`lab/challenge-samples/` + `evaluate_challenges.py`)
- جمعنا **12 تحديًا** بصيغة `.http` تحاكي تحديات حقيقية: **6 DVWA** (`SQLi`, `XSS-R`, `XSS-S`, `CMDi`, `LFI`, `CSRF`) + **6 PortSwigger** (`SSRF`, `XXE`, `SSTI`, `IDOR`, `JWT alg=none`, `Error-based SQLi in Cookie`).
- شغّلناهم تلقائيًا ضد `qwen2.5:3b` عبر برومبت `W1` ← حقق **12 / 12 (100.0%)** في تشخيص نوع الثغرة والباراميتر المصاب مع ذكر رقم السطر بسرعة **57–70 tok/s** (توثيق كامل في `deliverables/challenge-evaluation-results.md`). *(بكل أمانة: إشارات المقيّم الآلي Heuristic وتحتاج مراجعة بشرية عند الاعتماد النهائي).*

### 3. برومبت `PS1` + الفاحص السلبي + **Agentic Port Solver**
- **`prompts/web/PS1-portswigger-lab-analyst.md`** (ليصبح عدد البرومبتات **24**): برومبت مخصص لتحديد السطح الهجومي وخطة التحقق لتدريبات PortSwigger.
- **الفاحص السلبي (`scripts/lab_inspect.py`) + جدار الحماية (`scripts/safe_lab_http.py`):** بيعمل طلبات `GET` سلبية فقط لقراءة الفورمات والباراميترات من لاب التدريب، مع **منع برمجي صارم** لأي رابط خارج `*.web-security-academy.net`، ومنع `localhost` / `Private IPs` / `169.254.169.254` (SSRF Protection)، ومنع التحويل التلقائي لمضيف خارجي (`Redirect Host Pin`).
- **الحلّال الوكيلي الموثّق (`scripts/agentic_solver.py` + `scripts/port_solver.py`):**
  - يشتغل بحلقة **`Observe -> Reason -> Act -> Verify`** ويدعم تحويل XML كيانات (`ENCODE_XML`) وقراءة ردود الـ WAF لضبط الخطوة التالية.
  - **ضمان السلامة (Consent Gate):** طلبات الـ `POST` أو التي تغيّر الحالة معطّلة افتراضيًا ولا تعمل إلا لو المستخدم علّم بنفسه على مربع الموافقة (`allow_state_changes`).
  - **الصدق التام في النتيجة:** لا يدّعي أبدًا إن اللاب اتحل (`solved`) إلا لما يشوف إشارة النجاح الرسمية في رد السيرفر، ويفصل بين حالات `solved` و `attempted` و `not_solved` و `blocked` و `expired` مع حجب أسرار الجلسات (`Secret Redaction`).

### 4. منظومة الاختبارات الآلية (`tests/`)
- **`tests/test_solver_unit.py`:** **18 اختبار وحدة** يتحقق من قواعد النطاق، `safe_lab_http`، منطق الـ Solver بدون شبكة أو Ollama.
- **`tests/test_gui_api.py`:** **6 اختبارات FastAPI** تتحقق من كل المسارات، حماية التوكن/Origin، حد الـ 2 MiB، و `total_findings == 9`.
- **`tests/verify_gui_playwright.py`:** اختبار متصفح Chromium حقيقي يتأكد إن الـ 5 تبويبات بتفتح بصفر أخطاء JavaScript، صفر طلبات خارجية، الرسوم البيانية شغالة، وصور الـ PoC كلها محمّلة.

---

## الفصل 5: ورك فلو المناقشة الكامل مع المحاضر (Defense Playbook)

### أولًا: قائمة التحضير قبل دخول المناقشة (دقيقتين)
افتح PowerShell جوا مجلد المشروع وتأكد من الـ 4 أوامر دول قبل ما تبدأ تعرض:

```powershell
# 1. تأكد أن Ollama شغال ومعاه الموديلين
ollama list

# 2. شغّل الاختبارات السريعة (24 اختبار بيخلصوا في ثانيتين)
python tests/test_solver_unit.py
python tests/test_gui_api.py

# 3. شغّل واجهة AegisVAPT
python run_gui.py
```
- افتح المتصفح على `http://127.0.0.1:8000` (وتأكد من الـ Terminal إن مفيش غير الـ Window بتاعتك).
- جهّز جنب المتصفح: ملف العرض `deliverables/DEPI-Project5-Presentation.pptx` + التقرير النهائي `deliverables/VAPT-Report-Human-Edited.pdf`.

---

### ثانيًا: سيناريو شرح الـ 15 شريحة (8 دقائق منضبطة)

| الشريحة | الزمن | هتقول إيه بالظبط للمحاضر؟ |
|---|---|---|
| **1 — العنوان واللوجو** | 20 ث | "مشروعنا **AegisVAPT** هو Workflow متكامل لأتمتة وتوثيق اختبارات الاختراق باستخدام ذكاء اصطناعي محلي 100% وبمراجعة بشرية صارمة." |
| **2 — المشكلة والمبدأ** | 30 ث | "الـ VAPT بيستهلك نص الوقت في تنضيف الداتا وكتابة التقارير، بس الـ Cloud AI خطر على السرية والـ AI لوحده بيهلوس. مبدأنا: الـ AI بيساعد بس مبياخدش قرار." |
| **3 — المعمارية الـ 5 طبقات** | 40 ث | اشرح بسرعة من تحت لفوق: Ollama المحلي ← 5 محولات Ingest حتمية ← 24 برومبت بإلزام الاستشهاد ← بوابة التحقق L1–L4 ← أدوات التقارير و `calc_cvss.py`، وفوقهم واجهة AegisVAPT. |
| **4 — اللاب والخصوصية** | 35 ث | "شغالين على RTX 3050 Ti 4GB بـ Dual 3B models (`qwen` للكود والبنية و `llama` للسرعة والملخصات) مع قاعدة P1–P6 لمنع تسريب أي داتا خارج اللاب." |
| **5 — نتائج Benchmarks** | 35 ث | اشرح الرسم البياني لـ 6 مهام: "لاحظنا إن `llama` أسرع في النصوص لكن `qwen` أدق في JSON والسكربتات — عشان كده عملنا Routing لكل موديل في مهمته." |
| **6 — Week 2 (Recon + AD)** | 50 ث | "هنا فحص Nmap حقيقي على Kali WSL، وفي Active Directory استخدمنا **BFS Solver** يحسب أقصر طريق في BloodHound كـ Ground Truth قبل ما نسأل الـ AI فمسكنا هلوسة ربط مسارين غلط." |
| **7 — Week 3 (Live DVWA)** | 45 ث | "طبقنا على DVWA حيّ، وممررنا البايلودز على بوابة سلامة `W5` قبل التنفيذ، وثبتنا 5/5 ثغرات (SQLi, XSS-R, XSS-S, CMDi, LFI) بصور PoC حقيقية." |
| **8 — Week 3 (Mobile DIVA)** | 35 ث | "فكّينا `diva-beta.apk` بـ `jadx` وطلعنا 4 ثغرات بأرقام سطور حقيقية + 2 سكربت Frida اتراجعوا استاتيكيًا على أسماء الدوال والكود." |
| **9 — Week 4 (التقرير والـ Diff)** | 45 ث | "الموديل طلع مسودة 3050 كلمة، وبعد مراجعتنا وإعادة حساب كل الـ 9 ثغرات بـ `calc_cvss.py` بقى التقرير 2208 كلمة بتشابه 10.3% بس — إثبات رقمي للشغل البشري." |
| **10 — تدقيق الهلوسة** | 40 ث | "من 24 ادعاء متسجل، 54.2% صح من أول مرة و 20.8% اتصلح جزئيًا و 25% اترفض كهلوسة — ده مش عيب، ده إثبات إن بوابة اللاب مسكت 6 أخطاء خطيرة قبل التقرير." |
| **11 — واجهة AegisVAPT** | 35 ث | اعرض صورة الـ Dashboard واشرح إن الواجهة محلية `127.0.0.1` بمكتبات JS محلية وتوكن أمان وحماية `Origin/Host`. |
| **12 — تحديات الـ 12 ثغرة** | 30 ث | "اختبرنا 12 سيناريو DVWA و PortSwigger سلبيًا على `qwen2.5:3b` وجاب 12/12 في تشخيص الثغرة والباراميتر." |
| **13 — Agentic Port Solver** | 40 ث | "بنينا Solver بيمشي `Observe -> Reason -> Act -> Verify` بموافقة صريحة من المستخدم على طلبات POST، وحظر SSRF وتحويل المضيف." |
| **14 — Demo Plan** | 15 ث | "دلوقتي هوري حضرتك Live Demo سريع في 3 دقايق على الجهاز." |
| **15 — الدروس والأمانة العلمية** | 30 ث | اذكر حدود التجربة بكل أمانة (AD على لاب جراف + BFS، الموبايل static/jadx)، والملفات المسلمة النهائية. |

---

### ثالثًا: الـ Live Demo في 3 دقائق (خطوة بخطوة)

1. **(30 ثانية — CLI Ingest + CVSS):**
   ورّي المحاضر في PowerShell سريع إن الكور شغال سطر أوامر:
   ```powershell
   python scripts/reporting/calc_cvss.py "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H"
   ```
   *"هنا الحساب الحتمي للـ CVSS = 8.8 High بدون أي تخمين من الموديل."*
2. **(40 ثانية — Dashboard & Telemetry):**
   من متصفح **AegisVAPT** افتح تبويب **Dashboard** → ورّيه لمبة `Ollama ready · Qwen + Llama`، والـ KPIs (`24 Prompts`, `12 Challenges`, `54.2% Strict / 75.0% Usable`), والـ Charts وتحديات الـ 12.
3. **(45 ثانية — Challenge Load + Cross-Check في Analyzer):**
   اضغط **Load** على تحدي `SQL Injection` من الجدول → هينقلك على **Analyzer** بالكابتشر الحقيقي → اختار **Compare both models** (أو **Run analysis**) → شوف سرعة الـ RTX 3050 Ti والرد بأرقام السطور `[http:line]`.
4. **(35 ثانية — AD Attack Paths):**
   افتح تبويب **AD Attack Paths** → ورّيه جراف `LAB.LOCAL` ومساري الاختراق الملوّنين بالأخضر والبرتقالي (BFS Ground Truth)، واضغط على `svc-backup` عشان تظهر خصائصها والروابط.
5. **(30 ثانية — Reports & Export):**
   افتح **Reports & Export** → جرب حاسبة CVSS، ورّيه جدول الـ Diff (`10.3% similarity`) ومعرض صور الـ DVWA PoCs الخمسة، وافتح **Human-Edited VAPT Report PDF** النهائي.

*(خطة بديلة لو الجهاز علق لحظيًا أثناء الديمو: عندك الـ 5 لقطات المحفوظة في `deliverables/assets/gui-smoke-*.png` + ملف `deliverables/VAPT-Report-Human-Edited.pdf` تقدر تكمل عليهم فورًا بدون ما تضيع ثانية).*

---

## الفصل 6: بنك أسئلة المحاضر الصعبة والإجابات النموذجية (12 سؤالًا)

### 1) ليه استخدمتوا موديلين صغيرين `3B` بدل ما تستخدموا GPT-4 أو موديل `70B`؟
**الإجابة:** عشان هدفين أساسيين: **أولًا الخصوصية** (داتا الـ VAPT مينفعش تطلع لـ Cloud API خارجي)، **ثانيًا قيود الهاردوير الواقعية** (جهاز بـ 4 GB VRAM). أثبتنا بالـ Benchmark إن `qwen2.5:3b` مع محولات تنضيف الداتا (`ingest`) بيدي دقة عالية وسرعة ~60–70 tok/s، وبنستخدم `llama3.2:3b` للسرعة والمقارنة الثنائية (`--cross-check`) عشان نصيد أي هلوسة.

### 2) نسبة الدقة الصارمة 54.2% (13 من 24) مش رقم قليل شوية؟
**الإجابة:** بالعكس، ده **نقطة القوة والأمانة العلمية في مشروعنا**! نسبة المخرجات الصالحة بالمساعدة البشرية (`Verified + Partial`) هي **75.0% (18/24)**، والـ **25.0% (6 حالات)** هي هلاوس حقيقية *مشروعنا نجح إنه يصيدها ويرفضها* قبل ما تدخل التقرير. لو كان كل كلام الموديل طلع 100% من غير إثبات يبقى مفيش لازمة لـ Validation Framework أصلًا.

### 3) إيه دليلكم إن التقرير النهائي مش مجرد Output خام من الـ AI؟
**الإجابة:** عندنا دليل برمجي حتمي: سكربت `diff_draft.py` قارن `vapt-report-ai-draft.md` مع `vapt-report-human-edited.md` وأثبت إن التشابه في الكلمات **10.3%** فقط (تم حذف 339 كلمة وتصحيح 8+ أخطاء وتعديلات)، وكل درجات CVSS اتحسبت بمعادلة رياضية داخل `calc_cvss.py` مش بتخمين لغوي.

### 4) إزاي بتمنعوا الـ AI يهلوس في مسارات Active Directory؟
**الإجابة:** مش بنسيب الـ AI يخمّن المسار من JSON خام! سكربت `bloodhound_to_context.py` بيشغّل خوارزمية **BFS** رياضية الأول ويطلع `bloodhound_ground_truth.json`، ولما `qwen` أخطأ في التقييم `W2-05` وربط `svc-sync` بـ `IT-Admins`، الـ BFS كشفه فورًا.

### 5) هل شغلتوا Active Directory حقيقي بـ Windows Server أو Samba؟
**الإجابة:** بكل أمانة لأ — اشتغلنا على **Structured Lab Dataset (`LAB.LOCAL` 11 node / 8 edges)** ومحددين ده صراحة في التقرير والجدول عشان إمكانيات اللابتوب (16 GB RAM)، بينما Kali WSL Apache/MariaDB/DVWA و `jadx` اشتغلوا بشكل حي وفعلي بالكامل.

### 6) نفس السؤال عن الموبايل — هل شغلتوا Frida على Emulator أو موبايل حقيقي؟
**الإجابة:** التحقق في `DIVA` كان **Static + Signature Verification**: فكّينا `diva-beta.apk` فعليًا بـ `jadx v1.5.6` (`718` كلاس) واتأكدنا من سطور الثغرات ومن صحة الـ JS Syntax وأسماء الـ Classes/Methods اللي Frida scripts بتعمل لها hook، والسكربتات جاهزة للتشغيل على أي جهاز أو Emulator متاح.

### 7) لماذا ذكرتم إن المشروع "Privacy-First" مع إن Port Solver بيتصل بالإنترنت؟
**الإجابة:** نفرّق بدقة: **الاستدلال الذكي (`LLM Inference`)** شغال 100% محليًا على `127.0.0.1:11434` (مفيش أي prompt بيخرج لشركة AI). أما **ميزة PortSwigger Inspect / Solver** فهي أداة اختيارية بتتصل بـ HTTPS فقط بمثيل التدريب الخاص بالمستخدم (`*.web-security-academy.net`) بعد موافقته، وده موضّح صراحة في `README` و `Privacy Checklist`.

### 8) إزاي بتضمنوا إن الـ Port Solver ميهجمش على مواقع تانية أو يضرب `localhost` بـ SSRF؟
**الإجابة:** عن طريق طبقة **`scripts/safe_lab_http.py`**:
- بيقبل HTTPS فقط ولنطاق `*.web-security-academy.net` فقط.
- بيعمل DNS Resolution checks ويحظر أي IP خاص/محلي/Loopback/Metadata (`127.x`, `10.x`, `169.254.169.254`).
- بيقفل الـ Redirects (`Host Pinning`) عشان لو السيرفر حاول يحولك لهدف تاني يتوقف فورًا.
- أي طلب `POST` أو تغيير حالة مقفول إلا بعلامة الموافقة الصريحة من الـ GUI (`allow_state_changes`)، وبيشتغل بحد أقصى للطلبات.

### 9) إزاي بتتأكدوا إن الـ Port Solver مش بيكدب ويقول "Solved" وهو محلش اللاب؟
**الإجابة:** دالة `port_solver.py` بتفصل تمامًا بين حالة الاستنتاج (`Agentic Attempt`) وحالة النجاح (`solved`) — لا يُسجّل `solved` إلا لو ظهر نص تأكيد الحل الرسمي بتاع PortSwigger في رد الـ HTTP الحقيقي؛ غير كده يرجع `attempted` أو `not_solved` أو `blocked` أو `expired` بكل وضوح.

### 10) إيه فايدة التوكن (`X-VAPT-Session`) في واجهة الويب مادام السيرفر على `127.0.0.1`؟
**الإجابة:** عشان نمنع هجمات **CSRF أو DNS Rebinding** من أي صفحة ويب تانية فاتحها المستخدم على نفس المتصفح! أي `POST` على الـ Backend لازم يكون جاي من نفس الـ Origin (`127.0.0.1:8000`) ومعاه التوكن العشوائي اللي اتولد وقت التشغيل.

### 11) تحديات الـ 12 ثغرة جابت 12/12 — ده معناه إن الـ AI بيحل أي موقع لوحده 100%؟
**الإجابة:** لا طبعًا! تقييم الـ 12 كان **Passive Triage** على كابتشرات HTTP موجودة لتحديد نوع الثغرة والباراميتر (`W1` على `qwen2.5:3b`) بإشارات Heuristic (`deliverables/challenge-evaluation-results.md`)، وده بيوفر وقت القراءة الأولية جدًا، لكن الاستغلال الفعلي والتحقق بيفضل تحت إشراف المحلل.

### 12) لو هتطوروا المشروع ده بعد التخرج (`Future Work`) هتعملوا إيه؟
**الإجابة:** 3 خطوات مباشرة:
- إضافة `Ingest Adapters` جديدة لـ `Nuclei JSON` و `ffuf` و `Responder/CrackMapExec`.
- ربط موديلات `7B/8B` على GPU أكبر (أو موديلات `Ollama` أحدث) مع الحفاظ على نفس بوابة `L1–L4` ونظام الـ Regression Tests.
- تشغيل الـ AD والـ Mobile على بيئة حية (Samba/GOAD + Android Emulator مع Frida runtime) وإضافتها لنفس الداشبورد.
