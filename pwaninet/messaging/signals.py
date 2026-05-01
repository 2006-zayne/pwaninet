"""
Django signals for chat theme image optimization
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver
from .models import ConversationTheme
from .services.image_optimizer import ImageOptimizer


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
