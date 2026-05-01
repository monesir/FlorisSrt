import re

class Normalizer:
    """
    طبقة التنظيف (Normalizer) المسؤولة عن توحيد النص وإزالة الفوضى (Spaces, Quotes)
    مع الحفاظ التام على הـ Tags وبنية المعنى.
    """
    def __init__(self):
        pass

    def normalize_text(self, text, format='srt'):
        cleaned = text.strip()
        
        if format == 'srt':
            # دمج الأسطر المتعددة في سطر واحد لتسهيل الترجمة كسياق متصل
            # مع إبقاء الـ tags مثل <i> كما هي
            cleaned = re.sub(r'\s+', ' ', cleaned)
        elif format == 'ass':
            # استبدال الـ \N (سطر جديد في ASS) بمسافة
            # مع الاحتفاظ بكافة الـ Inline tags {\i1} وغيرها
            cleaned = cleaned.replace('\\N', ' ').replace('\\n', ' ')
            cleaned = re.sub(r'\s+', ' ', cleaned)
            
        # توحيد علامات الاقتباس لتجنب مشاكل הـ JSON أو הـ Tokenizer
        cleaned = cleaned.replace('“', '"').replace('”', '"')
        cleaned = cleaned.replace('‘', "'").replace('’', "'")
        
        # تصحيح بعض حالات الـ Mojibake الشائعة
        cleaned = cleaned.replace('â€™', "'")
        
        return cleaned.strip()

    def normalize_segments(self, segments, format='srt'):
        """تمرير مصفوفة الـ Segments بالكامل وإضافة حقل `text_clean` لكل عنصر"""
        normalized = []
        for seg in segments:
            # نأخذ نسخة للحفاظ على הـ dictionary الأصلي
            seg_copy = dict(seg)
            seg_copy['text_clean'] = self.normalize_text(seg['text'], format)
            normalized.append(seg_copy)
            
        return normalized
