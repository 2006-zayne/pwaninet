"""
Comprehensive Database Seed Script for Pwaninet

This script populates the database with sample data for all models across the application.
Run this with: python manage.py shell < seed_database.py
Or import and run: from seed_database import seed_database; seed_database()
"""

import os
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import transaction

# Import all models
from users.models import (
    User, Follow, Pinch, DeviceAccount, UserSession, Block, HiddenAuthor,
    GlobalRole, ThemePreference, FontSizePreference, LanguagePreference,
    FontFamilyPreference, FontStylePreference, PrivacyLevel, CollaborationStatus
)
from courses.models import (
    Faculty, Department, School, Year, Course, Unit, CourseAcademicUnit
)
from groups.models import Group, Membership, MembershipRole, MembershipStatus, JoinPolicy
from posts.models import (
    Post, PostImage, Like, Comment, CommentLike, Report, Repost,
    HiddenPost, AuthorPreference, SharedPost
)
from documents.academic.models import (
    AcademicYear, AcademicLevel, Semester, Faculty as DocFaculty,
    School as DocSchool, Department as DocDepartment, Programme,
    AcademicUnit, ProgrammeUnit
)
from documents.documents.models import (
    Category, Tag, Document, DocumentVersion, DocumentFile,
    DocumentAuthor, DocumentAcademicUnit, DocumentTag
)
from documents.engagement.models import (
    DocumentView, DocumentDownload, DocumentBookmark, DocumentRating,
    DocumentShare, DocumentAnalytics, DocumentReport
)
from documents.collections.models import Collection, CollectionItem, CollectionShare
from notifications.models import (
    NotificationPreference, NotificationObject, NotificationAction, DeliveryAttempt
)
from releases.models import Release, ReleaseItem, UserReleaseView


def clear_database():
    """Clear all existing data from the database."""
    print("Clearing existing database...")
    
    # Clear in reverse order of dependencies
    models_to_clear = [
        # User relationships
        Follow, Pinch, DeviceAccount, UserSession, Block, HiddenAuthor,
        
        # Posts
        SharedPost, AuthorPreference, HiddenPost, Repost, Report,
        CommentLike, Comment, Like, PostImage, Post,
        
        # Groups
        Membership, Group,
        
        # Document engagement
        DocumentReport, DocumentShare, DocumentRating, DocumentBookmark,
        DocumentDownload, DocumentView, DocumentAnalytics,
        
        # Collections
        CollectionShare, CollectionItem, Collection,
        
        # Documents
        DocumentTag, DocumentAcademicUnit, DocumentAuthor,
        DocumentFile, DocumentVersion, Document, Tag, Category,
        
        # Programme units
        ProgrammeUnit,
        
        # Academic structure
        AcademicUnit, Programme, DocDepartment, DocSchool, DocFaculty,
        Semester, AcademicYear, AcademicLevel,
        
        # Courses
        CourseAcademicUnit, Unit, Year, Course, Department, School, Faculty,
        
        # Notifications
        DeliveryAttempt, NotificationAction, NotificationObject, NotificationPreference,
        
        # Releases
        UserReleaseView, ReleaseItem, Release,
        
        # Users
        User,
    ]
    
    for model in models_to_clear:
        try:
            model.objects.all().delete()
            print(f"  Cleared {model.__name__}")
        except Exception as e:
            print(f"  Error clearing {model.__name__}: {e}")
    
    print("Database cleared successfully.\n")


