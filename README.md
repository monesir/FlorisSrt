<div align="center">
  <img src="assets/icon.png" width="150" alt="FlorisSrt Logo">
  <h1>FlorisSrt</h1>
  <p><b>Advanced Agentic AI Subtitle Localization Pipeline for Anime</b></p>
</div>

FlorisSrt is a highly specialized, context-aware translation pipeline designed for localizing Anime subtitles (ASS/SRT) using advanced Large Language Models (LLMs). It utilizes a robust architecture capable of maintaining character consistency, managing glossaries, and overcoming token limits without sacrificing translation quality.

---

## 🌟 Key Features

* **Agentic Translation System**: Uses dual-agents (Linguistic Validator & Translation Engine) to cross-verify JSON outputs, preventing the common "hallucinations" of LLMs.
* **Context-Aware Window**: Analyzes dialogue within a sliding window (Last 5 translated lines + Next 2 raw lines) to perfectly capture the flow of conversation and implicit pronouns.
* **Smart Glossary & Term Memory**: Automatically detects and enforces terminology from a project-wide glossary. It also builds a "Term Memory" across episodes to ensure consistency in long-running series.
* **Fault Tolerance & Circuit Breaker**: Resilient against API timeouts and rate limits with Exponential Backoff and an automated Circuit Breaker.
* **Batch Processing Queue**: Drag-and-drop entire folders to translate entire seasons autonomously. It skips already-translated files efficiently.
* **Intelligent Rebuilder**: Carefully preserves ASS timing, screen positions, and complex inline styling tags (`{\i1}`, `{\an8}`, etc.).

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

The application is divided into three main tabs:

### 1. Run Tab (Main Dashboard)
This is where the magic happens.
- **File Mode**: Select a single `.ass` or `.srt` file. The system will automatically resolve the anime name and episode number.
- **Folder Mode (Batch)**: Select an entire directory. The system will line up all subtitle files into a batch queue and translate them one by one. It intelligently skips files that have already been translated.
- **Resume Button**: If the translation was interrupted or stopped, clicking `Resume` will pick up exactly where it left off, avoiding duplicate token costs.
- **Live Logs**: Watch the dual-agent translation process in real-time, including context tracking and token usage.

### 2. Settings Tab
Configure your translation engine and parameters.
- **LLM Provider & Model Name**: Choose between `openai`, `deepseek`, `openrouter`, or `gemini`, and explicitly type the model name (e.g., `gpt-4o`, `deepseek-chat`).
- **API Key & Base URL**: Securely input your API key. If using proxy endpoints, define the custom API base URL here.
- **Test Connection**: A handy button to verify that your API key and network are working before starting a massive translation batch.
- **Path Overrides**: Optionally override the default project folders for Glossary, Characters, Context, and Output locations.
- **Constraint Mode**: 
  - `strict`: Enforces hard limits on characters per second (CPS) and strictly matches the source tags.
  - `balanced`: Relaxes line-length limits slightly for better linguistic flow.
  - `off`: Disables length constraints (not recommended for ASS).
- **Log Language**: Personalize the live logs to display in English, Arabic, or a Bilingual split format.
- **Max Retries & Timeout**: Configure the AI's fallback limits. If a response is mangled, the Validator will retry up to *Max Retries*. If the API is overloaded, it will wait up to *Timeout* seconds before triggering the Circuit Breaker.

### 3. Data Editor Tab (Unlocks upon running)
FlorisSrt organizes lore and terminology on a **per-project basis**. Once a translation is initialized for an anime, this tab unlocks.
- **Context & Story**: Write a brief synopsis of the episode or anime. The LLM uses this to understand the atmosphere.
- **Characters**: Add character names and genders. The LLM will use this to correctly attribute gendered pronouns in Arabic (e.g., using "أنتَ" for males vs "أنتِ" for females).
- **Glossary**: Add specific proper nouns or fictional terms (like Magic Spells, City names) and force the LLM to always use your translation.
- **Term Memory**: A read-only auto-generated dictionary where the LLM records how it translated new terms, guaranteeing that it uses the exact same translation in future episodes!

---

<div align="right" dir="rtl">

## 🌟 أبرز المميزات (النسخة العربية)

* **نظام الوكلاء الذكي (Agentic System)**: محرك الترجمة يمتلك نظام تدقيق داخلي (Validator) يراقب مخرجات الذكاء الاصطناعي ويجبره على تصحيح الأخطاء لضمان الجودة العالية وعدم فقدان التنسيقات.
* **نافذة السياق المحيط**: النظام لا يترجم السطر بشكل أعمى، بل يقرأ آخر 5 أسطر تمت ترجمتها مع أول سطرين قادمين ليفهم مجرى الحوار والمشاعر.
* **ذاكرة المصطلحات والقاموس**: يمكنك إضافة أسماء الشخصيات والقدرات ليلتزم بها المترجم. كما أن البرنامج يصنع ذاكرة تلقائية للمصطلحات التي يترجمها ليستعين بها في الحلقات القادمة.
* **حماية ضد الانهيار**: مزود بنظام (Circuit Breaker) للتعامل مع ضغط سيرفرات הـ API أو التوقف المفاجئ.
* **معالجة المجلدات (Batch Processing)**: حدد مجلداً كاملاً وسيقوم البرنامج بترجمة كافة الحلقات بداخله تباعاً أثناء نومك!

