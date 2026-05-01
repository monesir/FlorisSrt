# المواثيق والقواعد الإلزامية لمشروع Anime Translator (Contracts & Schemas)

## 0) قواعد إلزامية (Core Contract)
* **لا تعديل على منطق الترجمة في `pipeline.py`**.
* كل التواصل مع `pipeline.py` من الواجهة يتم عبر الـ `subprocess` فقط.
* كل البيانات تُخزن في ملفات `JSON` وفق المخططات (Schemas) المحددة أدناه حصراً.
* لا يُسمح للـ GUI بالكتابة في الملفات أثناء تشغيل `pipeline`.
* كل عمليات الكتابة إلى `JSON` يجب أن تكون **Atomic Write** (الكتابة إلى ملف مؤقت ثم عمل `rename` لتجنب تلف الملفات).

---

## 1) أولوية الإعدادات (Config Precedence - إلزامي)
الترتيب التفضيلي للإعدادات كالتالي:
`CLI args > GUI config (user_settings.json) > project data > defaults`
* إذا مرّر GUI قيمة، فهي تتغلب على الـ `project data`.
* إذا لم تُمرّر قيمة من الـ GUI، يستخدم النظام الـ `project data`.
* إن لم يوجد في أي منهما، يستخدم النظام الـ `default`.

---

## 2) تجريد مزود الخدمة (Provider Abstraction - إلزامي)
الاعتماد على واجهة واحدة للنماذج لتسهيل تغيير المزود:
```python
class ModelProvider:
    def send(self, prompt: str, timeout: int) -> str: ...
```
**التنفيذات (Implementations):**
* `OpenAIProvider`
* `AnthropicProvider`
* `LocalProvider`

**تحديد المزود في `user_settings.json`:**
```json
{
  "model": {
    "provider": "openai",
    "name": "gpt-4o",
    "api_key": "..."
  }
}
```

---

## 3) مخططات البيانات الإلزامية (Data Schemas)

### (A) `glossary.json`
```json
{
  "terms": [
    {
      "term": "master",
      "translation": "سيدي",
      "type": "hard"
    }
  ]
}
```

### (B) `characters.json`
```json
{
  "characters": [
    {
      "name": "Eren",
      "gender": "male"
    }
  ]
}
```

### (C) `work_context.json`
```json
{
  "description": "string"
}
```

### (D) `term_memory.json`
```json
{
  "master": {
    "translation": "سيدي",
    "count": 12,
    "last_used": 1710000000,
    "locked": true
  }
}
```

### (E) `state.json` (Episode-level)
```json
{
  "current_chunk": 3,
  "status": "running",
  "degraded_chunks": [5, 9]
}
```

### (F) `user_settings.json` (Global Config)
```json
{
  "model": {
    "provider": "openai",
    "name": "gpt-4o",
    "api_key": ""
  },
  "paths": {
    "glossary": "",
    "characters": "",
    "work_context": ""
  },
  "output": {
    "folder": ""
  },
  "execution": {
    "constraint_mode": "balanced",
    "max_retries": 5,
    "timeout": 30
  }
}
```

---

## 4) تحليل المشروع (Project Resolution - إلزامي)
```python
def resolve_project(input_path: str) -> tuple[str, str]:
    """
    returns (anime_slug, episode_slug)
    """
```
**القواعد:**
* استخدم مكتبة `guessit` لاستخراج المعلومات.
* في حال الفشل (Fallback): استخدم `regex: S\d+E\d+`.
* **الـ Normalization:** تحويل لأحرف صغيرة (lowercase)، استبدال المسافات بالشرطة (`-`)، وحذف الرموز.

---

## 5) تأسيس المشروع (Bootstrap - إلزامي)
```python
def bootstrap_project(anime: str) -> None:
```
* يُنشئ المجلدات: `projects/{anime}/data/`.
* يُنشئ ملفات الـ `JSON` الافتراضية فارغة بناءً على הـ Schemas المذكورة بالأعلى.
* لا يكتب أي قيم أو مفاتيح غير مطلوبة.

---

## 6) المشغل (Runner - subprocess فقط)
```python
def start_pipeline(input_path: str) -> subprocess.Popen:
```
* **يُمنع استخدام Thread داخل הـ GUI لتشغيل الـ Core.**
* استخدم `subprocess.Popen`.
* يجب تخزين الـ `PID` للتحكم.

**الإيقاف (Stop):**
```python
def stop_pipeline(process: subprocess.Popen) -> None:
    process.terminate()
```
**الاستئناف (Resume):**
* يعتمد كلياً على `state.json`.
* لا يُعيد التشغيل من البداية أبدًا.

