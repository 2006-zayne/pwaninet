from django.db import models


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

    def __str__(self):
        return self.name


class Unit(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='units')
    year = models.ForeignKey(Year, on_delete=models.CASCADE, null=True, blank=True, related_name='units')

    def __str__(self):
        return self.name
