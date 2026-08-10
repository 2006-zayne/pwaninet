"""
Django signals for chat theme image optimization and event emission
"""

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import ConversationTheme, Message, ConversationMember
from .services.image_optimizer import ImageOptimizer
from notifications.events import publish_event, EventTypes, EventSources, EventActions


@receiver(pre_save, sender=ConversationTheme)
def optimize_theme_images(sender, instance, **kwargs):
    """Optimize theme images before saving"""
    
    # Optimize light image
    if instance.light_image:
        try:
            # Generate hash for deduplication
            image_hash = ImageOptimizer.generate_image_hash(instance.light_image)
            if image_hash:
                instance.light_image_hash = image_hash
            
            # Optimize image
            optimized_image = ImageOptimizer.optimize_theme_image(instance.light_image)
            if optimized_image != instance.light_image:
                instance.light_image = optimized_image
                instance.light_image_size = optimized_image.size
            
        except Exception as e:
            print(f"Error optimizing light image: {e}")
    
    # Optimize dark image
    if instance.dark_image:
        try:
            # Generate hash for deduplication
            image_hash = ImageOptimizer.generate_image_hash(instance.dark_image)
            if image_hash:
                instance.dark_image_hash = image_hash
            
            # Optimize image
            optimized_image = ImageOptimizer.optimize_theme_image(instance.dark_image)
            if optimized_image != instance.dark_image:
                instance.dark_image = optimized_image
                instance.dark_image_size = optimized_image.size
            
        except Exception as e:
            print(f"Error optimizing dark image: {e}")


@receiver(post_save, sender=Message)
def message_sent(sender, instance, created, **kwargs):
    """Emit event when a message is sent."""
    if created:
        publish_event(
            event_type=EventTypes.MESSAGING_MESSAGE_SENT.value,
            source=EventSources.MESSAGING.value,
            action=EventActions.SENT.value,
            actor=instance.sender,
            target_type='Conversation',
            target_id=str(instance.conversation.id),
            metadata={
                'message_content': instance.content[:100],
                'conversation_type': instance.conversation.type,
                'sender_username': instance.sender.username
            }
        )


@receiver(post_save, sender=ConversationMember)
def conversation_member_added(sender, instance, created, **kwargs):
    """Emit event when a member is added to a conversation."""
    if created:
        publish_event(
            event_type=EventTypes.MESSAGING_CONVERSATION_MEMBER_ADDED.value,
            source=EventSources.MESSAGING.value,
            action=EventActions.ADDED.value,
            actor=instance.user,
            target_type='Conversation',
            target_id=str(instance.conversation.id),
            metadata={
                'conversation_type': instance.conversation.type,
                'member_username': instance.user.username
            }
        )
