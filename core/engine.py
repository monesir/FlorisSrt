import time
import json
import re
from datetime import datetime
from openai import OpenAI

log_lang = "Bilingual"

def t_print(en_msg, ar_msg=None, with_time=True):
    if ar_msg is None:
        if "|" in en_msg:
            parts = en_msg.split("|")
            en_msg = parts[0].strip()
            ar_msg = parts[1].strip()
        else:
            ar_msg = en_msg
            
    time_str = f"[{datetime.now().strftime('%H:%M:%S')}] " if with_time else ""
    
    if log_lang == "English":
        print(f"{time_str}{en_msg}")
    elif log_lang == "Arabic":
        print(f"{time_str}{ar_msg}")
    else:
        print(f"{time_str}{en_msg} | {ar_msg}")

class TranslationEngine:
    """
    نواة التنفيذ والمحرك الرئيسي.
    يحتوي على طبقة (Fault-Tolerant) للتعامل مع الـ Timeouts و הـ Rate Limits بأسلوب
    Exponential Backoff، وحماية الـ Circuit Breaker.
    """
    def __init__(self, api_key, provider="openai", base_url=None, model_name=None, log_language="Bilingual", translation_style="Standard (فصحى)", force_single_line=False, timeout=120, max_retries=3, infinite_retries=False):
        global log_lang
        log_lang = log_language
        self.translation_style = translation_style
        self.force_single_line = force_single_line
        self.timeout = timeout
        self.max_retries = max_retries
        self.infinite_retries = infinite_retries
        
        if provider == "deepseek" and not base_url:
            base_url = "https://api.deepseek.com"
            
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
            
        if provider == 'openrouter':
            self.client = OpenAI(api_key=api_key, base_url=base_url or "https://openrouter.ai/api/v1")
        elif provider == 'gemini':
            self.client = OpenAI(api_key=api_key, base_url=base_url or "https://generativelanguage.googleapis.com/v1beta/openai/")
        else:
            self.client = OpenAI(**kwargs)
            
        if model_name:
            self.model = model_name
        else:
            self.model = "deepseek-chat" if provider == "deepseek" else "gpt-4o"
        
        # إعدادات Circuit Breaker
        self.consecutive_failures = 0
        self.circuit_open = False
        
    def call_llm(self, system_prompt, user_prompt):
        """الاتصال المباشر بالـ API مع سقف للـ Timeout"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            timeout=self.timeout
        )
        usage = response.usage
        return {
            "content": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens if usage else 0,
                "completion_tokens": usage.completion_tokens if usage else 0,
                "total_tokens": usage.total_tokens if usage else 0
            }
        }

    def execute_with_fault_tolerance(self, system_prompt, user_prompt):
        """تنفيذ الاتصال مع حماية הـ Exponential Backoff"""
        if self.circuit_open:
            t_print("Circuit breaker is open. Waiting 60 seconds before resuming...", "تم تفعيل حماية الضغط (Circuit Breaker). انتظار 60 ثانية قبل الاستئناف...", False)
            time.sleep(60)
            self.circuit_open = False
            self.consecutive_failures = 0
            
        attempt = 0
        max_loops = 999999 if self.infinite_retries else self.max_retries
        for attempt in range(max_loops):
            try:
                res = self.call_llm(system_prompt, user_prompt)
                self.consecutive_failures = 0 # تصفير العداد عند النجاح
                return {"status": "success", "content": res["content"], "usage": res["usage"]}
                
            except Exception as e:
                self.consecutive_failures += 1
                if self.consecutive_failures >= 5:
                    self.circuit_open = True # فتح قاطع الدائرة
                    
                wait_time = 2 ** attempt # 1, 2, 4, 8...
                t_print(f"Network/API Error Attempt {attempt+1}/{self.max_retries}: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)
                
        # الانهيار الآمن بعد نفاد المحاولات الشبكية
        return {"status": "failed", "error": "Max network retries exceeded"}

    def run_chunk_pipeline(self, chunk, project_data, agents_prompt, validator, constraint_engine):
        """تشغيل الحزمة (Chunk) عبر הـ Pipeline بالكامل (LLM -> Validator -> Constraint)"""
        # 1. بناء الـ System Prompt
        system_prompt = agents_prompt
        if project_data.get('work_context') and project_data['work_context'].get('description'):
            system_prompt += f"\n\nWORK CONTEXT:\n{json.dumps(project_data['work_context'], ensure_ascii=False)}"
            
        if self.translation_style == "Colloquial (عامية)":
            system_prompt += "\n\nCRITICAL TRANSLATION STYLE:\nYou MUST translate the dialogues into modern Colloquial Arabic (العامية)، focusing on natural, everyday conversational flow rather than rigid Standard Arabic. Use regional slang where appropriate if the character speaks casually, but keep the core meaning intact. For formal characters, you may use a slightly elevated colloquial tone."
            
        if self.force_single_line:
            system_prompt += "\n\nCRITICAL FORMATTING:\nNEVER use '\\n' or line breaks inside the translated text. Keep the translation as a single continuous line, no matter how long it is."
            
        # إضافة تذكير نهائي للحفاظ على الوسوم (Tags) وعدم نسيانها بسبب الـ Recency Bias
        system_prompt += "\n\nFINAL CRITICAL REMINDER:\n1. You MUST preserve ALL subtitle tags (e.g., {\\an8}, {\\i1}, {\\pos(...)}) exactly as they appear in the original text. Do NOT delete them!\n2. Output valid JSON only."
            
        if project_data.get('characters') and project_data['characters'].get('characters'):
            # Smart Character Matcher
            all_text = ""
            if chunk.get('context_before'):
                all_text += " ".join([s.get('text', '') for s in chunk['context_before']]) + " "
            all_text += " ".join([s.get('text', '') for s in chunk['segments']]) + " "
            if chunk.get('context_after'):
                all_text += " ".join([s.get('text', '') for s in chunk['context_after']])
            
            all_text_lower = all_text.lower()
            matched_characters = []
            
            for char in project_data['characters']['characters']:
                char_name = char.get('name', '')
                if not char_name: continue
                
                # Split character name into parts (e.g., "Klein Moretti" -> ["Klein", "Moretti", "Klein Moretti"])
                name_parts = char_name.lower().split()
                name_parts.append(char_name.lower())
                
                found = False
                for part in name_parts:
                    if len(part) > 2:
                        pattern = r'\b' + re.escape(part) + r'\b'
                        if re.search(pattern, all_text_lower):
                            found = True
                            break
                            
                if found:
                    matched_characters.append(char)
                    
            if matched_characters:
                system_prompt += f"\n\nCHARACTERS (Detected in context):\n{json.dumps({'characters': matched_characters}, ensure_ascii=False)}"
                
                has_arabic_names = any(c.get('arabic_name') for c in matched_characters)
                if has_arabic_names:
                    system_prompt += "\nCRITICAL RULE: You MUST translate character names exactly as provided in the 'arabic_name' field! Also strictly respect their 'gender'."
                else:
                    system_prompt += "\nCRITICAL RULE: You MUST strictly respect the 'gender' of these characters when translating dialogues referring to them."
        # حفظ البرومبت للـ Debug
        try:
            with open("debug_last_prompt.txt", "w", encoding="utf-8") as f:
                f.write("=== SYSTEM PROMPT ===\n" + system_prompt + "\n\n=== USER PROMPT ===\n" + json.dumps(chunk['segments'], ensure_ascii=False))
        except Exception:
            pass
            
        # 2. بناء הـ User Prompt
        user_prompt_base = json.dumps(chunk['segments'], ensure_ascii=False)
        
        parts = []
        if chunk.get('context_before'):
            parts.append(f"CONTEXT BEFORE:\n{json.dumps(chunk['context_before'], ensure_ascii=False)}")
            
        parts.append(f"TO TRANSLATE:\n{user_prompt_base}")
        
        if chunk.get('context_after'):
            parts.append(f"CONTEXT AFTER:\n{json.dumps(chunk['context_after'], ensure_ascii=False)}")
            
        user_prompt = "\n\n".join(parts)
            
        # حلقة إعادة المحاولة لتدقيق הـ JSON (Prompt Drift Prevention)
        current_user_prompt = user_prompt
        retry_type = "full"
        last_valid_segments = []
        
        max_val_loops = 999999 if self.infinite_retries else self.max_retries
        for attempt in range(max_val_loops): # محاولات كحد أقصى للـ Validator
            
            if retry_type == "full":
                t_print(f"Sending data to engine ({self.model})... please wait", f"إرسال البيانات للمحرك ({self.model})... يرجى الانتظار", False)
                result = self.execute_with_fault_tolerance(system_prompt, current_user_prompt)
            else:
                issues_text = json.dumps(validation['issues'], ensure_ascii=False)
                failed_json = json.dumps(validation['failed_segments'], ensure_ascii=False)
                partial_prompt = f"The following specific segments failed validation. Fix them and return ONLY JSON for them.\nErrors: {issues_text}\n\nTO TRANSLATE (FIX THESE ONLY):\n{failed_json}"
                t_print("Requesting partial error correction from engine... please wait", "طلب تصحيح جزئي للأخطاء من المحرك... يرجى الانتظار", False)
                result = self.execute_with_fault_tolerance(system_prompt, partial_prompt)

            if result['status'] == 'failed':
                return {"status": "degraded", "segments": chunk['segments']} # Fallback
                
            usage = result.get('usage', {})
            if usage:
                t_print(f"Tokens: {usage.get('prompt_tokens')} IN | {usage.get('completion_tokens')} OUT | {usage.get('total_tokens')} TOTAL", f"التوكنز: {usage.get('prompt_tokens')} إدخال | {usage.get('completion_tokens')} إخراج | {usage.get('total_tokens')} الإجمالي", False)
                
            t_print("Response received, verifying and parsing...", "تم استلام الرد، جاري التدقيق والتحليل...", False)
                
            output_text = result['content']
            if retry_type == "partial":
                # Merge the partial fixes with the last valid segments
                try:
                    partial_parsed = json.loads(output_text.strip().replace("```json", "").replace("```", ""))
                    if isinstance(partial_parsed, dict) and 'segments' in partial_parsed:
                        partial_parsed = partial_parsed['segments']
                    merged_segments = last_valid_segments + partial_parsed
                    output_text = json.dumps({"segments": merged_segments})
                except Exception:
                    output_text = result['content']

            # 3. التدقيق (Validation)
            t_print("Running structural checks and JSON validation...", "جاري الفحص الهيكلي وتدقيق مخرجات الـ JSON...", False)
            validation = validator.validate(chunk['segments'], output_text)
            if validation['status'] == 'ok':
                t_print("Validation passed, applying constraints (CPS/Tags)...", "اجتياز الفحص، جاري ضبط قيود الشاشة (CPS) وتنسيقات (Tags)...", False)
                # 4. تطبيق القيود (Constraints)
                final_segments = []
                for seg in validation['segments']:
                    constrained_seg, _ = constraint_engine.apply_constraints(seg)
                    final_segments.append(constrained_seg)
                for seg in final_segments:
                    if self.force_single_line and 'translated' in seg and seg['translated']:
                        seg['translated'] = seg['translated'].replace('\n', ' ')
                    
                    # استعادة الوسوم (Tags) المفقودة برمجياً لضمان عدم تلف ملف الـ ASS
                    original_text = next((s['text'] for s in chunk['segments'] if s['id'] == seg['id']), "")
                    leading_tags_match = re.match(r'^(\{\\[^}]+\})+', original_text)
                    if leading_tags_match and 'translated' in seg:
                        leading_tags = leading_tags_match.group(0)
                        if not seg['translated'].startswith(leading_tags):
                            # تنظيف أي وسم جزئي قد يكون الـ LLM أضافه بالخطأ
                            clean_trans = re.sub(r'^\{\\[^}]+\}+', '', seg['translated']).strip()
                            seg['translated'] = leading_tags + clean_trans
                            
                return {"status": "success", "segments": final_segments, "usage": usage, "terms_detected": validation.get('terms_detected', [])}
                
            else:
                retry_type = validation.get('retry_type', 'full')
                last_valid_segments = validation.get('valid_segments', [])
                if retry_type == "full":
                    current_user_prompt = validator.generate_retry_prompt(user_prompt, validation)
                t_print(f"Errors detected, processing fix ({attempt+1}/3) [Mode: {retry_type}]...", f"اكتشاف أخطاء في المخرجات، جاري المعالجة ({attempt+1}/3) [نوع التدخل: {retry_type}]...", False)
                
        # الانهيار الآمن بعد فشل الـ Validator 3 مرات
        return {"status": "degraded", "segments": chunk['segments']}
