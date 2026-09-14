from django.test import TestCase
from .models import Course, Year, Unit


class CourseModelTest(TestCase):
    """Test cases for Course model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
    
    def test_course_creation(self):
        """Test that a course can be created"""
        self.assertEqual(self.course.name, 'Computer Science')
    
    def test_course_str(self):
        """Test course string representation"""
        self.assertEqual(str(self.course), 'Computer Science')


class YearModelTest(TestCase):
    """Test cases for Year model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
    
    def test_year_creation(self):
        """Test that a year can be created"""
        self.assertEqual(self.year.course, self.course)
        self.assertEqual(self.year.level, 1)
    
    def test_year_str(self):
        """Test year string representation"""
        self.assertEqual(str(self.year), 'Computer Science - Year 1')
    
    def test_unique_year(self):
        """Test that duplicate years are prevented"""
        Year.objects.create(course=self.course, level=2)
        
        with self.assertRaises(Exception):
            Year.objects.create(course=self.course, level=2)
    
    def test_year_ordering(self):
        """Test that years are ordered by level"""
        Year.objects.create(course=self.course, level=3)
        Year.objects.create(course=self.course, level=2)
        
        years = list(Year.objects.filter(course=self.course))
        self.assertEqual(years[0].level, 1)
        self.assertEqual(years[1].level, 2)
        self.assertEqual(years[2].level, 3)


class UnitModelTest(TestCase):
    """Test cases for Unit model"""
    
    def setUp(self):
        """Set up test data"""
        self.course = Course.objects.create(name='Computer Science')
        self.year = Year.objects.create(course=self.course, level=1)
        self.unit = Unit.objects.create(
            code='CS101',
            name='Introduction to Computer Science',
            course=self.course,
            year=self.year
        )
    
    def test_unit_creation(self):
        """Test that a unit can be created"""
        self.assertEqual(self.unit.code, 'CS101')
        self.assertEqual(self.unit.name, 'Introduction to Computer Science')
        self.assertEqual(self.unit.course, self.course)
        self.assertEqual(self.unit.year, self.year)
    
    def test_unit_str(self):
        """Test unit string representation"""
        self.assertEqual(str(self.unit), 'Introduction to Computer Science')
    
    def test_unique_unit_code(self):
        """Test that unit codes are unique"""
        with self.assertRaises(Exception):
            Unit.objects.create(
                code='CS101',
                name='Another Unit',
                course=self.course
            )
    
    def test_unit_without_year(self):
        """Test that a unit can be created without a year"""
        unit = Unit.objects.create(
            code='CS200',
            name='Advanced Computer Science',
            course=self.course
        )
        self.assertEqual(unit.code, 'CS200')
        self.assertIsNone(unit.year)


from django.core.management import call_command
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from .models import School, Department, Programme, OfficialSchoolCode, AcademicLevelType


