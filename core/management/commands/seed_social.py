from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import *
from faker import Faker
import random

fake = Faker()

User = get_user_model()


class Command(BaseCommand):
    help = "Seed database with users, groups, posts, comments, likes"

    def handle(self, *args, **kwargs):
        self.stdout.write("🚀 Seeding started...")

        self.create_users()
        self.create_groups()
        self.create_posts()
        self.create_comments()
        self.create_likes()
        self.create_follows()

        self.stdout.write(self.style.SUCCESS("🔥 Seeding complete"))

    # ---------------- USERS ----------------
    def create_users(self):
        self.users = []

        for i in range(30):
            user = User.objects.create_user(
                username=fake.user_name() + str(i),
                email=fake.email(),
                password="password123",
                first_name=fake.first_name(),
                second_name=fake.first_name(),
                last_name=fake.last_name(),
                bio=fake.text(max_nb_chars=120)
            )
            self.users.append(user)

        self.stdout.write("👤 Users created")

    # ---------------- GROUPS ----------------
    def create_groups(self):
        self.groups = []

        courses = Course.objects.all()
        if not courses:
            self.stdout.write("⚠️ No courses found — skipping group course linking")

        for i in range(8):
            group = Groups.objects.create(
                name=fake.word().capitalize() + " Society",
                creator=random.choice(self.users),
                description=fake.text(max_nb_chars=150),
                is_official=random.choice([True, False])
            )

            members = random.sample(self.users, k=random.randint(5, 20))
            group.members.set(members)

            # sync reverse relation
            for u in members:
                u.groups_in.add(group)

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
                    gradient_class=random.choice([c[0] for c in GRADIENT_CHOICES])
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

    # ---------------- FOLLOWS ----------------
    def create_follows(self):
        for user in self.users:
            others = [u for u in self.users if u != user]
            following = random.sample(others, k=random.randint(0, 8))

            for target in following:
                Follow.objects.get_or_create(follower=user, followed=target)

        self.stdout.write("🔗 Follows created")