def seed_academic_structure():
    """Seed academic structure (Faculty -> School -> Department -> Programme -> AcademicUnit)."""
    print("Seeding academic structure...")
    
    # Academic Levels
    levels_data = [
        (1, 'Year 1', 'First year of study'),
        (2, 'Year 2', 'Second year of study'),
        (3, 'Year 3', 'Third year of study'),
        (4, 'Year 4', 'Fourth year of study'),
    ]
    for level, name, desc in levels_data:
        AcademicLevel.objects.get_or_create(
            level=level,
            defaults={'name': name, 'description': desc, 'is_active': True}
        )
    
    # Academic Years
    current_year = datetime.now().year
    academic_years = [
        (f'{current_year-1}/{current_year}', f'{current_year-1}/{current_year}',
         datetime(current_year-1, 9, 1), datetime(current_year, 8, 31), False),
        (f'{current_year}/{current_year+1}', f'{current_year}/{current_year+1}',
         datetime(current_year, 9, 1), datetime(current_year+1, 8, 31), True),
    ]
    for code, name, start, end, is_current in academic_years:
        year, created = AcademicYear.objects.get_or_create(
            code=code,
            defaults={'name': name, 'start_date': start, 'end_date': end, 'is_current': is_current}
        )
        if is_current and not year.is_current:
            year.is_current = True
            year.save()
    
    # Get current academic year
    current_academic_year = AcademicYear.objects.get(is_current=True)
    
    # Semesters
    semesters = [
        (1, current_academic_year, datetime(current_year, 9, 1), datetime(current_year, 12, 15), True),
        (2, current_academic_year, datetime(current_year+1, 1, 5), datetime(current_year+1, 5, 15), False),
    ]
    for number, year, start, end, is_current in semesters:
        sem, created = Semester.objects.get_or_create(
            number=number, academic_year=year,
            defaults={'start_date': start, 'end_date': end, 'is_current': is_current}
        )
        if is_current and not sem.is_current:
            sem.is_current = True
            sem.save()
    
    current_semester = Semester.objects.get(is_current=True)
    
    # Faculties
    faculties_data = [
        ('SCI', 'Faculty of Science', 'Leading science education and research'),
        ('ENG', 'Faculty of Engineering', 'Innovating engineering solutions'),
        ('BUS', 'Faculty of Business', 'Developing business leaders'),
        ('ART', 'Faculty of Arts', 'Nurturing creative expression'),
    ]
    for code, name, desc in faculties_data:
        DocFaculty.objects.get_or_create(
            code=code,
            defaults={'name': name, 'description': desc}
        )
    
    # Schools
    sci_faculty = DocFaculty.objects.get(code='SCI')
    schools_data = [
        ('COMP', 'School of Computing', sci_faculty, 'Computer science and IT education'),
        ('MATH', 'School of Mathematics', sci_faculty, 'Mathematical sciences'),
    ]
    for code, name, faculty, desc in schools_data:
        DocSchool.objects.get_or_create(
            code=code,
            defaults={'name': name, 'faculty': faculty, 'description': desc}
        )
    
    # Departments
    comp_school = DocSchool.objects.get(code='COMP')
    departments_data = [
        ('CS', 'Computer Science', comp_school, 'Computer science department'),
        ('IT', 'Information Technology', comp_school, 'IT department'),
    ]
    for code, name, school, desc in departments_data:
        DocDepartment.objects.get_or_create(
            code=code,
            defaults={'name': name, 'school': school, 'description': desc}
        )
    
    # Programmes
    cs_dept = DocDepartment.objects.get(code='CS')
    programmes_data = [
        ('BSC-CS', 'Bachelor of Computer Science', cs_dept, 'Bachelor', 4, 'Undergraduate CS program'),
        ('MSC-CS', 'Master of Computer Science', cs_dept, 'Master', 2, 'Graduate CS program'),
    ]
    for code, name, dept, degree, duration, desc in programmes_data:
        Programme.objects.get_or_create(
            code=code,
            defaults={
                'name': name, 'department': dept, 'degree_type': degree,
                'duration_years': duration, 'description': desc, 'is_active': True
            }
        )
    
    # Academic Units
    units_data = [
        ('CSC101', 'Introduction to Programming', 'Fundamental programming concepts'),
        ('CSC102', 'Data Structures', 'Data structures and algorithms'),
        ('CSC201', 'Database Systems', 'Database design and management'),
        ('CSC202', 'Web Development', 'Modern web technologies'),
        ('CSC301', 'Software Engineering', 'Software development methodologies'),
        ('CSC302', 'Machine Learning', 'Introduction to ML'),
    ]
    for code, name, desc in units_data:
        AcademicUnit.objects.get_or_create(
            code=code,
            defaults={'name': name, 'description': desc, 'credit_hours': 3, 'is_active': True}
        )
    
    # Programme Units (mapping programmes to units)
    bsc_cs = Programme.objects.get(code='BSC-CS')
    year1 = AcademicLevel.objects.get(level=1)
    year2 = AcademicLevel.objects.get(level=2)
    year3 = AcademicLevel.objects.get(level=3)
    
    programme_units = [
        (bsc_cs, AcademicUnit.objects.get(code='CSC101'), year1, current_academic_year, current_semester, True, False),
        (bsc_cs, AcademicUnit.objects.get(code='CSC102'), year1, current_academic_year, current_semester, True, False),
        (bsc_cs, AcademicUnit.objects.get(code='CSC201'), year2, current_academic_year, current_semester, True, False),
        (bsc_cs, AcademicUnit.objects.get(code='CSC202'), year2, current_academic_year, current_semester, True, False),
        (bsc_cs, AcademicUnit.objects.get(code='CSC301'), year3, current_academic_year, current_semester, True, False),
        (bsc_cs, AcademicUnit.objects.get(code='CSC302'), year3, current_academic_year, current_semester, False, True),
    ]
    for prog, unit, level, year, sem, core, elective in programme_units:
        ProgrammeUnit.objects.get_or_create(
            programme=prog, academic_unit=unit, academic_level=level,
            academic_year=year, semester=sem,
            defaults={'is_core': core, 'is_elective': elective}
        )
    
    print("Academic structure seeded successfully.\n")
    return current_academic_year, current_semester, bsc_cs


