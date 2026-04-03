from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

class Year(models.Model):
    level = models.PositiveIntegerField()
    
    course = models.ForeignKey(
        'Course', 
        on_delete=models.CASCADE, 
        related_name='years'
    )# related_name='years' allows Course.years.all() to work

    def __str__(self):
        return f"{self.course.name} - Year {self.level}"

    class Meta:
      
        ordering = ['level'] #  Ensures Year 1 comes before Year 2 in the dropdowns
        unique_together = ['level', 'course']   # Prevents duplicate years for the same course (e.g., two "Year 1"s for CS)
       #pass

class Course(models.Model):
    name = models.CharField(max_length=30)
    #unit = models.ForeignKey('Unit' , on_delete=models.CASCADE )
    #year = models.ForeignKey(Year , on_delete=models.CASCADE )

    def __str__(self):
        return self.name
    

class Unit(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    course = models.ForeignKey(Course, on_delete=models.CASCADE ,related_name='units')
    year = models.ForeignKey(Year, on_delete = models.CASCADE ,null=True , blank=True , related_name= 'units')

    def __str__(self):
        return self.name




class User(AbstractUser):
    first_name = models.CharField(max_length=200 ,null=True,blank=True)
    second_name = models.CharField(max_length=200 ,null=True,blank=True)
    last_name = models.CharField(max_length=200 ,null=True,blank=True)
    year = models.ForeignKey(Year, on_delete=models.SET_NULL, null=True)
    course = models.ForeignKey(Course, on_delete=models.CASCADE,  null=True ,blank=True)
    
    def __str__(self):
        return f"{self.first_name } { self.second_name}".strip() or self.username
    
    @property
    def is_profile_complete(self):
        return bool(self.course and self.year)


   

class Post(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.author} on {self.date.strftime('%Y-%m-%d')}"

