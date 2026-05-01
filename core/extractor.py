import json
import time
from openai import OpenAI
import os

class ExtractorEngine:
    def __init__(self, provider, api_key, model, timeout=30):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        
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
        
        try:
            if self.provider == "anthropic":
                # Anthropic doesn't natively support response_format={"type": "json_object"} in standard messages API yet without tools, 
                # but we can instruct it strongly.
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
                
            # Extract JSON from markdown or conversational text
            import re
            json_match = re.search(r"\{[\s\S]*\}", content)
            if json_match:
                content = json_match.group(0)
                
            data = json.loads(content)
            
            # Ensure lists are returned even if LLM gives null
            return {
                "characters": data.get("characters") or [],
                "terms": data.get("terms") or []
            }
        except Exception as e:
            print(f"Extraction Error: {e}")
            return {"characters": [], "terms": []}

    def process_file(self, filepath, source_lang, progress_callback=None):
        """
        يقرأ الملف، يقسمه لكتل كبيرة (200 سطر)، ويستخرج منها البيانات.
        """
        from parsers.subtitle_parser import SubtitleParser
        parser = SubtitleParser()
        try:
            segments = parser.parse(filepath)
        except Exception as e:
            print(f"Failed to parse {filepath}: {e}")
            return {"characters": [], "terms": []}
            
        chunk_size = 150 # Reduced from 200 to avoid token limits and truncated JSON
        chunks = [segments[i:i + chunk_size] for i in range(0, len(segments), chunk_size)]
        
        all_chars = {}
        all_terms = {}
        
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx, len(chunks))
                
            text_block = "\n".join([seg['text'] for seg in chunk])
            result = self.extract_from_text(text_block, source_lang)
            
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
