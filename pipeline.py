import argparse
import os
import json
from datetime import datetime
from core.project_resolution import ProjectResolution
from core.state_manager import StateManager
from core.chunker import Chunker
from core.engine import TranslationEngine
from core.translation_cache import TranslationCache
from parsers.subtitle_parser import SubtitleParser
from parsers.normalizer import Normalizer
from parsers.rebuilder import Rebuilder
from processors.validator import Validator
from processors.constraint_engine import ConstraintEngine
from processors.glossary_matcher import GlossaryMatcher

log_lang = "Bilingual"

def t_print(en_msg, ar_msg=None, with_time=True):
    if ar_msg is None:
        if "|" in en_msg:
            parts = en_msg.split("|")
            en_msg = parts[0].strip()
            ar_msg = parts[1].strip()
        else:
            ar_msg = en_msg
            
    time_str = f"[{datetime.now().strftime('%H:%M:%S')}] " if with_time else ""
    
    if log_lang == "English":
        print(f"{time_str}{en_msg}")
    elif log_lang == "Arabic":
        print(f"{time_str}{ar_msg}")
    else:
        print(f"{time_str}{en_msg} | {ar_msg}")

def main():
    parser = argparse.ArgumentParser(description="Anime Translator Pipeline (Project-Aware)")
    parser.add_argument("--input", help="مسار الملف الخام (SRT/ASS)")
    parser.add_argument("--resume", action="store_true", help="استئناف الترجمة من آخر نقطة حفظ")
    parser.add_argument("--provider", default="openai", help="مزود הـ API (openai أو deepseek)")
    parser.add_argument("--base-url", help="تعديل הـ Base URL للـ API")
    parser.add_argument("--api-key", help="مفتاح الـ API", required=True)
    parser.add_argument("--model-name", help="اسم الموديل المطلوب (مثلا gpt-4o)")
    parser.add_argument("--max-chunks", type=int, help="الحد الأقصى للشنكات (للتجارب)", default=None)
    parser.add_argument("--project-name", help="اسم المشروع الإجباري (لتجاوز الاستخراج من اسم الملف)", default=None)
    parser.add_argument("--log-language", help="Log Language", default="Bilingual")
    parser.add_argument("--translation-style", help="Translation Style (Standard/Colloquial)", default="Standard (فصحى)")
    parser.add_argument("--force-single-line", action="store_true", help="Force single line output")
    parser.add_argument("--timeout", type=int, default=120, help="API Timeout in seconds")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retries for API and Validation")
    parser.add_argument("--infinite-retries", action="store_true", help="Never skip chunk on failure")
    
    args = parser.parse_args()
    
    global log_lang
    log_lang = args.log_language

    if not args.input:
        t_print("Input required for new projects.", "يجب تحديد --input للمشاريع الجديدة.")
        return
        
    t_print("Starting FlorisSrt...", "بدء نظام FlorisSrt...")

    # Initialize components
    resolver = ProjectResolution()
    sub_parser = SubtitleParser()
    normalizer = Normalizer()
    chunker = Chunker(chunk_size=20)
    engine = TranslationEngine(
        api_key=args.api_key, 
        provider=args.provider, 
        base_url=args.base_url, 
        model_name=args.model_name, 
        log_language=args.log_language,
        translation_style=args.translation_style,
        force_single_line=args.force_single_line,
        timeout=args.timeout,
        max_retries=args.max_retries,
        infinite_retries=args.infinite_retries
    )
    validator = Validator()
    constraint_engine = ConstraintEngine()
    rebuilder = Rebuilder()

    # 1. Project Resolution
    t_print(f"Analyzing project path for file: {args.input}...", f"جاري تحليل مسار المشروع لملف: {args.input}...", False)
    proj_info = resolver.resolve_project(args.input, force_anime_name=args.project_name)
    t_print(f"✅ Anime: {proj_info['anime']} | Episode: {proj_info['episode']}", f"✅ الأنمي: {proj_info['anime']} | الحلقة: {proj_info['episode']}", False)
    
    # 2. State Management
    state_manager = StateManager(proj_info['episode_path'])
    
    # 3. Parsing & Normalization
    t_print("Parsing subtitle file... | جاري تحليل ملف الترجمة...")
    raw_segments = sub_parser.parse(args.input)
    format_type = 'ass' if args.input.lower().endswith('.ass') else 'srt'
    normalized_segments = normalizer.normalize_segments(raw_segments, format=format_type)
    
    # 4. Chunking
    chunks = chunker.create_chunks(normalized_segments)
    state = state_manager.load_or_create_state(len(chunks))
    
    # Store metadata for Rebuilder in Review Tab
    state_manager.update_state_metadata({
        "input_file": os.path.abspath(args.input),
        "format_type": format_type
    })
    
    # Load project data (Glossary, Context, Memory)
    project_data = resolver.load_project_data(proj_info['data_path'])
    
    # دمج القاموس مع ذاكرة المصطلحات للبحث عنها سوياً
    combined_glossary = {}
    
    raw_glossary = project_data.get('glossary', {})
    if isinstance(raw_glossary, dict) and 'terms' in raw_glossary:
        for t in raw_glossary['terms']:
            term_key = t.get('term', '').lower()
            if term_key:
                combined_glossary[term_key] = {
                    "variants": [term_key],
                    "translation": t.get('translation', ''),
                    "type": t.get('type', '')
                }
                
    raw_term_memory = project_data.get('term_memory', {})
    if isinstance(raw_term_memory, dict):
        for k, v in raw_term_memory.items():
            k_lower = k.lower()
            if k_lower not in combined_glossary: # القاموس الأساسي له الأولوية
                combined_glossary[k_lower] = v
                
    glossary_matcher = GlossaryMatcher(combined_glossary)
    translation_cache = TranslationCache(proj_info['project_path'])
    
    # Load Agent Prompts
    agents_prompt_path = os.path.join('agents', 'AGENTS.md')
    soul_prompt_path = os.path.join('agents', 'SOUL.md')
    
    agents_prompt = ""
    if os.path.exists(agents_prompt_path):
        with open(agents_prompt_path, 'r', encoding='utf-8') as f:
            agents_prompt = f.read()
    if os.path.exists(soul_prompt_path):
        with open(soul_prompt_path, 'r', encoding='utf-8') as f:
            agents_prompt += "\n\n" + f.read()

    # 5. Execution Loop
    completed = set(state.get('completed_chunks', []))
    chunks_to_process = min(args.max_chunks, len(chunks)) if args.max_chunks else len(chunks)
    
    all_final_segments = []
    
    for i in range(chunks_to_process):
        if i in completed and args.resume:
            chunk_data = state_manager.load_chunk(i)
            if chunk_data and 'segments' in chunk_data:
                t_print(f"Skipping chunk {i} (already completed)", f"تخطي الشنك {i} (مكتمل مسبقاً)", False)
                all_final_segments.extend(chunk_data['segments'])
                continue
            else:
                t_print(f"Chunk {i} is marked completed but data is missing. Retranslating...", f"الشنك {i} مكتمل لكن بياناته مفقودة. إعادة الترجمة...", False)
            
        t_print("──────────────────────────────────────────────────")
        t_print(f"Processing chunk {i+1}/{len(chunks)}... | معالجة الشنك {i+1}/{len(chunks)}...")
        t_print(f"Building context... | تجميع السياق...")
        
        # Build Context
        prev_chunk = state_manager.load_chunk(i-1) if i > 0 else None
        next_chunk = chunks[i+1] if i+1 < len(chunks) else None
        
        chunk_payload = chunker.build_context(
            current_chunk=chunks[i],
            prev_translated_chunk=prev_chunk['segments'] if prev_chunk and 'segments' in prev_chunk else None,
            next_raw_chunk=next_chunk
        )
        
        # Inject Glossary
        matched_terms = glossary_matcher.extract_terms_for_chunk(
            chunks[i], 
            chunk_payload['context_before'], 
            chunk_payload['context_after']
        )
        
        if matched_terms:
            t_print(f"Detected {len(matched_terms)} glossary terms | تم اكتشاف {len(matched_terms)} مصطلح من القواميس")
            agents_prompt_temp = agents_prompt + f"\n\nGLOSSARY MATCHES:\n{json.dumps(matched_terms, ensure_ascii=False)}"
        else:
            agents_prompt_temp = agents_prompt
            
        # Extract Cached Translations
        untranslated_segments, cached_translations = translation_cache.extract_cached_segments(
            chunk_payload['segments'], raw_segments
        )
        
        if not untranslated_segments:
            t_print("All segments matched in cache! Skipping LLM... | تم إيجاد كل الأسطر في الذاكرة! جاري تخطي الذكاء الاصطناعي...")
            final_segs = []
            for seg in chunk_payload['segments']:
                seg_copy = dict(seg)
                seg_copy['translated'] = cached_translations[seg['id']]
                final_segs.append(seg_copy)
                
            result = {
                "status": "success",
                "segments": final_segs,
                "terms_detected": []
            }
        else:
            original_chunk_segments = chunk_payload['segments']
            chunk_payload['segments'] = untranslated_segments
            
            # Run Pipeline
            result = engine.run_chunk_pipeline(
                chunk_payload, 
                project_data, 
                agents_prompt_temp, 
                validator, 
                constraint_engine
            )
            
            # Merge back if success or degraded
            if result['status'] in ['success', 'degraded']:
                merged_segments = []
                untranslated_map = {seg['id']: seg for seg in result.get('segments', [])}
                for seg in original_chunk_segments:
                    if seg['id'] in cached_translations:
                        seg_copy = dict(seg)
                        seg_copy['translated'] = cached_translations[seg['id']]
                        merged_segments.append(seg_copy)
                    elif seg['id'] in untranslated_map:
                        merged_segments.append(untranslated_map[seg['id']])
                    else:
                        merged_segments.append(seg)
                result['segments'] = merged_segments
                
            chunk_payload['segments'] = original_chunk_segments
        
        # Update State
        state_manager.save_chunk(i, result)
        
        # Clean up existing state for this chunk to avoid duplicates on resume
        if i in state.get('completed_chunks', []): state['completed_chunks'].remove(i)
        if i in state.get('degraded_chunks', []): state['degraded_chunks'].remove(i)
        if i in state.get('failed_chunks', []): state['failed_chunks'].remove(i)
        
        if result['status'] == 'success':
            state.setdefault('completed_chunks', []).append(i)
            t_print(f"✅ Chunk {i+1} success | ✅ نجاح الشنك {i+1}")
            
            translation_cache.add_translations(result['segments'], raw_segments)
            
            # تحديث الـ Term Memory آلياً
            terms = result.get('terms_detected', [])
            if terms:
                t_print(f"Updating term memory ({len(terms)} terms) | تحديث ذاكرة المصطلحات ({len(terms)} مصطلح)...")
                term_memory = project_data.setdefault('term_memory', {})
                for term in terms:
                    src = term.get('source', '').lower()
                    trans = term.get('translation', '')
                    if src and trans:
                        if src not in term_memory:
                            term_memory[src] = {"variants": [src], "translation": trans, "count": 1}
                        else:
                            term_memory[src]["count"] = term_memory[src].get("count", 0) + 1
                
                term_memory_path = os.path.join(proj_info['data_path'], 'term_memory.json')
                with open(term_memory_path, 'w', encoding='utf-8') as f:
                    json.dump(term_memory, f, ensure_ascii=False, indent=2)
                    
        elif result['status'] == 'degraded':
            state.setdefault('degraded_chunks', []).append(i)
            t_print(f"Chunk {i+1} degraded | انهيار آمن للشنك {i+1}")
        elif result['status'] == 'failed':
            state.setdefault('failed_chunks', []).append(i)
            t_print(f"Chunk {i+1} failed | فشل الشنك {i+1}")
            
        state_manager.save_state(state)
        all_final_segments.extend(result['segments'])

    # 6. Rebuilding
    if len(all_final_segments) == len(raw_segments) or (args.max_chunks and len(all_final_segments) > 0):
        t_print("Building final file... | جاري بناء الملف النهائي...")
        base_name = os.path.splitext(os.path.basename(args.input))[0]
        output_filename = f"{base_name}_floris.{format_type}"
        output_filepath = os.path.join(proj_info['episode_path'], output_filename)
        
        if format_type == 'srt':
            rebuilder.build_srt(all_final_segments, output_filepath)
        else:
            rebuilder.build_ass(all_final_segments, args.input, output_filepath)
            
        t_print(f"Translation completed. File saved at: {output_filepath}", f"اكتملت الترجمة. تم حفظ الملف في: {output_filepath}", False)
    else:
        t_print(f"Not all chunks completed (Expected {len(raw_segments)}, Got {len(all_final_segments)}), final file not built.", f"لم تكتمل كافة الشنكات (المطلوب {len(raw_segments)}، المتاح {len(all_final_segments)})، لم يتم بناء الملف النهائي بعد.", False)

if __name__ == "__main__":
    main()
