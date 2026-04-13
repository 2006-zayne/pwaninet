from django.shortcuts import render, get_object_or_404, redirect 
from django.contrib.auth.decorators import login_required
from .models import Post, Unit, Course ,Year ,User ,Notifications ,Groups ,Like ,Follow
from .forms import PwaniSignupForm ,PostForm , ProfileUpdateForm ,GroupForm
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.db.models import Q ,Count
import random
from django.http import JsonResponse  ,HttpResponse


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


    # pwaninet/core/views.py

@login_required
def home_view(request):
    user = request.user
    suggestions = get_suggestions(request)
    following_ids = user.following.values_list('id', flat=True)
    suggested_groups = Groups.objects.filter(members__id__in=following_ids).exclude(members=user).distinct()[:5]

    feed_query = Post.objects.filter(
        Q(group__isnull=True) | 
        Q(group__members=user) | 
        Q(course=user.course, unit__year=user.year)
    ).distinct().order_by('?') # Randomize at DB level

    posts_qs = feed_query.select_related('author', 'unit').prefetch_related('likes')
    
    # Take a slice and convert to list
    posts = list(posts_qs[:40])
    
    # Shuffle or sample if the pool is large enough
    if len(posts) > 10:
        # random.sample provides a random subset WITHOUT re-sorting them by date
        posts = random.sample(posts, k=min(len(posts), 15))


    liked_post_ids = Like.objects.filter(
        user=user, 
        post__in=posts
    ).values_list('post_id', flat=True)

    return render(request, 'home.html', {
        'posts': posts,
        'suggested_groups': suggested_groups,
        'suggestions': suggestions,
        'liked_post_ids': liked_post_ids,
        'title': 'PwaniNet Command Feed',
    })

@login_required
def notifications_list(request):
    """
    Retrieves and displays all intelligence alerts for the current operative.
    Orders by most recent timestamp.
    """
    # Fetch all notifications for the user
    my_notifs = request.user.notifications.all().order_by('-timestamp')

    my_notifs.filter(is_read=False).update(is_read=True)
    
    context = {
        'notifications': my_notifs,
    }
    
    return render(request, 'notifications.html', context)

