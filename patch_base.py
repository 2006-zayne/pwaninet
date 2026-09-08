with open("templates/base.html", "r") as f:
    text = f.read()

script = """
    <script>
    function copyLinkToClipboard(url) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(url).then(function() {
                // Show a toast or alert
                let toast = document.createElement('div');
                toast.textContent = 'Link copied to clipboard!';
                toast.style.position = 'fixed';
                toast.style.bottom = '20px';
                toast.style.left = '50%';
                toast.style.transform = 'translateX(-50%)';
                toast.style.backgroundColor = 'rgba(0,0,0,0.8)';
                toast.style.color = 'white';
                toast.style.padding = '10px 20px';
                toast.style.borderRadius = '5px';
                toast.style.zIndex = '9999';
                document.body.appendChild(toast);
                setTimeout(() => toast.remove(), 2500);
            });
        } else {
            // Fallback
            let input = document.createElement('input');
            input.value = url;
            document.body.appendChild(input);
            input.select();
            document.execCommand('copy');
            document.body.removeChild(input);
            alert('Link copied to clipboard!');
        }
    }
    </script>
</body>
"""

text = text.replace("</body>", script)

with open("templates/base.html", "w") as f:
    f.write(text)
