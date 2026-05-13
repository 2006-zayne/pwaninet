# PwaniNet Database Seeding Guide

## Overview
This guide explains how to use the `seed_complete_data` management command to populate your PwaniNet database with comprehensive test data.

## Prerequisites
- Django project properly configured
- Database migrations applied
- Python environment with Django installed

## Usage

### Basic Usage
```bash
python manage.py seed_complete_data
```

This will create:
- 50 regular users
- 5 posts per user (minimum)
- Educational structure (schools, courses, years)
- Official groups and study groups
- Comments, likes, shares on posts
- Follow relationships
- Group memberships
- Message conversations

### Custom Number of Users
```bash
python manage.py seed_complete_data --users 100
```

### Custom Posts Per User
```bash
python manage.py seed_complete_data --posts-per-user 10
```

### Clean Existing Data First
```bash
python manage.py seed_complete_data --clean
```

### Combined Options
```bash
python manage.py seed_complete_data --users 75 --posts-per-user 8 --clean
```

## What Gets Created

### 1. Educational Structure

#### Schools (6 schools)
- School of Pure and Applied Sciences
- School of Business and Economics  
- School of Engineering and Technology
- School of Health Sciences
- School of Humanities and Social Sciences
- School of Law

#### Courses (29 courses)
- 5 courses per school on average
- Each course belongs to a specific school
- Examples: Computer Science, Business Administration, Software Engineering, Medicine, Law

#### Years (116 years)
- Years 1-4 for each course
- Total years = 29 courses × 4 years

### 2. Groups

#### Official Academic Groups
- One group per course/year combination (e.g., "Computer Science - Year 1")
- Marked as `is_official=True`
- Marked as `auto_join_on_signup=True`
- Users automatically enrolled in their matching groups

#### School Community Groups  
- One group per school (e.g., "School of Pure and Applied Sciences Community")
- Marked as `is_official=True`
- Not auto-joined (manual enrollment)

#### Study Groups (5 groups)
- Python Programming Study Group
- Mathematics Study Group
- Web Development Study Group
- Data Structures Study Group
- Machine Learning Study Group
- Marked as unofficial, open to join

### 3. Users

#### Admin User
- **Username**: `admin`
- **Password**: `Admin@123`
- **Email**: `admin@pwaninet.com`
- **Role**: PRESIDENT (superuser)
- **Staff**: Yes
- **Superuser**: Yes

#### Test Users (2 users)
- **Username**: `testuser1`
- **Password**: `Test@123`
- **Email**: `testuser1@pwaninet.com`
- **Role**: VERIFIED

- **Username**: `testuser2`
- **Password**: `Test@123`  
- **Email**: `testuser2@pwaninet.com`
- **Role**: VERIFIED

#### Regular Users (50 by default)
- **Password**: `password123` (shared by all regular users)
- **Roles**: Mostly NORMAL, some VERIFIED (5%), some DELEGATE (2%)
- **Profile data**: 
  - Random names, bios, course, year
  - 70% have skills (2-5 skills each)
  - 50% have projects (1 project each)
  - 60% have headlines
  - 80% have collaboration status

### 4. Posts

#### Post Statistics (for 50 users with 5 posts each)
- **Total Posts**: ~250-300 posts
- **Content**: Realistic campus-life posts
- **Courses**: 40% tagged with specific courses
- **Gradients**: Random visual styling
- **Timestamps**: Distributed over last 60 days

#### Post Content Examples
- "Just finished my assignment! 🎉 Who else is relieved?"
- "Campus life is hitting different this semester 💯"
- "Coffee is the only thing keeping me alive today ☕"
- "Study session at the library going strong! 📖"

### 5. Interactions

#### Comments
- **Per Post**: 2-8 comments
- **Total Comments**: ~500-1,500 comments
- **Timing**: 1-72 hours after post creation
- **Content**: Realistic engagement responses

#### Likes
- **Per Post**: 3-25 likes
- **Total Likes**: ~750-2,500 likes
- **Timing**: 0-48 hours after post creation

#### Shares
- **Per Post**: 30% of posts get shared
- **Shares per Shared Post**: 1-5 shares
- **Total Shares**: ~40-100 shares
- **Timing**: 1-72 hours after post creation
- **Viewed Status**: Randomly marked as viewed/unviewed

### 6. Social Graph

#### Follows
- **Per User**: 5-25 follows
- **Total Follows**: ~250-1,000 follows
- **Pattern**: Random but realistic distribution

### 7. Group Memberships

#### Automatic Enrollments
- All users enrolled in their official course/year group
- Status: APPROVED (immediate access)

