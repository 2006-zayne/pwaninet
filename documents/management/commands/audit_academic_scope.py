"""Audit academic catalogue scope without writing any data.

Reports how existing canonical (documents.*) and legacy (courses.*) records
map to institutions through the Faculty → School → Department → Programme
hierarchy. Orphaned, conflicting, or ambiguous records are reported and left
unmapped — this command never assigns, creates, or modifies records.
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Report institution mapping coverage for academic catalogue and student records (read-only)."

    def handle(self, *args, **options):
        from documents.academic.models import Faculty, School, Department, Programme
        from django.contrib.auth import get_user_model

        User = get_user_model()

        faculties = list(Faculty.objects.select_related('institution').all())
        mapped = [f for f in faculties if f.institution_id]
        unmapped = [f for f in faculties if not f.institution_id]
        self.stdout.write(f"Faculties: {len(faculties)} total, {len(mapped)} mapped, {len(unmapped)} unmapped")
        for f in unmapped:
            self.stdout.write(f"  UNMAPPED faculty id={f.id} code={f.code} name={f.name}")

        schools = School.objects.select_related('faculty__institution').all()
        orphan_schools = [s for s in schools if not getattr(getattr(s, 'faculty', None), 'institution_id', None)]
        self.stdout.write(f"Schools: {schools.count()} total, {len(orphan_schools)} without institution scope")

        departments = Department.objects.select_related('school__faculty__institution').all()
        orphan_depts = [d for d in departments if d.get_institution() is None]
        self.stdout.write(f"Departments: {departments.count()} total, {len(orphan_depts)} without institution scope")

        programmes = list(Programme.objects.select_related(
            'department__school__faculty__institution').filter(is_active=True))
        orphan_progs = [p for p in programmes if p.get_institution() is None]
        self.stdout.write(
            f"Active programmes: {len(programmes)} total, {len(orphan_progs)} without institution scope")
        for p in orphan_progs[:50]:
            self.stdout.write(f"  UNMAPPED programme id={p.id} code={p.code} name={p.name}")

        users_with_programme = User.objects.filter(programme__isnull=False).select_related(
            'institution', 'programme__department__school__faculty__institution')
        mismatched = []
        no_institution = 0
        for u in users_with_programme:
            derived = None
            try:
                derived = u.get_programme_institution()
            except Exception:
                derived = None
            if u.institution_id is None:
                no_institution += 1
            elif derived is not None and derived.pk != u.institution_id:
                mismatched.append(u.id)
        self.stdout.write(
            f"Users with programme: {users_with_programme.count()} total, "
            f"{no_institution} without explicit institution, {len(mismatched)} mismatched")
        if mismatched:
            self.stdout.write(f"  MISMATCHED user ids (sample): {mismatched[:50]}")

        legacy_users = User.objects.filter(course__isnull=False).count()
        legacy_no_canonical = User.objects.filter(
            course__isnull=False, programme__isnull=True).count()
        self.stdout.write(
            f"Legacy course users: {legacy_users} total, {legacy_no_canonical} without canonical programme")

        self.stdout.write(self.style.SUCCESS("Audit complete. No records were created or modified."))
