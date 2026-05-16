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
