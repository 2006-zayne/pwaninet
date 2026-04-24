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
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)
    
    def __str__(self):
        return f"{self.first_name } { self.second_name}".strip() or self.username
    
    @property
    def is_profile_complete(self):
        return bool(self.course and self.year)


   

class Post(models.Model):
    group = models.ForeignKey('Groups', on_delete=models.CASCADE, null=True, blank=True, related_name='posts')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    course = models.ForeignKey(Course, on_delete=models.CASCADE ,null= True ,blank=True )
    unit = models.ForeignKey(Unit, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    image = models.ImageField(upload_to='posts/images' , blank=True , null= True)
    video = models.FileField(upload_to='posts/videos' , blank= True , null= True )
    docs = models.FileField(upload_to= 'posts/docs' , blank= True , null= True )
    gradient_class = models.CharField(max_length=50 , choices=GRADIENT_CHOICES , default= 'none' , blank= True )
    date = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"Post by {self.author} on {self.date.strftime('%Y-%m-%d')}"

    @property
    def get_intel_file(self):
        """Returns the active media file regardless of type."""
        if self.image:
            return self.image
        if self.video:
            return self.video
        if self.docs:
            return self.docs
        return None

    @property
    def get_all_images(self):
        """Returns all images related to this post."""
        return self.post_images.all()

    def is_liked_by(self, user):
        if user.is_authenticated:
            # We check your 'Like' model specifically
            return self.likes.filter(user=user).exists()
        return False

    @property
    def like_count(self):
        return self.likes.count()

    @property
    def comment_count(self):
        return self.comments.count()

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


class PostImage(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='post_images')
    image = models.ImageField(upload_to='posts/images')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def save(self, *args, **kwargs):
        if self.image:
            img = Image.open(self.image)
            if img.mode != 'RGB':
                img = img.convert('RGB')

            # Downscale for storage efficiency
            if img.height > 1080 or img.width > 1080:
                img.thumbnail((1080, 1080))

            output = BytesIO()
            img.save(output, format='JPEG', quality=75)
            output.seek(0)

            file_name = self.image.name.split('.')[0]
            self.image = InMemoryUploadedFile(
                output, 'ImageField', f"{file_name}.jpg",
                'image/jpeg', sys.getsizeof(output), None
            )

        super(PostImage, self).save(*args, **kwargs)

    def __str__(self):
        return f"Image for Post {self.post.id}"

class Notifications(models.Model):
    INVITE = 'INVITE'
    ALERTE = 'ALERT'
    LIKE = 'LIKE'     # New Protocol
    FOLLOW = 'FOLLOW' # New Protocol
    
    TYPE_CHOICES = [
        (INVITE, 'Group Invite'), 
        (ALERTE, 'General Alert'),
        (LIKE, 'Post Like'),
        (FOLLOW, 'New Follower')
    ]

    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    group = models.ForeignKey('Groups', on_delete=models.CASCADE, null=True, blank=True)
    post = models.ForeignKey('Post', on_delete=models.CASCADE, null=True, blank=True) # Link to the intel
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default=ALERTE)
    msg = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username}"


class Groups(models.Model):
    name = models.CharField(max_length=200, unique=True)
    creator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_groups')
    members = models.ManyToManyField(User, related_name='joined_groups', blank=True)
    description = models.TextField(max_length=500, blank=True)
    group_pic = models.ImageField(upload_to='group_profile_pic' , null=True , blank=True)
    is_official = models.BooleanField(default=False) #Only allows us the admins to create official groups


    def __str__(self):
        return self.name
    
    @property
    def get_photo_url(self):
        if self.group_pic and hasattr(self.group_pic, 'url'):
            return self.group_pic.url
        # Tactical Fallback: Points to your STATIC folder, not MEDIA
        return f"{settings.STATIC_URL}images/default_group.jpg"


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post') # Hard constraint: one like per post per operative   


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following_relationships')
    followed = models.ForeignKey(User, on_delete=models.CASCADE, related_name='follower_relationships')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'followed') # Prevent duplicate tracking

    def __str__(self):
        return f"{self.follower.username} follows {self.followed.username}"


class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField(max_length=1000)
    likes = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='liked_comments', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
    
    @property
    def like_count(self):
        return self.likes.count()
    
    def is_liked_by(self, user):
        """Check if a comment is liked by a specific user."""
        if user.is_authenticated:
            return self.likes.filter(user=user).exists()
        return False

    def __str__(self):
        return f"Comment by {self.author.username} on {self.post.id}"