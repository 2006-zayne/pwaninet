from django.urls import path
from core import views

urlpatterns = [
    path('dashboard/', views.groups_dashboard, name='groups_dashboard'),
    path('<int:group_id>/', views.groups_detail_view, name='groups_detail'),
    path('create/', views.create_group_view, name='create_group'),
    path('toggle/<int:group_id>/', views.toggle_group_membership, name='toggle_membership'),
    path('<int:group_id>/edit/', views.edit_group, name='edit_group'),
    path('<int:group_id>/invite/<int:user_id>/', views.invite_to_group, name='invite_to_group'),
    path('invite/respond/<int:notif_id>/<str:action>/', views.respond_to_invite, name='respond_to_invite'),
]
