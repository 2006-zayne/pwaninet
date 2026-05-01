# Database Population Script

This script populates your Django database with comprehensive test data including users, courses, groups, posts, comments, likes, reposts, and shared posts.

## Prerequisites

Make sure you have the required package installed:

```bash
pip install faker
```

## Usage

### Basic Usage (Default Amounts)

```bash
python manage.py populate_db
```

This creates:
- 20 users
- 50 posts
- 10 groups
- 100 comments

### Custom Amounts

You can specify custom numbers for each entity:

```bash
# Create more users and posts
python manage.py populate_db --users 50 --posts 100 --groups 20 --comments 200
```

### Available Options

- `--users NUMBER` - Number of users to create (default: 20)
- `--posts NUMBER` - Number of posts to create (default: 50)
- `--groups NUMBER` - Number of groups to create (default: 10)
- `--comments NUMBER` - Number of comments to create (default: 100)

## What Gets Created

### Users
- 1 Admin user (username: `admin`, password: `admin123`)
- 1 Test user (username: `testuser`, password: `testuser123`)
- Additional random users with:
  - Random names, emails, and bios
  - Assigned to random courses and years
  - Various global roles (NORMAL, VERIFIED, DELEGATE)

### Courses & Years
- 6 courses (CS, IT, Software Engineering, Data Science, Web Dev, Cybersecurity)
- 3 year levels per course
- 4 units per course

### Groups
- Groups for each course
- Random group settings (open/approval/invite join policies)
- Random official/unofficial status
- Random members and roles

### Posts
- Posts with random content
- Randomly assigned to courses/groups
- Random gradient styling
- Distributed across the past 30 days

### Engagement
- **Likes**: 1-15 likes per post, 0-5 likes per comment
- **Comments**: Random comments on posts
- **Reposts**: Reposts of 50% of posts (1-5 reposts each)
- **Shared Posts**: Sharing 1/3 of posts (0-3 shares each)

### Relationships
- User follows (each user follows 3-7 others)
- Group memberships (5-15 members per group)
- Comment interactions

## Example Output

```
🚀 Starting database population...
📚 Creating courses and years...
👥 Creating 20 users...
🔗 Creating user follows...
👫 Creating 10 groups...
📋 Creating group memberships...
📝 Creating 50 posts...
❤️ Creating post likes...
💬 Creating 100 comments...
❤️ Creating comment likes...
🔄 Creating reposts...
📤 Creating shared posts...

✅ Database population completed successfully!
   - Users: 22
   - Courses: 6
   - Groups: 10
   - Posts: 50
   - Comments: 100
   - Likes: 435
   - Reposts: 85
   - Shared Posts: 127
```

## Test Accounts

After running the script, you can login with:

**Admin Account:**
- Username: `admin`
- Password: `admin123`

**Test Account:**
- Username: `testuser`
- Password: `testuser123`

## Cleaning Up

To delete all test data and start fresh:

```bash
python manage.py flush
```

This will delete all data from the database and you can run the population script again.

## Notes

- Usernames are automatically made unique by appending numbers
- The script uses `get_or_create()` to avoid duplicates
- Timestamps are distributed across the past 30 days for realistic data
- All users have the password `testpass123` (except admin and testuser)
- Group creators are automatically added as ADMIN members
