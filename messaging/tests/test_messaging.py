import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from channels.testing import WebsocketCommunicator
from pwaninet.asgi import application
from messaging.models import Conversation, ConversationMember, Message, MessageReaction

User = get_user_model()


class MessagingAPITestCase(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='alice', password='password123', email='alice@example.com')
        self.user2 = User.objects.create_user(username='bob', password='password123', email='bob@example.com')
        self.user3 = User.objects.create_user(username='charlie', password='password123', email='charlie@example.com')

        self.conv = Conversation.objects.create(type=Conversation.DIRECT)
        ConversationMember.objects.create(conversation=self.conv, user=self.user1)
        ConversationMember.objects.create(conversation=self.conv, user=self.user2)

        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)

    def test_direct_conversation_lookup(self):
        found = Conversation.get_direct_conversation_between(self.user1, self.user2)
        self.assertIsNotNone(found)
        self.assertEqual(found.id, self.conv.id)

    def test_create_message_api(self):
        response = self.client.post('/messaging/v1/messages/', {
            'conversation': self.conv.id,
            'content': 'Hello from REST!'
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Message.objects.filter(conversation=self.conv).count(), 1)
        msg = Message.objects.first()
        self.assertEqual(msg.content, 'Hello from REST!')
        self.assertEqual(msg.sender, self.user1)

    def test_cursor_pagination_api(self):
        for i in range(5):
            Message.objects.create(conversation=self.conv, sender=self.user1, content=f'Msg {i}')
        response = self.client.get(f'/messaging/v1/messages/paginated/?conversation_id={self.conv.id}&limit=3')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn('results', data)
        self.assertEqual(len(data['results']), 3)

    def test_unauthorized_user_cannot_access_conversation(self):
        self.client.force_authenticate(user=self.user3)
        response = self.client.get(f'/messaging/v1/messages/paginated/?conversation_id={self.conv.id}')
        self.assertEqual(response.status_code, 404)
