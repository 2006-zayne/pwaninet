import re
with open("pwaninet/urls.py", "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for i, line in enumerate(lines):
    if line.strip() == "logger = logging.getLogger(__name__)" and i > 80 and i < 100:
        if skip: continue
        skip = True
        new_lines.append(line)
    elif line.strip() == '@require_http_methods(["GET", "HEAD"])' and i > 80 and i < 100:
        if getattr(fix_urls2, "saw_dec", False): continue
        fix_urls2.saw_dec = True
        new_lines.append(line)
    else:
        new_lines.append(line)

with open("pwaninet/urls.py", "w") as f:
    f.writelines(new_lines)
