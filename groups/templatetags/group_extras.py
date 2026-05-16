from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a value from a dictionary by key.
    Usage: {{ my_dict|get_item:key }}
    """
    if dictionary is None:
        return 0
    return dictionary.get(key, 0)


@register.simple_tag
def get_user_groups(user):
    """
    Template tag to get all groups a user is a member of.
    Usage: {% get_user_groups request.user as user_groups %}
    """
    from groups.models import Membership, MembershipStatus
    group_ids = Membership.objects.filter(
        user=user,
        status=MembershipStatus.APPROVED
    ).values_list('group_id', flat=True)
    from groups.models import Group
    return Group.objects.filter(id__in=group_ids)