class StatutoryAcademicHierarchyTest(TestCase):
    """Test cases for statutory Pwani University School, Department, and Programme models."""

    def setUp(self):
        self.spas = School.objects.create(
            code=OfficialSchoolCode.SPAS,
            name="School of Pure and Applied Sciences"
        )
        self.sbe = School.objects.create(
            code=OfficialSchoolCode.SBE,
            name="School of Business and Economics"
        )
        self.comp_dept = Department.objects.create(
            code="COMP",
            name="Department of Computing",
            school=self.spas
        )

    def test_school_creation_and_str(self):
        """Verify school string representation and slug generation."""
        self.assertEqual(str(self.spas), "SPAS - School of Pure and Applied Sciences")
        self.assertEqual(self.spas.slug, "school-of-pure-and-applied-sciences")

    def test_department_creation_and_str(self):
        """Verify department string representation and slug."""
        self.assertEqual(str(self.comp_dept), "Department of Computing (SPAS)")
        self.assertEqual(self.comp_dept.slug, "spas-department-of-computing")

    def test_programme_creation_and_validation(self):
        """Verify programme creation with clean() validation."""
        prog = Programme.objects.create(
            code="BSC-CS",
            name="Bachelor of Science in Computer Science",
            school=self.spas,
            department=self.comp_dept,
            academic_level=AcademicLevelType.BACHELOR,
            duration_years=4
        )
        self.assertEqual(str(prog), "BSC-CS - Bachelor of Science in Computer Science (Undergraduate Degree (Bachelor))")
        self.assertEqual(prog.slug, "bsc-cs-bachelor-of-science-in-computer-science")

    def test_cross_school_mismatch_raises_validation_error(self):
        """Verify that associating a department with a mismatched school raises a ValidationError."""
        prog = Programme(
            code="BSC-CS-BAD",
            name="BSc CS in Wrong School",
            school=self.sbe,  # SBE while department belongs to SPAS!
            department=self.comp_dept,
            academic_level=AcademicLevelType.BACHELOR,
            duration_years=4
        )
        with self.assertRaises(ValidationError):
            prog.clean()

    def test_school_protection_on_deletion(self):
        """Verify models.PROTECT prevents deleting a school that has active departments."""
        with self.assertRaises(ProtectedError):
            self.spas.delete()

    def test_department_protection_on_deletion(self):
        """Verify models.PROTECT prevents deleting a department that has active programmes."""
        Programme.objects.create(
            code="BSC-CS",
            name="Bachelor of Science in Computer Science",
            school=self.spas,
            department=self.comp_dept,
            academic_level=AcademicLevelType.BACHELOR,
            duration_years=4
        )
        with self.assertRaises(ProtectedError):
            self.comp_dept.delete()


class SeedStatutoryAcademicCoreCommandTest(TestCase):
    """Test verification of the statutory core academic seed command."""

    def test_seed_statutory_academic_core_execution(self):
        """Execute the command and verify all schools, departments, and programmes."""
        call_command("seed_statutory_academic_core")

        # 1. Verify 7 Statutory Schools
        self.assertEqual(School.objects.count(), 7)
        for code in [
            OfficialSchoolCode.SEDU, OfficialSchoolCode.SHSS, OfficialSchoolCode.SPAS,
            OfficialSchoolCode.SAAB, OfficialSchoolCode.SEES, OfficialSchoolCode.SHHS,
            OfficialSchoolCode.SBE
        ]:
            self.assertTrue(School.objects.filter(code=code).exists())

        # 2. Verify Statutory Departments
        self.assertEqual(Department.objects.count(), 27)

        # 3. Verify Audited Programmes Count (130+ programmes)
        self.assertGreaterEqual(Programme.objects.count(), 130)

        # 4. Verify Realignments
        # Realignment 1: Fashion Design -> TECH (SPAS)
        fdgm_prog = Programme.objects.get(code="DIP-FDGM")
        self.assertEqual(fdgm_prog.department.code, "TECH")
        self.assertEqual(fdgm_prog.school.code, OfficialSchoolCode.SPAS)

        # Realignment 2: Cosmetology -> TECH (SPAS)
        cosm_prog = Programme.objects.get(code="DIP-COSM")
        self.assertEqual(cosm_prog.department.code, "TECH")
        self.assertEqual(cosm_prog.school.code, OfficialSchoolCode.SPAS)

        # Realignment 3: Marine Engineering -> MRFS (SEES)
        mare_prog = Programme.objects.get(code="DIP-MARE")
        self.assertEqual(mare_prog.department.code, "MRFS")
        self.assertEqual(mare_prog.school.code, OfficialSchoolCode.SEES)

        # Realignment 4: Multidisciplinary Studies -> SPAS-ID
        gen_prog = Programme.objects.get(code="BSC-GEN")
        self.assertEqual(gen_prog.department.code, "SPAS-ID")
        self.assertEqual(gen_prog.school.code, OfficialSchoolCode.SPAS)

        # 5. Verify Idempotence (Running again updates without duplication)
        call_command("seed_statutory_academic_core")
        self.assertEqual(School.objects.count(), 7)
        self.assertEqual(Department.objects.count(), 27)

