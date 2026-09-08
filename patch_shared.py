import re

with open("posts/templates/posts/partials/shared_post_card.html", "r") as f:
    text = f.read()

text = text.replace('{{ shared_post.message }}', '{{ shared_post.message|urlize|linebreaksbr }}')

with open("posts/templates/posts/partials/shared_post_card.html", "w") as f:
    f.write(text)
