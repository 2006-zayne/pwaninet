from django.db import models
from django.utils.text import slugify
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError


class OfficialSchoolCode(models.TextChoices):
    SEDU = 'SEDU', 'School of Education'
    SHSS = 'SHSS', 'School of Humanities and Social Sciences'
    SPAS = 'SPAS', 'School of Pure and Applied Sciences'
    SAAB = 'SAAB', 'School of Agricultural Sciences and Agribusiness'
    SEES = 'SEES', 'School of Environmental and Earth Sciences'
    SHHS = 'SHHS', 'School of Health and Human Sciences'
    SBE = 'SBE', 'School of Business and Economics'


class AcademicLevelType(models.TextChoices):
    ARTISAN = 'ARTISAN', 'TVET Artisan Certificate'
    CRAFT_CERT = 'CRAFT_CERT', 'TVET Craft Certificate'
    DIPLOMA = 'DIPLOMA', 'Diploma / TVET Diploma'
    BACHELOR = 'BACHELOR', 'Undergraduate Degree (Bachelor)'
    POSTGRAD_DIPLOMA = 'POSTGRAD_DIPLOMA', 'Postgraduate Diploma'
    MASTERS = 'MASTERS', 'Masters'
    PHD = 'PHD', 'Doctor of Philosophy (PhD)'


class Faculty(models.Model):
    """Represents a faculty (legacy abstraction)."""
    
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


class School(models.Model):
    """Pwani University Official School Tier (Statutory Academic Division)."""
    
    code = models.CharField(
        max_length=10,
        unique=True,
        choices=OfficialSchoolCode.choices,
        default=OfficialSchoolCode.SPAS,
        help_text="Official Pwani University school code"
    )
    name = models.CharField(
        max_length=200, 
        unique=True,
        help_text="Full name of the school"
    )
    slug = models.SlugField(
        max_length=220, 
        unique=True, 
        blank=True,
        help_text="URL-friendly slug"
    )
    description = models.TextField(
        blank=True, 
        default='',
        help_text="Description of the school"
    )
    # Legacy link kept for schema backward compatibility
    department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legacy_schools',
        help_text="Legacy link to Department model"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this school is currently active"
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
        verbose_name = "School"
        verbose_name_plural = "Schools"


class Department(models.Model):
    """Academic Department hosted within a Pwani University School."""
    
    code = models.CharField(
        max_length=20,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9\-]{2,10}$', 'Code must be 2-10 uppercase alphanumeric or hyphen characters.')],
        help_text="Unique department code (e.g., 'COMP', 'EDCI')"
    )
    name = models.CharField(
        max_length=200,
        help_text="Full name of the department"
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        blank=True,
        help_text="URL-friendly slug"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='departments',
        help_text="The school this department belongs to"
    )
    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='departments',
        help_text="Legacy faculty this department belongs to"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of the department"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this department is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        school_label = f" ({self.school.code})" if self.school else ""
        return f"{self.name}{school_label}"

    def save(self, *args, **kwargs):
        if not self.slug:
            prefix = f"{self.school.code}-" if self.school else ""
            self.slug = slugify(f"{prefix}{self.name}")
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['code']
        unique_together = [['school', 'name']]


class Programme(models.Model):
    """Academic Programme accredited under a Pwani University Department."""
    
    code = models.CharField(
        max_length=30,
        unique=True,
        validators=[RegexValidator(r'^[A-Z0-9\-]{3,30}$', 'Programme code must be uppercase alphanumeric with dashes.')],
        help_text="Official PU Programme Code (e.g., 'BSC-CS', 'BED-SCI')"
    )
    name = models.CharField(
        max_length=255,
        help_text="Full programme title"
    )
    slug = models.SlugField(
        max_length=280,
        unique=True,
        blank=True,
        help_text="URL-friendly slug"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name='programmes',
        help_text="Parent School administering this programme"
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name='programmes',
        help_text="Department hosting this programme"
    )
    academic_level = models.CharField(
        max_length=25,
        choices=AcademicLevelType.choices,
        default=AcademicLevelType.BACHELOR,
        help_text="Statutory academic level"
    )
    duration_years = models.PositiveSmallIntegerField(
        default=4,
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
        unique_together = [['name', 'academic_level']]
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['school']),
            models.Index(fields=['department']),
            models.Index(fields=['academic_level']),
            models.Index(fields=['is_active']),
        ]

    def clean(self):
        super().clean()
        if self.department_id and self.school_id:
            if self.department.school_id and self.department.school_id != self.school_id:
                raise ValidationError({
                    'department': f"Department '{self.department.name}' does not roll up to {self.school.code}."
                })

    def save(self, *args, **kwargs):
        if self.department_id and not self.school_id:
            self.school = self.department.school
        self.full_clean()
        if not self.slug:
            self.slug = slugify(f"{self.code}-{self.name}")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.code} - {self.name} ({self.get_academic_level_display()})"


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
    programme = models.ForeignKey(
        Programme,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='legacy_courses',
        help_text="Link to statutory Programme model"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.SET_NULL,
        related_name='courses',
        null=True,
        blank=True,
        help_text="Parent School"
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
        on_delete=models.SET_NULL,
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