## 🚀 متطلبات التشغيل

- **بايثون (Python 3.10+)**
- مفتاح API نشط (مثل DeepSeek أو OpenAI).

لتشغيل البرنامج بعد تحميله وتثبيت المكتبات `pip install -r requirements.txt`، يمكنك فقط الضغط مرتين على أيقونة `FlorisSrt` (الاختصار الموجود في المجلد) وسيعمل بواجهته الأنيقة مباشرة!

## 💻 دليل استخدام الواجهة (GUI)

البرنامج مقسم إلى ثلاثة تبويبات رئيسية لتسهيل العمل:

### 1. تبويب التشغيل (Run)
هو غرفة التحكم الرئيسية للمترجم.
- **ترجمة ملف واحد (File)**: اختر ملف حلقة واحدة، وسيتعرف البرنامج تلقائياً على اسم الأنمي ورقم الحلقة.
- **ترجمة مجلد كامل (Folder)**: يمكنك تحديد مجلد الموسم بالكامل! سيقوم البرنامج بوضع كل الحلقات في طابور انتظار، ويترجمها حلقة تلو الأخرى تلقائياً. (كما يتخطى الحلقات المترجمة مسبقاً بذكاء).
- **زر الاستئناف (Resume)**: في حال انقطاع الإنترنت أو إيقافك للبرنامج، اضغط هنا ليعود البرنامج للترجمة من نفس السطر الذي توقف عنده دون استهلاك رصيد API إضافي!
- **سجل الأحداث (Logs)**: شاشة حية تعرض لك ما يقرؤه ويترجمه الذكاء الاصطناعي لحظة بلحظة.

### 2. تبويب الإعدادات (Settings)
مكان تجهيز المحرك والمزود بدقة متناهية.
- **المزود واسم الموديل (Provider & Model)**: يدعم (DeepSeek, OpenAI, OpenRouter) وغيرها، مع إمكانية كتابة اسم الموديل يدوياً (مثل `gpt-4o`).
- **مفتاح API والـ Base URL**: ضع مفتاحك هنا بأمان. وإذا كنت تستخدم خوادم بديلة أو بروكسي، يمكنك وضع الرابط المخصص.
- **فحص الاتصال (Test Connection)**: زر سريع للتأكد من أن مفتاحك يعمل والإنترنت مستقر قبل بدء ترجمة مجلد ضخم.
- **مسارات مخصصة (Path Overrides)**: إن لم تكن ترغب في استخدام المسارات الافتراضية للبرنامج، يمكنك تحديد مسار خارجي للقاموس أو مجلد المخرجات.
- **نظام القيود (Constraint Mode)**:
  - `strict`: صارم جداً! يجبر الذكاء الاصطناعي على الالتزام بعدد محدد من الحروف في الثانية (CPS) ومطابقة وسوم الألوان تماماً.
  - `balanced`: متوازن. يعطي الذكاء الاصطناعي مساحة حرية إضافية في طول الجمل للحفاظ على بلاغة اللغة العربية.
  - `off`: إيقاف القيود (لا يُنصح به لملفات الـ ASS المتقدمة).
- **لغة السجل (Log Language)**: يمكنك اختيار عرض سجل الأحداث باللغة العربية، أو الإنجليزية، أو مدمج.
- **محاولات التصحيح والمهلة (Retries & Timeout)**: إذا أخطأ الذكاء الاصطناعي في هيكل التنسيق، سيقوم (المدقق) بإجباره على إعادة المحاولة بناءً على العدد الذي تحدده هنا. كما يمكنك تحديد مهلة الانتظار القصوى للرد.

### 3. تبويب محرر البيانات (Data Editor)
**هذا التبويب يفتح تلقائياً بمجرد بدئك لترجمة أي أنمي!** وهو المكان السري الذي يجعل ترجمتك احترافية:
- **سياق القصة (Context)**: يمكنك كتابة نبذة عن الأنمي ليفهم المحرك طبيعة العالم (هل هو عالم سحري؟ حروب فضاء؟ كوميديا؟).
- **الشخصيات (Characters)**: أضف أسماء الشخصيات وجنسهم (ذكر/أنثى)، ليتمكن البرنامج من استخدام الضمائر العربية بشكل صحيح تماماً (أنتَ / أنتِ / ذهبتْ / ذهبَ).
- **القاموس (Glossary)**: أضف المصطلحات الخيالية، أسماء المدن، والقدرات السحرية، وأجبر الذكاء الاصطناعي على ترجمتها كما تريد أنت في كل مرة.
- **ذاكرة المصطلحات (Term Memory)**: جدول ذكي يقوم الذكاء الاصطناعي بتعبئته بنفسه! حين يترجم مصطلحاً جديداً لأول مرة سيحفظه هنا ليتذكره في الحلقات القادمة دون تدخل منك!

</div>
