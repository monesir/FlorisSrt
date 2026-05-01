import json
import re

class Validator:
    """
    المدقق الداخلي للتأكد من مخرجات النموذج،
    يمنع المخرجات الناقصة، الفارغة، أو ذات הה IDs الخاطئة.
    """
    def __init__(self):
        pass

    def validate(self, input_segments, output_text):
        issues = []
        try:
            # 1. تنظيف مخرجات הـ JSON من الـ Markdown
            output_text = output_text.strip()
            if output_text.startswith("```json"):
                output_text = output_text[7:]
            if output_text.startswith("```"):
                output_text = output_text[3:]
            if output_text.endswith("```"):
                output_text = output_text[:-3]
            
            output_text = output_text.strip()
            parsed_output = json.loads(output_text)
            terms_detected = []
            if isinstance(parsed_output, dict):
                if 'terms_detected' in parsed_output:
                    terms_detected = parsed_output['terms_detected']
                if 'segments' in parsed_output:
                    parsed_output = parsed_output['segments']
                else:
                    raise ValueError("Expected a JSON object with a 'segments' array.")
            elif not isinstance(parsed_output, list):
                raise ValueError("Expected a JSON object with a 'segments' array.")
        except Exception as e:
            return {"status": "retry", "segments": [], "terms_detected": [], "issues": [{"type": "parse_error", "message": str(e)}]}

        # 2. التأكد من الـ IDs (عدم وجود نقص أو زيادة)
        input_ids = {seg['id'] for seg in input_segments}
        output_ids = {seg.get('id') for seg in parsed_output if seg.get('id') is not None}

        missing_ids = input_ids - output_ids
        extra_ids = output_ids - input_ids

        if missing_ids or extra_ids:
            return {
                "status": "retry", 
                "retry_type": "full",
                "valid_segments": [],
                "failed_segments": input_segments,
                "terms_detected": [],
                "issues": [{"type": "id_mismatch", "missing": list(missing_ids), "extra": list(extra_ids)}]
            }

        valid_segments = []
        failed_segments = []
        final_segments = []
        issues = []
        
        output_dict = {seg.get('id'): seg.get('translated', '') for seg in parsed_output if seg.get('id') is not None}

        for in_seg in input_segments:
            seg_id = in_seg['id']
            translated_text = output_dict[seg_id]
            
            if not translated_text:
                issues.append({"type": "empty_translation", "id": seg_id})
                failed_segments.append(in_seg)
                continue
                
            # التحقق من الوسوم (Tags) والتنسيقات (Rule E)
            original_tags = re.findall(r'<[^>]+>|{[^}]+}', in_seg['text'])
            missing_tags = []
            for tag in original_tags:
                if tag not in translated_text:
                    missing_tags.append(tag)
                    
            if missing_tags:
                issues.append({"type": "missing_tags", "id": seg_id, "tags": missing_tags})
                failed_segments.append(in_seg)
                continue
                
            final_seg = dict(in_seg)
            final_seg['translated'] = translated_text
            valid_segments.append({"id": seg_id, "translated": translated_text})
            final_segments.append(final_seg)

        if issues:
            return {"status": "retry", "retry_type": "partial", "segments": [], "valid_segments": valid_segments, "failed_segments": failed_segments, "terms_detected": terms_detected, "issues": issues}
            
        return {"status": "ok", "segments": final_segments, "terms_detected": terms_detected, "issues": []}

    def generate_retry_prompt(self, original_prompt, validation_result):
        """توليد Prompt يحتوي على الخطأ لمنع الـ Prompt Drift"""
        issues_text = ", ".join([str(issue) for issue in validation_result['issues']])
        feedback = f"\n\nCRITICAL ERROR IN PREVIOUS RESPONSE:\nYour previous response was rejected by the validator due to: {issues_text}\nFix the output strictly according to the format rules. Make sure ALL IDs match exactly and NO translation is empty."
        return original_prompt + feedback
