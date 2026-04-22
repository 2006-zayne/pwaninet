from django.core.management.base import BaseCommand
from core.models import Post, User, Like, Groups, Unit, Course, Year
import random
from faker import Faker

fake = Faker()

# Sample post content templates
POST_TEMPLATES = [
    "Just finished studying for {unit}. This topic is so interesting! 📚",
    "Can anyone help me understand {unit}? I'm stuck on the assignment.",
    "The lecture today on {unit} was amazing! Really pushing my limits 💪",
    "Anyone else thinking {unit} is the hardest subject? Let's study together!",
    "Got an A on my {unit} test! So proud of this achievement 🎉",
    "Looking for study partners for {unit}. DM me if interested!",
    "Just realized {unit} concepts are easier than I thought. Keep grinding!",
    "{unit} exam in 2 days... panic mode activated 😅",
    "Pro tip: Use this method for {unit} problems. Saves so much time!",
    "My opinion: {unit} should be the favorite subject for everyone",
    "{unit} is honestly the most practical course we're taking",
    "Struggling with {unit} right now. Any good resources?",
    "Just had a breakthrough with {unit}! Finally understand it 🧠",
    "University life hit different. {unit} is no joke.",
    "That feeling when you finally solve a {unit} problem 😤",
    "Can we talk about how {unit} is changing the world right now?",
    "Study session for {unit} this weekend. Who's down?",
    "The instructor's explanation of {unit} today was 🔥",
    "Honestly, {unit} is the reason I chose this course",
    "Just completed my {unit} project. Feeling accomplished!",
    "Group project for {unit} is driving me crazy lol",
    "Coffee + textbook + {unit} = my life right now",
    "Why is {unit} so interesting yet so challenging?",
    "Finally getting the hang of {unit} concepts!",
    "The {unit} assignment is lowkey fun. Change my mind.",
    "Spent 4 hours on {unit} today. Worth it though!",
    "{unit} never made sense until now. Eureka! 💡",
    "Who else is addicted to learning {unit}?",
    "The best feeling is when {unit} clicks",
    "Just aced my {unit} quiz! Consistency pays off 💯"
]

class Command(BaseCommand):
    help = 'Populate database with 30 random posts and random likes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=30,
            help='Number of posts to create (default: 30)'
        )

    def handle(self, *args, **options):
        count = options['count']
        
        # Get all users
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Create some users first!'))
            return
        
        # Get all units
        units = list(Unit.objects.all())
        if not units:
            self.stdout.write(self.style.WARNING('No units found. Posts will be created without units.'))
            units = [None]
        
        # Get all courses
        courses = list(Course.objects.all())
        if not courses:
            self.stdout.write(self.style.WARNING('No courses found. Posts will be created without courses.'))
            courses = [None]
        
        # Get all groups
        groups = list(Groups.objects.all())
        groups_list = groups if groups else [None]
        
        created_posts = 0
        
        self.stdout.write(self.style.SUCCESS(f'Creating {count} posts...'))
        
        for i in range(count):
            try:
                # Pick random author
                author = random.choice(users)
                
                # Pick random course
                course = random.choice(courses)
                
                # Pick random unit (if available)
                unit = random.choice(units)
                
                # Pick random group (80% chance no group, 20% chance with group)
                group = random.choice(groups_list) if random.random() < 0.2 else None
                
                # Generate content
                if unit:
                    content = random.choice(POST_TEMPLATES).format(unit=unit.code)
                else:
                    content = fake.paragraph(nb_sentences=3)
                
                # Create post
                post = Post.objects.create(
                    author=author,
                    course=course,
                    unit=unit,
                    group=group,
                    content=content,
                    gradient_class=random.choice(['none', 'grad-ocean', 'grad-forest', 'grad-magma', 'grad-midnight'])
                )
                
                # Add random likes (0-50 likes per post)
                num_likes = random.randint(0, 50)
                liked_users = random.sample(users, min(num_likes, len(users)))
                
                for user in liked_users:
                    try:
                        Like.objects.get_or_create(user=user, post=post)
                    except Exception as e:
                        pass  # Skip if like already exists
                
                created_posts += 1
                
                if (i + 1) % 5 == 0:
                    self.stdout.write(f'Created {i + 1}/{count} posts...')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error creating post {i + 1}: {str(e)}'))
                continue
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Successfully created {created_posts} posts with random likes!')
        )
        
        # Show summary
        total_likes = Like.objects.count()
        total_posts = Post.objects.count()
        self.stdout.write(f'\n📊 Stats:')
        self.stdout.write(f'   Total posts: {total_posts}')
        self.stdout.write(f'   Total likes: {total_likes}')
        self.stdout.write(f'   Average likes per post: {total_likes / total_posts:.1f}')
