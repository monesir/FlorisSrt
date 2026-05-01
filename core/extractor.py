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

    def extract_from_text(self, text, source_lang="English"):
        """
        يستخرج الشخصيات والمصطلحات من النص ويعيدها بصيغة JSON
        """
        system_prompt = f"""You are an expert anime localizer.
Your task is to analyze the following {source_lang} subtitle text and extract:
1. Character Names: Anyone speaking, spoken to, or mentioned.
2. Glossary Terms: Unique locations, abilities, slang, organizations, or specific terms.

You MUST respond strictly in valid JSON format with the following schema:
{{
  "characters": [
    {{"name": "...", "description": "Brief context about the character"}}
  ],
  "terms": [
    {{"term": "...", "translation_suggestion": "Suggested Arabic translation", "type": "location/ability/etc"}}
  ]
}}
If none are found, return empty arrays.
"""
        
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
                    
                import re
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    content = json_match.group(0)
                    
                data = json.loads(content)
                
                return {
                    "characters": data.get("characters") or [],
                    "terms": data.get("terms") or []
                }
            except Exception as e:
                err_msg = str(e)
                if attempt >= max_loops:
                    return {"characters": [], "terms": [], "error": err_msg}
                time.sleep(3) # Wait before retry
                
        return {"characters": [], "terms": []}

    def process_file(self, filepath, source_lang, progress_callback=None, log_callback=None):
        """
        يقرأ الملف، يقسمه لكتل كبيرة (200 سطر)، ويستخرج منها البيانات.
        """
        from parsers.subtitle_parser import SubtitleParser
        parser = SubtitleParser()
        try:
            segments = parser.parse(filepath)
            if log_callback: log_callback(f"Successfully loaded {len(segments)} segments from {os.path.basename(filepath)}")
        except Exception as e:
            if log_callback: log_callback(f"Failed to parse {filepath}: {e}")
            return {"characters": [], "terms": []}
            
        chunk_size = 150 # Reduced from 200 to avoid token limits and truncated JSON
        chunks = [segments[i:i + chunk_size] for i in range(0, len(segments), chunk_size)]
        
        if log_callback: log_callback(f"Split file into {len(chunks)} chunks.")
        
        all_chars = {}
        all_terms = {}
        
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx, len(chunks))
                
            text_block = "\n".join([seg['text'] for seg in chunk])
            if log_callback: log_callback(f"Analyzing chunk {idx+1}/{len(chunks)}...")
            result = self.extract_from_text(text_block, source_lang)
            
            if "error" in result:
                if log_callback: log_callback(f"Error in chunk {idx+1}: {result['error']}")
            
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
