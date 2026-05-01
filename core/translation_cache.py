import os
import json

class TranslationCache:
    """
    نظام ذاكرة الترجمة (Translation Cache Memory)
    يتذكر الأسطر المترجمة سابقاً ويتأكد من تطابق السياق (السطر السابق أو اللاحق)
    لمنع ترجمة كلمات فردية بشكل خاطئ بسبب تغير السياق.
    """
    def __init__(self, project_dir):
        self.cache_file = os.path.join(project_dir, 'translation_cache.json')
        self.cache = self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache(self):
        temp_file = self.cache_file + ".tmp"
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)
        os.replace(temp_file, self.cache_file)

    def extract_cached_segments(self, current_chunk_segments, all_segments):
        """
        يفحص الشنك الحالي ويستخرج الأسطر التي تُرجمت مسبقاً بنفس السياق.
        يرجع:
        - untranslated: الأسطر التي تحتاج ترجمة من الذكاء الاصطناعي
        - cached_translations: الترجمات الجاهزة (مفهرسة بـ ID السطر)
        """
        untranslated = []
        cached_translations = {}

        # إنشاء فهرس سريع لكل الأسطر للوصول للسياق
        segments_by_id = {seg['id']: seg for seg in all_segments}

        for seg in current_chunk_segments:
            text = seg.get('text_clean', '').strip()
            if not text or text not in self.cache:
                untranslated.append(seg)
                continue

            # استخراج السياق الفعلي لهذا السطر في الملف الحالي
            current_id = seg['id']
            prev_text = segments_by_id[current_id - 1].get('text_clean', '').strip() if (current_id - 1) in segments_by_id else ""
            next_text = segments_by_id[current_id + 1].get('text_clean', '').strip() if (current_id + 1) in segments_by_id else ""

            matched = False
            for entry in self.cache[text]:
                entry_prev = entry.get('prev', '')
                entry_next = entry.get('next', '')

                # يطابق إذا كان السياق السابق مطابقاً (أو) السياق اللاحق مطابقاً
                if (prev_text and prev_text == entry_prev) or (next_text and next_text == entry_next):
                    cached_translations[current_id] = entry['translation']
                    matched = True
                    break

            if not matched:
                untranslated.append(seg)

        return untranslated, cached_translations

    def add_translations(self, translated_segments, all_segments):
        """
        يضيف الترجمات الجديدة إلى الذاكرة ليتم استخدامها لاحقاً.
        """
        segments_by_id = {seg['id']: seg for seg in all_segments}
        updated = False

        for seg in translated_segments:
            text = seg.get('text_clean', '').strip()
            translation = seg.get('translated', '').strip()
            
            if not text or not translation:
                continue

            current_id = seg['id']
            prev_text = segments_by_id[current_id - 1].get('text_clean', '').strip() if (current_id - 1) in segments_by_id else ""
            next_text = segments_by_id[current_id + 1].get('text_clean', '').strip() if (current_id + 1) in segments_by_id else ""

            # تجاهل الأسطر القصيرة جداً التي لا تملك سياقاً (حماية إضافية)
            if not prev_text and not next_text:
                continue

            if text not in self.cache:
                self.cache[text] = []

            # التأكد من عدم التكرار
            exists = False
            for entry in self.cache[text]:
                if entry.get('translation') == translation and entry.get('prev') == prev_text and entry.get('next') == next_text:
                    exists = True
                    break
            
            if not exists:
                self.cache[text].append({
                    "translation": translation,
                    "prev": prev_text,
                    "next": next_text
                })
                updated = True

        if updated:
            self._save_cache()
