import pytest
from django.urls import reverse

@pytest.mark.django_db
def test_post_uuid_lookup(client, post_factory):
    post = post_factory()
    url = reverse('posts:post_details', kwargs={'share_id': str(post.share_id)})
    
    response = client.get(url)
    assert response.status_code == 200
