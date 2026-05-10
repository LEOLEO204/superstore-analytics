import os
import re

def patch_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if 'importlib.reload(utils.ui_components)' in content:
        print(f"Skipping {filepath}, already patched.")
        return
        
    pattern = r"(from utils\.ui_components import .*)"
    if not re.search(pattern, content):
        print(f"Could not find ui_components import in {filepath}")
        return
        
    replacement = r"import importlib\nimport utils.ui_components\nimportlib.reload(utils.ui_components)\n\1"
    new_content = re.sub(pattern, replacement, content, count=1)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Patched {filepath} successfully.")

# Patch all pages
pages_dir = 'pages'
for filename in os.listdir(pages_dir):
    if filename.endswith('.py'):
        patch_file(os.path.join(pages_dir, filename))
