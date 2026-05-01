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

    def wrap_after_limit(self, text, limit=40):
        """قص النص عند أقرب كلمة (مسافة) بعد الحد المسموح"""
        if len(text) <= limit:
            return text
            
        lines = []
        current_text = text
        while len(current_text) > limit:
            split_idx = current_text.find(' ', limit)
            if split_idx == -1:
                break
            
            lines.append(current_text[:split_idx].strip())
            current_text = current_text[split_idx:].strip()
            
        if current_text:
            lines.append(current_text)
            
        return '\n'.join(lines)

    def programmatic_compress(self, text):
        """ضغط النص برمجياً لإزالة الحشو البصري"""
        import re
        text = re.sub(r'\.{2,}', '.', text)
        text = re.sub(r'^(آه|أوه|امم|همم|حسنًا|حسنا)[،,]\s*', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def apply_constraints(self, segment):
        """تطبيق القيود على السطر وإرجاع حالة الضغط للـ Logs"""
        import re
        text = segment['translated']
        duration = self.calculate_duration(segment['start'], segment['end'])
        
        # استخراج النص المرئي فقط لحساب الطول والـ CPS بدون وسوم الـ ASS
        visible_text = re.sub(r'\{.*?\}', '', text)
        visible_len = len(visible_text)
        cps_before = self.calculate_cps(visible_text, duration)
        
        compressed = False
        lines_split = 1
        
        # إذا הـ CPS مرتفع جداً، نقوم بضغط النص برمجياً أولاً
        if cps_before > 20:
            text = self.programmatic_compress(text)
            new_visible_text = re.sub(r'\{.*?\}', '', text)
            if len(new_visible_text) < visible_len:
                compressed = True
                visible_text = new_visible_text
                
        # إذا كان السطر طويلاً، نفرض التقسيم بعد 40 حرف
        if len(visible_text) > self.max_length:
            if '\n' not in text:
                text = self.wrap_after_limit(text, limit=40)
                lines_split = len(text.split('\n'))
                
        segment['translated'] = text
        
        constraint_log = {
            "seg_id": segment['id'],
            "cps_before": round(cps_before, 2),
            "cps_after": round(self.calculate_cps(text, duration), 2),
            "compressed": compressed,
            "lines_split": lines_split
        }
        
        return segment, constraint_log
