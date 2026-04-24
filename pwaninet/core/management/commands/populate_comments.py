from django.core.management.base import BaseCommand
from core.models import Comment, Post, User
import random
from faker import Faker

fake = Faker()

# Sample comment templates
COMMENT_TEMPLATES = [
    "This is so helpful! Thanks for sharing 🙌",
    "I completely agree with this take",
    "Can you elaborate more on this? Would love to understand better",
    "This just made my day! 😄",
    "Great perspective. Never thought of it this way",
    "100% agree with you on this",
    "This is exactly what I needed to hear",
    "Mind blown 🤯",
    "Saving this for later. Very useful!",
    "Well said! You captured it perfectly",
    "This is gold. Keep posting content like this",
    "Your explanation is so clear. Thanks!",
    "Couldn't have said it better myself",
    "This deserves more recognition 👏",
    "Fighting for this viewpoint! Great post",
    "Pure brilliance right here",
    "This should be taught in class ngl",
    "Finally someone said it",
    "Take a bow, this is amazing",
    "This is the post I've been looking for",
    "Absolutely love the energy here",
    "This is genuinely insightful",
    "You're speaking facts no cap",
    "This hits different fr fr 💯",
    "Genuine wisdom right here",
    "This deserves an award",
    "Comment saved. This is too good",
    "Why isn't this getting more views?",
    "This should be pinned",
    "Underrated post for sure",
    "This is everything I needed today",
    "Your content never misses",
    "This is the kind of energy we need",
    "Respect the thought process here",
    "This is genuinely helpful, thank you",
    "Can relate to this on so many levels",
    "This perspective is refreshing",
    "Love how you approached this",
    "This makes so much sense now",
    "Couldn't agree more with this take",
    "This is what peak performance looks like",
    "You deserve a medal for this post",
    "This is going to help me so much",
    "The accuracy is unmatched",
    "This is the reality check I needed",
    "Genuinely one of the best posts here",
    "This hits home fr",
    "Absolutely on point with everything you said",
    "This deserves to go viral",
    "Best thing I've read all day",
    "Post of the year material right here"
]

class Command(BaseCommand):
    help = 'Populate database with random comments on existing posts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--per-post',
            type=int,
            default=3,
            help='Average number of comments per post (default: 3)'
        )

    def handle(self, *args, **options):
        per_post = options['per_post']
        
        # Get all posts
        posts = list(Post.objects.all())
        if not posts:
            self.stdout.write(self.style.ERROR('No posts found. Create some posts first!'))
            return
        
        # Get all users
        users = list(User.objects.all())
        if not users:
            self.stdout.write(self.style.ERROR('No users found. Create some users first!'))
            return
        
        created_comments = 0
        total_posts = len(posts)
        
        self.stdout.write(self.style.SUCCESS(f'Creating comments on {total_posts} posts (avg {per_post} per post)...'))
        
        for idx, post in enumerate(posts):
            try:
                # Random number of comments for this post (between 0 and per_post*2)
                num_comments = random.randint(0, per_post * 2)
                
                # Create comments on this post
                for i in range(num_comments):
                    try:
                        # Pick random user as commenter
                        commenter = random.choice(users)
                        
                        # Don't let the post author comment their own post (most of the time)
                        if commenter == post.author and random.random() < 0.7:
                            commenter = random.choice([u for u in users if u != post.author])
                        
                        # Generate comment content
                        content = random.choice(COMMENT_TEMPLATES)
                        
                        # Create comment
                        Comment.objects.create(
                            post=post,
                            author=commenter,
                            content=content
                        )
                        
                        created_comments += 1
                        
                    except Exception as e:
                        pass  # Skip if error
                
                if (idx + 1) % 10 == 0:
                    self.stdout.write(f'Processed {idx + 1}/{total_posts} posts...')
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Error on post {idx + 1}: {str(e)}'))
                continue
        
        # Get updated stats
        total_comments = Comment.objects.count()
        avg_comments_per_post = total_comments / total_posts if total_posts > 0 else 0
        
        self.stdout.write(
            self.style.SUCCESS(f'\n✅ Successfully created {created_comments} comments!')
        )
        
        # Show summary
        self.stdout.write(f'\n📊 Stats:')
        self.stdout.write(f'   Total posts: {total_posts}')
        self.stdout.write(f'   Total comments: {total_comments}')
        self.stdout.write(f'   Average comments per post: {avg_comments_per_post:.1f}')
