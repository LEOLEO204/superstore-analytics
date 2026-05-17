import os
import glob

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if "import sys" in content and "sys.path.insert" in content:
        return # already patched

    if "from utils" not in content and "import utils" not in content:
        return # no utils import

    lines = content.split('\n')
    out_lines = []
    patched = False
    
    patch_code = """
import os
import sys
# Thêm thư mục gốc vào sys.path để có thể import module utils
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(current_dir, "..", "..")) if "pages" in current_dir else os.path.abspath(os.path.join(current_dir, ".."))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
"""

    for line in lines:
        if not patched and (line.startswith("from utils") or line.startswith("import utils")):
            out_lines.extend(patch_code.strip().split('\n'))
            patched = True
        out_lines.append(line)
        
    if patched:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(out_lines))
        print(f"Patched: {filepath}")

for root, _, files in os.walk('streamlit_backup'):
    for file in files:
        if file.endswith('.py'):
            patch_file(os.path.join(root, file))

print("Done patching.")
