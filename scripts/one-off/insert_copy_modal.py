import re

def add_modal_copy_button(filepath, variable_name):
    with open(filepath, "r") as f:
        content = f.read()
    
    copy_html = f"""
                <div class="mb-3 d-grid">
                    <button type="button" class="btn btn-outline-primary"
                            onclick="copyLinkToClipboard(window.location.origin + '{{% url 'posts:post_details' {variable_name} %}}')">
                        <i class="bi bi-link-45deg"></i> Copy Link to Clipboard
                    </button>
                </div>
                <hr>
"""
    # Find the nav-tabs and insert above
    pattern = r"(<ul class=\"nav nav-tabs mb-3\" id=\"shareTabs-[^\"]+\" role=\"tablist\">)"
    content = re.sub(pattern, copy_html + r"\1", content)
    
    with open(filepath, "w") as f:
        f.write(content)

add_modal_copy_button("posts/templates/posts/partials/post_card.html", "post.share_id")
add_modal_copy_button("posts/templates/posts/partials/post_detail_content.html", "post.share_id")
add_modal_copy_button("posts/templates/posts/partials/shared_post_card.html", "shared_post.original_post.share_id")

