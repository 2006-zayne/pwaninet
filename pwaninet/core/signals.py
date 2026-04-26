# signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import User
from groups.models import Group, Membership, MembershipRole, MembershipStatus

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