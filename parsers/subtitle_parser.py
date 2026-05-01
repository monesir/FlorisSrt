import re

class SubtitleParser:
    """
    محلل الترجمة (Parser) المسؤول عن تحويل ملفات SRT و ASS إلى مصفوفة JSON موحدة.
    لا يقوم بتعديل النص أو تنظيفه (هذه مهمة הـ Normalizer).
    """
    def __init__(self):
        pass

    def parse_srt(self, filepath):
        """تحليل ملف SRT واستخراج الـ Segments"""
        segments = []
        try:
            with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
                content = f.read()
        except Exception as e:
            raise IOError(f"Failed to read file {filepath}: {e}")

        # تقسيم الملف إلى Blocks بناءً على الأسطر الفارغة
        blocks = re.split(r'\n\s*\n', content.strip())
        
        for block in blocks:
            lines = block.strip().split('\n')
            if len(lines) >= 3:
                try:
                    idx = int(lines[0].strip())
                    timecode = lines[1].strip()
                    
                    if ' --> ' in timecode:
                        start, end = timecode.split(' --> ')
                        text = '\n'.join(lines[2:])
                        segments.append({
                            "id": idx,
                            "start": start.strip(),
                            "end": end.strip(),
                            "text": text.strip()
                        })
                except ValueError:
                    # تجاوز الـ Blocks المعطوبة التي لا تبدأ برقم أو لا تمتلك وقت صالح
                    pass
                    
        return segments

    def parse_ass(self, filepath):
        """تحليل ملف ASS واستخراج الـ Segments مع الحفاظ على البيانات الوصفية"""
        segments = []
        try:
            with open(filepath, 'r', encoding='utf-8-sig', errors='replace') as f:
                lines = f.readlines()
        except Exception as e:
            raise IOError(f"Failed to read file {filepath}: {e}")

        idx = 1
        in_events = False
        
        for line in lines:
            line = line.strip()
            if line == '[Events]':
                in_events = True
                continue
            
            if in_events and line.startswith('Dialogue:'):
                # بنية السطر: Dialogue: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
                # نقوم بالفصل بناءً على أول 9 فواصل فقط لضمان عدم فصل النص نفسه
                parts = line.split(',', 9)
                if len(parts) == 10:
                    start = parts[1].strip()
                    end = parts[2].strip()
                    text = parts[9].strip()
                    
                    segments.append({
                        "id": idx,
                        "start": start,
                        "end": end,
                        "text": text,
                        "raw_line": line  # حفظ السطر كاملاً مهم جداً للـ Rebuilder
                    })
                    idx += 1
                    
        return segments

    def parse(self, filepath):
        """التعرف التلقائي على الصيغة واستخراج البيانات"""
        if filepath.lower().endswith('.ass'):
            return self.parse_ass(filepath)
        elif filepath.lower().endswith('.srt'):
            return self.parse_srt(filepath)
        else:
            raise ValueError(f"Unsupported subtitle format for file: {filepath}")
