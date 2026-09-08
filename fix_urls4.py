with open("pwaninet/urls.py", "r") as f:
    text = f.read()

text = text.replace('@require_http_methods(["GET", "HEAD"])\nlogger = logging.getLogger(__name__)\ndef download_android_apk(request):', 
'''logger = logging.getLogger(__name__)

@require_http_methods(["GET", "HEAD"])
def download_android_apk(request):''')

with open("pwaninet/urls.py", "w") as f:
    f.write(text)
