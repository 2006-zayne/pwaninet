from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# API Router
router = DefaultRouter()
router.register(r'api/posts', views.PostViewSet, basename='post')
router.register(r'api/comments', views.CommentViewSet, basename='comment')
router.register(r'api/reports', views.ReportViewSet, basename='report')
router.register(r'api/author-preferences', views.AuthorPreferenceViewSet, basename='authorpreference')
router.register(r'api/shared-posts', views.SharedPostViewSet, basename='sharedpost')

urlpatterns = [
    path('', views.home_view, name='home'),
    path('post/new/', views.create_post_view, name='create_post'),
    path('post/<int:post_id>/', views.post_detail_view, name='post_details'),
    path('like/<int:post_id>/', views.toggle_like, name='toggle_like'),
    path('post/<int:post_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/like/', views.toggle_comment_like, name='toggle_comment_like'),
    path('post/<int:post_id>/likers/', views.post_likers_list, name='post_likers_list'),
    path('unit/<int:unit_id>/', views.unit_posts_view, name='unit_detail'),
    path('search/', views.search_view, name='search'),
    path('post/<int:post_id>/image/<int:image_index>/', views.view_image_fullscreen, name='view_image_fullscreen'),
    path('post/<int:post_id>/share/', views.share_post_view, name='share_post'),
    path('', include(router.urls)),
]
