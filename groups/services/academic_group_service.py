from groups.models import Group, Membership, MembershipRole, MembershipStatus


def enroll_user_in_academic_groups(user):
    """
    Automatically enroll a new user in official academic groups based on their course and year.
    
    This function finds all official groups marked for auto-join that match the user's
    course and year, and automatically approves their membership.
    
    Args:
        user: The User instance to enroll in academic groups
        
    Returns:
        list: A list of Group objects the user was enrolled in
    """
    enrolled_groups = []
    
    # Only proceed if user has course and year information
    if not user.course or not user.year:
        return enrolled_groups
    
    # Find official groups marked for auto-join that match user's course and year
    matching_groups = Group.objects.filter(
        is_official=True,
        auto_join_on_signup=True,
        course=user.course,
        year=user.year
    )
    
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
