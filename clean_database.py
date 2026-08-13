"""
Database Cleanup Script for Pwaninet

This script clears all existing data from the database.
Run this with: python manage.py shell < clean_database.py
Or import and run: from clean_database import clean_database; clean_database()
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pwaninet.settings.local')
django.setup()

from django.db import transaction

# Import all models
from users.models import (
    User, Follow, Pinch, DeviceAccount, UserSession, Block, HiddenAuthor
)
from courses.models import (
    Faculty, Department, School, Year, Course, Unit, CourseAcademicUnit
)
from groups.models import Group, Membership
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


def clean_database():
    """Clear all existing data from the database."""
    print("=" * 60)
    print("Cleaning Database")
    print("=" * 60)
    print()
    
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
            count = model.objects.count()
            if count > 0:
                model.objects.all().delete()
                print(f"  ✓ Cleared {model.__name__} ({count} records)")
            else:
                print(f"  - {model.__name__} (already empty)")
        except Exception as e:
            print(f"  ✗ Error clearing {model.__name__}: {e}")
    
    print()
    print("=" * 60)
    print("Database Cleaned Successfully!")
    print("=" * 60)
    print()


if __name__ == '__main__':
    with transaction.atomic():
        clean_database()
