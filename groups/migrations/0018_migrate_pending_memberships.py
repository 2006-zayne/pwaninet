from django.db import migrations

def forwards_func(apps, schema_editor):
    Membership = apps.get_model('groups', 'Membership')
    GroupJoinRequest = apps.get_model('groups', 'GroupJoinRequest')
    
    # 1. Pending memberships: convert to GroupJoinRequest if not exists
    for m in Membership.objects.filter(status='PENDING'):
        if not GroupJoinRequest.objects.filter(user=m.user, group=m.group, status='PENDING').exists():
            GroupJoinRequest.objects.create(
                user=m.user,
                group=m.group,
                status='PENDING',
                created_at=m.joined_at
            )
            
    # 2. Rejected memberships: convert to GroupJoinRequest with REJECTED
    for m in Membership.objects.filter(status='REJECTED'):
        if not GroupJoinRequest.objects.filter(user=m.user, group=m.group).exists():
            GroupJoinRequest.objects.create(
                user=m.user,
                group=m.group,
                status='REJECTED',
                created_at=m.joined_at
            )

def backwards_func(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('groups', '0017_group_academic_level_group_programme_and_more'),
    ]

    operations = [
        migrations.RunPython(forwards_func, backwards_func),
    ]