def seed_courses():
    """Seed legacy course structure."""
    print("Seeding courses...")
    
    # Faculties (legacy)
    Faculty.objects.get_or_create(
        code='SCI',
        defaults={'name': 'Faculty of Science', 'description': 'Science faculty'}
    )
    
    # Departments (legacy)
    sci_faculty = Faculty.objects.get(code='SCI')
    Department.objects.get_or_create(
        code='CS',
        defaults={'name': 'Computer Science', 'faculty': sci_faculty}
    )
    
    # Schools (legacy)
    cs_dept = Department.objects.get(code='CS')
    School.objects.get_or_create(
        name='School of Computing',
        defaults={'department': cs_dept}
    )
    
    # Courses
    school = School.objects.get(name='School of Computing')
    courses_data = [
        ('BSC-CS', 'Bachelor of Science in Computer Science', school, 'Bachelor', 4),
        ('BIT', 'Bachelor of Information Technology', school, 'Bachelor', 4),
    ]
    for code, name, sch, degree, duration in courses_data:
        Course.objects.get_or_create(
            code=code,
            defaults={
                'name': name, 'school': sch, 'degree_type': degree,
                'duration_years': duration, 'is_active': True
            }
        )
    
    # Years for courses
    for course in Course.objects.all():
        for year_num in range(1, course.duration_years + 1):
            Year.objects.get_or_create(
                level=year_num, course=course
            )
    
    # Units (legacy)
    bsc_cs = Course.objects.get(code='BSC-CS')
    year1 = Year.objects.get(course=bsc_cs, level=1)
    units_data = [
        ('CSC101', 'Introduction to Programming', bsc_cs, year1),
        ('CSC102', 'Data Structures', bsc_cs, year1),
    ]
    for code, name, course, year in units_data:
        Unit.objects.get_or_create(
            code=code,
            defaults={'name': name, 'course': course, 'year': year}
        )
    
    print("Courses seeded successfully.\n")
    return bsc_cs


