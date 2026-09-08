import re
with open("pwaninet/urls.py", "r") as f:
    text = f.read()

# Replace all these lines before def download_android_apk
# with just one decorator and one logger
bad_chunk = r'logger = logging\.getLogger\(__name__\)\n\n@require_http_methods\(\["GET", "HEAD"\]\)\n@require_http_methods\(\["GET", "HEAD"\]\)\nlogger = logging\.getLogger\(__name__\)'
text = re.sub(bad_chunk, '@require_http_methods(["GET", "HEAD"])\nlogger = logging.getLogger(__name__)', text)

with open("pwaninet/urls.py", "w") as f:
    f.write(text)
