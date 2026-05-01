import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath('.')))
from gui.services import ProjectService
from core.state_manager import StateManager

ps = ProjectService(base_dir='D:/clwd/FlorisSrt/projects')
tree = ps.get_projects_tree()
print('Projects Tree:', tree)

sm = StateManager('D:/clwd/FlorisSrt/projects/TestAnime/episodes/ep01')
state = sm.load_or_create_state(0)
chunks = sm.load_all_chunks(state['total_chunks'])

failed_count = 0
for seg in chunks:
    is_failed = (seg.get('text', '') == seg.get('translated', '')) or not seg.get('translated', '')
    print(f"ID: {seg['id']}, En: '{seg['text']}', Ar: '{seg['translated']}', Failed: {is_failed}")
    if is_failed: failed_count += 1

print(f'Total Failed Segments: {failed_count}')
