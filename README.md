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

## 💻 Usage

### Launching the GUI
You can start the graphical user interface by double-clicking the `FlorisSrt.lnk` shortcut, or by running the following command in the terminal:
```cmd
pythonw gui/main.py
```

### 1. Configuration
Navigate to the **Settings** tab to:
- Select your preferred LLM Provider (DeepSeek, OpenAI, etc.).
- Input your API Key.
- Select the Log Language (Bilingual, English, or Arabic).

### 2. Single File Translation
1. Go to the **Run** tab.
2. Click **File** and select an `.ass` or `.srt` file.
3. Click **Start Translation**. 

### 3. Batch Directory Translation
1. Go to the **Run** tab.
2. Click **Folder** and select a directory containing multiple subtitle files.
3. The queue will automatically populate and process episodes sequentially.

### 4. Data Editor (Context & Glossary)
FlorisSrt organizes data on a **per-project basis**. 
Once a translation is started, the **Data Editor** unlocks, allowing you to:
- Add characters and their background descriptions to improve the AI's understanding of the narrative.
- Manage the Global Glossary to enforce specific translations (e.g., proper nouns, magic spells).
- View the auto-generated Term Memory.

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

</div>
