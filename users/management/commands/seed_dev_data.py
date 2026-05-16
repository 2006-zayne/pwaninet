import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from posts.models import Post, Comment, Like
from users.models import Follow
from courses.models import Course, Year

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed development database with realistic sample data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=100,
            help='Number of users to create (default: 100)',
        )
        parser.add_argument(
            '--posts-per-user',
            type=int,
            default=5,
            help='Average posts per user (default: 5)',
        )
        parser.add_argument(
            '--clean',
            action='store_true',
            help='Clean existing seed data before seeding',
        )

    def handle(self, *args, **options):
        num_users = options['users']
        posts_per_user = options['posts_per_user']
        clean = options['clean']

        if clean:
            self.clean_seed_data()

        self.stdout.write(self.style.SUCCESS('Starting seed data generation...'))

        # Check if courses exist, create if needed
        courses = self.get_or_create_courses()
        years = self.get_or_create_years(courses)

        # Create users
        users = self.create_users(num_users, courses, years)
        self.stdout.write(self.style.SUCCESS(f'Created {len(users)} users'))

        # Create posts
        posts = self.create_posts(users, posts_per_user, courses)
        self.stdout.write(self.style.SUCCESS(f'Created {len(posts)} posts'))

        # Create comments
        comments = self.create_comments(posts, users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(comments)} comments'))

        # Create likes
        likes = self.create_likes(posts, users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(likes)} likes'))

        # Create follows
        follows = self.create_follows(users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(follows)} follows'))

        self.stdout.write(self.style.SUCCESS('Seed data generation complete!'))

    def clean_seed_data(self):
        """Clean existing seed data"""
        self.stdout.write(self.style.WARNING('Cleaning existing seed data...'))
        Follow.objects.all().delete()
        Like.objects.all().delete()
        Comment.objects.all().delete()
        Post.objects.all().delete()
        
        # Delete seed users (exclude superuser)
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(self.style.SUCCESS('Seed data cleaned'))

    def get_or_create_courses(self):
        """Get or create courses"""
        course_names = [
            'Software Engineering',
            'Computer Science',
            'Information Technology',
            'Business IT',
            'Civil Engineering',
            'Mechanical Engineering',
            'Nursing',
            'Medicine',
            'Economics',
            'Law',
            'Architecture',
            'Data Science',
            'Education',
            'Marketing',
        ]
        
        courses = []
        for name in course_names:
            course, created = Course.objects.get_or_create(name=name)
            courses.append(course)
        
        return courses

    def get_or_create_years(self, courses):
        """Get or create years for each course"""
        years = []
        for course in courses:
            for level in [1, 2, 3, 4, 5]:  # 5 = Graduate
                year, created = Year.objects.get_or_create(
                    level=level,
                    course=course
                )
                years.append(year)
        return years

    def create_users(self, num_users, courses, years):
        """Create users with realistic data"""
        first_names = [
            'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
            'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
            'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa',
            'Matthew', 'Betty', 'Anthony', 'Margaret', 'Mark', 'Sandra', 'Donald', 'Ashley',
            'Steven', 'Dorothy', 'Paul', 'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle',
            'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Melissa', 'George', 'Deborah',
            'Edward', 'Stephanie', 'Ronald', 'Rebecca', 'Timothy', 'Sharon', 'Jason', 'Laura',
            'Jeffrey', 'Cynthia', 'Ryan', 'Kathleen', 'Jacob', 'Amy', 'Gary', 'Shirley',
            'Nicholas', 'Angela', 'Eric', 'Helen', 'Jonathan', 'Anna', 'Stephen', 'Brenda',
            'Larry', 'Pamela', 'Justin', 'Nicole', 'Scott', 'Emma', 'Brandon', 'Samantha',
            'Benjamin', 'Katherine', 'Samuel', 'Christine', 'Gregory', 'Debra', 'Frank', 'Rachel',
            'Alexander', 'Carolyn', 'Raymond', 'Janet', 'Patrick', 'Catherine', 'Jack', 'Maria',
            'Dennis', 'Heather', 'Jerry', 'Diane', 'Tyler', 'Julie', 'Aaron', 'Joyce',
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
            'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
            'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
            'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
            'Mitchell', 'Carter', 'Roberts', 'Gomez', 'Phillips', 'Evans', 'Turner', 'Diaz',
            'Parker', 'Cruz', 'Edwards', 'Collins', 'Reyes', 'Stewart', 'Morris', 'Morales',
            'Murphy', 'Cook', 'Rogers', 'Gutierrez', 'Ortiz', 'Cooper', 'Peterson', 'Bailey',
            'Reed', 'Kelly', 'Howard', 'Ramos', 'Kim', 'Cox', 'Ward', 'Richardson', 'Watson',
            'Brooks', 'Chavez', 'Wood', 'Bennett', 'Gray', 'Mendoza', 'Ruiz', 'Hughes',
            'Price', 'Alvarez', 'Castillo', 'Sanders', 'Patel', 'Myers', 'Long', 'Ross',
        ]
        
        bios = [
            'Just living life one day at a time 🌟',
            'Coffee addict ☕ | Code enthusiast 💻',
            'Dream big, work hard, stay humble',
            'Making memories and chasing dreams',
            'Student by day, gamer by night 🎮',
            'Fitness enthusiast 💪 | Food lover 🍕',
            'Always learning, always growing',
            'Creating my own path',
            'Living for the weekend 🎉',
            'Bookworm 📚 | Nature lover 🌿',
            'Music is my therapy 🎵',
            'Adventure awaits ✈️',
            'Simplicity is the ultimate sophistication',
            'Work hard, play harder',
            'Believer in magic ✨',
            'Tech geek | Cat person 🐱',
            'On a journey to self-discovery',
            'Capturing moments 📸',
            'Food blogger in the making 🍳',
            'Just another soul searching for meaning',
        ]
        
        users_to_create = []
        existing_usernames = set(User.objects.values_list('username', flat=True))
        
        for i in range(num_users):
            first_name = random.choice(first_names)
            last_name = random.choice(last_names)
            username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
            
            # Ensure unique username
            while username in existing_usernames:
                username = f"{first_name.lower()}{last_name.lower()}{random.randint(1, 999)}"
            
            existing_usernames.add(username)
            
            email = f"{username}@example.com"
            course = random.choice(courses)
            year = random.choice([y for y in years if y.course == course])
            bio = random.choice(bios)
            
            # Mostly normal users, very few with special roles
            if random.random() < 0.02:  # 2% chance
                global_role = 'VERIFIED'
            else:
                global_role = 'NORMAL'
            
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                second_name=random.choice(['', 'A', 'B', 'C', 'D', 'E']) if random.random() < 0.3 else '',
                last_name=last_name,
                bio=bio,
                course=course,
                year=year,
                global_role=global_role,
                is_active=True,
            )
            user.set_password('password123')  # Default password for all seed users
            users_to_create.append(user)
        
        created_users = User.objects.bulk_create(users_to_create)
        return created_users

    def create_posts(self, users, posts_per_user, courses):
        """Create posts with realistic content"""
        post_contents = [
            "Just finished my assignment! 🎉 Who else is relieved?",
            "Campus life is hitting different this semester 💯",
            "Anyone else struggling with this week's lectures? 📚",
            "Coffee is the only thing keeping me alive today ☕",
            "Study session at the library going strong! 📖",
            "Can't wait for the weekend plans 🎉",
            "Just had the best lunch at the cafeteria 🍕",
            "Group project meeting... wish me luck! 🤞",
            "Finally understanding this concept! 💡",
            "Late night coding session 💻",
            "Campus sunset views never get old 🌅",
            "Who's going to the event tonight? 🎊",
            "Stress levels: 💀 but we push through",
            "Just submitted my application! Fingers crossed 🤞",
            "Library vibes today 📚☕",
            "Campus coffee shop is my second home ☕",
            "Making memories with friends 👯",
            "Assignment done, freedom gained! 🎉",
            "Why do deadlines always come together? 😅",
            "Study break: scrolling through feed 😂",
            "New semester, new goals! 🎯",
            "Campus fashion check: pass or fail? 👕",
            "Group study session was productive! 📚",
            "Just joined a new club! Excited! 🎉",
            "Weekend plans: sleep and repeat 😴",
            "Campus wifi is acting up again 📶",
            "Who else is hungry? Food time! 🍔",
            "Lecture notes: 0/10 would not recommend 😅",
            "Making the most of university life! 🌟",
            "Can't believe it's already this time of semester ⏰",
            "Study playlist on repeat 🎵",
            "Campus adventures await! 🗺️",
            "Just made a new friend today! 👋",
            "Assignment deadline approaching... panic mode 😰",
            "Coffee run anyone? ☕",
            "Library is my second home this week 📚",
            "Campus events are the best! 🎉",
            "Taking a break from studying 🧘",
            "Group project progress: slow but steady 🐢",
            "Who's ready for the weekend? 🙋",
            "Campus life is what you make it! 🌟",
            "Just had an amazing class discussion! 💭",
            "Study mode: ACTIVATED 📚",
            "Campus food recommendations needed! 🍽️",
            "Making connections and networking 🤝",
            "University life is a journey 🚀",
        ]
        
        posts_to_create = []
        now = datetime.now()
        
        for user in users:
            num_posts = random.randint(3, posts_per_user + 2)
            for _ in range(num_posts):
                # Random timestamp within last 60 days
                days_ago = random.randint(0, 60)
                hours_ago = random.randint(0, 23)
                created_at = now - timedelta(days=days_ago, hours=hours_ago)
                
                post = Post(
                    author=user,
                    content=random.choice(post_contents),
                    course=random.choice(courses) if random.random() < 0.5 else None,
                    gradient_class=random.choice(['none', 'grad-ocean', 'grad-forest', 'grad-magma', 'grad-midnight', 'grad-desert', 'grad-stealth']),
                    created_at=created_at,
                    updated_at=created_at,
                )
                posts_to_create.append(post)
        
        created_posts = Post.objects.bulk_create(posts_to_create)
        return created_posts

    def create_comments(self, posts, users):
        """Create comments on posts"""
        comment_contents = [
            "This is so relatable! 😂",
            "Same here! 🙌",
            "Totally agree with this!",
            "Great post! 👍",
            "Thanks for sharing!",
            "Can relate so much 😅",
            "This made my day!",
            "So true! 💯",
            "Love this! ❤️",
            "Haha, same!",
            "I feel you on this one",
            "Exactly what I needed to hear",
            "This is gold! 🤣",
            "Preach! 🙏",
            "Couldn't agree more",
            "You're not alone! 💪",
            "This! A million times this!",
            "Facts! ✅",
            "Keep it up! 🌟",
            "So inspiring!",
            "Tell me about it 😂",
            "Same struggle here",
            "This is amazing!",
            "Love the energy! 🔥",
            "Keep grinding! 💪",
            "We got this! 🙌",
            "Motivation level: 💯",
            "This helps so much!",
            "Thanks for the tip!",
            "Great perspective!",
            "Needed to hear this today",
        ]
        
        comments_to_create = []
        
        for post in posts:
            # 2-8 comments per post
            num_comments = random.randint(2, 8)
            post_users = random.sample(users, min(num_comments, len(users)))
            
            for user in post_users:
                # Comments should be after the post
                post_time = post.created_at
                hours_after = random.randint(1, 72)
                created_at = post_time + timedelta(hours=hours_after)
                
                comment = Comment(
                    post=post,
                    author=user,
                    content=random.choice(comment_contents),
                    created_at=created_at,
                )
                comments_to_create.append(comment)
        
        created_comments = Comment.objects.bulk_create(comments_to_create)
        return created_comments

    def create_likes(self, posts, users):
        """Create likes on posts"""
        likes_to_create = []
        seen_combinations = set()
        
        for post in posts:
            # Random number of likes per post (0-20)
            num_likes = random.randint(0, 20)
            post_users = random.sample(users, min(num_likes, len(users)))
            
            for user in post_users:
                # Avoid duplicate likes
                combination = (user.id, post.id)
                if combination not in seen_combinations:
                    seen_combinations.add(combination)
                    
                    # Like should be after post creation
                    post_time = post.created_at
                    hours_after = random.randint(0, 48)
                    created_at = post_time + timedelta(hours=hours_after)
                    
                    like = Like(
                        user=user,
                        post=post,
                        created_at=created_at,
                    )
                    likes_to_create.append(like)
        
        created_likes = Like.objects.bulk_create(likes_to_create, ignore_conflicts=True)
        return created_likes

    def create_follows(self, users):
        """Create follow relationships"""
        follows_to_create = []
        seen_combinations = set()
        
        for user in users:
            # Each user follows 5-20 others
            num_follows = random.randint(5, 20)
            potential_follows = [u for u in users if u.id != user.id]
            
            if potential_follows:
                users_to_follow = random.sample(potential_follows, min(num_follows, len(potential_follows)))
                
                for follow_user in users_to_follow:
                    # Avoid duplicate follows
                    combination = (user.id, follow_user.id)
                    if combination not in seen_combinations:
                        seen_combinations.add(combination)
                        
                        follow = Follow(
                            follower=user,
                            followed=follow_user,
                        )
                        follows_to_create.append(follow)
        
        created_follows = Follow.objects.bulk_create(follows_to_create, ignore_conflicts=True)
        return created_follows
