from django.shortcuts import render, get_object_or_404, redirect 
from django.contrib.auth.decorators import login_required
from .models import Post, Unit, Course ,Year ,User ,Notifications ,Groups ,Like
from .forms import PwaniSignupForm ,PostForm , ProfileUpdateForm ,GroupForm
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q ,Count
import random
from django.http import JsonResponse


User = get_user_model()

# --- REGISTRATION & PROFILE ---

def register_view(request):
    if request.method == 'POST':
        form = PwaniSignupForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account successfully registered.")
            return redirect('login')
    else:
        form = PwaniSignupForm()
    return render(request, 'register.html', {'form': form})



def load_years(request):
    course_id = request.GET.get('course')
    # Fetch only the years assigned to the selected course
    years = Year.objects.filter(course_id=course_id).order_by('level')
    
    # We return a partial HTML snippet, not a full page
    return render(request, 'partials/year_options.html', {'years': years})

@login_required
def profile_view(request, username):
    user_profile = get_object_or_404(User, username=username)
    is_following = request.user.following.filter(id=user_profile.id).exists()
    
    # Calculate Impact (Total Likes received across all posts)
    total_likes = Post.objects.filter(author=user_profile).aggregate(total=Count('likes'))['total'] or 0
    
    user_posts = user_profile.posts.all().order_by('-date')

    context = {
        'profile_user': user_profile,
        'following_count': user_profile.following.count(),
        'followers_count': user_profile.followers.count(),
        'total_likes': total_likes, # Added this to the context
        'posts': user_posts,
        'is_following': is_following,
    }
    return render(request, 'profile.html', context)

