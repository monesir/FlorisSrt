import os
import re

def replace_in_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except UnicodeDecodeError:
        try:
            with open(filepath, 'r', encoding='utf-16') as f:
                content = f.read()
        except:
            return

    new_content = content
    
    new_content = re.sub(r'current_project', 'current_project', new_content)
    new_content = re.sub(r'project_name', 'project_name', new_content)
    new_content = re.sub(r'force_project_name', 'force_project_name', new_content)
    new_content = re.sub(r'project_cb', 'project_cb', new_content)
    new_content = re.sub(r'lbl_project', 'lbl_project', new_content)
    new_content = re.sub(r'project_path', 'project_path', new_content)
    new_content = re.sub(r'project_dir', 'project_dir', new_content)
    
    new_content = re.sub(r'\bAnime\b', 'Project', new_content)
    new_content = re.sub(r'\banime\b', 'project', new_content)
    new_content = re.sub(r'\bANIME\b', 'PROJECT', new_content)
    
    new_content = new_content.replace('FlorisSrt', 'FlorisSrt')
    new_content = new_content.replace('FlorisSrt', 'FlorisSrt')
    
    if new_content != content:
        # Write back in the same encoding it was read in
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
        except:
            pass
        print(f"Updated {filepath}")

def main():
    root = '.'
    for dirpath, dirnames, filenames in os.walk(root):
        if 'venv' in dirpath or '.git' in dirpath or '__pycache__' in dirpath:
            continue
        for filename in filenames:
            if filename.endswith(('.py', '.md', '.json', '.txt')):
                replace_in_file(os.path.join(dirpath, filename))

if __name__ == '__main__':
    main()
