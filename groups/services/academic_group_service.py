from django.db.models import Q
from groups.models import Group, Membership, MembershipRole, MembershipStatus


def enroll_user_in_academic_groups(user):
    """
    Automatically enroll a user in official academic groups based on their
    programme and academic_level (modern) or course and year (legacy).
    
    This function finds all official groups marked for auto-join that match the user's
    academic details, and automatically approves their membership.
    
    Args:
        user: The User instance to enroll in academic groups
        
    Returns:
        list: A list of Group objects the user was enrolled in
    """
    enrolled_groups = []
    
    q_filter = Q()
    has_criteria = False
    
    if getattr(user, 'programme_id', None) and getattr(user, 'academic_level_id', None):
        q_filter |= Q(programme=user.programme, academic_level=user.academic_level)
        has_criteria = True
        
    if getattr(user, 'course_id', None) and getattr(user, 'year_id', None):
        q_filter |= Q(course=user.course, year=user.year)
        has_criteria = True
        
    if not has_criteria:
        return enrolled_groups
    
    # Find official groups marked for auto-join that match user's academic details
    matching_groups = Group.objects.filter(
        is_official=True,
        auto_join_on_signup=True
    ).filter(q_filter)
    
    # Enroll user in each matching group
    for group in matching_groups:
        membership, created = Membership.objects.get_or_create(
            user=user,
            group=group,
            defaults={
                'role': MembershipRole.MEMBER,
                'status': MembershipStatus.APPROVED  # Auto-approve for official academic groups
            }
        )
        
        if created:
            enrolled_groups.append(group)
        elif membership.status != MembershipStatus.APPROVED:
            # Update existing membership to approved
            membership.status = MembershipStatus.APPROVED
            membership.save()
            enrolled_groups.append(group)
    
    return enrolled_groups

