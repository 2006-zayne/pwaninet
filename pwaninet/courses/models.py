from django.db import models
from django.utils.text import slugify


class School(models.Model):
    name = models.CharField(max_length=200, unique=True)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True, null=True)
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
    level = models.PositiveIntegerField()
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
    name = models.CharField(max_length=30)
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name='courses',
        null=True,
        blank=True
    )

    def __str__(self):
        return self.name


class Unit(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')
    year = models.ForeignKey(Year, on_delete=models.CASCADE, null=True, blank=True, related_name='units')

    def __str__(self):
        return self.name
