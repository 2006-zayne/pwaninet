from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
from .validators import validate_image_size, validate_video_size, validate_document_size

GRADIENT_CHOICES = [
    ('none', 'Standard (No Gradient)'),
    ('grad-ocean', 'Ocean Blue'),
    ('grad-forest', 'Forest Green'),
    ('grad-magma', 'Magma Red'),
    ('grad-midnight', 'Midnight Purple'),
]

class Year(models.Model):
    level = models.PositiveIntegerField()
    
    course = models.ForeignKey(
        'Course', 
        on_delete=models.CASCADE, 
        related_name='years'
    )# related_name='years' allows Course.years.all() to work ok fam?

    def __str__(self):
        return f"{self.course.name} - Year {self.level}"

    class Meta:
      
        ordering = ['level'] #  Ensures Year 1 comes before Year 2 in the dropdowns
        unique_together = ['level', 'course']   # Prevents duplicate years for the same course 
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
    profile_pic = models.ImageField(default='profile_pic/default_pic1.jpg', upload_to='profile_pic')
    bio = models.TextField(max_length=500 , blank=True)
    #groups_in = models.ManyToManyField('Groups' , related_name='members')
    
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
    image = models.ImageField(upload_to='posts/images' , blank=True , null= True)
    video = models.FileField(upload_to='posts/videos' , blank= True , null= True )
    docs = models.FileField(upload_to= 'posts/docs' , blank= True , null= True )
    gradient_class = models.CharField(max_length=50 , choices=GRADIENT_CHOICES , default= 'none' , blank= True )
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Post by {self.author} on {self.date.strftime('%Y-%m-%d')}"
    
    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # Downscale for HP ProBook storage efficiency
            if img.height > 1080 or img.width > 1080:
                img.thumbnail((1080, 1080))
            
            output = BytesIO()
            img.save(output, format='JPEG', quality=75) # Crushing file size by ~60%
            output.seek(0)
            
            file_name = self.image.name.split('.')[0]
            self.image = InMemoryUploadedFile(
                output, 'ImageField', f"{file_name}.jpg", 
                'image/jpeg', sys.getsizeof(output), None
            )

        super(Post, self).save(*args, **kwargs)

#Wagwan Jeff This is the notification model to store every student's notification it contains,the receiver,sender,and the is read field which determines if they have already read it.
class Notifications(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE , related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE ,related_name='sent_notifications' )
    msg = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.recipient.username}"#Just for identify purposes for it not to bring crazy names when we nee to show it in the frontend hahahahahah!
    