from django.core.management.base import BaseCommand
from django.db.models import Q
from users.models import User
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from groups.services.academic_group_service import enroll_user_in_academic_groups


class Command(BaseCommand):
    help = 'Enroll existing users in their academic groups based on course and year'

    def handle(self, *args, **options):
        # Find all users who have course and year but might not be in groups
        users_to_enroll = User.objects.filter(
            course__isnull=False,
            year__isnull=False
        )

        total_users = users_to_enroll.count()
        enrolled_count = 0
        skipped_count = 0

        self.stdout.write(f'Found {total_users} users with course and year information.')

        for user in users_to_enroll:
            # Check if user is already enrolled in any matching group
            existing_membership = Membership.objects.filter(
                user=user,
                group__course=user.course,
                group__year=user.year,
                status=MembershipStatus.APPROVED
            ).exists()

            if existing_membership:
                skipped_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipping {user.username} - already enrolled in group for {user.course.name} Year {user.year.level}'
                    )
                )
                continue

            # Try to enroll user using the service
            enrolled_groups = enroll_user_in_academic_groups(user)

            if enrolled_groups:
                enrolled_count += 1
                group_names = [group.name for group in enrolled_groups]
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Enrolled {user.username} in: {", ".join(group_names)}'
                    )
                )
            else:
                # Fallback: create group if none exists
                target_group_name = f"{user.course.name} - Year {user.year.level}"
                
                group, created_group = Group.objects.get_or_create(
                    name=target_group_name,
                    defaults={
                        'description': f"Official academic hub for {target_group_name} students.",
                        'is_official': True,
                        'auto_join_on_signup': True,
                        'course': user.course,
                        'year': user.year
                    }
                )
                
                if created_group:
                    self.stdout.write(
                        self.style.WARNING(
                            f'Created new group: {target_group_name}'
                        )
                    )
                
                # Create membership
                membership, created_membership = Membership.objects.get_or_create(
                    user=user,
                    group=group,
                    defaults={
                        'role': MembershipRole.MEMBER,
                        'status': MembershipStatus.APPROVED
                    }
                )
                
                if created_membership:
                    enrolled_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Enrolled {user.username} in {target_group_name}'
                        )
                    )
                elif membership.status != MembershipStatus.APPROVED:
                    membership.status = MembershipStatus.APPROVED
                    membership.save()
                    enrolled_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Approved membership for {user.username} in {target_group_name}'
                        )
                    )

        self.stdout.write(self.style.SUCCESS('\n=== Summary ==='))
        self.stdout.write(f'Total users processed: {total_users}')
        self.stdout.write(self.style.SUCCESS(f'Users enrolled: {enrolled_count}'))
        self.stdout.write(self.style.WARNING(f'Users skipped (already enrolled): {skipped_count}'))
        self.stdout.write(self.style.SUCCESS('Enrollment complete.'))
