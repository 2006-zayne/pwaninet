from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from users.models import User, Follow, GlobalRole
from posts.models import Post, Like, Comment, CommentLike, GRADIENT_CHOICES
from groups.models import Group, MembershipRole, MembershipStatus, Membership
from courses.models import Course, Unit, Year
from faker import Faker
import random

fake = Faker()


class Command(BaseCommand):
    help = "Seed social data for the application"

    def add_arguments(self, parser):
        parser.add_argument(
            '--sync-only',
            action='store_true',
            help='Only sync existing group memberships without creating new data',
        )

    def handle(self, *args, **kwargs):
        sync_only = kwargs.get('sync_only', False)

        if sync_only:
            self.sync_group_memberships()
            self.stdout.write(self.style.SUCCESS("🔗 Group memberships synced"))
        else:
            self.stdout.write("🚀 Seeding started...")

            self.create_courses()
            self.create_years()
            self.create_units()
            self.create_users()
            self.create_groups()
            self.create_posts()
            self.create_comments()
            self.create_likes()
            self.create_comment_likes()
            self.create_follows()

            self.stdout.write(self.style.SUCCESS("🔥 Seeding complete"))

    def sync_group_memberships(self):
        for group in Group.objects.all():
            for membership in group.memberships.filter(status='APPROVED'):
                # Membership model now handles the relationship
                pass
        self.stdout.write("🔗 Group memberships synced")

    # ---------------- COURSES ----------------
    def create_courses(self):
        self.courses = []
        course_names = [
            "Computer Science", "Software Engineering", "Information Technology",
            "Data Science", "Cybersecurity", "Business Administration",
            "Economics", "Mechanical Engineering", "Electrical Engineering",
            "Civil Engineering"
        ]

        for name in course_names:
            course = Course.objects.create(name=name)
            self.courses.append(course)

        self.stdout.write("📚 Courses created")

    # ---------------- YEARS ----------------
    def create_years(self):
        self.years = []
        for course in self.courses:
            for level in [1, 2, 3, 4]:
                year = Year.objects.create(course=course, level=level)
                self.years.append(year)

        self.stdout.write("📅 Years created")

    # ---------------- UNITS ----------------
    def create_units(self):
        self.units = []
        unit_data = {
            "Computer Science": ["Introduction to Programming", "Data Structures", "Algorithms", "Database Systems", "Software Engineering"],
            "Software Engineering": ["Requirements Engineering", "Software Design", "Testing & QA", "Project Management", "DevOps"],
            "Information Technology": ["Network Fundamentals", "System Administration", "Web Development", "Cloud Computing", "IT Security"],
            "Data Science": ["Statistics", "Machine Learning", "Data Visualization", "Big Data", "Deep Learning"],
            "Cybersecurity": ["Network Security", "Ethical Hacking", "Cryptography", "Incident Response", "Security Policy"],
            "Business Administration": ["Principles of Management", "Marketing", "Finance", "Human Resources", "Business Strategy"],
            "Economics": ["Microeconomics", "Macroeconomics", "Econometrics", "International Trade", "Financial Economics"],
            "Mechanical Engineering": ["Thermodynamics", "Fluid Mechanics", "Mechanics of Materials", "Manufacturing Processes", "CAD"],
            "Electrical Engineering": ["Circuit Analysis", "Electronics", "Power Systems", "Control Systems", "Signal Processing"],
            "Civil Engineering": ["Structural Analysis", "Geotechnical Engineering", "Transportation Engineering", "Hydraulics", "Construction Management"]
        }

        for course in self.courses:
            if course.name in unit_data:
                for unit_name in unit_data[course.name]:
                    year = random.choice([y for y in self.years if y.course == course])
                    unit = Unit.objects.create(
                        code=f"{course.name[:3].upper()}{random.randint(100, 999)}",
                        name=unit_name,
                        course=course,
                        year=year
                    )
                    self.units.append(unit)

        self.stdout.write("📖 Units created")

    # ---------------- USERS ----------------
    def create_users(self):
        self.users = []

        for i in range(30):
            course = random.choice(self.courses)
            year = random.choice([y for y in self.years if y.course == course])
            user = User.objects.create_user(
                username=fake.user_name() + str(i),
                email=fake.email(),
                password="password123",
                first_name=fake.first_name(),
                second_name=fake.first_name(),
                last_name=fake.last_name(),
                bio=fake.text(max_nb_chars=120),
                course=course,
                year=year,
                global_role=random.choice(list(GlobalRole.choices))[0]
            )
            self.users.append(user)

        self.stdout.write("👤 Users created")

    # ---------------- GROUPS ----------------
    def create_groups(self):
        self.groups = []

        for i in range(8):
            selected_course = random.choice(self.courses)
            group = Group.objects.create(
                name=fake.word().capitalize() + " Society",
                created_by=random.choice(self.users),
                description=fake.text(max_nb_chars=150),
                is_official=random.choice([True, False]),
                course=selected_course,
                year=random.choice([y for y in self.years if y.course == selected_course])
            )

            members = random.sample(self.users, k=random.randint(5, 20))
            # Create memberships instead of using direct M2M
            for idx, u in enumerate(members):
                # Assign roles: first member as admin, some as moderators, rest as members
                if idx == 0:
                    role = MembershipRole.ADMIN
                elif idx < len(members) // 4:
                    role = MembershipRole.MODERATOR
                else:
                    role = MembershipRole.MEMBER
                
                Membership.objects.create(
                    user=u,
                    group=group,
                    role=role,
                    status=MembershipStatus.APPROVED
                )

            self.groups.append(group)

        self.stdout.write("👥 Groups created")

    # ---------------- POSTS ----------------
    def create_posts(self):
        self.posts = []

        units = list(Unit.objects.all())

        for user in self.users:
            for _ in range(random.randint(1, 4)):
                post = Post.objects.create(
                    author=user,
                    group=random.choice(self.groups) if random.random() > 0.4 else None,
                    course=user.course,
                    unit=random.choice(units) if units else None,
                    content=fake.paragraph(nb_sentences=5),
                    gradient_class=random.choice([c[0] for c in GRADIENT_CHOICES]),
                    image=None,  # Will be populated with actual media if needed
                    video=None,
                    docs=None
                )
                self.posts.append(post)

        self.stdout.write("📝 Posts created")

    # ---------------- COMMENTS ----------------
    def create_comments(self):
        self.comments = []

        for post in self.posts:
            for _ in range(random.randint(0, 6)):
                comment = Comment.objects.create(
                    post=post,
                    author=random.choice(self.users),
                    content=fake.sentence()
                )
                self.comments.append(comment)

        self.stdout.write("💬 Comments created")

    # ---------------- LIKES ----------------
    def create_likes(self):
        for post in self.posts:
            likers = random.sample(self.users, k=random.randint(0, len(self.users)//3))
            for user in likers:
                Like.objects.get_or_create(user=user, post=post)

        self.stdout.write("❤️ Likes created")

    # ---------------- COMMENT LIKES ----------------
    def create_comment_likes(self):
        for comment in self.comments:
            likers = random.sample(self.users, k=random.randint(0, len(self.users)//4))
            for user in likers:
                CommentLike.objects.get_or_create(user=user, comment=comment)

        self.stdout.write("💝 Comment likes created")

    # ---------------- FOLLOWS ----------------
    def create_follows(self):
        for user in self.users:
            others = [u for u in self.users if u != user]
            following = random.sample(others, k=random.randint(0, 8))

            for target in following:
                Follow.objects.get_or_create(follower=user, followed=target)

        self.stdout.write("🔗 Follows created")