def seed_users():
    """Seed users with different roles and profiles."""
    print("Seeding users...")
    
    # Get academic data
    programme = Programme.objects.get(code='BSC-CS')
    academic_level = AcademicLevel.objects.get(level=2)
    academic_year = AcademicYear.objects.get(is_current=True)
    semester = Semester.objects.get(is_current=True)
    
    course = Course.objects.get(code='BSC-CS')
    year = Year.objects.get(course=course, level=2)
    
    # Create users with different roles
    users_data = [
        # President
        {
            'username': 'president',
            'email': 'president@pwaninet.app',
            'first_name': 'John',
            'last_name': 'President',
            'global_role': GlobalRole.PRESIDENT,
            'bio': 'Student body president',
            'is_staff': True,
            'is_superuser': True,
        },
        # Delegates
        {
            'username': 'delegate1',
            'email': 'delegate1@pwaninet.app',
            'first_name': 'Alice',
            'last_name': 'Delegate',
            'global_role': GlobalRole.DELEGATE,
            'bio': 'Faculty of Science delegate',
            'is_staff': True,
        },
        {
            'username': 'delegate2',
            'email': 'delegate2@pwaninet.app',
            'first_name': 'Bob',
            'last_name': 'Delegate',
            'global_role': GlobalRole.DELEGATE,
            'bio': 'Faculty of Engineering delegate',
            'is_staff': True,
        },
        # Verified users
        {
            'username': 'verified1',
            'email': 'verified1@pwaninet.app',
            'first_name': 'Charlie',
            'last_name': 'Verified',
            'global_role': GlobalRole.VERIFIED,
            'bio': 'Verified student',
        },
        # Regular users
        {
            'username': 'student1',
            'email': 'student1@pwaninet.app',
            'first_name': 'David',
            'last_name': 'Student',
            'global_role': GlobalRole.NORMAL,
            'bio': 'Computer science student',
            'programme': programme,
            'academic_level': academic_level,
            'academic_year': academic_year,
            'semester': semester,
            'course': course,
            'year': year,
        },
        {
            'username': 'student2',
            'email': 'student2@pwaninet.app',
            'first_name': 'Emma',
            'last_name': 'Student',
            'global_role': GlobalRole.NORMAL,
            'bio': 'IT student',
            'programme': programme,
            'academic_level': academic_level,
            'academic_year': academic_year,
            'semester': semester,
        },
        {
            'username': 'student3',
            'email': 'student3@pwaninet.app',
            'first_name': 'Frank',
            'last_name': 'Student',
            'global_role': GlobalRole.NORMAL,
            'bio': 'Engineering student',
        },
        {
            'username': 'student4',
            'email': 'student4@pwaninet.app',
            'first_name': 'Grace',
            'last_name': 'Student',
            'global_role': GlobalRole.NORMAL,
            'bio': 'Business student',
        },
        {
            'username': 'student5',
            'email': 'student5@pwaninet.app',
            'first_name': 'Henry',
            'last_name': 'Student',
            'global_role': GlobalRole.NORMAL,
            'bio': 'Arts student',
        },
    ]
    
    created_users = []
    for user_data in users_data:
        username = user_data.pop('username')
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                **user_data,
                'password': make_password('password123'),
                'email_verified': True,
                'has_completed_onboarding': True,
                'headline': f'{user_data.get("first_name", "")} - Student',
                'interests': 'programming, technology, learning',
                'collaboration_status': CollaborationStatus.OPEN_TO_NETWORKING,
                'skills': ['Python', 'JavaScript', 'Django'],
                'projects': [
                    {
                        'title': 'Portfolio Website',
                        'description': 'Personal portfolio website',
                        'link': 'https://github.com/example/portfolio'
                    }
                ],
                'github_url': f'https://github.com/{username}',
                'linkedin_url': f'https://linkedin.com/in/{username}',
            }
        )
        if created:
            created_users.append(user)
            print(f"  Created user: {username}")
        else:
            print(f"  User already exists: {username}")
    
    print(f"Users seeded successfully. Total: {User.objects.count()}\n")
    return created_users


