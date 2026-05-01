class GlossaryMatcher:
    """
    نظام القاموس الذكي، يحلل الشنك والسياقات المجاورة
    للعثور على المصطلحات المراد حقنها، بدلاً من إرسال القاموس بأكمله لتوفير הـ Tokens ومنع الهلوسة.
    """
    def __init__(self, glossary_data):
        self.glossary = glossary_data

    def extract_terms_for_chunk(self, segments, context_before, context_after):
        """
        يبحث عن المصطلحات في النص الإنجليزي الأصلي المُنظف للشنك، والسياق اللاحق.
        """
        # نجمع النص المُنظف من الشنك
        combined_text = " ".join([seg['text_clean'] for seg in segments]).lower()
        
        # ندمج معه السياق اللاحق (لأنه أصلي إنجليزي، على عكس السابق الذي يكون مترجماً)
        if context_after:
            combined_text += " " + " ".join([seg['text'] for seg in context_after]).lower()
            
        import re
        matched_terms = {}
        for key, value in self.glossary.items():
            # البحث عن הـ Variants المختلفة للمصطلح (مثل master, the master, my master)
            variants = value.get("variants", [key.lower()])
            for variant in variants:
                pattern = r'\b' + re.escape(variant.lower()) + r'\b'
                if re.search(pattern, combined_text):
                    matched_terms[key] = value
                    break # وجدنا الكلمة، ننتقل للمصطلح التالي
                    
        return matched_terms
