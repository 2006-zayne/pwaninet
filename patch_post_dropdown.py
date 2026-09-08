import glob

# Files to patch
files = [
    "posts/templates/posts/partials/post_card.html",
    "posts/templates/posts/partials/post_detail_content.html",
    "posts/templates/posts/partials/shared_post_card.html"
]

copy_link_html = """
                <li>
                    <button class="dropdown-item d-flex align-items-center gap-2"
                            onclick="copyLinkToClipboard(window.location.origin + '{% url 'posts:post_details' post.share_id %}')">
                        <i class="bi bi-link-45deg"></i> Copy Link
                    </button>
                </li>
"""

# For shared_post_card, it uses `shared_post.original_post.share_id` instead of `post.share_id` sometimes, but wait. Let's inspect the files.
