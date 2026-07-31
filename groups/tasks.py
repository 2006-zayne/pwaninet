from celery import shared_task
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from groups.services.academic_group_service import enroll_user_in_academic_groups
import logging

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
        
        # Only proceed if user has course and year information
        if not user.course or not user.year:
            logger.info(f"User {user_id} has no course/year information, skipping auto-group join")
            return
        
        # Try the new service-based approach first
        enrolled_groups = enroll_user_in_academic_groups(user)
        
        # Fallback: if no auto-join groups exist, use the old naming convention approach
        # This ensures backwards compatibility while transitioning to the new system
        if not enrolled_groups:
            # Standardize the naming convention for official groups
            # e.g., "Computer Science - Year 1"
            target_group_name = f"{user.course.name} - Year {user.year.level}"
            
            # Logic: Search for the group. If it doesn't exist, create it.
            # 'get_or_create' returns a tuple: (object, created_bool)
            group, created_group = Group.objects.get_or_create(
                name=target_group_name,
                defaults={
                    'description': f"Official academic hub for {target_group_name} students.",
                    'is_official': True,
                    'auto_join_on_signup': True,  # Enable auto-join for backwards compatibility
                    'course': user.course,
                    'year': user.year
                }
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
