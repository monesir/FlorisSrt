import json
import time
from openai import OpenAI
import os

class ExtractorEngine:
    def __init__(self, provider, api_key, model, timeout=30, max_retries=3, infinite_retries=False):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.infinite_retries = infinite_retries
        
        # إعداد الـ Client بناءً على المزود
        if provider == "openai":
            self.client = OpenAI(api_key=api_key)
        elif provider == "anthropic":
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
        elif provider == "deepseek":
            self.client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        elif provider == "openrouter":
            self.client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        elif provider == "gemini":
            self.client = OpenAI(api_key=api_key, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
        elif provider == "local":
            self.client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        else:
            self.client = OpenAI(api_key=api_key)

    def extract_from_text(self, text, source_lang="English", work_context=""):
        """
        يستخرج الشخصيات والمصطلحات من النص ويعيدها بصيغة JSON
        """
        context_block = f"\nStory/Project Context:\n{work_context}\n" if work_context else ""
        
        if source_lang.lower() == "arabic":
            system_prompt = f"""You are an expert anime localizer analyzing Arabic subtitle text.
Your task is to extract important narrative elements to build a localization glossary.

{context_block}
Extract the following:
1. Character Names: Anyone speaking, spoken to, or mentioned in the text. Provide their Arabic name and a brief description of their role/context.
2. Glossary Terms: Unique locations, abilities, specific in-world slang, organizations, or objects. Suggest a precise Arabic translation (or keep it as is if it's a proper noun) and classify its type (location/ability/organization/etc).

You MUST respond strictly in valid JSON format with the following schema:
{{
  "characters": [
    {{"name": "...", "description": "..."}}
  ],
  "terms": [
    {{"term": "...", "translation_suggestion": "...", "type": "..."}}
  ]
}}
If none are found, return empty arrays."""
        else:
            system_prompt = f"""You are an expert anime localizer analyzing {source_lang} subtitle text.
Your task is to extract important narrative elements to build a localization glossary.

{context_block}
Extract the following:
1. Character Names: Anyone speaking, spoken to, or mentioned in the text. Provide their original name and a brief description of their role/context.
2. Glossary Terms: Unique locations, abilities, specific in-world slang, organizations, or objects. Suggest a precise Arabic translation and classify its type (location/ability/organization/etc).

You MUST respond strictly in valid JSON format with the following schema:
{{
  "characters": [
    {{"name": "...", "description": "..."}}
  ],
  "terms": [
    {{"term": "...", "translation_suggestion": "...", "type": "..."}}
  ]
}}
If none are found, return empty arrays."""
        
        user_prompt = f"Subtitle Text:\n{text}"
        
        max_loops = 999999 if self.infinite_retries else self.max_retries
        attempt = 0
        
        while attempt < max_loops:
            attempt += 1
            try:
                if self.provider == "anthropic":
                    response = self.client.messages.create(
                        model=self.model,
                        max_tokens=2048,
                        system=system_prompt,
                        messages=[{"role": "user", "content": user_prompt}]
                    )
                    content = response.content[0].text
                    usage_data = {"prompt_tokens": response.usage.input_tokens, "completion_tokens": response.usage.output_tokens, "total_tokens": response.usage.input_tokens + response.usage.output_tokens} if hasattr(response, 'usage') else None
                else:
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        response_format={"type": "json_object"},
                        timeout=self.timeout
                    )
                    content = response.choices[0].message.content
                    usage_data = {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "total_tokens": response.usage.total_tokens} if hasattr(response, 'usage') and response.usage else None
                    
                import re
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    content = json_match.group(0)
                    
                data = json.loads(content)
                
                return {
                    "characters": data.get("characters") or [],
                    "terms": data.get("terms") or [],
                    "usage": usage_data
                }
            except Exception as e:
                err_msg = str(e)
                if attempt >= max_loops:
                    return {"characters": [], "terms": [], "error": err_msg}
                time.sleep(3) # Wait before retry
                
        return {"characters": [], "terms": []}

    def process_file(self, filepath, source_lang, work_context="", progress_callback=None, log_callback=None, chunk_size=75):
        """
        يقرأ الملف، يقسمه لكتل، ويستخرج منها البيانات.
        """
        from parsers.subtitle_parser import SubtitleParser
        parser = SubtitleParser()
        try:
            segments = parser.parse(filepath)
            if log_callback: log_callback(f"Successfully loaded {len(segments)} segments from {os.path.basename(filepath)}")
        except Exception as e:
            if log_callback: log_callback(f"Failed to parse {filepath}: {e}")
            return {"characters": [], "terms": []}
            
        chunks = [segments[i:i + chunk_size] for i in range(0, len(segments), chunk_size)]
        
        if log_callback: log_callback(f"Split file into {len(chunks)} chunks.")
        
        all_chars = {}
        all_terms = {}
        
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx, len(chunks))
                
            import re
            def strip_tags(text):
                text = text.replace('\\N', ' ').replace('\\n', ' ')
                return re.sub(r'\{.*?\}', '', text).strip()
                
            text_block = "\n".join([strip_tags(seg['text']) for seg in chunk])
            if log_callback: log_callback(f"Analyzing chunk {idx+1}/{len(chunks)}...")
            result = self.extract_from_text(text_block, source_lang, work_context)
            
            if "error" in result:
                if log_callback: log_callback(f"Error in chunk {idx+1}: {result['error']}")
                
            if "usage" in result and result["usage"] and log_callback:
                u = result["usage"]
                log_callback(f"Tokens: {u.get('prompt_tokens')} IN | {u.get('completion_tokens')} OUT | {u.get('total_tokens')} TOTAL")
            
            # Merge Results
            chars_list = result.get('characters') or []
            for char in chars_list:
                name = char.get('name', '').strip()
                if name and name not in all_chars:
                    all_chars[name] = char
                    
            terms_list = result.get('terms') or []
            for term in terms_list:
                t_name = term.get('term', '').strip()
                if t_name and t_name not in all_terms:
                    all_terms[t_name] = term
                    
        return {
            "characters": list(all_chars.values()),
            "terms": list(all_terms.values())
        }
