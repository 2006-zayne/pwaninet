from django.db import migrations


def seed_pwani_university_and_link_data(apps, schema_editor):
    Institution = apps.get_model('documents', 'Institution')
    Faculty = apps.get_model('documents', 'Faculty')
    School = apps.get_model('documents', 'School')
    User = apps.get_model('users', 'User')

    pu, created = Institution.objects.get_or_create(
        name='Pwani University',
        defaults={
            'short_name': 'PU',
            'slug': 'pwani-university',
            'institution_type': 'university',
            'country': 'Kenya',
            'county_or_region': 'Kilifi',
            'city': 'Kilifi',
            'website': 'https://pu.ac.ke',
            'email_domains': 'pu.ac.ke,student.pu.ac.ke',
            'brand_color': '#0d6efd',
            'is_active': True,
        }
    )

    # Link all existing unlinked faculties to Pwani University
    Faculty.objects.filter(institution__isnull=True).update(institution=pu)

    # Link all existing unlinked schools to Pwani University
    School.objects.filter(institution__isnull=True).update(institution=pu)

    # Link all existing users who have a programme to Pwani University
    User.objects.filter(programme__isnull=False, institution__isnull=True).update(institution=pu)


def reverse_func(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0018_institution_brand_color_institution_city_and_more'),
        ('users', '0039_user_institution'),
    ]

    operations = [
        migrations.RunPython(seed_pwani_university_and_link_data, reverse_func),
    ]
