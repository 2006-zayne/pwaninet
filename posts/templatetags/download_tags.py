from django import template
from django.core import signing
from django.urls import reverse
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def protected_download_url(context, post, media_type='video', media_id=None):
    request = context.get('request')
    if not request or not request.user.is_authenticated or not post or not post.allow_downloads:
        return ''
    payload = {'post': str(post.share_id), 'user': request.user.pk, 'type': media_type}
    if media_id is not None:
        payload['media'] = int(media_id)
    token = signing.dumps(payload, salt='posts.media-download')
    return f"{reverse('posts:download_post_media', args=[post.share_id])}?{urlencode({'token': token})}"
