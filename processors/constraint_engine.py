class ConstraintEngine:
    """
    محرك القيود لتنظيم طول السطر وحساب הـ CPS (Characters Per Second)
    وتقسيم الجمل الطويلة لغوياً للحفاظ على قابلية القراءة.
    """
    def __init__(self, max_length=42, max_lines=2):
        self.max_length = max_length
        self.max_lines = max_lines

    def calculate_duration(self, start, end):
        """حساب المدة الزمنية بالثواني"""
        def time_to_seconds(t):
            t = t.replace(',', '.')
            parts = t.split(':')
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            return 0
        return time_to_seconds(end) - time_to_seconds(start)

    def calculate_cps(self, text, duration):
        if duration <= 0:
            return 0
        return len(text) / duration

    def smart_split(self, text):
        """تقسيم النص الذكي بناءً على الفواصل المنطقية"""
        split_chars = ['،', '.', '؟', '!', ' و', ' لكن', ' ثم']
        best_split_idx = -1
        mid = len(text) // 2
        min_dist = len(text)
        
        for char in split_chars:
            idx = text.find(char)
            while idx != -1:
                dist = abs(idx - mid)
                if dist < min_dist:
                    min_dist = dist
                    best_split_idx = idx + (len(char) if not char.startswith(' ') else 0)
                idx = text.find(char, idx + 1)
                
        if best_split_idx != -1 and min_dist < (len(text) // 3):
            return text[:best_split_idx].strip() + "\n" + text[best_split_idx:].strip()
            
        words = text.split(' ')
        if len(words) > 1:
            mid_word = len(words) // 2
            return ' '.join(words[:mid_word]) + '\n' + ' '.join(words[mid_word:])
            
        return text

    def programmatic_compress(self, text):
        """ضغط النص برمجياً لإزالة الحشو البصري"""
        import re
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'^(آه|أوه|امم|همم|حسنًا|حسنا)[،,]\s*', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def apply_constraints(self, segment):
        """تطبيق القيود على السطر وإرجاع حالة الضغط للـ Logs"""
        text = segment['translated']
        duration = self.calculate_duration(segment['start'], segment['end'])
        cps_before = self.calculate_cps(text, duration)
        
        compressed = False
        lines_split = 1
        
        # إذا הـ CPS مرتفع جداً، نقوم بضغط النص برمجياً أولاً
        if cps_before > 20:
            original_len = len(text)
            text = self.programmatic_compress(text)
            if len(text) < original_len:
                compressed = True
                
        # إذا كان السطر طويلاً أو הـ CPS ما زال مرتفعاً، نفرض التقسيم
        if self.calculate_cps(text, duration) > 17 or len(text) > self.max_length:
            if '\n' not in text:
                text = self.smart_split(text)
                lines_split = 2
                
        segment['translated'] = text
        
        constraint_log = {
            "seg_id": segment['id'],
            "cps_before": round(cps_before, 2),
            "cps_after": round(self.calculate_cps(text, duration), 2),
            "compressed": compressed,
            "lines_split": lines_split
        }
        
        return segment, constraint_log
