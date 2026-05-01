import os
import re
import json

class ProjectResolution:
    """
    الطبقة المسؤولة عن تحليل اسم الملف وربطه بالمشروع المناسب (Anime)
    وإنشاء الهيكلية التلقائية لملفات הـ Data الخاصة بالمشروع.
    """
    def __init__(self, projects_dir="projects"):
        self.projects_dir = projects_dir
        
    def sanitize_name(self, name):
        """تطبيع اسم المشروع: أحرف صغيرة، واستبدال المسافات بـ hyphens"""
        name = name.lower().strip()
        name = re.sub(r'[^a-z0-9\s-]', '', name)
        name = re.sub(r'\s+', '-', name)
        return name

    def resolve_project(self, filepath, force_anime_name=None):
        """تحليل مسار الملف واستخراج الأنمي ورقم الحلقة"""
        filename = os.path.basename(filepath)
        anime_name = None
        episode_name = "ep01"
        
        try:
            from guessit import guessit
            info = guessit(filename)
            if 'title' in info:
                anime_name = self.sanitize_name(info['title'])
            if 'episode' in info:
                ep_num = info['episode']
                season = info.get('season', 1)
                episode_name = f"s{season:02d}e{ep_num:02d}"
        except ImportError:
            print("Warning: 'guessit' library not found. Falling back to basic filename extraction.")
            # Fallback في حال غياب المكتبة
            clean_name = re.sub(r'\[.*?\]|\(.*?\)', '', filename).strip()
            match = re.search(r'(?i)s(\d+)e(\d+)', clean_name)
            if match:
                s, e = match.groups()
                if match.start() == 0:
                    anime_name = self.sanitize_name(clean_name[match.end():])
                else:
                    anime_name = self.sanitize_name(clean_name[:match.start()])
                    
                if not anime_name:
                    anime_name = "unknown-anime"
                    
                episode_name = f"s{int(s):02d}e{int(e):02d}"
            else:
                parts = clean_name.split(' - ')
                if len(parts) >= 2:
                    anime_name = self.sanitize_name(parts[0])
                    episode_name = f"ep_{self.sanitize_name(parts[1])}"
                else:
                    # Fallback for standalone numbers like "01.ass"
                    num_match = re.search(r'(\d+)', clean_name)
                    if num_match:
                        episode_name = f"ep_{int(num_match.group(1)):02d}"
                    
        # Override with forced name if provided
        if force_anime_name:
            anime_name = self.sanitize_name(force_anime_name)
        else:
            # استخراج اسم المجلد الأب كخيار إنقاذ إذا كان اسم الملف ضعيفاً أو مجرد أرقام
            if not anime_name or len(anime_name.replace('-', '')) < 2 or anime_name in ["unknown-project", "unknown-anime"] or anime_name.replace('-', '').isdigit():
                parent_dir = os.path.basename(os.path.dirname(os.path.abspath(filepath)))
                if parent_dir and parent_dir.lower() not in ['downloads', 'desktop', 'documents']:
                    anime_name = self.sanitize_name(parent_dir)
                    
            if not anime_name or anime_name == "-":
                anime_name = "unknown-anime"

        project_path = os.path.join(self.projects_dir, anime_name)
        data_path = os.path.join(project_path, 'data')
        episodes_path = os.path.join(project_path, 'episodes', episode_name)
        
        # إنشاء المجلدات إن لم تكن موجودة
        os.makedirs(data_path, exist_ok=True)
        os.makedirs(episodes_path, exist_ok=True)
        
        # إنشاء ملفات הـ Data الأولية إن لم تكن موجودة
        files_to_create = ['glossary.json', 'work_context.json', 'term_memory.json', 'characters.json']
        for file in files_to_create:
            file_path = os.path.join(data_path, file)
            if not os.path.exists(file_path):
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                    
        return {
            "anime": anime_name,
            "episode": episode_name,
            "project_path": project_path,
            "data_path": data_path,
            "episode_path": episodes_path
        }
        
    def load_project_data(self, data_path):
        """تحميل القواميس وسياق العمل للمشروع"""
        data = {}
        for file in ['glossary.json', 'work_context.json', 'term_memory.json', 'characters.json']:
            file_path = os.path.join(data_path, file)
            with open(file_path, 'r', encoding='utf-8') as f:
                data[file.replace('.json', '')] = json.load(f)
        return data
