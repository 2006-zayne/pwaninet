from django.urls import path
from . import views

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
]