---

## 7) قارئ السجلات (Log Reader)
```python
def read_progress(project_path: str) -> dict:
```
يقرأ ملف `chunks.log` ويعيد البيانات التالية للـ GUI لتحديث شريط التقدم:
```json
{
  "current": 3,
  "total": 20,
  "status": "running"
}
```

---

## 8) مستخرج البيانات (JSON Extractor - إلزامي)
```python
def extract_json(text: str) -> list:
```
**الخطوات الإلزامية:**
1. إزالة وسوم الماركدون ````json ```` إن وُجدت.
2. استخدام `regex` لاستخراج المصفوفة `[ ... ]` من النص.
3. معالجتها عبر `json.loads`.
4. **إذا فشل** ← يتم رمي استثناء (Raise) ← يؤدي للـ `Retry`.

---

## 9) سياسة إعادة المحاولة (Retry Policy - إلزامي)
* الحد الأقصى للمحاولات: `max_retries = 5`
* استراتيجية الانتظار (Exponential Backoff): `backoff = 2 ** attempt`
* مهلة الطلب (Timeout): تُؤخذ من `config.execution.timeout`

---

## 10) سياسة الفشل (Failure Policy)
إذا استُنفدت كل المحاولات (`max_retries`):
1. تعليم الشنك كـ `degraded`.
2. استخدام النص الأصلي الإنجليزي (Fallback) لضمان عدم توقف المشروع.

---

## 11) محرك القيود (Constraint Engine)
```python
def apply_constraints(text: str, duration: float) -> str:
```
**القواعد الأساسية:**
* الحد الأقصى للأسطر: 2 (`max 2 lines`).
* الحد الأقصى للسطر الواحد: 40 حرف (`max 40 char/line`).
* **عتبات الـ CPS (Characters Per Second):**
  * إذا تجاوز `22` ← تفعيل الضغط (Compress).
  * إذا تجاوز `17` ← تفعيل التقسيم (Split).

---

## 12) قواعد ذاكرة المصطلحات (Term Memory Rules)
* الحد الأقصى للإدخالات: `max 50 entries`.
* **الإخلاء (Eviction):** ترتيب تصاعدي حسب الاستخدام الأقل، ثم الأقدم (`sort by count ASC, last_used ASC`).
* **القفل (Locked):** إذا كان `locked: true`، يُمنع حذفه أو تغييره آلياً.

---

## 13) أولوية القواميس (Glossary Priority)
الترتيب من الأقوى للأضعف:
`hard glossary > locked term_memory > normal term_memory > model`

---

## 14) قواعد الواجهة (GUI Rules - إلزامي)
* يُمنع تشغيل `pipeline` داخل הـ `UI thread`.
* كل العمليات الثقيلة يجب أن تنفذ في الخلفية خارج הـ `UI`.
* **محرر البيانات (Data Editor):** يتم تعطيله (Disabled) أثناء التشغيل.
* يجب عرض المشروع الفعال בوضوح: `Editing Project: {anime}`.

---

## 15) قفل الملفات (File Locking)
* **الكتابة:** `write temp → rename` (كتابة ذرية Atomic).
* **القراءة:** `read-only` فقط، دون الاحتفاظ بالقفل (`hold lock`).

---

## 16) الترميز (Encoding)
* المحاولة الأولى: `try utf-8`
* البديل في حال الفشل: `else chardet detect`

---

## 17) أمان الإيقاف (Stop Safety)
* عند ضغط `Stop`، **لا يُحذف** ملف `state.json`.
* يجب أن يدعم النظام الـ `resume` بكل سلاسة وموثوقية من النقطة التي توقف عندها.

---

## 18) وضع التصحيح (Debug Mode)
* إذا كان `"debug": true`:
  → يجب حفظ الـ `prompt` المُرسل كاملاً.
  → يجب حفظ الـ `raw response` العائد من النموذج في السجلات لمراجعته.

---

## 19) الممنوعات المطلقة (Strict Prohibitions)
* ❌ **لا تُجبر المستخدم على كتابة ملفات `JSON` يدوياً أبداً.**
* ❌ **لا تُعدل على `pipeline` مباشرة أو تعبث بآلية عمله الداخلية.**
* ❌ **لا تستخدم المتغيرات العامة (Global variables) لإدارة الحالة (State).**
* ❌ **لا تُحدّث `term_memory` أثناء التشغيل المتوازي (Parallel execution) منعاً لتعارض الكتابة (Race Conditions).**
