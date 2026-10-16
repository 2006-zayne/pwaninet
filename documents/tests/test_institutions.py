"""Phase 2: Institution foundation — hierarchy-derived scope, no denormalisation."""

from django.core.exceptions import ValidationError
from django.test import TestCase

from documents.academic.models import (
    AcademicLevel,
    Department,
    Faculty,
    Institution,
    Programme,
    School,
)


class InstitutionScopeTest(TestCase):
    def setUp(self):
        self.inst_a = Institution.objects.create(name='Scope University A', short_name='SUA')
        self.inst_b = Institution.objects.create(name='Scope University B', short_name='SUB')
        fac_a = Faculty.objects.create(code='FCA', name='Faculty A', institution=self.inst_a)
        fac_b = Faculty.objects.create(code='FCB', name='Faculty B', institution=self.inst_b)
        sch_a = School.objects.create(code='SHA', name='School A', faculty=fac_a)
        dept_a = Department.objects.create(code='DPA', name='Department A', school=sch_a)
        sch_b = School.objects.create(code='SHB', name='School B', faculty=fac_b)
        dept_b = Department.objects.create(code='DPB', name='Department B', school=sch_b)
        self.prog_a = Programme.objects.create(
            code='PRGA', name='Programme A', department=dept_a,
            degree_type='Bachelor', duration_years=4)
        self.prog_b = Programme.objects.create(
            code='PRGB', name='Programme B', department=dept_b,
            degree_type='Bachelor', duration_years=4)
        # Legacy unmapped catalogue (no institution anywhere in the chain).
        fac_none = Faculty.objects.create(code='FCN', name='Unmapped Faculty')
        sch_none = School.objects.create(code='SHN', name='Unmapped School', faculty=fac_none)
        dept_none = Department.objects.create(code='DPN', name='Unmapped Dept', school=sch_none)
        self.prog_none = Programme.objects.create(
            code='PRGN', name='Unmapped Programme', department=dept_none,
            degree_type='Bachelor', duration_years=4)

    def test_institution_slug_auto_derived(self):
        inst = Institution.objects.create(name='New College of Testing')
        self.assertEqual(inst.slug, 'new-college-of-testing')

    def test_scope_derived_through_hierarchy(self):
        self.assertEqual(self.prog_a.get_institution(), self.inst_a)
        self.assertEqual(self.prog_b.get_institution(), self.inst_b)
        self.assertIsNone(self.prog_none.get_institution())

    def test_programmes_scoped_per_institution(self):
        scoped = Programme.objects.filter(
            is_active=True,
            department__school__faculty__institution=self.inst_a,
        )
        self.assertIn(self.prog_a, scoped)
        self.assertNotIn(self.prog_b, scoped)
        self.assertNotIn(self.prog_none, scoped)

    def test_faculty_institution_nullable_for_legacy(self):
        fac = Faculty.objects.create(code='FCL', name='Legacy Faculty')
        self.assertIsNone(fac.institution)

    def test_user_mismatch_rejected_only_on_definite_conflict(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User(username='scopeuser', institution=self.inst_a, programme=self.prog_b)
        with self.assertRaises(ValidationError):
            user.full_clean(exclude=['password'])
        # Nulls never raise.
        User(username='nullsok', institution=self.inst_a).full_clean(exclude=['password'])
        ok_user = User(username='oksok', institution=self.inst_a, programme=self.prog_a)
        ok_user.full_clean(exclude=['password'])
        # Legacy unmapped programme never raises (ambiguous, left unmapped).
        User(username='unmappedok', institution=self.inst_a,
             programme=self.prog_none).full_clean(exclude=['password'])

    def test_academic_level_compatibility_rule(self):
        from users.forms import InstitutionSetupForm
        level5 = AcademicLevel.objects.create(level=5, name='Year 5')
        form = InstitutionSetupForm(data={
            'institution': str(self.inst_a.id),
            'programme': str(self.prog_a.id),  # duration 4
            'academic_level': str(level5.id),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('academic_level', form.errors)

    def test_inactive_programme_rejected(self):
        from users.forms import InstitutionSetupForm
        self.prog_a.is_active = False
        self.prog_a.save(update_fields=['is_active'])
        form = InstitutionSetupForm(data={
            'institution': str(self.inst_a.id),
            'programme': str(self.prog_a.id),
        })
        self.assertFalse(form.is_valid())