def seed_user_relationships(users):
    """Seed user relationships (follows, pinches, blocks)."""
    print("Seeding user relationships...")
    
    if len(users) < 2:
        print("  Not enough users for relationships")
        return
    
    # Follow relationships
    follow_pairs = [
        (users[0], users[3]),  # president follows student1
        (users[0], users[4]),  # president follows student2
        (users[3], users[4]),  # student1 follows student2
        (users[4], users[3]),  # student2 follows student1 (mutual)
        (users[3], users[5]),  # student1 follows student3
    ]
    for follower, followed in follow_pairs:
        Follow.objects.get_or_create(follower=follower, followed=followed)
    
    # Pinches
    pinch_pairs = [
        (users[3], users[4]),
        (users[4], users[5]),
    ]
    for pinch_user, pinched_user in pinch_pairs:
        Pinch.objects.get_or_create(pinch_user=pinch_user, pinched_user=pinched_user)
    
    # Blocks
    if len(users) >= 6:
        Block.objects.get_or_create(blocker=users[3], blocked=users[6])
    
    print("User relationships seeded successfully.\n")


def seed_groups(users):
    """Seed groups and memberships."""
    print("Seeding groups...")
    
    if not users:
        print("  No users available")
        return
    
    course = Course.objects.first()
    year = Year.objects.first()
    
    groups_data = [
        {
            'name': 'Computer Science Society',
            'description': 'Official CS student group',
            'created_by': users[0],
            'is_official': True,
            'join_policy': JoinPolicy.OPEN,
            'course': course,
            'year': year,
        },
        {
            'name': 'Programming Club',
            'description': 'For programming enthusiasts',
            'created_by': users[3],
            'is_official': False,
            'join_policy': JoinPolicy.APPROVAL,
        },
        {
            'name': 'Study Group - Data Structures',
            'description': 'Study group for CSC102',
            'created_by': users[3],
            'is_official': False,
            'join_policy': JoinPolicy.OPEN,
        },
    ]
    
    created_groups = []
    for group_data in groups_data:
        group, created = Group.objects.get_or_create(
            name=group_data['name'],
            defaults=group_data
        )
        if created:
            created_groups.append(group)
            print(f"  Created group: {group.name}")
    
    # Create memberships
    if created_groups:
        # President as admin of CS Society
        Membership.objects.get_or_create(
            user=users[0], group=created_groups[0],
            defaults={'role': MembershipRole.ADMIN, 'status': MembershipStatus.APPROVED}
        )
        
        # Student1 as member of CS Society
        Membership.objects.get_or_create(
            user=users[3], group=created_groups[0],
            defaults={'role': MembershipRole.MEMBER, 'status': MembershipStatus.APPROVED}
        )
        
        # Student1 as admin of Programming Club
        Membership.objects.get_or_create(
            user=users[3], group=created_groups[1],
            defaults={'role': MembershipRole.ADMIN, 'status': MembershipStatus.APPROVED}
        )
        
        # Student2 as pending member of Programming Club
        Membership.objects.get_or_create(
            user=users[4], group=created_groups[1],
            defaults={'role': MembershipRole.MEMBER, 'status': MembershipStatus.PENDING}
        )
        
        # Student1, Student2, Student3 in Study Group
        for i, user in enumerate([users[3], users[4], users[5]]):
            if user:
                Membership.objects.get_or_create(
                    user=user, group=created_groups[2],
                    defaults={'role': MembershipRole.MEMBER, 'status': MembershipStatus.APPROVED}
                )
    
    print(f"Groups seeded successfully. Total: {Group.objects.count()}\n")
    return created_groups


