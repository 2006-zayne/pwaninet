from celery import shared_task
from groups.models import Group, Membership, MembershipRole, MembershipStatus, AnnouncementAttachment
from groups.services.academic_group_service import enroll_user_in_academic_groups
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import logging
import sys

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2)
def auto_join_course_group_task(self, user_id):
    """
    Asynchronously enroll a new user in official academic groups based on their course and year.
    
    This task runs in the background to prevent blocking the main thread and causing timeouts
    during user signup. It uses the service-based approach with database flags and falls back
    to creating groups if none exist.
    
    Args:
        user_id: The ID of the user to enroll in academic groups
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        
        # Check if user has academic information
        has_academic_info = bool(
            (user.programme and user.academic_level) or
            (user.course and user.year)
        )
        if not has_academic_info:
            logger.info(f"User {user_id} has no course/year or programme/level information, skipping auto-group join")
            return
        
        # Try the new service-based approach first
        enrolled_groups = enroll_user_in_academic_groups(user)
        
        # Fallback: if no auto-join groups exist, use standardized naming convention approach
        if not enrolled_groups:
            if user.programme and user.academic_level:
                target_group_name = f"{user.programme.name} - {user.academic_level.name}"
                defaults = {
                    'description': f"Official academic hub for {target_group_name} students.",
                    'is_official': True,
                    'auto_join_on_signup': True,
                    'programme': user.programme,
                    'academic_level': user.academic_level,
                    'course': user.course,
                    'year': user.year
                }
            else:
                target_group_name = f"{user.course.name} - Year {user.year.level}"
                defaults = {
                    'description': f"Official academic hub for {target_group_name} students.",
                    'is_official': True,
                    'auto_join_on_signup': True,
                    'course': user.course,
                    'year': user.year
                }
            
            # Logic: Search for the group. If it doesn't exist, create it.
            group, created_group = Group.objects.get_or_create(
                name=target_group_name,
                defaults=defaults
            )
            
            if created_group:
                logger.info(f"Created new academic group: {target_group_name}")
            
            # Create membership instead of using direct M2M
            # Use APPROVED status for official academic groups to allow immediate access
            membership, created_membership = Membership.objects.get_or_create(
                user=user,
                group=group,
                defaults={
                    'role': MembershipRole.MEMBER,
                    'status': MembershipStatus.APPROVED
                }
            )
            
            # If membership already existed but was pending, approve it
            if not created_membership and membership.status == MembershipStatus.PENDING:
                membership.status = MembershipStatus.APPROVED
                membership.save()
                logger.info(f"Approved pending membership for user {user_id} in group {group.id}")
            elif created_membership:
                logger.info(f"Created membership for user {user_id} in group {group.id}")
            else:
                logger.info(f"User {user_id} already has approved membership in group {group.id}")
        else:
            logger.info(f"Enrolled user {user_id} in {len(enrolled_groups)} existing academic groups")
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for auto-group join")
    except Exception as e:
        logger.error(f"Error in auto-group join task for user {user_id}: {e}")
        # Retry the task with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def generate_attachment_thumbnail(attachment_id):
    """
    Generate thumbnail for announcement attachments (images only).
    
    This task creates optimized thumbnails for image attachments to improve
    loading performance and provide consistent sizing in the feed.
    
    Args:
        attachment_id: ID of the AnnouncementAttachment to generate thumbnail for
    """
    try:
        attachment = AnnouncementAttachment.objects.get(id=attachment_id)
        
        # Skip if attachment is not an image
        if not attachment.file or not attachment.file.name.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            logger.info(f"Attachment {attachment_id} is not an image, skipping thumbnail generation")
            return
        
        # Open the image
        img = Image.open(attachment.file.path)
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize to thumbnail dimensions (max 800x600)
        max_width, max_height = 800, 600
        if img.width > max_width or img.height > max_height:
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        # Create thumbnail
        output = BytesIO()
        img.save(output, format='JPEG', quality=85, optimize=True)
        output.seek(0)
        
        # Generate thumbnail filename
        original_name = attachment.file.name.split('/')[-1]
        thumbnail_name = f"thumb_{original_name.rsplit('.', 1)[0]}.jpg"
        
        # Save thumbnail to the model
        attachment.thumbnail.save(
            thumbnail_name,
            InMemoryUploadedFile(
                output, 'ImageField', thumbnail_name, 'image/jpeg',
                sys.getsizeof(output), None
            ),
            save=True
        )
        
        logger.info(f"Generated thumbnail for attachment {attachment_id}: {thumbnail_name}")
        
    except AnnouncementAttachment.DoesNotExist:
        logger.error(f"Attachment {attachment_id} not found for thumbnail generation")
    except Exception as e:
        logger.error(f"Error generating thumbnail for attachment {attachment_id}: {e}")


@shared_task
def generate_announcement_attachments_thumbnails(announcement_id):
    """
    Generate thumbnails for all attachments of an announcement.
    
    This is a convenience task that triggers thumbnail generation for all
    attachments of a specific announcement.
    
    Args:
        announcement_id: ID of the announcement
    """
    from groups.models import Announcement
    
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        
        for attachment in announcement.attachments.all():
            generate_attachment_thumbnail.delay(attachment.id)
            
        logger.info(f"Triggered thumbnail generation for {announcement.attachments.count()} attachments of announcement {announcement_id}")
        
    except Announcement.DoesNotExist:
        logger.error(f"Announcement {announcement_id} not found for batch thumbnail generation")
    except Exception as e:
        logger.error(f"Error in batch thumbnail generation for announcement {announcement_id}: {e}")
