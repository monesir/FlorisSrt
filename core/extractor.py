import json
import time
from openai import OpenAI
import os

from core.usage_tracker import UsageTracker

class ExtractorEngine:
    def __init__(self, provider, api_key, model, timeout=30, max_retries=3, infinite_retries=False, project_name="unknown"):
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        self.infinite_retries = infinite_retries
        self.project_name = project_name
        self.usage_tracker = UsageTracker()
        
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

    def extract_from_text(self, text, source_lang="English", work_context="", mode="Balanced", translate_result=True):
        """
        يستخرج الشخصيات والمصطلحات من النص ويعيدها بصيغة JSON
        """
        context_block = f"\nStory/Project Context:\n{work_context}\n" if work_context else ""
        
        # Decide what to extract based on mode
        extract_instructions = []
        schema_dict = {}
        
        # Translation instructions
        if translate_result:
            char_translation_inst = 'the exact Arabic translation used in the text as "arabic_name"' if source_lang.lower() == "arabic" else 'suggest an accurate Arabic translation/transliteration for their name as "arabic_name"'
            char_name_inst = 'their deduced English/Romaji name as "name"' if source_lang.lower() == "arabic" else 'their original name as "name"'
            term_translation_inst = 'the exact Arabic translation used in the text as "translation_suggestion"' if source_lang.lower() == "arabic" else 'Suggest a precise Arabic translation as "translation_suggestion"'
            term_name_inst = 'the deduced English/Romaji term as "term"' if source_lang.lower() == "arabic" else 'the original term as "term"'
            
            char_json = '{"name": "...", "arabic_name": "...", "description": "..."}'
            term_json = '{"term": "...", "translation_suggestion": "...", "type": "..."}'
        else:
            char_name_inst = 'their original name as "name"'
            char_translation_inst = 'Omit any arabic_name or translation field'
            term_name_inst = 'the original term as "term"'
            term_translation_inst = 'Omit any translation_suggestion field'
            
            char_json = '{"name": "...", "description": "..."}'
            term_json = '{"term": "...", "type": "..."}'

        if mode in ["Balanced", "Characters Only"]:
            extract_instructions.append(f"1. Character Names: Anyone speaking, spoken to, or mentioned in the text. Provide {char_name_inst}, {char_translation_inst}, and a brief description of their role/context.")
            schema_dict["characters"] = [json.loads(char_json)]
            
        if mode in ["Balanced", "Terms Only"]:
            extract_instructions.append(f"2. Glossary Terms: Unique locations, abilities, specific in-world slang, organizations, or objects. Provide {term_name_inst}, {term_translation_inst}, and classify its type (location/ability/organization/etc).")
            schema_dict["terms"] = [json.loads(term_json)]
            
        instructions_text = "\n".join(extract_instructions)
        schema_text = json.dumps(schema_dict, indent=2)

        system_prompt = f"""You are an expert project localizer analyzing {source_lang} subtitle text.
Your task is to extract important narrative elements to build a localization glossary.

{context_block}
Extract the following:
{instructions_text}

You MUST respond strictly in valid JSON format with the following schema:
{schema_text}
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
                    kwargs = {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        "timeout": self.timeout
                    }
                    
                    unsupported = ["reasoner", "o1", "o3", "claude"]
                    is_json_supported = True
                    
                    if self.provider in ["openrouter", "local"]:
                        is_json_supported = False
                        
                    for u in unsupported:
                        if u in self.model.lower():
                            is_json_supported = False
                            break
                            
                    if is_json_supported:
                        kwargs["response_format"] = {"type": "json_object"}
                        
                    response = self.client.chat.completions.create(**kwargs)
                    content = response.choices[0].message.content
                    usage_data = {"prompt_tokens": response.usage.prompt_tokens, "completion_tokens": response.usage.completion_tokens, "total_tokens": response.usage.total_tokens, "cached_tokens": 0} if hasattr(response, 'usage') and response.usage else None
                    if usage_data:
                        if hasattr(response.usage, 'prompt_cache_hit_tokens') and response.usage.prompt_cache_hit_tokens:
                            usage_data["cached_tokens"] = response.usage.prompt_cache_hit_tokens
                        elif hasattr(response.usage, 'prompt_tokens_details') and response.usage.prompt_tokens_details and hasattr(response.usage.prompt_tokens_details, 'cached_tokens') and response.usage.prompt_tokens_details.cached_tokens:
                            usage_data["cached_tokens"] = response.usage.prompt_tokens_details.cached_tokens
                    
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

    def process_file(self, filepath, source_lang, work_context="", progress_callback=None, log_callback=None, chunk_size=75, mode="Balanced", translate_result=True):
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
        total_tokens_used = 0
        
        for idx, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(idx, len(chunks))
                
            import re
            def strip_tags(text):
                text = text.replace('\\N', ' ').replace('\\n', ' ')
                return re.sub(r'\{.*?\}', '', text).strip()
                
            text_block = "\n".join([strip_tags(seg['text']) for seg in chunk])
            if log_callback: log_callback(f"Analyzing chunk {idx+1}/{len(chunks)}...")
            result = self.extract_from_text(text_block, source_lang, work_context, mode, translate_result)
            
            if "error" in result:
                if log_callback: log_callback(f"Error in chunk {idx+1}: {result['error']}")
                
            if "usage" in result and result["usage"]:
                u = result["usage"]
                p_tok = u.get('prompt_tokens', 0)
                c_tok = u.get('completion_tokens', 0)
                total_tokens_used += u.get('total_tokens', 0)
                if log_callback: 
                    cache_str = f" (Cached: {u.get('cached_tokens', 0)})" if u.get('cached_tokens', 0) > 0 else ""
                    log_callback(f"Tokens: {p_tok} IN{cache_str} | {c_tok} OUT | {u.get('total_tokens', 0)} TOTAL")
                
                self.usage_tracker.record_usage(
                    project=self.project_name,
                    episode=os.path.basename(filepath),
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    estimated=False
                )
            else:
                # Fallback estimation
                p_tok = len(text_block) // 4
                c_tok = 50 # minimal completion for extraction
                total_tokens_used += (p_tok + c_tok)
                self.usage_tracker.record_usage(
                    project=self.project_name,
                    episode=os.path.basename(filepath),
                    provider=self.provider,
                    model=self.model,
                    prompt_tokens=p_tok,
                    completion_tokens=c_tok,
                    estimated=True
                )
            
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
                    
            # Flush tokens safely after each chunk
            self.usage_tracker.flush()
            
        return {
            "characters": list(all_chars.values()),
            "terms": list(all_terms.values()),
            "total_tokens": total_tokens_used
        }
