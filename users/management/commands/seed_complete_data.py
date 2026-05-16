import random
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from posts.models import Post, Comment, Like, SharedPost
from users.models import Follow
from courses.models import Course, Year, School
from groups.models import Group, Membership, MembershipRole, MembershipStatus
from messaging.models import Conversation, Message, ConversationMember

User = get_user_model()


class Command(BaseCommand):
    help = 'Seed complete database with schools, courses, groups, users, posts, interactions, and messages'

    def add_arguments(self, parser):
        parser.add_argument(
            '--users',
            type=int,
            default=50,
            help='Number of regular users to create (default: 50)',
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

        self.stdout.write(self.style.SUCCESS('Starting complete seed data generation...'))

        # Create educational structure
        schools = self.create_schools()
        self.stdout.write(self.style.SUCCESS(f'Created {len(schools)} schools'))

        courses = self.create_courses(schools)
        self.stdout.write(self.style.SUCCESS(f'Created {len(courses)} courses'))

        years = self.create_years(courses)
        self.stdout.write(self.style.SUCCESS(f'Created {len(years)} years'))

        # Create groups
        groups = self.create_groups(courses, years, schools)
        self.stdout.write(self.style.SUCCESS(f'Created {len(groups)} groups'))

        # Create users (admin + test users + regular users)
        admin_user, test_users, regular_users = self.create_users(num_users, courses, years)
        all_users = [admin_user] + test_users + regular_users
        self.stdout.write(self.style.SUCCESS(f'Created {len(all_users)} users (1 admin + 2 test + {len(regular_users)} regular)'))

        # Create posts
        posts = self.create_posts(all_users, posts_per_user, courses)
        self.stdout.write(self.style.SUCCESS(f'Created {len(posts)} posts'))

        # Create interactions
        comments = self.create_comments(posts, all_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(comments)} comments'))

        likes = self.create_likes(posts, all_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(likes)} likes'))

        shares = self.create_shares(posts, all_users, groups)
        self.stdout.write(self.style.SUCCESS(f'Created {len(shares)} shares'))

        follows = self.create_follows(all_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(follows)} follows'))

        # Create group memberships
        memberships = self.create_group_memberships(all_users, groups)
        self.stdout.write(self.style.SUCCESS(f'Created {len(memberships)} group memberships'))

        # Create message conversations
        conversations = self.create_conversations(admin_user, test_users)
        self.stdout.write(self.style.SUCCESS(f'Created {len(conversations)} conversations'))

        # Output credentials
        self.output_credentials(admin_user, test_users, regular_users)

        self.stdout.write(self.style.SUCCESS('Complete seed data generation finished!'))

    def clean_seed_data(self):
        """Clean existing seed data"""
        self.stdout.write(self.style.WARNING('Cleaning existing seed data...'))
        
        # Clean in order of dependencies
        ConversationMember.objects.all().delete()
        Message.objects.all().delete()
        Conversation.objects.all().delete()
        Membership.objects.all().delete()
        Group.objects.all().delete()
        Follow.objects.all().delete()
        SharedPost.objects.all().delete()
        Like.objects.all().delete()
        Comment.objects.all().delete()
        Post.objects.all().delete()
        Year.objects.all().delete()
        Course.objects.all().delete()
        School.objects.all().delete()
        
        # Delete seed users (exclude superuser)
        User.objects.filter(is_superuser=False).delete()
        
        self.stdout.write(self.style.SUCCESS('Seed data cleaned'))

    def create_schools(self):
        """Create educational schools"""
        school_data = [
            {
                'name': 'School of Pure and Applied Sciences',
                'slug': 'pure-applied-sciences',
                'description': 'Home to sciences, mathematics, and applied disciplines'
            },
            {
                'name': 'School of Business and Economics',
                'slug': 'business-economics',
                'description': 'Business, finance, economics, and management studies'
            },
            {
                'name': 'School of Engineering and Technology',
                'slug': 'engineering-technology',
                'description': 'Engineering, computer science, and technology programs'
            },
            {
                'name': 'School of Health Sciences',
                'slug': 'health-sciences',
                'description': 'Medicine, nursing, pharmacy, and health programs'
            },
            {
                'name': 'School of Humanities and Social Sciences',
                'slug': 'humanities-social-sciences',
                'description': 'Arts, humanities, social sciences, and education'
            },
            {
                'name': 'School of Law',
                'slug': 'law',
                'description': 'Legal studies, law, and justice programs'
            },
        ]
        
        schools = []
        for school_info in school_data:
            school, created = School.objects.get_or_create(
                slug=school_info['slug'],
                defaults={
                    'name': school_info['name'],
                    'description': school_info['description']
                }
            )
            schools.append(school)
        
        return schools

    def create_courses(self, schools):
        """Create courses under schools"""
        courses_data = [
            # Pure and Applied Sciences
            {'name': 'Computer Science', 'school': 'pure-applied-sciences'},
            {'name': 'Mathematics', 'school': 'pure-applied-sciences'},
            {'name': 'Physics', 'school': 'pure-applied-sciences'},
            {'name': 'Chemistry', 'school': 'pure-applied-sciences'},
            {'name': 'Biology', 'school': 'pure-applied-sciences'},
            
            # Business and Economics
            {'name': 'Business Administration', 'school': 'business-economics'},
            {'name': 'Economics', 'school': 'business-economics'},
            {'name': 'Accounting', 'school': 'business-economics'},
            {'name': 'Finance', 'school': 'business-economics'},
            {'name': 'Marketing', 'school': 'business-economics'},
            
            # Engineering and Technology
            {'name': 'Software Engineering', 'school': 'engineering-technology'},
            {'name': 'Civil Engineering', 'school': 'engineering-technology'},
            {'name': 'Mechanical Engineering', 'school': 'engineering-technology'},
            {'name': 'Electrical Engineering', 'school': 'engineering-technology'},
            {'name': 'Information Technology', 'school': 'engineering-technology'},
            
            # Health Sciences
            {'name': 'Medicine', 'school': 'health-sciences'},
            {'name': 'Nursing', 'school': 'health-sciences'},
            {'name': 'Pharmacy', 'school': 'health-sciences'},
            {'name': 'Public Health', 'school': 'health-sciences'},
            {'name': 'Medical Laboratory Science', 'school': 'health-sciences'},
            
            # Humanities and Social Sciences
            {'name': 'Education', 'school': 'humanities-social-sciences'},
            {'name': 'Psychology', 'school': 'humanities-social-sciences'},
            {'name': 'Sociology', 'school': 'humanities-social-sciences'},
            {'name': 'English Literature', 'school': 'humanities-social-sciences'},
            {'name': 'History', 'school': 'humanities-social-sciences'},
            
            # Law
            {'name': 'Law (LLB)', 'school': 'law'},
            {'name': 'Commercial Law', 'school': 'law'},
            {'name': 'International Law', 'school': 'law'},
        ]
        
        school_map = {school.slug: school for school in schools}
        courses = []
        
        for course_data in courses_data:
            school = school_map.get(course_data['school'])
            if school:
                course, created = Course.objects.get_or_create(
                    name=course_data['name'],
                    school=school
                )
                courses.append(course)
        
        return courses

    def create_years(self, courses):
        """Create years for each course"""
        years = []
        for course in courses:
            for level in [1, 2, 3, 4]:  # Years 1-4
                year, created = Year.objects.get_or_create(
                    level=level,
                    course=course
                )
                years.append(year)
        return years

    def create_groups(self, courses, years, schools):
        """Create educational groups"""
        groups = []
        
        # Create official course/year groups
        for year in years:
            group_name = f"{year.course.name} - Year {year.level}"
            group, created = Group.objects.get_or_create(
                name=group_name,
                defaults={
                    'description': f"Official academic group for {group_name}",
                    'is_official': True,
                    'auto_join_on_signup': True,
                    'course': year.course,
                    'year': year,
                }
            )
            if created:
                groups.append(group)
        
        # Create school community groups
        for school in schools:
            group_name = f"{school.name} Community"
            group, created = Group.objects.get_or_create(
                name=group_name,
                defaults={
                    'description': f"Official community for {school.name}",
                    'is_official': True,
                    'auto_join_on_signup': False,  # Don't auto-join school groups
                }
            )
            if created:
                groups.append(group)
        
        # Create some study groups
        study_group_names = [
            'Study Group - Python Programming',
            'Study Group - Mathematics',
            'Study Group - Web Development',
            'Study Group - Data Structures',
            'Study Group - Machine Learning',
        ]
        
        for group_name in study_group_names:
            group, created = Group.objects.get_or_create(
                name=group_name,
                defaults={
                    'description': f"Collaborative study group for {group_name}",
                    'is_official': False,
                    'auto_join_on_signup': False,
                    'join_policy': 'open',
                }
            )
            if created:
                groups.append(group)
        
        return groups

    def create_users(self, num_users, courses, years):
        """Create admin, test users, and regular users"""
        
        # Create admin user using create_user or manual creation to avoid validation issues
        try:
            admin_user = User.objects.get(username='admin')
        except User.DoesNotExist:
            admin_user = User.objects.create_user(
                username='admin',
                email='admin@pwaninet.com',
                password='Admin@123',
                first_name='Admin',
                last_name='User',
                global_role='PRESIDENT',
                is_staff=True,
                is_superuser=True,
                is_active=True,
            )
        
        # Create test users
        test_users_data = [
            {
                'username': 'testuser1',
                'email': 'testuser1@pwaninet.com',
                'first_name': 'Test',
                'last_name': 'User One',
                'password': 'Test@123'
            },
            {
                'username': 'testuser2',
                'email': 'testuser2@pwaninet.com',
                'first_name': 'Test',
                'last_name': 'User Two',
                'password': 'Test@123'
            }
        ]
        
        test_users = []
        for test_user_data in test_users_data:
            try:
                test_user = User.objects.get(username=test_user_data['username'])
            except User.DoesNotExist:
                test_user = User.objects.create_user(
                    username=test_user_data['username'],
                    email=test_user_data['email'],
                    password=test_user_data['password'],
                    first_name=test_user_data['first_name'],
                    last_name=test_user_data['last_name'],
                    global_role='VERIFIED',
                    is_active=True,
                )
                # Assign course and year
                test_user.course = random.choice(courses)
                test_user.year = random.choice([y for y in years if y.course == test_user.course])
                test_user.save()
            else:
                # Update existing user with course/year if missing
                if not test_user.course:
                    test_user.course = random.choice(courses)
                if not test_user.year:
                    test_user.year = random.choice([y for y in years if y.course == test_user.course])
                test_user.save()
            test_users.append(test_user)
        
        # Create regular users
        first_names = [
            'James', 'Mary', 'John', 'Patricia', 'Robert', 'Jennifer', 'Michael', 'Linda',
            'William', 'Elizabeth', 'David', 'Barbara', 'Richard', 'Susan', 'Joseph', 'Jessica',
            'Thomas', 'Sarah', 'Charles', 'Karen', 'Christopher', 'Nancy', 'Daniel', 'Lisa',
            'Matthew', 'Betty', 'Anthony', 'Margaret', 'Mark', 'Sandra', 'Donald', 'Ashley',
            'Steven', 'Dorothy', 'Paul', 'Emily', 'Andrew', 'Donna', 'Joshua', 'Michelle',
            'Kenneth', 'Carol', 'Kevin', 'Amanda', 'Brian', 'Melissa', 'George', 'Deborah',
            'Edward', 'Stephanie', 'Ronald', 'Rebecca', 'Timothy', 'Sharon', 'Jason', 'Laura',
            'Jeffrey', 'Cynthia', 'Ryan', 'Kathleen', 'Jacob', 'Amy', 'Gary', 'Shirley',
        ]
        
        last_names = [
            'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia', 'Miller', 'Davis',
            'Rodriguez', 'Martinez', 'Hernandez', 'Lopez', 'Gonzalez', 'Wilson', 'Anderson',
            'Thomas', 'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Perez', 'Thompson',
            'White', 'Harris', 'Sanchez', 'Clark', 'Ramirez', 'Lewis', 'Robinson', 'Walker',
            'Young', 'Allen', 'King', 'Wright', 'Scott', 'Torres', 'Nguyen', 'Hill',
            'Flores', 'Green', 'Adams', 'Nelson', 'Baker', 'Hall', 'Rivera', 'Campbell',
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
        ]
        
        regular_users = []
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
            
            # Random global role
            if random.random() < 0.05:  # 5% chance
                global_role = 'VERIFIED'
            elif random.random() < 0.02:  # 2% chance
                global_role = 'DELEGATE'
            else:
                global_role = 'NORMAL'
            
            # Add skills and projects for some users
            skills = []
            projects = []
            if random.random() < 0.7:  # 70% of users have skills
                skills = random.sample(['Python', 'JavaScript', 'React', 'Django', 'Java', 'C++', 'SQL', 'AWS', 'Docker', 'Git'], random.randint(2, 5))
            if random.random() < 0.5:  # 50% of users have projects
                projects = [
                    {
                        'title': f'{random.choice(["My", "A", "The"])} {random.choice(["Project", "App", "Website", "Tool"])}',
                        'description': random.choice(['A personal project', 'Course assignment', 'Collaborative work', 'Open source contribution']),
                        'link': f'https://github.com/{username}/project1' if random.random() < 0.5 else ''
                    }
                ]
            
            # Use create_user to handle password properly
            user = User.objects.create_user(
                username=username,
                email=email,
                password='password123',
                first_name=first_name,
                second_name=random.choice(['', 'A', 'B', 'C']) if random.random() < 0.3 else '',
                last_name=last_name,
                bio=bio,
                course=course,
                year=year,
                global_role=global_role,
                skills=skills,
                projects=projects,
                headline=random.choice(['Student | Developer', 'Aspiring Engineer', 'Tech Enthusiast', 'Lifelong Learner']) if random.random() < 0.6 else '',
                collaboration_status=random.choice(['open_to_projects', 'open_to_study_groups', 'open_to_networking', 'not_looking']) if random.random() < 0.8 else '',
                is_active=True,
            )
            
            regular_users.append(user)
        
        return admin_user, test_users, regular_users

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
        ]
        
        posts_to_create = []
        now = datetime.now()
        
        for user in users:
            # Ensure at least 5 posts per user
            num_posts = max(posts_per_user, random.randint(posts_per_user, posts_per_user + 3))
            for _ in range(num_posts):
                # Random timestamp within last 60 days
                days_ago = random.randint(0, 60)
                hours_ago = random.randint(0, 23)
                created_at = now - timedelta(days=days_ago, hours=hours_ago)
                
                post = Post(
                    author=user,
                    content=random.choice(post_contents),
                    course=random.choice(courses) if random.random() < 0.4 else None,
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
            # Random number of likes per post (3-25)
            num_likes = random.randint(3, 25)
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

    def create_shares(self, posts, users, groups):
        """Create shares of posts"""
        shares_to_create = []
        seen_combinations = set()
        
        # Get user groups for realistic sharing
        user_groups = {}
        for user in users:
            user_groups[user.id] = list(Membership.objects.filter(
                user=user, 
                status=MembershipStatus.APPROVED
            ).values_list('group', flat=True))
        
        for post in posts:
            # 1-5 shares per post
            if random.random() < 0.3:  # 30% of posts get shared
                num_shares = random.randint(1, 5)
                post_users = random.sample(users, min(num_shares, len(users)))
                
                for user in post_users:
                    # Avoid duplicate shares
                    combination = (user.id, post.id)
                    if combination not in seen_combinations and user.id != post.author.id:
                        seen_combinations.add(combination)
                        
                        # Share should be after post creation
                        post_time = post.created_at
                        hours_after = random.randint(1, 72)
                        created_at = post_time + timedelta(hours=hours_after)
                        
                        # Randomly decide whether to share to user or group
                        share_to_user = random.choice([True, False])  # 50/50 chance
                        
                        if share_to_user:
                            # Share to a random user (different from sharer and post author)
                            potential_recipients = [u for u in users if u.id != user.id and u.id != post.author.id]
                            if potential_recipients:
                                recipient = random.choice(potential_recipients)
                                share = SharedPost(
                                    original_post=post,
                                    sharer=user,
                                    shared_to=recipient,
                                    created_at=created_at,
                                    is_viewed=random.choice([True, False])
                                )
                                shares_to_create.append(share)
                        else:
                            # Share to a random group that user is a member of
                            user_group_ids = user_groups.get(user.id, [])
                            if user_group_ids:
                                group_id = random.choice(user_group_ids)
                                try:
                                    group = Group.objects.get(id=group_id)
                                    share = SharedPost(
                                        original_post=post,
                                        sharer=user,
                                        shared_to_group=group,
                                        created_at=created_at,
                                        is_viewed=random.choice([True, False])
                                    )
                                    shares_to_create.append(share)
                                except Group.DoesNotExist:
                                    pass  # Skip if group doesn't exist
        
        created_shares = SharedPost.objects.bulk_create(shares_to_create, ignore_conflicts=True)
        return created_shares

    def create_follows(self, users):
        """Create follow relationships"""
        follows_to_create = []
        seen_combinations = set()
        
        for user in users:
            # Each user follows 5-25 others
            num_follows = random.randint(5, 25)
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

    def create_group_memberships(self, users, groups):
        """Create group memberships"""
        memberships_to_create = []
        seen_combinations = set()
        
        # Auto-enroll users in their official course/year groups
        official_groups = [g for g in groups if g.is_official and g.auto_join_on_signup]
        
        for user in users:
            # Enroll in matching official groups
            for group in official_groups:
                if group.course == user.course and group.year == user.year:
                    combination = (user.id, group.id)
                    if combination not in seen_combinations:
                        seen_combinations.add(combination)
                        
                        membership = Membership(
                            user=user,
                            group=group,
                            role=MembershipRole.MEMBER,
                            status=MembershipStatus.APPROVED,
                        )
                        memberships_to_create.append(membership)
            
            # Randomly join some other groups (2-5 additional groups)
            other_groups = [g for g in groups if not (g.is_official and g.auto_join_on_signup)]
            if other_groups and random.random() < 0.7:  # 70% chance to join additional groups
                num_joins = random.randint(2, min(5, len(other_groups)))
                groups_to_join = random.sample(other_groups, min(num_joins, len(other_groups)))
                
                for group in groups_to_join:
                    combination = (user.id, group.id)
                    if combination not in seen_combinations:
                        seen_combinations.add(combination)
                        
                        # Random status
                        if random.random() < 0.8:  # 80% approved
                            status = MembershipStatus.APPROVED
                        else:
                            status = MembershipStatus.PENDING
                        
                        membership = Membership(
                            user=user,
                            group=group,
                            role=MembershipRole.MEMBER,
                            status=status,
                        )
                        memberships_to_create.append(membership)
        
        created_memberships = Membership.objects.bulk_create(memberships_to_create, ignore_conflicts=True)
        return created_memberships

    def create_conversations(self, admin_user, test_users):
        """Create message conversations between admin and test users"""
        conversations_to_create = []
        messages_to_create = []
        conversation_members = []
        
        # Create individual conversations with each test user
        for test_user in test_users:
            # Create direct conversation
            conversation = Conversation.objects.create(
                type=Conversation.DIRECT,
                is_encrypted=False  # Disable encryption for seed data
            )
            conversations_to_create.append(conversation)
            
            # Add participants using ConversationMember
            admin_member = ConversationMember(
                conversation=conversation,
                user=admin_user
            )
            conversation_members.append(admin_member)
            
            test_member = ConversationMember(
                conversation=conversation,
                user=test_user
            )
            conversation_members.append(test_member)
            
            # Create messages
            message_contents = [
                "Welcome to PwaniNet! Let me know if you need any help.",
                "Thanks for joining! How are you finding the platform?",
                "Feel free to reach out if you have any questions.",
                "Great to have you here! Don't hesitate to ask for assistance.",
            ]
            
            # 3-6 messages per conversation
            num_messages = random.randint(3, 6)
            for i in range(num_messages):
                # Alternate between admin and test user
                sender = admin_user if i % 2 == 0 else test_user
                
                hours_ago = (num_messages - i) * random.randint(1, 3)
                created_at = datetime.now() - timedelta(hours=hours_ago)
                
                message = Message(
                    conversation=conversation,
                    sender=sender,
                    content=random.choice(message_contents) if i % 2 == 0 else random.choice([
                        "Thanks! Everything is going well.",
                        "I have a question about the groups feature.",
                        "The platform looks great so far!",
                        "Can you help me with something?",
                    ]),
                    is_encrypted=False,  # Disable encryption for seed data
                    created_at=created_at,
                    status='sent'
                )
                messages_to_create.append(message)
        
        # Bulk create conversation members first (required for relationships)
        ConversationMember.objects.bulk_create(conversation_members)
        
        # Then bulk create messages
        created_messages = Message.objects.bulk_create(messages_to_create)
        return conversations_to_create

    def output_credentials(self, admin_user, test_users, regular_users):
        """Output user credentials for easy access"""
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('USER CREDENTIALS'))
        self.stdout.write(self.style.SUCCESS('='*60))
        
        self.stdout.write(self.style.WARNING('\n🔑 ADMIN USER:'))
        self.stdout.write(self.style.SUCCESS(f'   Username: {admin_user.username}'))
        self.stdout.write(self.style.SUCCESS(f'   Password: Admin@123'))
        self.stdout.write(self.style.SUCCESS(f'   Email: {admin_user.email}'))
        
        self.stdout.write(self.style.WARNING('\n🔑 TEST USERS:'))
        for i, test_user in enumerate(test_users, 1):
            self.stdout.write(self.style.SUCCESS(f'   Test User {i}:'))
            self.stdout.write(self.style.SUCCESS(f'     Username: {test_user.username}'))
            self.stdout.write(self.style.SUCCESS(f'     Password: Test@123'))
            self.stdout.write(self.style.SUCCESS(f'     Email: {test_user.email}'))
        
        self.stdout.write(self.style.WARNING(f'\n🔑 REGULAR USERS (first 5):'))
        for i, user in enumerate(regular_users[:5], 1):
            self.stdout.write(self.style.SUCCESS(f'   User {i}:'))
            self.stdout.write(self.style.SUCCESS(f'     Username: {user.username}'))
            self.stdout.write(self.style.SUCCESS(f'     Password: password123'))
        
        self.stdout.write(self.style.WARNING(f'\n🔑 ALL REGULAR USERS SHARE PASSWORD:'))
        self.stdout.write(self.style.SUCCESS(f'   Password: password123'))
        
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Total users created:'))
        self.stdout.write(self.style.SUCCESS(f'   - 1 Admin user'))
        self.stdout.write(self.style.SUCCESS(f'   - {len(test_users)} Test users'))
        self.stdout.write(self.style.SUCCESS(f'   - {len(regular_users)} Regular users'))
        self.stdout.write(self.style.SUCCESS('='*60 + '\n'))
