<div align="center">
  <img src="assets/icon.png" width="150" alt="FlorisSrt Logo">
  <h1>FlorisSrt</h1>
  <p><b>Advanced Agentic AI Subtitle Localization Pipeline for Project</b></p>
</div>

FlorisSrt is a highly specialized, context-aware translation pipeline designed for localizing Project subtitles (ASS/SRT) using advanced Large Language Models (LLMs). It utilizes a robust architecture capable of maintaining character consistency, managing glossaries, tracking costs, and overcoming token limits without sacrificing translation quality.

---

## 🌟 Key Features

* **Agentic Translation System**: Uses dual-agents (Linguistic Validator & Translation Engine) to cross-verify JSON outputs, preventing the common "hallucinations" of LLMs.
* **Wiki Scraper (NEW)**: Fetch character names, genders, abilities, and locations directly from **Anilist**, **MAL**, or **Fandom** wikis — import them into any project with one click.
* **Pre-Analyze (Auto-Extraction)**: AI-powered extraction of characters and terminology from raw subtitle files before translation begins.
* **Global Usage Ledger & Cost Tracker**: A complete accounting system that tracks Token consumption, estimates costs securely with crash-proof buffers (atomic writes), and provides detailed filtering across providers and models.
* **Fault Tolerance & Dynamic Fallbacks**: Resilient against API timeouts with Exponential Backoff and Circuit Breakers. It dynamically drops rigid JSON structures when interacting with advanced reasoning models (DeepSeek-Reasoner, OpenAI o1) preventing 400 Bad Request loops.
* **Context-Aware Window**: Analyzes dialogue within a sliding window (Last 5 translated lines + Next 2 raw lines) to perfectly capture the flow of conversation and implicit pronouns.
* **Smart Glossary & Term Memory**: Automatically detects and enforces terminology from a project-wide glossary. It also builds a "Term Memory" across episodes to ensure consistency in long-running series.
* **Batch Processing Queue**: Drag-and-drop entire folders to translate entire seasons autonomously. It skips already-translated files efficiently.
* **Full UTF-8/Arabic File Support**: Native support for Unicode file names, allowing Arabic project titles to parse perfectly without metadata loss.

## 🚀 Installation & Prerequisites

### Prerequisites
- **Python 3.10+**
- An active API Key for OpenAI, DeepSeek, OpenRouter, or Gemini.

### Setup
1. Clone the repository:
   ```cmd
   git clone https://github.com/monesir/FlorisSrt.git
   cd FlorisSrt
   ```
2. Install the required dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

