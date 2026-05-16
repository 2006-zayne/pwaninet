"""
Populate database with test data for users, courses, groups, posts, comments, likes, shares and reposts.
Usage: python manage.py populate_db
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from faker import Faker
import random
from datetime import timedelta

from users.models import User, Follow, GlobalRole
from courses.models import Course, Year, Unit
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from posts.models import Post, Like, Comment, CommentLike, Repost, SharedPost


class Command(BaseCommand):
    help = 'Populate database with test data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=20,
            help='Number of users to create'
        )
        parser.add_argument(
            '--posts',
            type=int,
            default=50,
            help='Number of posts to create'
        )
        parser.add_argument(
            '--groups',
            type=int,
            default=10,
            help='Number of groups to create'
        )
        parser.add_argument(
            '--comments',
            type=int,
            default=100,
            help='Number of comments to create'
        )

    def handle(self, *args, **options):
        fake = Faker()
        num_users = options['users']
        num_posts = options['posts']
        num_groups = options['groups']
        num_comments = options['comments']

        self.stdout.write(self.style.SUCCESS('🚀 Starting database population...'))

        # Create courses and years
        self.stdout.write(self.style.HTTP_INFO('📚 Creating courses and years...'))
        courses = self.create_courses()
        
        # Create users
        self.stdout.write(self.style.HTTP_INFO(f'👥 Creating {num_users} users...'))
        users = self.create_users(num_users, courses, fake)
        
        # Create follows
        self.stdout.write(self.style.HTTP_INFO('🔗 Creating user follows...'))
        self.create_follows(users, fake)
        
        # Create groups
        self.stdout.write(self.style.HTTP_INFO(f'👫 Creating {num_groups} groups...'))
        groups = self.create_groups(num_groups, users, courses, fake)
        
        # Create group memberships
        self.stdout.write(self.style.HTTP_INFO('📋 Creating group memberships...'))
        self.create_memberships(groups, users)
        
        # Create posts
        self.stdout.write(self.style.HTTP_INFO(f'📝 Creating {num_posts} posts...'))
        posts = self.create_posts(num_posts, users, groups, courses, fake)
        
        # Create likes on posts
        self.stdout.write(self.style.HTTP_INFO('❤️ Creating post likes...'))
        self.create_likes(posts, users)
        
        # Create comments
        self.stdout.write(self.style.HTTP_INFO(f'💬 Creating {num_comments} comments...'))
        comments = self.create_comments(num_comments, posts, users, fake)
        
        # Create likes on comments
        self.stdout.write(self.style.HTTP_INFO('❤️ Creating comment likes...'))
        self.create_comment_likes(comments, users)
        
        # Create reposts
        self.stdout.write(self.style.HTTP_INFO('🔄 Creating reposts...'))
        self.create_reposts(posts, users, fake)
        
        # Create shared posts
        self.stdout.write(self.style.HTTP_INFO('📤 Creating shared posts...'))
        self.create_shared_posts(posts, users, groups, fake)

        self.stdout.write(self.style.SUCCESS('\n✅ Database population completed successfully!'))
        self.stdout.write(self.style.SUCCESS(f'   - Users: {User.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Courses: {Course.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Groups: {Group.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Posts: {Post.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Comments: {Comment.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Likes: {Like.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Reposts: {Repost.objects.count()}'))
        self.stdout.write(self.style.SUCCESS(f'   - Shared Posts: {SharedPost.objects.count()}'))

    def create_courses(self):
        """Create courses and years"""
        course_names = [
            'Computer Science',
            'Information Technology',
            'Software Engineering',
            'Data Science',
            'Web Development',
            'Cybersecurity',
        ]
        
        courses = []
        for name in course_names:
            course, _ = Course.objects.get_or_create(name=name)
            courses.append(course)
            
            # Create years for each course
            for year_level in range(1, 4):
                Year.objects.get_or_create(
                    level=year_level,
                    course=course
                )
            
            # Create units for the course
            units_per_course = ['Database Design', 'Web Technologies', 'Mobile Development', 'AI/ML']
            for idx, unit_name in enumerate(units_per_course):
                Unit.objects.get_or_create(
                    code=f"{name[:3].upper()}{year_level}0{idx+1}",
                    name=unit_name,
                    course=course,
                    year=course.years.first()
                )
        
        return courses

    def create_users(self, count, courses, fake):
        """Create test users"""
        users = []
        
        # Create admin user
        admin, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'first_name': 'Admin',
                'second_name': 'User',
                'last_name': 'Super',
                'global_role': GlobalRole.PRESIDENT,
                'is_staff': True,
                'is_superuser': True,
                'password': make_password('admin123'),
            }
        )
        users.append(admin)
        
        # Create regular test user
        testuser, created = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'first_name': 'Test',
                'second_name': 'User',
                'last_name': 'Demo',
                'global_role': GlobalRole.VERIFIED,
                'password': make_password('testuser123'),
            }
        )
        users.append(testuser)
        
        # Create additional random users
        for i in range(count - 2):
            username = f"user_{fake.user_name()}_{i}"
            if not User.objects.filter(username=username).exists():
                user = User.objects.create(
                    username=username,
                    email=fake.email(),
                    first_name=fake.first_name(),
                    second_name=fake.first_name(),
                    last_name=fake.last_name(),
                    bio=fake.text(max_nb_chars=100),
                    course=random.choice(courses),
                    year=random.choice(Year.objects.all()) if Year.objects.exists() else None,
                    global_role=random.choice([GlobalRole.NORMAL, GlobalRole.VERIFIED, GlobalRole.DELEGATE]),
                    password=make_password('testpass123'),
                )
                users.append(user)
        
        return users

    def create_follows(self, users, fake):
        """Create follow relationships"""
        if len(users) < 2:
            return
        
        for user in users:
            # Each user follows 3-7 random users
            num_follows = random.randint(3, min(7, len(users) - 1))
            potential_follows = [u for u in users if u != user]
            
            for followed in random.sample(potential_follows, min(num_follows, len(potential_follows))):
                Follow.objects.get_or_create(
                    follower=user,
                    followed=followed
                )

    def create_groups(self, count, users, courses, fake):
        """Create test groups"""
        groups = []
        
        for course in courses:
            group_names = [
                f'{course.name} Class',
                f'{course.name} Study Group',
                f'{course.name} Discussion'
            ]
            
            for name_template in group_names:
                group, created = Group.objects.get_or_create(
                    name=name_template,
                    defaults={
                        'created_by': random.choice(users),
                        'description': fake.text(max_nb_chars=150),
                        'is_official': random.choice([True, False]),
                        'join_policy': random.choice(['open', 'approval', 'invite']),
                        'course': course,
                    }
                )
                if created:
                    groups.append(group)
        
        # Create additional random groups
        existing_count = len(groups)
        for i in range(max(0, count - existing_count)):
            group, created = Group.objects.get_or_create(
                name=f'{fake.company()} Group {i}',
                defaults={
                    'created_by': random.choice(users),
                    'description': fake.text(max_nb_chars=150),
                    'is_official': random.choice([True, False]),
                    'join_policy': random.choice(['open', 'approval', 'invite']),
                    'course': random.choice(courses),
                }
            )
            if created:
                groups.append(group)
        
        return groups[:count]

    def create_memberships(self, groups, users):
        """Create group memberships"""
        for group in groups:
            # Add creator as admin
            Membership.objects.get_or_create(
                user=group.created_by,
                group=group,
                defaults={
                    'role': MembershipRole.ADMIN,
                    'status': MembershipStatus.APPROVED,
                }
            )
            
            # Add random members
            num_members = random.randint(5, min(15, len(users)))
            potential_members = [u for u in users if u != group.created_by]
            
            for member in random.sample(potential_members, min(num_members, len(potential_members))):
                Membership.objects.get_or_create(
                    user=member,
                    group=group,
                    defaults={
                        'role': random.choice([MembershipRole.MEMBER, MembershipRole.MODERATOR]),
                        'status': random.choice([MembershipStatus.APPROVED, MembershipStatus.PENDING]),
                    }
                )

    def create_posts(self, count, users, groups, courses, fake):
        """Create test posts"""
        posts = []
        
        for i in range(count):
            post = Post.objects.create(
                author=random.choice(users),
                course=random.choice(courses) if random.choice([True, False]) else None,
                group=random.choice(groups) if random.choice([True, False]) and groups else None,
                content=fake.paragraph(nb_sentences=random.randint(3, 8)),
                gradient_class=random.choice(['none', 'grad-ocean', 'grad-forest', 'grad-magma']),
            )
            
            # Randomly add created_at in the past
            days_back = random.randint(0, 30)
            post.created_at = timezone.now() - timedelta(days=days_back)
            post.save()
            posts.append(post)
        
        return posts

    def create_likes(self, posts, users):
        """Create likes on posts"""
        for post in posts:
            # Each post gets 1-15 likes
            num_likes = random.randint(1, min(15, len(users)))
            likers = random.sample(users, min(num_likes, len(users)))
            
            for user in likers:
                Like.objects.get_or_create(
                    user=user,
                    post=post
                )

    def create_comments(self, count, posts, users, fake):
        """Create comments on posts"""
        comments = []
        
        if not posts:
            return comments
        
        for i in range(count):
            comment = Comment.objects.create(
                post=random.choice(posts),
                author=random.choice(users),
                content=fake.paragraph(nb_sentences=random.randint(1, 3)),
            )
            
            # Randomly add created_at in the past
            days_back = random.randint(0, 30)
            comment.created_at = timezone.now() - timedelta(days=days_back)
            comment.save()
            comments.append(comment)
        
        return comments

    def create_comment_likes(self, comments, users):
        """Create likes on comments"""
        for comment in comments:
            # Each comment gets 0-5 likes
            num_likes = random.randint(0, min(5, len(users)))
            if num_likes == 0:
                continue
            
            likers = random.sample(users, min(num_likes, len(users)))
            
            for user in likers:
                CommentLike.objects.get_or_create(
                    user=user,
                    comment=comment
                )

    def create_reposts(self, posts, users, fake):
        """Create reposts of posts"""
        for post in posts[:len(posts)//2]:  # Only repost half the posts
            num_reposts = random.randint(0, min(5, len(users)))
            if num_reposts == 0:
                continue
            
            reposters = random.sample(users, min(num_reposts, len(users)))
            
            for reposter in reposters:
                if post.author != reposter:  # Don't let users repost their own posts
                    Repost.objects.get_or_create(
                        original_post=post,
                        reposter=reposter,
                        defaults={
                            'content': fake.paragraph(nb_sentences=random.randint(0, 2)) if random.choice([True, False]) else None,
                        }
                    )

    def create_shared_posts(self, posts, users, groups, fake):
        """Create shared posts"""
        for post in posts[:len(posts)//3]:  # Share 1/3 of posts
            num_shares = random.randint(0, 3)
            
            for _ in range(num_shares):
                sharer = random.choice(users)
                
                # Random choice: share to user or group
                if random.choice([True, False]) and groups:
                    SharedPost.objects.get_or_create(
                        original_post=post,
                        sharer=sharer,
                        shared_to_group=random.choice(groups),
                        defaults={
                            'message': fake.sentence() if random.choice([True, False]) else None,
                        }
                    )
                else:
                    # Share to a random user (not the original author)
                    potential_recipients = [u for u in users if u != post.author]
                    if potential_recipients:
                        SharedPost.objects.get_or_create(
                            original_post=post,
                            sharer=sharer,
                            shared_to=random.choice(potential_recipients),
                            defaults={
                                'message': fake.sentence() if random.choice([True, False]) else None,
                            }
                        )
