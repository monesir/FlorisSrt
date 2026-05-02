<div align="center">
  <img src="assets/icon.png" width="150" alt="FlorisSrt Logo">
  <h1>FlorisSrt</h1>
  <p><b>Advanced Agentic AI Subtitle Localization Pipeline for Project</b></p>
</div>

FlorisSrt is a highly specialized, context-aware translation pipeline designed for localizing Project subtitles (ASS/SRT) using advanced Large Language Models (LLMs). It utilizes a robust architecture capable of maintaining character consistency, managing glossaries, tracking costs, and overcoming token limits without sacrificing translation quality.

---

## 🌟 Key Features

* **Agentic Translation System**: Uses dual-agents (Linguistic Validator & Translation Engine) to cross-verify JSON outputs, preventing the common "hallucinations" of LLMs.
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

## 💻 GUI Guide (How to Use)

### Launching the App
You can start the graphical user interface by double-clicking the **`FlorisSrt`** shortcut, or by running:
```cmd
pythonw gui/main.py
```

The application is divided into several main tabs:

### 1. Run Tab (Main Dashboard)
This is where the magic happens.
- **File/Folder Mode (Batch)**: Select a single file or a directory. The system will line up files and translate them sequentially, smartly auto-detecting or assigning the Target Project name based on your choice.
- **Resume Button**: If the translation was interrupted, clicking `Resume` will pick up exactly where it left off, avoiding duplicate token costs.

### 2. Settings Tab
Configure your translation engine and parameters.
- **LLM Provider & Model Name**: Choose between `openai`, `deepseek`, `openrouter`, or `gemini`, and explicitly type the model name.
- **Test Connection**: A handy button to verify that your API key and network are working before starting a massive translation batch.
- **Constraint Mode**: 
  - `strict`: Enforces hard limits on characters per second (CPS) and strictly matches the source tags.
  - `balanced`: Relaxes line-length limits slightly for better linguistic flow.
  - `off`: Disables length constraints.

### 3. Usage Tab (Cost Tracking)
A unified hub to monitor your API usage and tokens.
- **Interactive Table**: Displays a detailed, filterable, and resizable grid showing input/output tokens and cost per run.
- **Pricing Setup**: Manually input the pricing (In/Out per 1M tokens) for your favorite models to generate accurate `$0.00` estimates.

### 4. Review Tab
Post-translation editing interface.
- **Splitter UI**: A fluid `QSplitter` layout allowing you to view translation chunks, spot errors (marked Failed if identical to English), and manually rewrite subtitles with ease before saving the final `.ass` file.

### 5. Data Editor Tab
Organizes lore and terminology on a per-project basis.
- **Characters & Context**: Define the story, names, and genders. The LLM uses this to attribute pronouns perfectly.
- **Glossary & Term Memory**: Force specific terms to be used, and watch as the LLM naturally populates the Term Memory to remember newly discovered lore across episodes.

---

<div align="right" dir="rtl">

## 🌟 أبرز المميزات (النسخة العربية)

* **نظام الوكلاء الذكي (Agentic System)**: محرك الترجمة يمتلك نظام تدقيق داخلي (Validator) يراقب مخرجات الذكاء الاصطناعي ويجبره على تصحيح الأخطاء لضمان الجودة العالية.
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

### 2. تبويب الإعدادات (Settings)
- **فحص الاتصال (Test Connection)**: زر سريع للتأكد من أن مفتاحك يعمل.
- **نظام القيود (Constraint Mode)**: اختر `strict` للالتزام الصارم بتوقيتات الـ ASS ووسومه، أو `balanced` لإعطاء الذكاء حرية لغوية أكبر.

### 3. تبويب الاستهلاك (Usage)
- لوحة تحكم ذكية لعرض المبالغ المستهلكة بالدولار لكل أنمي أو موديل. يمكنك إدخال تسعيرة الموديل (لكل مليون توكن) وسيحسب لك التكلفة اللحظية للـ `Run` الحالي.

### 4. تبويب المراجعة (Review)
- واجهة مقسمة (Splitter) تتيح لك قراءة الترجمة، اكتشاف الأسطر المتطابقة مع الإنجليزية (Unchanged/Failed)، وتعديلها يدوياً بسهولة في مساحة عمل مريحة ثم إعادة بناء الملف.

### 5. محرر البيانات (Data Editor)
- **السياق (Context)**: نبذة عن الأنمي ليفهم المحرك طبيعة العالم.
- **الشخصيات (Characters)**: حدد جنس الشخصيات ليضبط البرنامج الضمائر العربية.
- **القاموس (Glossary)**: لتوحيد أسماء القدرات والمدن طوال الأنمي.

</div>