```

The application is divided into **7 main tabs**:

### 1. Run Tab (Main Dashboard)
This is where the magic happens.
- **File/Folder Mode (Batch)**: Select a single file or a directory. The system will line up files and translate them sequentially, smartly auto-detecting or assigning the Target Project name based on your choice.
- **Resume Button**: If the translation was interrupted, clicking `Resume` will pick up exactly where it left off, avoiding duplicate token costs.
- **`+ New` Button**: Instantly create a new project without switching tabs.

### 2. Pre-Analyze Tab (Auto-Extraction)
AI-powered analysis that reads raw subtitle files and automatically extracts:
- **Characters**: Names, descriptions, and suggested Arabic transliterations.
- **Glossary Terms**: Locations, abilities, organizations, and in-world terminology.
- **Modes**: `Balanced` (both), `Characters Only`, or `Terms Only`.
- Results can be reviewed, selectively imported to any project, or exported.
- Supports all LLM providers (OpenAI, DeepSeek, Gemini, OpenRouter, Anthropic).

### 3. Data Editor Tab
Organizes lore and terminology on a per-project basis.
- **Characters & Context**: Define the story, names, genders, and arabic names. The LLM uses this to attribute pronouns perfectly.
- **Glossary & Term Memory**: Force specific terms to be used, and watch as the LLM naturally populates the Term Memory to remember newly discovered lore across episodes.
- **`+ New` Button**: Create projects inline.

### 4. Review Tab
Post-translation editing interface.
- **Splitter UI**: A fluid `QSplitter` layout allowing you to view translation chunks, spot errors (marked Failed if identical to English), and manually rewrite subtitles with ease before saving the final `.ass` file.

### 5. Usage Tab (Cost Tracking)
A unified hub to monitor your API usage and tokens.
- **Interactive Table**: Displays a detailed, filterable, and resizable grid showing input/output tokens and cost per run.
- **Pricing Setup**: Manually input the pricing (In/Out per 1M tokens) for your favorite models to generate accurate `$0.00` estimates.

### 6. Wiki Scraper Tab (NEW ✨)
Fetch metadata directly from anime databases without leaving the app.
- **Sources**: Anilist, MAL (MyAnimeList), Fandom (Characters), Fandom (Wiki Data).
- **Characters**: Automatically detects gender using category analysis or wikitext pronoun detection.
- **Fandom Wiki Data**: Extracts abilities, locations, and lore terms from Fandom wikis.
- **Subpage Filter**: Automatically removes false entries like `/Abilities`, `/Gallery` subpages.
- **Import**: One-click import of characters or glossary terms to any selected project.
- **Export**: Export results as CSV for external use.
- **`+ New` Button**: Create a project directly from the scraper tab.
- **Searchable Dropdown**: Type to filter projects instantly.

### 7. Settings Tab
Configure your translation engine and parameters.
- **LLM Provider & Model Name**: Choose between `openai`, `deepseek`, `openrouter`, `gemini`, or `local`, and explicitly type the model name.
- **Test Connection**: A handy button to verify that your API key and network are working before starting a massive translation batch.
- **Translation Style**: Standard (فصحى), White Colloquial (عامية بيضاء), Egyptian (عامية مصرية), Saudi (عامية سعودية).

---

<div align="right" dir="rtl">

## 🌟 أبرز المميزات (النسخة العربية)

* **نظام الوكلاء الذكي (Agentic System)**: محرك الترجمة يمتلك نظام تدقيق داخلي (Validator) يراقب مخرجات الذكاء الاصطناعي ويجبره على تصحيح الأخطاء لضمان الجودة العالية.
* **جالب الويكي (Wiki Scraper) ✨**: جلب أسماء الشخصيات وجنسهم والقدرات والأماكن مباشرة من **Anilist** و **MAL** و **Fandom** — واستيرادها لأي مشروع بضغطة واحدة.
* **التحليل المسبق (Pre-Analyze)**: استخراج ذكي للشخصيات والمصطلحات من ملفات الترجمة الخام قبل بدء الترجمة.
* **دفتر محاسبة الاستهلاك (Usage Ledger)**: نظام محاسبي كامل يتعقب استهلاك التوكنز ويحسب التكلفة بالدولار بدقة عالية لكل مزود وموديل، مع نظام حفظ آمن (Atomic Writes) لمنع تلف البيانات.
* **دعم الموديلات المعقدة (o1 & Reasoner)**: ميزة ديناميكية لتخطي قيود الـ JSON والسماح للموديلات الحديثة جداً بالعمل بكفاءة دون أخطاء الـ `400 Bad Request`.
* **نافذة السياق المحيط**: النظام لا يترجم السطر بشكل أعمى، بل يقرأ آخر 5 أسطر تمت ترجمتها مع أول سطرين قادمين ليفهم مجرى الحوار.
* **ذاكرة المصطلحات والقاموس**: يمكنك إضافة أسماء الشخصيات والقدرات ليلتزم بها المترجم. البرنامج أيضاً يصنع ذاكرة تلقائية للمصطلحات.
* **دعم أسماء الملفات العربية**: توافق كامل لإنشاء مشاريع مسماة باللغة العربية دون فقدان خصائصها أو تعرضها للأخطاء.

## 🚀 متطلبات التشغيل

- **بايثون (Python 3.10+)**
- مفتاح API نشط (مثل DeepSeek أو OpenAI).

لتشغيل البرنامج بعد تحميله وتثبيت المكتبات `pip install -r requirements.txt`، اضغط على ملف `main.py` أو الاختصار الجاهز وسيعمل بواجهته الأنيقة مباشرة!

## 💻 دليل استخدام الواجهة (GUI)

### 1. تبويب التشغيل (Run)
- **ترجمة مجلد كامل (Batch Folder)**: حدد مجلداً كاملاً وسيقوم بوضع كل الحلقات في طابور و يترجمها تباعاً. سيتم فرض اسم المشروع الذي تختاره من خانة `Target Project` على كامل الدفعة.
- **زر الاستئناف (Resume)**: إن توقف البرنامج، اضغطه ليعود المترجم من نفس السطر الذي توقف عنده لتوفير التكلفة!

### 2. التحليل المسبق (Pre-Analyze)
- تحليل ذكي يستخرج الشخصيات والمصطلحات من ملفات الترجمة الخام تلقائياً باستخدام الذكاء الاصطناعي.
- يدعم 3 أوضاع: متوازن، شخصيات فقط، مصطلحات فقط.

### 3. محرر البيانات (Data Editor)
- **السياق (Context)**: نبذة عن الأنمي ليفهم المحرك طبيعة العالم.
- **الشخصيات (Characters)**: حدد جنس الشخصيات ليضبط البرنامج الضمائر العربية.
- **القاموس (Glossary)**: لتوحيد أسماء القدرات والمدن طوال الأنمي.

### 4. تبويب المراجعة (Review)
- واجهة مقسمة (Splitter) تتيح لك قراءة الترجمة، اكتشاف الأسطر المتطابقة مع الإنجليزية (Unchanged/Failed)، وتعديلها يدوياً بسهولة في مساحة عمل مريحة ثم إعادة بناء الملف.

### 5. تبويب الاستهلاك (Usage)
- لوحة تحكم ذكية لعرض المبالغ المستهلكة بالدولار لكل أنمي أو موديل. يمكنك إدخال تسعيرة الموديل (لكل مليون توكن) وسيحسب لك التكلفة اللحظية للـ `Run` الحالي.

### 6. جالب الويكي (Wiki Scraper) ✨
- **جلب من مصادر متعددة**: Anilist، MAL، Fandom (شخصيات)، Fandom (بيانات ويكي).
- **كشف الجنس تلقائياً**: عبر تصنيفات الفاندوم أو تحليل الضمائر في نصوص الويكي.
- **فلتر الصفحات الفرعية**: يحذف تلقائياً الصفحات الزائفة مثل `/Abilities` و `/Gallery`.
- **استيراد بضغطة واحدة**: استيراد الشخصيات أو المصطلحات لأي مشروع مباشرة.
- **تصدير CSV**: لتصدير النتائج واستخدامها خارجياً.

### 7. تبويب الإعدادات (Settings)
- **فحص الاتصال (Test Connection)**: زر سريع للتأكد من أن مفتاحك يعمل.
- **نمط الترجمة**: فصحى معيارية، عامية بيضاء، عامية مصرية، عامية سعودية.

</div>