def unread_notification_count(request):
    """Tactical update for the navbar badge via HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse("")
        
    count = request.user.notifications.filter(is_read=False).count()
    
    # We return just the internal HTML of the link to update the badge
    html = f'<i class="bi bi-bell-fill"></i>'
    if count > 0:
        html += f'''
            <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger border border-light" 
                  style="font-size: 0.6rem; padding: 0.35em 0.5em;">
                {count}
            </span>'''
    return HttpResponse(html)

@login_required
def mark_notification_as_read(request, notif_id):
    """
    Marks a single notification as read and removes it from the UI.
    """
    notification = get_object_or_404(Notifications, id=notif_id, recipient=request.user)
    notification.is_read = True
    notification.save()

    # AMMO: Trigger the navbar to refresh the unread count
    response = HttpResponse("") # Returning empty string removes the element if hx-swap is 'outerHTML'
    response['HX-Trigger'] = 'notificationUpdate'
    return response

@login_required
def mark_all_as_read(request):
    # 1. Neutralize all unread intelligence alerts
    Notifications.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    
    # 2. Retrieve updated list (FIXED: changed order_index to order_by)
    notifications = Notifications.objects.filter(recipient=request.user).order_by('-timestamp')
    
    # 3. Deploy the partial to the UI
    # IMPORTANT: Ensure templates/partials/notification_list_items.html exists!
    response = render(request, 'partials/notification_list_items.html', {'notifications': notifications})
    
    # 4. SIGNAL: Trigger the navbar badge to refresh immediately
    response['HX-Trigger'] = 'notificationUpdate'
    return response

@login_required
def invite_to_group(request, group_id, user_id):
    group = get_object_or_404(Groups, id=group_id)
    target_user = get_object_or_404(User, id=user_id)
    
    # Check if target is already in the sector
    if target_user not in group.members.all():
        # Check if an invite is already pending to avoid spam
        exists = Notifications.objects.filter(
            recipient=target_user, 
            group=group, 
            notification_type='INVITE'
        ).exists()
        
        if not exists:
            Notifications.objects.create(
                recipient=target_user,
                sender=request.user,
                group=group,
                notification_type='INVITE',
                msg=f"wants you to join the sector: {group.name}"
            )
    
    return redirect('groups_detail', group_id=group.id)


@login_required
def respond_to_invite(request, notif_id, action):
    notification = get_object_or_404(Notifications, id=notif_id, recipient=request.user)
    
    if action == 'accept' and notification.group:
        notification.group.members.add(request.user)

    else :
        return redirect('notifications')
    
    # Task complete: terminate the notification
    notification.delete()
    return redirect('notifications')

# --- GROUP & UNIT LOGIC ---

@login_required
def groups_dashboard(request):
    user = request.user
    
    # We use the members=user to find the groups that the user part of remember the user is the one using the site.
    user_groups = Groups.objects.filter(members=user)

    # We use'exclude" to filter out the groups that I'm in.
    # REMOVED course/year filters because they don't exist in your model yet
    all_groups = Groups.objects.all().exclude(members=user)

    # Suggested groups based on following
    following_ids = user.following.values_list('id', flat=True)
    suggested_groups = Groups.objects.filter(
        members__id__in=following_ids
    ).exclude(members=user).distinct()[:10]#We won't suggest a group that I'm one of the users.

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
    
    # Track existing connections for the "Follow" button toggle
    following_ids = request.user.following.values_list('id', flat=True)

    # RECRUITMENT RADAR
    query = request.GET.get('search_user')
    search_results = None
    if query:
        search_results = User.objects.filter(
            username__icontains=query
        ).exclude(id__in=group.members.all())[:10]

    return render(request, 'groups_detail.html', {
        'group': group,
        'posts': group_posts,
        'is_member': is_member,
        'search_results': search_results,
        'query': query,
        'following_ids': following_ids,
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
    group_id = request.GET.get('group')  or request.POST.get('group')# Capture the sector ID from the URL
    
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, user=user)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = user

            # FORCE GROUP ATTACHMENT
            # This ensures the relationship is built even if the field is hidden in the form
            if group_id:
                post.group = get_object_or_404(Groups, id=group_id)

            # ENSURE DUAL VISIBILITY (Home Feed + Group)
            # Stamping with course/year ensures it appears on the home feed
            post.course = user.course
            post.year = user.year 
            
            if post.unit:
                post.course = post.unit.course

            post.save()
            form.save_m2m() # Critical for saving likes/tags
        
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
        # Pass the group into initial data so the form knows about it during GET
        initial_data = {}
        if group_id:
            initial_data['group'] = get_object_or_404(Groups, id=group_id)
        
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
    """
    Tactical Toggle: Manages the follower-followed relationship 
    and triggers automated notifications via signals.
    """
    target_user = get_object_or_404(User, username=username)
    
    if target_user == request.user:
        return JsonResponse({"error": "Self-following is prohibited."}, status=400)

    # Tactical Check: Query the dedicated Follow model
    follow_qs = Follow.objects.filter(follower=request.user, followed=target_user)
    
    if follow_qs.exists():
        # Objective: Termination of following relationship
        follow_qs.delete()
        request.user.following.remove(target_user) # Keep M2M in sync
        is_following = False
    else:
        # Objective: Establishment of new following relationship
        # This create() call triggers the post_save signal in signals.py
        Follow.objects.create(follower=request.user, followed=target_user)
        request.user.following.add(target_user) # Keep M2M in sync
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
def post_detail_view(request, post_id):
    """
    Tactical View: Displays a single intelligence update in full detail.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # Check if the current user has liked this specific post
    is_liked = post.likes.filter(user=request.user).exists()
    
    return render(request, 'post_detail.html', {
        'post': post,
        'is_liked': is_liked,
    })


@login_required
def post_likers_list(request, post_id):
    """
    Tactical Retrieval: Fetches the manifest of all operatives who liked the intel.
    """
    post = get_object_or_404(Post, id=post_id)
    
    # We grab the 'Like' objects and select the related 'user' to avoid crash
    # Then we extract the users from those likes
    likes = post.likes.select_related('user').all()
    likers = [like.user for like in likes]
    
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

@login_required
def edit_group(request, group_id):
    group = get_object_or_404(Groups, id=group_id)
    
    # Security Check: Only the creator can modify sector intel
    if request.user != group.creator:
        return redirect('groups_detail', group_id=group.id)

    if request.method == 'POST':
        group.name = request.POST.get('name')
        group.description = request.POST.get('description')
        
        # Check if a new photo was uploaded
        if 'photo' in request.FILES:
            group.group_profile_pic = request.FILES['photo']
            
        group.save()
        return redirect('group_detail', group_id=group.id)
    
    return redirect('groups_detail', group_id=group.id)

@login_required
def invite_to_group(request, group_id, user_id):
    group = get_object_or_404(Groups, id=group_id)
    target_user = get_object_or_404(User, id=user_id)
    
    # Security check: Only members can invite others
    if request.user in group.members.all():
        if target_user not in group.members.all():
            group.members.add(target_user)
            # Optional: Add a success message here later
        if target_user != request.user:
            Notifications.objects.create(
                recipient=target_user,
                sender=request.user,
                msg=f"{request.user.first_name} invited you to join a group :{ group.name }"
            )


    # Redirect back to the sector briefing
    return redirect('groups_detail', group_id=group.id)