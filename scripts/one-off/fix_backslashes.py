files = [
    "posts/templates/posts/partials/post_card.html",
    "posts/templates/posts/partials/post_detail_content.html",
    "posts/templates/posts/partials/shared_post_card.html"
]

for filepath in files:
    with open(filepath, "r") as f:
        text = f.read()

    text = text.replace("window[\\'removeUser", "window['removeUser")
    text = text.replace("window[\\'removeGroup", "window['removeGroup")
    text = text.replace("window[\\'removeUserShared", "window['removeUserShared")
    text = text.replace("window[\\'removeGroupShared", "window['removeGroupShared")
    text = text.replace("}\\']", "}']")

    with open(filepath, "w") as f:
        f.write(text)
