with open('gui/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

idx_main = -1
for i, line in enumerate(lines):
    if line.startswith('if __name__ == "__main__":'):
        idx_main = i
        break

idx_methods = -1
for i, line in enumerate(lines):
    if line.strip() == '# --- Pre-Analyze Tab Methods ---':
        idx_methods = i
        break

top = lines[:idx_main]
bottom = lines[idx_main:idx_methods]
methods = lines[idx_methods:]

with open('gui/main.py', 'w', encoding='utf-8') as f:
    f.writelines(top)
    for line in methods:
        f.write('    ' + line)
    f.write('\n')
    f.writelines(bottom)
