with open("posts/templates/posts/partials/post_content.html", "r") as f:
    text = f.read()

replacement = """
    <p class="mb-0 text-dark post-content-text" style="font-size: 16px; line-height: 1.5;">
        {% if post.repost_of %}
            {% if post.content %}<p class="mb-2 text-dark" style="font-size: 16px;">{{ post.content|urlize|linebreaksbr }}</p>{% endif %}
            <span class="post-content-full">{{ post.repost_of.content|urlize|linebreaksbr }}</span>
            <span class="post-content-truncated" style="display: none;">{{ post.repost_of.content|truncatechars:200|urlize|linebreaksbr }}</span>
        {% else %}
            <span class="post-content-full">{{ post.content|urlize|linebreaksbr }}</span>
            <span class="post-content-truncated" style="display: none;">{{ post.content|truncatechars:200|urlize|linebreaksbr }}</span>
        {% endif %}
    </p>
"""
import re
text = re.sub(r'<p class="mb-0 text-dark post-content-text" style="font-size: 16px; line-height: 1.5;">.*?</p>', replacement.strip(), text, flags=re.DOTALL)

with open("posts/templates/posts/partials/post_content.html", "w") as f:
    f.write(text)
