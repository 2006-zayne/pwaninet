from django.urls import path

from . import views

urlpatterns = [
    path("", views.UploadCollectionView.as_view(), name="upload-collection"),
    path("<uuid:id>/", views.UploadDetailView.as_view(), name="upload-detail"),
    path("<uuid:id>/events/", views.UploadEventsView.as_view(), name="upload-events"),
    path("<uuid:id>/authorize/", views.UploadAuthorizeView.as_view(), name="upload-authorize"),
    path("<uuid:id>/complete/", views.UploadCompleteView.as_view(), name="upload-complete"),
    path("<uuid:id>/retry/", views.UploadRetryView.as_view(), name="upload-retry"),
    path("<uuid:id>/cancel/", views.UploadCancelView.as_view(), name="upload-cancel"),
    path("<uuid:id>/delete/", views.UploadDeleteView.as_view(), name="upload-delete"),
]
