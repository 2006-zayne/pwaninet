"""Academic domain models for university structure.

These models represent the hierarchical academic structure of the university
and are designed to be reusable across PwaniNet modules.

Hierarchy:
Faculty → School → Department → Programme → Academic Unit → Semester → Academic Year
"""

from django.db import models
from django.core.validators import RegexValidator
from django.utils.text import slugify


class AcademicYear(models.Model):
    """Represents an academic year (e.g., 2024/2025)."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        help_text="Unique identifier for the academic year (e.g., '2024/2025')"
    )
    name = models.CharField(
        max_length=50,
        help_text="Human-readable name (e.g., '2024/2025')"
    )
    start_date = models.DateField(help_text="Start date of the academic year")
    end_date = models.DateField(help_text="End date of the academic year")
    is_current = models.BooleanField(
        default=False,
        help_text="Whether this is the current academic year"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-start_date']
        verbose_name = "Academic Year"
        verbose_name_plural = "Academic Years"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['is_current']),
        ]
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        # Ensure only one current academic year
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class Semester(models.Model):
    """Represents a semester within an academic year."""
    
    SEMESTER_CHOICES = [
        (1, 'Semester 1'),
        (2, 'Semester 2'),
        (3, 'Semester 3'),
    ]
    
    number = models.PositiveSmallIntegerField(
        choices=SEMESTER_CHOICES,
        help_text="Semester number (1, 2, or 3)"
    )
    academic_year = models.ForeignKey(
        AcademicYear,
        on_delete=models.CASCADE,
        related_name='semesters',
        help_text="The academic year this semester belongs to"
    )
    start_date = models.DateField(help_text="Start date of the semester")
    end_date = models.DateField(help_text="End date of the semester")
    is_current = models.BooleanField(
        default=False,
        help_text="Whether this is the current semester"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['academic_year', 'number']
        unique_together = ['number', 'academic_year']
        verbose_name = "Semester"
        verbose_name_plural = "Semesters"
        indexes = [
            models.Index(fields=['academic_year', 'number']),
            models.Index(fields=['is_current']),
        ]
    
    def __str__(self):
        return f"{self.get_number_display()} - {self.academic_year}"
    
    def save(self, *args, **kwargs):
        # Ensure only one current semester
        if self.is_current:
            Semester.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


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
    
    class Meta:
        ordering = ['code']
        verbose_name = "Faculty"
        verbose_name_plural = "Faculties"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class School(models.Model):
    """Represents a school within a faculty (e.g., School of Computing)."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{2,10}$', 'Code must be uppercase letters only')],
        help_text="Unique school code (e.g., 'COMP')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the school"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='schools',
        help_text="The faculty this school belongs to"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the school"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "School"
        verbose_name_plural = "Schools"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
            models.Index(fields=['faculty']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Department(models.Model):
    """Represents a department within a school."""
    
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
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='departments',
        help_text="The school this department belongs to"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the department"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "Department"
        verbose_name_plural = "Departments"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
            models.Index(fields=['school']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Programme(models.Model):
    """Represents an academic programme (e.g., BSc Computer Science)."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9]{2,20}$', 'Code must be alphanumeric uppercase')],
        help_text="Unique programme code (e.g., 'BSC-CS')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the programme"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.CASCADE,
        related_name='programmes',
        help_text="The department this programme belongs to"
    )
    degree_type = models.CharField(
        max_length=50,
        help_text="Type of degree (e.g., 'Bachelor', 'Master', 'PhD')"
    )
    duration_years = models.PositiveSmallIntegerField(
        help_text="Duration of the programme in years"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the programme"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this programme is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "Programme"
        verbose_name_plural = "Programmes"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
            models.Index(fields=['department']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class AcademicUnit(models.Model):
    """Represents an academic unit/course (e.g., CSC221 Database Systems).
    
    This is a shared entity that can belong to multiple programmes.
    Use junction tables to map programmes to units.
    """
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z]{3}\d{3}$', 'Code must be like CSC221')],
        help_text="Unique unit code (e.g., 'CSC221')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the academic unit"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text="URL-friendly slug"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the academic unit"
    )
    credit_hours = models.PositiveSmallIntegerField(
        default=3,
        help_text="Credit hours for this unit"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this unit is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['code']
        verbose_name = "Academic Unit"
        verbose_name_plural = "Academic Units"
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.code} {self.name}")
        super().save(*args, **kwargs)


class ProgrammeUnit(models.Model):
    """Junction table mapping Programmes to Academic Units.
    
    Many programmes can share the same unit, and one programme can have many units.
    This junction table prevents duplicate unit creation.
    """
    
    programme = models.ForeignKey(
        Programme,
        on_delete=models.CASCADE,
        related_name='programme_units'
    )
    academic_unit = models.ForeignKey(
        AcademicUnit,
        on_delete=models.CASCADE,
        related_name='programme_units'
    )
    semester = models.ForeignKey(
        Semester,
        on_delete=models.CASCADE,
        related_name='programme_units',
        help_text="The semester this unit is offered in this programme"
    )
    is_core = models.BooleanField(
        default=True,
        help_text="Whether this is a core unit for the programme"
    )
    is_elective = models.BooleanField(
        default=False,
        help_text="Whether this is an elective unit"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['programme', 'academic_unit', 'semester']
        verbose_name = "Programme Unit"
        verbose_name_plural = "Programme Units"
        indexes = [
            models.Index(fields=['programme']),
            models.Index(fields=['academic_unit']),
            models.Index(fields=['semester']),
        ]
    
    def __str__(self):
        return f"{self.programme.code} - {self.academic_unit.code} ({self.semester})"
