from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DeviceAccount, User
from .services.device_service import get_or_create_device_id, hash_device_id
from groups.models import Group, Membership, MembershipRole, MembershipStatus


@receiver(user_logged_in)
def track_device_on_login(sender, request, user, **kwargs):
    """
    Automatically create or update DeviceAccount when a user logs in.
    This tracks which accounts have been used on which devices.
    """
    # Try to get device ID from headers first (HTMX requests)
    device_id = request.headers.get('X-Device-ID')
    
    # Fallback to POST data (regular form submissions)
    if not device_id:
        device_id = request.POST.get('device_id')
    
    if device_id:
        # Hash the device ID before storing
        hashed_device_id = hash_device_id(device_id)
        
        # Create or update the DeviceAccount record
        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': request.session.session_key
            }
        )
    else:
        # If no device ID, generate one and store it
        from .services.device_service import generate_device_id
        device_id = generate_device_id()
        hashed_device_id = hash_device_id(device_id)
        DeviceAccount.objects.update_or_create(
            user=user,
            device_id=hashed_device_id,
            defaults={
                'session_key': request.session.session_key
            }
        )


@receiver(user_logged_out)
def clear_session_on_logout(sender, request, user, **kwargs):
    """
    Clear the session key from DeviceAccount when user logs out.
    """
    device_id = get_or_create_device_id(request)
    
    if device_id and user:
        hashed_device_id = hash_device_id(device_id)
        DeviceAccount.objects.filter(
            user=user,
            device_id=hashed_device_id
        ).update(session_key=None)


@receiver(post_save, sender=User)
def auto_join_course_group(sender, instance, created, **kwargs):
    """
    Scans registration data and assigns user to their official 
    Academic Unit Group automatically.
    """
    # Only execute for NEW users who have completed their profile intel
    if created and instance.course and instance.year:
        
        # Standardize the naming convention for official groups
        # e.g., "Computer Science - Year 1"
        target_group_name = f"{instance.course.name} - Year {instance.year.level}"
        
        # Logic: Search for the group. If it doesn't exist, create it.
        # 'get_or_create' returns a tuple: (object, created_bool)
        group, created_group = Group.objects.get_or_create(
            name=target_group_name,
            defaults={
                'description': f"Official academic hub for {target_group_name} operatives.",
                'is_official': True,
                'course': instance.course,
                'year': instance.year
            }
        )
        
        # Create membership instead of using direct M2M
        # Use PENDING status for official groups to require admin approval
        Membership.objects.get_or_create(
            user=instance,
            group=group,
            defaults={
                'role': MembershipRole.MEMBER,
                'status': MembershipStatus.PENDING
            }
        )
