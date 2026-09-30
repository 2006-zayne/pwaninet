import re

def add_copy_button(filepath, variable_name):
    with open(filepath, "r") as f:
        content = f.read()
    
    copy_html = f"""
                <li>
                    <button class="dropdown-item d-flex align-items-center gap-2"
                            onclick="copyLinkToClipboard(window.location.origin + '{{% url 'posts:post_details' {variable_name} %}}')">
                        <i class="bi bi-link-45deg"></i> Copy Link
                    </button>
                </li>
"""
    # Find the report modal li and append ours before it
    pattern = r"(<li>\s*<button class=\"dropdown-item[^\"]*\"\s*data-bs-toggle=\"modal\" data-bs-target=\"#reportModal-.*?</li>)"
    content = re.sub(pattern, copy_html + r"\1", content, flags=re.DOTALL)
    
    with open(filepath, "w") as f:
        f.write(content)

add_copy_button("posts/templates/posts/partials/post_card.html", "post.share_id")
add_copy_button("posts/templates/posts/partials/post_detail_content.html", "post.share_id")
# shared_post_card has different variable
add_copy_button("posts/templates/posts/partials/shared_post_card.html", "shared_post.original_post.share_id")