def seed_posts(users, groups):
    """Seed posts with images, likes, and comments."""
    print("Seeding posts...")
    
    if not users:
        print("  No users available")
        return
    
    course = Course.objects.first()
    unit = Unit.objects.first()
    
    posts_data = [
        {
            'author': users[3],
            'content': 'Just finished my programming assignment! 🎉',
            'course': course,
            'unit': unit,
        },
        {
            'author': users[4],
            'content': 'Looking for study partners for the upcoming exam',
            'course': course,
        },
        {
            'author': users[0],
            'content': 'Welcome to all new students! Feel free to ask questions.',
            'gradient_class': 'grad-ocean',
        },
        {
            'author': users[3],
            'content': 'Check out this cool resource I found for learning Django',
            'gradient_class': 'grad-forest',
        },
        {
            'author': users[5],
            'content': 'Does anyone have notes for CSC201?',
            'course': course,
        },
    ]
    
    created_posts = []
    for i, post_data in enumerate(posts_data):
        # Add group to some posts
        if groups and i < len(groups):
            post_data['group'] = groups[i]
        
        post = Post.objects.create(**post_data)
        created_posts.append(post)
        print(f"  Created post: {post.content[:50]}...")
    
    # Create likes
    if len(created_posts) >= 2 and len(users) >= 3:
        Like.objects.get_or_create(user=users[4], post=created_posts[0])
        Like.objects.get_or_create(user=users[5], post=created_posts[0])
        Like.objects.get_or_create(user=users[3], post=created_posts[1])
    
    # Create comments
    if len(created_posts) >= 1 and len(users) >= 2:
        Comment.objects.create(
            post=created_posts[0],
            author=users[4],
            content='Great work! Keep it up!'
        )
        Comment.objects.create(
            post=created_posts[0],
            author=users[5],
            content='Congrats! 🎊'
        )
    
    # Create comment replies
    if created_posts[0].comments.exists():
        parent_comment = created_posts[0].comments.first()
        Comment.objects.create(
            post=created_posts[0],
            author=users[3],
            content='Thanks everyone!',
            parent_comment=parent_comment
        )
    
    print(f"Posts seeded successfully. Total: {Post.objects.count()}\n")
    return created_posts


def seed_documents(users):
    """Seed documents with categories, tags, and engagement."""
    print("Seeding documents...")
    
    if not users:
        print("  No users available")
        return
    
    # Categories
    categories_data = [
        ('past_paper', 'Past Paper', 'Previous examination papers'),
        ('lecture_notes', 'Lecture Notes', 'Class lecture materials'),
        ('assignment', 'Assignment', 'Course assignments'),
        ('slides', 'Slides', 'Presentation slides'),
    ]
    for code, name, desc in categories_data:
        Category.objects.get_or_create(
            code=code,
            defaults={'name': name, 'description': desc, 'is_active': True}
        )
    
    # Tags
    tags_data = [
        'python', 'django', 'algorithms', 'database', 'web-development',
        'machine-learning', 'data-structures', 'programming'
    ]
    for tag_name in tags_data:
        Tag.objects.get_or_create(
            name=tag_name,
            defaults={'slug': tag_name.replace('-', '_'), 'usage_count': 0}
        )
    
    # Get academic data
    category = Category.objects.first()
    academic_unit = AcademicUnit.objects.first()
    academic_level = AcademicLevel.objects.get(level=2)
    academic_year = AcademicYear.objects.get(is_current=True)
    semester = Semester.objects.get(is_current=True)
    
    # Documents
    documents_data = [
        {
            'title': 'Introduction to Python Programming',
            'description': 'Comprehensive guide to Python basics',
            'category': category,
            'uploaded_by': users[3],
            'visibility': 'public',
            'status': 'ready',
        },
        {
            'title': 'Data Structures and Algorithms Notes',
            'description': 'Complete notes for CSC102',
            'category': category,
            'uploaded_by': users[4],
            'visibility': 'public',
            'status': 'ready',
        },
        {
            'title': 'Database Systems Past Paper 2023',
            'description': 'Previous year examination paper',
            'category': Category.objects.get(code='past_paper'),
            'uploaded_by': users[0],
            'visibility': 'public',
            'status': 'ready',
        },
    ]
    
    created_documents = []
    for doc_data in documents_data:
        doc = Document.objects.create(**doc_data)
        created_documents.append(doc)
        print(f"  Created document: {doc.title}")
    
    # Create document versions and files
    for doc in created_documents:
        version = DocumentVersion.objects.create(
            document=doc,
            version_number=1,
            change_notes='Initial version',
            created_by=doc.uploaded_by,
            is_latest=True
        )
        
        # Create a dummy file for each document version
        DocumentFile.objects.create(
            document_version=version,
            file=None,  # No actual file for seeding
            original_filename=f'{doc.slug}.pdf',
            storage_path=f'documents/{doc.slug}.pdf',
            mime_type='application/pdf',
            extension='pdf',
            size_bytes=1024000,  # 1MB dummy size
            storage_provider='local',
            processing_status='ready',
            uploaded_by=doc.uploaded_by
        )
    
    # Link documents to academic units
    for doc in created_documents:
        DocumentAcademicUnit.objects.create(
            document=doc,
            academic_unit=academic_unit,
            academic_level=academic_level,
            semester=semester,
            academic_year=academic_year,
            is_primary=True
        )
    
    # Add tags to documents
    python_tag = Tag.objects.get(name='python')
    for doc in created_documents[:2]:
        DocumentTag.objects.create(document=doc, tag=python_tag)
    
    # Create document authors
    for doc in created_documents:
        DocumentAuthor.objects.create(
            document=doc,
            user=doc.uploaded_by,
            author_type='uploader'
        )
    
    # Create analytics
    for doc in created_documents:
        DocumentAnalytics.objects.create(
            document=doc,
            view_count=10,
            download_count=5,
            bookmark_count=2,
            share_count=1,
            rating_count=3,
            positive_rating_count=2,
            negative_rating_count=1
        )
    
    # Create engagement data
    if len(created_documents) >= 1 and len(users) >= 2:
        # Get the first document's file
        first_doc_file = created_documents[0].latest_version.files.first() if created_documents[0].latest_version else None
        
        # Views
        DocumentView.objects.create(
            document=created_documents[0],
            user=users[4],
            viewed_at=timezone.now() - timedelta(hours=2)
        )
        DocumentView.objects.create(
            document=created_documents[0],
            user=users[5],
            viewed_at=timezone.now() - timedelta(hours=1)
        )
        
        # Downloads (require document_file)
        if first_doc_file:
            DocumentDownload.objects.create(
                document=created_documents[0],
                document_file=first_doc_file,
                user=users[4],
                downloaded_at=timezone.now() - timedelta(hours=1)
            )
        
        # Bookmarks
        DocumentBookmark.objects.create(
            document=created_documents[0],
            user=users[4],
            is_favorite=True
        )
        
        # Ratings
        DocumentRating.objects.create(
            document=created_documents[0],
            user=users[4],
            rating=1  # Thumbs up
        )
        DocumentRating.objects.create(
            document=created_documents[0],
            user=users[5],
            rating=1  # Thumbs up
        )
    
    print(f"Documents seeded successfully. Total: {Document.objects.count()}\n")
    return created_documents


