import re

files = [
    "posts/templates/posts/partials/post_card.html",
    "posts/templates/posts/partials/post_content.html",
    "posts/templates/posts/partials/post_detail_content.html",
    "posts/templates/posts/partials/post_thumbnail.html",
    "posts/templates/posts/partials/shared_posts_content.html",
    "posts/templates/posts/partials/shared_post_card.html",
    "posts/templates/posts/partials/comment_item.html"
]

def add_urlize(text):
    # Only replace {{ post.content }} if it doesn't already have a filter
    text = re.sub(r'{{ post\.content }}', r'{{ post.content|urlize }}', text)
    text = re.sub(r'{{ post\.repost_of\.content }}', r'{{ post.repost_of.content|urlize }}', text)
    text = re.sub(r'{{ shared_post\.message }}', r'{{ shared_post.message|urlize }}', text)
    text = re.sub(r'{{ comment\.content }}', r'{{ comment.content|urlize }}', text)
    return text

import os
for filepath in files:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as f:
        text = f.read()
    
    text = add_urlize(text)
    
    with open(filepath, "w") as f:
        f.write(text)
