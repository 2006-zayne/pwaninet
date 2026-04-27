from django.core.management.base import BaseCommand
from django.db.models import Q, Count
from groups.models import Group, Membership, MembershipRole, MembershipStatus


class Command(BaseCommand):
    help = 'Assign admins to groups that have no admins'

    def handle(self, *args, **options):
        # Find all groups with no approved admins
        groups_without_admins = Group.objects.annotate(
            admin_count=Count('memberships', filter=Q(
                memberships__role=MembershipRole.ADMIN,
                memberships__status=MembershipStatus.APPROVED
            ))
        ).filter(admin_count=0)

        if not groups_without_admins.exists():
            self.stdout.write(self.style.SUCCESS('All groups have admins.'))
            return

        self.stdout.write(f'Found {groups_without_admins.count()} groups without admins.')

        for group in groups_without_admins:
            # Try to find a moderator first
            moderator = Membership.objects.filter(
                group=group,
                role=MembershipRole.MODERATOR,
                status=MembershipStatus.APPROVED
            ).first()

            if moderator:
                moderator.role = MembershipRole.ADMIN
                moderator.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Promoted moderator {moderator.user.username} to admin for group "{group.name}"'
                    )
                )
                continue

            # If no moderator, find the most recent member
            member = Membership.objects.filter(
                group=group,
                role=MembershipRole.MEMBER,
                status=MembershipStatus.APPROVED
            ).order_by('-id').first()

            if member:
                member.role = MembershipRole.ADMIN
                member.save()
                self.stdout.write(
                    self.style.WARNING(
                        f'Promoted member {member.user.username} to admin for group "{group.name}" (no moderators found)'
                    )
                )
                continue

            # If no members at all, skip
            self.stdout.write(
                self.style.ERROR(
                    f'Group "{group.name}" has no members. Cannot assign admin.'
                )
            )

        self.stdout.write(self.style.SUCCESS('Admin assignment complete.'))
