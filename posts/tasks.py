"""
Celery tasks for background post processing.

This module contains async tasks for handling large media uploads
and post creation in the background with progress tracking.
"""
from celery import shared_task
from celery import current_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def create_post_with_media(self, user_id, content, unit_id=None, group_id=None, 
                          gradient_class='none', images_data=None, video_data=None, 
                          docs_data=None, audio_data=None):
    """
    Create a post in the background with progress tracking.
    
    Args:
        user_id: ID of the user creating the post
        content: Post content text
        unit_id: Optional unit ID
        group_id: Optional group ID
        gradient_class: Background style class
        images_data: List of image file data
        video_data: Video file data
        docs_data: Document file data
        audio_data: Audio file data
    
    Returns:
        dict: Post creation result with post ID
    """
    from django.contrib.auth import get_user_model
    from posts.models import Post, PostImage
    from courses.models import Unit
    from groups.models import Group
    from io import BytesIO
    from django.core.files.uploadedfile import InMemoryUploadedFile
    import sys
    
    User = get_user_model()
    
    total_steps = 5
    current_step = 0
    
    try:
        # Step 1: Get user and validate
        current_step += 1
        self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Validating user...'})
        user = User.objects.get(id=user_id)
        
        # Step 2: Create post
        current_step += 1
        self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Creating post...'})
        
        post_data = {
            'author': user,
            'content': content,
            'gradient_class': gradient_class,
        }
        
        if unit_id:
            post_data['unit'] = Unit.objects.get(id=unit_id)
        if group_id:
            post_data['group'] = Group.objects.get(id=group_id)
            
        post = Post.objects.create(**post_data)
        
        # Step 3: Process images
        if images_data:
            current_step += 1
            self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': f'Processing {len(images_data)} images...'})
            
            for idx, image_data in enumerate(images_data):
                # Convert base64 or file data to InMemoryUploadedFile
                # This is a simplified version - you'll need to adapt based on your data format
                from PIL import Image
                img = Image.open(BytesIO(image_data))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                if img.height > 1080 or img.width > 1080:
                    img.thumbnail((1080, 1080))
                output = BytesIO()
                img.save(output, format='JPEG', quality=75)
                output.seek(0)
                file_name = f"post_{post.id}_image_{idx}.jpg"
                image_file = InMemoryUploadedFile(
                    output, 'ImageField', file_name,
                    'image/jpeg', sys.getsizeof(output), None
                )
                PostImage.objects.create(post=post, image=image_file, order=idx)
        
        # Step 4: Process video
        if video_data:
            current_step += 1
            self.update_state(state='PROGRESS', meta={'current': current_step, 'total': total_steps, 'status': 'Processing video...'})
            # Process video file - adapt based on your data format
            post.video = video_data
            post.save()
        
        # Step 5: Process docs/audio
        if docs_data:
            self.update_state(state='PROGRESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Processing document...'})
            post.docs = docs_data
            post.save()
        
        if audio_data:
            self.update_state(state='PROGRESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Processing audio...'})
            post.audio = audio_data
            post.save()
        
        # Final step
        self.update_state(state='SUCCESS', meta={'current': total_steps, 'total': total_steps, 'status': 'Post created successfully!'})
        
        return {
            'post_id': post.id,
            'status': 'success',
            'message': 'Post created successfully'
        }
        
    except Exception as e:
        logger.error(f"Error creating post in background: {e}")
        self.update_state(state='FAILURE', meta={'current': current_step, 'total': total_steps, 'status': f'Error: {str(e)}'})
        raise


@shared_task
def process_large_video(post_id, video_file_path):
    """
    Process large video files in the background (compression, transcoding, etc.)
    
    Args:
        post_id: ID of the post
        video_file_path: Path to the video file to process
    """
    # This would contain video processing logic
    # For now, it's a placeholder for future implementation
    pass
