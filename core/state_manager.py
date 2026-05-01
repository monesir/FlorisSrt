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
