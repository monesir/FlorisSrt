import json

class Chunker:
    """
    مسؤول عن تقسيم الأسطر إلى مصفوفات ثابتة (20 سطر) وبناء سياقات الربط (القبلية والبعدية).
    """
    def __init__(self, chunk_size=20):
        self.chunk_size = chunk_size

    def create_chunks(self, segments):
        """تقسيم الأسطر الخام المُطبعة إلى شنكات"""
        chunks = []
        for i in range(0, len(segments), self.chunk_size):
            chunks.append(segments[i:i + self.chunk_size])
        return chunks

    def build_context(self, current_chunk, prev_translated_chunk=None, next_raw_chunk=None):
        """
        بناء السياق الخارجي للشنك (Context Before / After)
        prev_translated_chunk: الشنك السابق بعد اكتمال ترجمته (لأخذ آخر 5 أسطر بالعربية).
        next_raw_chunk: الشنك التالي الخام (لأخذ أول سطرين بالإنجليزية).
        """
        context_before = []
        context_after = []

        if prev_translated_chunk:
            # آخر 5 أسطر مترجمة من الشنك السابق
            last_5 = prev_translated_chunk[-5:]
            context_before = [{"id": seg["id"], "text": seg.get("translated", seg["text_clean"])} for seg in last_5]

        if next_raw_chunk:
            # أول سطرين خام من الشنك اللاحق
            first_2 = next_raw_chunk[:2]
            context_after = [{"id": seg["id"], "text": seg["text_clean"]} for seg in first_2]

        return {
            "context_before": context_before,
            "context_after": context_after,
            "segments": current_chunk
        }
