from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator


class Faculty(models.Model):
    """Represents a faculty (e.g., Faculty of Science)."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{2,10}$', 'Code must be uppercase letters only')],
        help_text="Unique faculty code (e.g., 'SCI')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the faculty"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the faculty"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['code']


class Department(models.Model):
    """Represents a department within a faculty."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{2,10}$', 'Code must be uppercase letters only')],
        help_text="Unique department code (e.g., 'CS')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the department"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='departments',
        help_text="The faculty this department belongs to"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the department"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.code} - {self.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['code']


class School(models.Model):
    """Legacy model for backward compatibility.
    
    Deprecated: Use Department instead. This is kept for existing data.
    """
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legacy_schools',
        help_text="Link to new Department model"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['name']


class Year(models.Model):
    """Student year of study (Year 1, Year 2, Year 3, Year 4).
    
    This is different from AcademicYear (2024/2025). This represents
    the student's level in their program.
    """
    level = models.PositiveIntegerField(
        validators=[],
        help_text="Year of study (1, 2, 3, 4, etc.)"
    )
    course = models.ForeignKey(
        'Course', 
        on_delete=models.CASCADE, 
        related_name='years'
    )

    def __str__(self):
        return f"{self.course.name} - Year {self.level}"

    class Meta:
        ordering = ['level']
        unique_together = ['level', 'course']


class Course(models.Model):
    """Represents an academic program/course of study.
    
    This is the student's enrolled program (e.g., BSc Computer Science).
    """
    name = models.CharField(
        max_length=100,
        help_text="Full name of the course/program"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True,
        help_text="Legacy field - use department instead"
    )
    code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True,
        validators=[RegexValidator(r'^[A-Z0-9]{2,20}$', 'Code must be alphanumeric uppercase')],
        help_text="Unique course code (e.g., 'BSC-CS')"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        null=True,
        blank=True,
        help_text="URL-friendly slug"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True,
        help_text="The department this course belongs to"
    )
    degree_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Type of degree (e.g., 'Bachelor', 'Master', 'PhD', 'Diploma')"
    )
    duration_years = models.PositiveSmallIntegerField(
        default=4,
        null=True,
        blank=True,
        help_text="Duration of the course in years"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the course"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this course is currently active"
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,
        blank=True
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['code']


class Unit(models.Model):
    """Legacy model for backward compatibility.
    
    Deprecated: Use CourseAcademicUnit for new relationships. 
    This is kept for existing data.
    """
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')
    year = models.ForeignKey(Year, on_delete=models.CASCADE, null=True, blank=True, related_name='units')

    def __str__(self):
        return self.name


class CourseAcademicUnit(models.Model):
    """Bridge model linking courses to academic units.
    
    This represents which academic units are offered in which courses,
    at which year level and semester. Multiple courses can share the same
    academic unit (e.g., CSC101 is taken by CS, IT, and Comp Education).
    """
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='course_academic_units'
    )
    academic_unit = models.ForeignKey(
        'documents.AcademicUnit',
        on_delete=models.CASCADE,
        related_name='course_units',
        help_text="Reference to the academic unit in documents domain"
    )
    year_level = models.ForeignKey(
        Year,
        on_delete=models.CASCADE,
        related_name='course_academic_units',
        help_text="The year level this unit is offered in this course"
    )
    semester = models.ForeignKey(
        'documents.Semester',
        on_delete=models.CASCADE,
        related_name='course_units',
        help_text="The semester this unit is offered in this course"
    )
    is_core = models.BooleanField(
        default=True,
        help_text="Whether this is a core unit for the course"
    )
    is_elective = models.BooleanField(
        default=False,
        help_text="Whether this is an elective unit"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.code} - {self.academic_unit.code} (Year {self.year_level.level}, {self.semester})"

    class Meta:
        ordering = ['course', 'year_level', 'semester']
        unique_together = ['course', 'academic_unit', 'year_level', 'semester']
        indexes = [
            models.Index(fields=['course']),
            models.Index(fields=['academic_unit']),
            models.Index(fields=['year_level']),
            models.Index(fields=['semester']),
        ]