def seed_collections(users, documents):
    """Seed document collections."""
    print("Seeding collections...")
    
    if not users or not documents:
        print("  Not enough users or documents")
        return
    
    # Collections
    collections_data = [
        {
            'name': 'My Study Materials',
            'description': 'Important study resources',
            'owner': users[3],
            'visibility': 'private',
        },
        {
            'name': 'Python Resources',
            'description': 'Python learning materials',
            'owner': users[4],
            'visibility': 'public',
        },
    ]
    
    created_collections = []
    for coll_data in collections_data:
        coll = Collection.objects.create(**coll_data)
        created_collections.append(coll)
        print(f"  Created collection: {coll.name}")
    
    # Add documents to collections
    if created_collections and documents:
        CollectionItem.objects.create(
            collection=created_collections[0],
            document=documents[0],
            added_by=users[3],
            order=0
        )
        CollectionItem.objects.create(
            collection=created_collections[0],
            document=documents[1],
            added_by=users[3],
            order=1
        )
        CollectionItem.objects.create(
            collection=created_collections[1],
            document=documents[0],
            added_by=users[4],
            order=0
        )
    
    # Share collection
    if len(created_collections) >= 2 and len(users) >= 2:
        CollectionShare.objects.create(
            collection=created_collections[0],
            shared_with=users[4],
            shared_by=users[3],
            can_edit=False
        )
    
    print(f"Collections seeded successfully. Total: {Collection.objects.count()}\n")