@login_required
def update_profile_view(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile' , username=request.user.username)
    else:
        form = ProfileUpdateForm(instance=request.user)
    return render(request, 'update_profile.html', {'form': form})

# --- FEED & NOTIFICATIONS ---

@login_required
def post_list_view(request):
    user = request.user
    suggestions = get_suggestions(request)
    following_ids = user.following.values_list('id', flat=True)
    suggested_groups = Groups.objects.filter(members__id__in=following_ids).exclude(members=user).distinct()[:5]

    feed_query = Post.objects.filter(
        Q(group__isnull=True) | 
        Q(group__members=user) | 
        Q(course=user.course, unit__year=user.year)
    ).distinct().order_by('-date')

    # Optimization: select_related/prefetch_related to speed up loading
    posts_qs = feed_query.select_related('author', 'unit').prefetch_related('likes')
    
    posts = list(posts_qs[:40])
    if len(posts) > 10:
        posts = random.sample(posts, k=min(len(posts), 15))
        posts.sort(key=lambda x: x.date, reverse=True)

    # NEW: Identify which intel the operative has already liked
    # This checks your 'Like' model for all posts in the current feed
    liked_post_ids = Like.objects.filter(
        user=user, 
        post__in=posts
    ).values_list('post_id', flat=True)

    return render(request, 'home.html', {
        'posts': posts,
        'suggested_groups': suggested_groups,
        'suggestions': suggestions,
        'liked_post_ids': liked_post_ids, # Pass this to the template
        'title': 'PwaniNet Command Feed',
    })

@login_required
def notifications_list(request):
    my_notifs = request.user.notifications.all().order_by('-timestamp')
    my_notifs.filter(is_read=False).update(is_read=True)
    return render(request, 'notifications.html', {'notifications': my_notifs})

# --- GROUP & UNIT LOGIC ---

@login_required
def groups_dashboard(request):
    user = request.user
    
    # Use 'members' to find groups the user is in
    user_groups = Groups.objects.filter(members=user)

    # Use 'exclude' to find groups the user is NOT in
    # REMOVED course/year filters because they don't exist in your model yet
    all_groups = Groups.objects.all().exclude(members=user)

    # Suggested groups based on following
    following_ids = user.following.values_list('id', flat=True)
    suggested_groups = Groups.objects.filter(
        members__id__in=following_ids
    ).exclude(members=user).distinct()[:5]

    return render(request, 'groups_dashboard.html', {
        'user_groups': user_groups,
        'all_groups': all_groups,
        'suggested_groups': suggested_groups,
    })

@login_required
def groups_detail_view(request, group_id):
    group = get_object_or_404(Groups, id=group_id)
    group_posts = Post.objects.filter(group=group).order_by('-date')
    is_member = group.members.filter(id=request.user.id).exists()

    return render(request, 'groups_detail.html', {
        'group': group,
        'posts': group_posts,
        'is_member': is_member,
    })

@login_required
def create_group_view(request):
    if request.method == 'POST':
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save(commit=False)
            group.is_official = False 
            group.save()
            group.members.add(request.user)
            return redirect('groups_dashboard')
    else:
        form = GroupForm()
    return render(request, 'create_group.html', {'form': form})

# --- POST CREATION & INTERACTION ---

@login_required
def create_post_view(request):
    user = request.user
    # Support for ?group=ID in URL
    group_id = request.GET.get('group')
    initial_data = {}
    
    if group_id:
        group = get_object_or_404(Groups, id=group_id)
        initial_data['group'] = group

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = user
            
            # If the user selected a group in the form
            if post.group and post.group.is_official:
                post.course = user.course 
            
            if post.unit:
                post.course = post.unit.course

            post.save()
        
            # Notification Deployment
            if post.group:
                recipients = post.group.members.exclude(id=user.id)
                msg_text = f"posted in the {post.group.name} squad."
            else:
                recipients = User.objects.filter(course=user.course, year=user.year).exclude(id=user.id)
                msg_text = "posted a new update in the global feed."

            notif_list = [Notifications(recipient=student, sender=user, msg=msg_text) for student in recipients]
            Notifications.objects.bulk_create(notif_list)

            messages.success(request, "Intelligence deployed successfully.")
            return redirect('groups_detail', group_id=post.group.id) if post.group else redirect('home')
    else:
        form = PostForm(user=user, initial=initial_data)

    return render(request, 'create_post.html', {'form': form})

@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    like_qs = Like.objects.filter(user=request.user, post=post)

    if like_qs.exists():
        like_qs.delete()
        is_liked = False
    else:
        Like.objects.create(user=request.user, post=post)
        is_liked = True
        if post.author != request.user:
            Notifications.objects.create(
                recipient=post.author,
                sender=request.user,
                msg=f"liked your intelligence update: '{post.content[:20]}...'"
            )

    return render(request, 'partials/like_button.html', {
        'post': post, 'is_liked': is_liked, 'like_count': post.likes.count()
    })

# --- UTILITIES ---

def get_suggestions(request):
    user = request.user
    already_following = user.following.values_list('id', flat=True)
    my_groups = user.joined_groups.all() # Corrected to your joined_groups relation
    return User.objects.filter(joined_groups__in=my_groups).exclude(
        Q(id__in=already_following) | Q(id=user.id)
    ).distinct()[:5]

@login_required
def toggle_follow(request, username):
    target_user = get_object_or_404(User, username=username)
    
    if target_user == request.user:
        return JsonResponse({"error": "Self-following is prohibited."}, status=400)

    if target_user in request.user.following.all():
        request.user.following.remove(target_user)
        is_following = False
    else:
        request.user.following.add(target_user)
        is_following = True

    return JsonResponse({
        "is_following": is_following,
        "follower_count": target_user.followers.count()
    })

@login_required
def unit_posts_view(request, unit_id):
    target_unit = get_object_or_404(Unit, id=unit_id)
    posts = Post.objects.filter(unit=target_unit).order_by('-date')
    return render(request, 'unit_detail.html', {'unit': target_unit, 'posts': posts})

@login_required
def post_likers_list(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    likers = post.likes.all().select_related('user')
    return render(request, 'partials/likers_modal_content.html', {'likers': likers})

@login_required
def toggle_group_membership(request, group_id):
    group = get_object_or_404(Groups, id=group_id)
    if group.members.filter(id=request.user.id).exists():
        group.members.remove(request.user)
        messages.info(request, f"You have left the {group.name} squad.")
    else:
        group.members.add(request.user)
        messages.success(request, f"You have joined the {group.name} squad.")
    return redirect('groups_detail', group_id=group.id)