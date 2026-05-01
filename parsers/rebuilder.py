import re

class Rebuilder:
    """
    يقوم ببناء ملف SRT أو تعديل ملف ASS باستخدام الشنكات المترجمة المحفوظة.
    """
    def __init__(self):
        pass

    def build_srt(self, segments, output_filepath):
        """تجميع ملف SRT جديد بالترتيب الزمني الصحيح"""
        sorted_segments = sorted(segments, key=lambda x: x['id'])
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            for seg in sorted_segments:
                f.write(f"{seg['id']}\n")
                f.write(f"{seg['start']} --> {seg['end']}\n")
                # Fallback to original text if translation is missing
                text = seg.get('translated', seg.get('text', ''))
                text = self._apply_rtl_fixes(text)
                f.write(f"{text}\n\n")

    def build_ass(self, segments, original_filepath, output_filepath):
        """تجميع ملف ASS بتعديل أسطر Dialogue فقط والحفاظ على ההيدر والأنماط"""
        sorted_segments = sorted(segments, key=lambda x: x['id'])
        seg_dict = {seg['id']: seg.get('translated', seg.get('text', '')) for seg in sorted_segments}
        
        try:
            with open(original_filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            raise IOError(f"Cannot read original ASS file for rebuilding: {e}")
            
        idx = 1
        in_events = False
        
        with open(output_filepath, 'w', encoding='utf-8') as f:
            for line in lines:
                if line.strip() == '[Events]':
                    in_events = True
                    f.write(line)
                    continue
                    
                if in_events and line.startswith('Dialogue:'):
                    parts = line.split(',', 9)
                    if len(parts) == 10:
                        if idx in seg_dict:
                            # تحويل הـ newline العادي إلى \N ليتوافق مع ASS
                            translated_text = seg_dict[idx].replace('\n', '\\N')
                            translated_text = self._apply_rtl_fixes(translated_text)
                            parts[9] = translated_text + '\n'
                            f.write(','.join(parts))
                        else:
                            f.write(line)
                        idx += 1
                        continue
                f.write(line)

    def _apply_rtl_fixes(self, text):
        """
        إصلاح مشاكل اتجاه النص (RTL) وعلامات الترقيم التي تنعكس في مشغلات الفيديو.
        """
        if not text:
            return text
            
        # 1. إزالة الأقواس الخاطئة حول أمر السطر الجديد التي ينتجها الذكاء الاصطناعي أحياناً
        text = text.replace('{\\N\u202b}', '\\N\u202b').replace('{\\N}', '\\N')
        
        # 2. حقن علامة (Right-to-Left Mark \u200f) بعد علامات الترقيم 
        # التي تسبق أكواد التنسيق أو السطر الجديد أو نهاية النص
        text = re.sub(r'([.?!,:؛،\"»]+)(?=\{|\\N|\n|$)', r'\1' + '\u200f', text)
        
        return text
