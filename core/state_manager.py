import os
import json
import shutil

class StateManager:
    """
    مدير الحالة المسؤول عن حفظ تقدم المشروع، الشنكات، وضمان عدم التلف عبر الكتابة الذرية (Atomic Writes).
    هذا يضمن أن الانقطاع المفاجئ لا يدمر ملف project.json
    """
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.state_file = os.path.join(self.project_dir, 'project.json')
        self.chunks_dir = os.path.join(self.project_dir, 'chunks')
        
        # التأكد من وجود المجلدات الأساسية
        os.makedirs(self.chunks_dir, exist_ok=True)
        
    def load_or_create_state(self, total_chunks):
        """تحميل الحالة السابقة أو إنشاء حالة جديدة"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        # Create new state
        state = {
            "total_chunks": total_chunks,
            "completed_chunks": [],
            "failed_chunks": [],
            "degraded_chunks": []
        }
        self.save_state(state)
        return state
        
    def save_state(self, state):
        """حفظ الحالة بشكل ذري (Atomic) لتجنب التلف عند الانقطاع"""
        temp_file = self.state_file + '.tmp'
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        shutil.move(temp_file, self.state_file)
        
    def update_state_metadata(self, metadata):
        """تحديث بيانات وصفية في ملف الحالة دون تدمير بيانات التقدم"""
        if os.path.exists(self.state_file):
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            state.update(metadata)
            self.save_state(state)
        
    def save_chunk(self, chunk_index, chunk_data):
        """حفظ بيانات الشنك بشكل ذري"""
        chunk_file = os.path.join(self.chunks_dir, f'chunk_{chunk_index}.json')
        temp_file = chunk_file + '.tmp'
        
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(chunk_data, f, ensure_ascii=False, indent=2)
        shutil.move(temp_file, chunk_file)
        
    def load_chunk(self, chunk_index):
        """تحميل شنك محفوظ مسبقاً (مفيد لجلب الـ Backward Context)"""
        chunk_file = os.path.join(self.chunks_dir, f'chunk_{chunk_index}.json')
        if os.path.exists(chunk_file):
            with open(chunk_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
        
    def load_all_chunks(self, total_chunks):
        """تحميل كل الشنكات دفعة واحدة للمراجعة مع حقن رقم الشنك"""
        all_segments = []
        for i in range(total_chunks):
            chunk_data = self.load_chunk(i)
            if chunk_data and 'segments' in chunk_data:
                for seg in chunk_data['segments']:
                    seg['chunk_index'] = i
                    all_segments.append(seg)
        return all_segments
        
    def save_segments_to_chunks(self, segments):
        """حفظ التعديلات من جدول المراجعة إلى ملفات الشنكات المناسبة"""
        chunk_map = {}
        for seg in segments:
            c_idx = seg.get('chunk_index')
            if c_idx is not None:
                if c_idx not in chunk_map:
                    chunk_map[c_idx] = self.load_chunk(c_idx) or {"segments": [], "status": "success"}
                
                # Update the specific segment in the chunk
                for idx, c_seg in enumerate(chunk_map[c_idx]['segments']):
                    if c_seg['id'] == seg['id']:
                        chunk_map[c_idx]['segments'][idx]['translated'] = seg.get('translated', '')
                        break
                        
        for c_idx, data in chunk_map.items():
            self.save_chunk(c_idx, data)
