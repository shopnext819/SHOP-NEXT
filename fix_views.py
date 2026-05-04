import os

filepath = r"c:\SHOP NEXT\shop\views.py"
with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

old_str = """            has_w = request.POST.get("has_warranty")
            if has_w is not None:
                p.has_warranty = (has_w == "true" or has_w == "on")"""

new_str = """            w_type = request.POST.get("warranty_type")
            if w_type:
                p.warranty_type = w_type"""

if old_str in content:
    content = content.replace(old_str, new_str)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed!")
else:
    print("Target string not found. Trying line-by-line replace.")
    # More robust replace:
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'p.has_warranty = (has_w == "true" or has_w == "on")' in line:
            lines[i] = '                p.warranty_type = w_type'
            lines[i-1] = '            if w_type:'
            lines[i-2] = '            w_type = request.POST.get("warranty_type")'
    with open(filepath, "w", encoding="utf-8") as f:
        f.write('\n'.join(lines))
    print("Fixed via line replace!")
