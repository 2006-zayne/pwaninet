import pytest
from django.urls import reverse
from django.core.signing import TimestampSigner

@pytest.mark.django_db
def test_signed_document_download(client, document_factory):
    document = document_factory()
    signer = TimestampSigner()
    valid_token = signer.sign_object(str(document.share_id))
    
    url = reverse('documents:serve_download', kwargs={'share_id': str(document.share_id)})
    
    # Missing token
    response = client.get(url)
    assert response.status_code == 403
    
    # Invalid token
    response = client.get(f"{url}?t=invalid_token")
    assert response.status_code == 403
