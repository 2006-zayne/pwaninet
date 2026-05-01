from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ConversationViewSet,
    MessageViewSet,
    MessageReactionViewSet,
    ConversationThemeViewSet,
    conversation_list,
    conversation_detail,
    search_followed_users,
    create_conversation
)

router = DefaultRouter()
router.register(r'conversations', ConversationViewSet, basename='conversation')
router.register(r'messages', MessageViewSet, basename='message')
router.register(r'reactions', MessageReactionViewSet, basename='reaction')
router.register(r'themes', ConversationThemeViewSet, basename='theme')

app_name = 'messaging'

urlpatterns = [
    path('v1/', include(router.urls)),
    path('', conversation_list, name='conversation_list'),
    path('conversation/<int:conversation_id>/', conversation_detail, name='conversation_detail'),
    path('search-followed-users/', search_followed_users, name='search_followed_users'),
    path('create/', create_conversation, name='create_conversation'),
]