def seed_notifications(users):
    """Seed notification preferences and sample notifications."""
    print("Seeding notifications...")
    
    if not users:
        print("  No users available")
        return
    
    # Create notification preferences for all users
    for user in users:
        NotificationPreference.objects.get_or_create(
            user=user,
            defaults={
                'email_enabled': True,
                'push_enabled': True,
                'in_app_enabled': True,
                'quiet_hours_enabled': False,
            }
        )
    
    # Create sample notifications
    if len(users) >= 2:
        NotificationObject.objects.create(
            recipient=users[3],
            notification_type='LIKE',
            category='SOCIAL',
            priority='NORMAL',
            title='New like on your post',
            summary='Someone liked your recent post',
            status='DELIVERED',
            delivery_policy='IMMEDIATE'
        )
        
        NotificationObject.objects.create(
            recipient=users[4],
            notification_type='FOLLOW',
            category='SOCIAL',
            priority='NORMAL',
            title='New follower',
            summary='Someone started following you',
            status='SEEN',
            delivery_policy='IMMEDIATE'
        )
        
        NotificationObject.objects.create(
            recipient=users[3],
            notification_type='COMMENT',
            category='SOCIAL',
            priority='NORMAL',
            title='New comment',
            summary='Someone commented on your post',
            status='READ',
            delivery_policy='IMMEDIATE'
        )
    
    print(f"Notifications seeded successfully. Total: {NotificationObject.objects.count()}\n")


def seed_releases(users):
    """Seed release information."""
    print("Seeding releases...")
    
    # Create a release
    release = Release.objects.create(
        version='1.0.0',
        build_number=1,
        release_title='Initial Release',
        release_summary='First stable release of Pwaninet',
        release_type='MAJOR',
        status='PUBLISHED',
        release_channel='STABLE',
        is_current_release=True,
        mandatory_update=False,
        published=True,
        release_date=timezone.now(),
        published_at=timezone.now(),
        created_by=users[0] if users else None,
        published_by=users[0] if users else None,
    )
    
    # Add release items
    ReleaseItem.objects.create(
        release=release,
        category='FEATURE',
        title='User Authentication',
        description='Complete user authentication system',
        display_order=1
    )
    ReleaseItem.objects.create(
        release=release,
        category='FEATURE',
        title='Post Creation',
        description='Create and share posts',
        display_order=2
    )
    ReleaseItem.objects.create(
        release=release,
        category='IMPROVEMENT',
        title='Performance Improvements',
        description='Optimized database queries',
        display_order=3
    )
    
    # Mark as viewed by some users
    if users and len(users) >= 2:
        UserReleaseView.objects.create(
            user=users[0],
            release=release
        )
        UserReleaseView.objects.create(
            user=users[3],
            release=release
        )
    
    print(f"Releases seeded successfully. Total: {Release.objects.count()}\n")


@transaction.atomic
def seed_database():
    """Main function to seed the entire database."""
    print("=" * 60)
    print("Starting Database Seeding")
    print("=" * 60)
    print()
    
    # Clear existing data
    clear_database()
    
    # Seed in dependency order
    academic_year, semester, programme = seed_academic_structure()
    course = seed_courses()
    users = seed_users()
    seed_user_relationships(users)
    groups = seed_groups(users)
    posts = seed_posts(users, groups)
    documents = seed_documents(users)
    seed_collections(users, documents)
    seed_notifications(users)
    seed_releases(users)
    
    print("=" * 60)
    print("Database Seeding Completed Successfully!")
    print("=" * 60)
    print()
    print("Summary:")
    print(f"  Users: {User.objects.count()}")
    print(f"  Groups: {Group.objects.count()}")
    print(f"  Posts: {Post.objects.count()}")
    print(f"  Documents: {Document.objects.count()}")
    print(f"  Collections: {Collection.objects.count()}")
    print(f"  Notifications: {NotificationObject.objects.count()}")
    print(f"  Releases: {Release.objects.count()}")
    print()
    print("Default login credentials:")
    print("  Username: president")
    print("  Password: password123")
    print()


if __name__ == '__main__':
    seed_database()
