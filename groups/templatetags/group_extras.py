from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Template filter to get a value from a dictionary by key.
    Usage: {{ my_dict|get_item:key }}
    """
    if not isinstance(dictionary, dict):
        return 0
    if key in dictionary:
        return dictionary[key]
    str_key = str(key)
    if str_key in dictionary:
        return dictionary[str_key]
    if isinstance(key, str) and key.isdigit():
        int_key = int(key)
        if int_key in dictionary:
            return dictionary[int_key]
    return 0


@register.filter
def get_activity(group_activity, key):
    """
    Template filter to safely get group activity dict by group_id.
    Usage: {{ group_activity|get_activity:group.id }}
    """
    default = {'announcement': 0, 'post': 0, 'total': 0}
    if not isinstance(group_activity, dict):
        return default
    act = group_activity.get(key)
    if act is None:
        act = group_activity.get(str(key))
    if act is None and isinstance(key, str) and key.isdigit():
        act = group_activity.get(int(key))
    if isinstance(act, dict):
        return act
    return default



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
