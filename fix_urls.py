import re
with open("pwaninet/urls.py", "r") as f:
    content = f.read()

# Fix double decorators
content = re.sub(r'logger = logging\.getLogger\(__name__\)\n\n@require_http_methods\(\["GET", "HEAD"\]\)\n@require_http_methods\(\["GET", "HEAD"\]\)\nlogger = logging\.getLogger\(__name__\)', r'@require_http_methods(["GET", "HEAD"])\nlogger = logging.getLogger(__name__)', content)

with open("pwaninet/urls.py", "w") as f:
    f.write(content)