#### Additional Group Memberships
- **Per User**: 70% join 2-5 additional groups
- **Status**: 80% APPROVED, 20% PENDING
- **Total Memberships**: ~100-300 memberships

### 8. Message Conversations

#### Admin ↔ Test Users
- **Conversations**: 2 (one per test user)
- **Messages per Conversation**: 3-6 messages
- **Total Messages**: ~6-12 messages
- **Pattern**: Alternating between admin and test user
- **Read Status**: Latest message unread, others read

#### Message Content Examples
- Admin: "Welcome to PwaniNet! Let me know if you need any help."
- Test User: "Thanks! Everything is going well."
- Admin: "Great to have you here! Don't hesitate to ask for assistance."

## User Credentials Summary

### Quick Reference
```
Admin: admin / Admin@123
Test User 1: testuser1 / Test@123
Test User 2: testuser2 / Test@123
All Regular Users: {username} / password123
```

### Accessing Regular Users
To log in as any regular user:
1. Check the credentials output when running the command
2. Use the displayed username with password `password123`
3. First 5 regular users are shown in the output

## Data Distribution

### Course Distribution
Users are randomly distributed across all 29 courses, ensuring:
- Each course has students from different years
- Realistic class sizes
- Mix of academic disciplines

### Year Distribution  
Users are randomly assigned to years 1-4 within their course:
- Year 1: ~25% of students
- Year 2: ~25% of students
- Year 3: ~25% of students
- Year 4: ~25% of students

### Activity Distribution
- Post creation: Spread over last 60 days
- Engagement: Peaks within 48 hours of post creation
- Follow relationships: Realistic clustering

## Customization

### Modifying User Generation
Edit the `create_users()` method to change:
- Name pools (first_names, last_names lists)
- Bio options (bios list)
- Role distribution (global_role assignment logic)
- Skills/projects likelihood

### Modifying Post Content
Edit the `post_contents` list in `create_posts()` to:
- Add more post variations
- Include course-specific content
- Add different language styles

### Modifying Group Structure
Edit the `create_groups()` method to:
- Add more study groups
- Create school-specific groups
- Adjust official group naming

## Performance Considerations

### Database Size
- 50 users: ~50-100 MB
- 100 users: ~100-200 MB
- 500 users: ~500-1 GB

### Creation Time
- 50 users: ~30-60 seconds
- 100 users: ~60-120 seconds
- 500 users: ~5-10 minutes

### Memory Usage
- Bulk operations used for efficiency
- Transaction wrapping for data integrity
- Minimal memory footprint during creation

## Cleanup

### Removing Seed Data
```bash
python manage.py seed_complete_data --clean
```

This removes:
- All seed data (except superusers)
- All follows, likes, comments, posts
- All group memberships and groups
- All courses, years, schools
- All non-superuser accounts

### Manual Cleanup
```python
# In Django shell
from posts.models import Post, Comment, Like, SharedPost
from users.models import Follow, User
from groups.models import Group, Membership
from messaging.models import Conversation, Message
from courses.models import Course, Year, School

# Clear in dependency order
Message.objects.all().delete()
Conversation.objects.all().delete()
Membership.objects.all().delete()
Group.objects.all().delete()
Follow.objects.all().delete()
SharedPost.objects.all().delete()
Like.objects.all().delete()
Comment.objects.all().delete()
Post.objects.all().delete()
User.objects.filter(is_superuser=False).delete()
Year.objects.all().delete()
Course.objects.all().delete()
School.objects.all().delete()
```

## Troubleshooting

### Command Not Found
```bash
# Ensure __init__.py files exist in:
# - users/management/__init__.py
# - users/management/commands/__init__.py
```

### Database Lock Errors
```bash
# Stop any running Django processes
# Then retry the command
python manage.py seed_complete_data
```

### Import Errors
```bash
# Ensure all apps are installed
python manage.py migrate
# Then retry
python manage.py seed_complete_data
```

## Best Practices

### Development
- Use `--clean` flag when regenerating data
- Start with smaller datasets for testing
- Increase gradually to test performance

### Testing
- Use consistent seed data for reproducible tests
- Create specific test datasets for different scenarios
- Document custom modifications

### Production
- Never use seed commands in production
- Use proper data migration scripts
- Implement proper data validation

## Next Steps

After seeding:
1. Test user login with provided credentials
2. Verify group memberships are correct
3. Check post interactions work properly
4. Test messaging between admin and test users
5. Verify feed shows appropriate content
6. Test profile completion features

## Support

For issues or questions about the seed command:
1. Check Django logs for error messages
2. Verify database migrations are current
3. Ensure all required models exist
4. Check for import errors in custom code
