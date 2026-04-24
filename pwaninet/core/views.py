from django.shortcuts import render, get_object_or_404, redirect 
from django.contrib.auth.decorators import login_required
from .models import Post, Unit, Year ,User ,Notifications ,Groups ,Follow ,Comment
from .forms import PwaniSignupForm ,PostForm , ProfileUpdateForm ,GroupForm
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.http import JsonResponse  ,HttpResponse
from django.urls import reverse
from core.queries.profile_queries import get_followers_count
from core.services.comment_service import (
    build_comments_context,
    handle_add_comment_request,
    toggle_comment_like_for_user,
)
from .services.feed_service import build_home_feed_context, invalidate_home_feed_context
from .services.group_service import (
    build_group_detail_context,
    build_groups_dashboard_context,
)
from .services.notification_service import (
    build_notifications_context,
    build_unread_notification_html,
    invalidate_unread_count_cache,
    mark_single_notification_as_read,
)
from .services.profile_service import build_profile_context
from core.services.post_service import (
    create_post_for_user,
    prepare_post_form_initial,
    toggle_post_like_for_user,
)
from .services.search_service import build_search_context


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
    context = build_profile_context(request.user, user_profile)
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
    context = build_home_feed_context(request.user, page=1)
    return render(request, 'home.html', context)


@login_required
def home_feed_page(request):
    page = request.GET.get("page", 1)
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1

    context = build_home_feed_context(request.user, page=page)
    return render(request, "partials/feed_posts_page.html", context)

@login_required
def notifications_list(request):
    """
    Retrieves and displays all intelligence alerts for the current operative.
    Orders by most recent timestamp.
    """
    context = build_notifications_context(request.user, mark_read=False)
    return render(request, 'notifications.html', context)

def unread_notification_count(request):
    """Tactical update for the navbar badge via HTMX."""
    if not request.user.is_authenticated:
        return HttpResponse("")
    
    html = build_unread_notification_html(request.user)
    return HttpResponse(html)

@login_required
def mark_notification_as_read(request, notif_id):
    """
    Marks a single notification as read and removes it from the UI.
    """
    if request.method != "POST":
        return HttpResponse("", status=405)

    notification = mark_single_notification_as_read(request.user, notif_id)
    if notification is None:
        return HttpResponse("", status=404)

    # AMMO: Trigger the navbar to refresh the unread count
    response = HttpResponse("") # Returning empty string removes the element if hx-swap is 'outerHTML'
    response['HX-Trigger'] = 'notificationUpdate'
    return response

@login_required
def mark_all_as_read(request):
    if request.method != "POST":
        return HttpResponse("", status=405)

    context = build_notifications_context(request.user, mark_read=True)
    response = render(request, 'partials/notification_list_items.html', context)
    
    # 4. SIGNAL: Trigger the navbar badge to refresh immediately
    response['HX-Trigger'] = 'notificationUpdate'
    return response

@login_required
def invite_to_group(request, group_id, user_id):
    if request.method != "POST":
        return HttpResponse("", status=405)

    group = get_object_or_404(Groups, id=group_id)
    target_user = get_object_or_404(User, id=user_id)
    
    # Check if target is already in the sector
    if request.user not in group.members.all():
        return HttpResponse("", status=403)

    if target_user not in group.members.all() and target_user != request.user:
        # Check if an invite is already pending to avoid spam
        exists = Notifications.objects.filter(
            recipient=target_user, 
            sender=request.user,
            group=group, 
            notification_type='INVITE',
            is_read=False,
        ).exists()
        
        if not exists:
            Notifications.objects.create(
                recipient=target_user,
                sender=request.user,
                group=group,
                notification_type='INVITE',
                msg=f"wants you to join the sector: {group.name}"
            )
            invalidate_unread_count_cache(target_user.id)
    
    return redirect('groups_detail', group_id=group.id)


@login_required
def respond_to_invite(request, notif_id, action):
    if request.method != "POST":
        return HttpResponse("", status=405)

    notification = get_object_or_404(Notifications, id=notif_id, recipient=request.user)
    
    if action == 'accept' and notification.group:
        notification.group.members.add(request.user)
        invalidate_home_feed_context(request.user.id)
    elif action != "decline":
        return HttpResponse("", status=400)
    
    # Task complete: terminate the notification
    notification.delete()
    invalidate_unread_count_cache(request.user.id)
    return redirect('notifications')


@login_required
def notification_redirect(request, notif_id):
    notification = get_object_or_404(Notifications, id=notif_id, recipient=request.user)

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        invalidate_unread_count_cache(request.user.id)

    if notification.notification_type == Notifications.INVITE and notification.group_id:
        return redirect(f"{reverse('notifications')}#notification-{notification.id}")

    if notification.post_id:
        return redirect('post_details', post_id=notification.post_id)

    if notification.notification_type == Notifications.FOLLOW:
        return redirect('profile', username=notification.sender.username)

    return redirect('notifications')

# --- GROUP & UNIT LOGIC ---

@login_required
def groups_dashboard(request):
    context = build_groups_dashboard_context(request.user)
    return render(request, 'groups_dashboard.html', context)

@login_required
def groups_detail_view(request, group_id):
    group = get_object_or_404(Groups, id=group_id)
    query = request.GET.get('search_user')
    context = build_group_detail_context(request.user, group, query)
    return render(request, 'groups_detail.html', context)

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
            post = create_post_for_user(form, user, group_id=group_id)
            messages.success(request, "Intelligence deployed successfully.")
            return redirect('groups_detail', group_id=post.group.id) if post.group else redirect('home')
    else:
        form = PostForm(user=user, initial=prepare_post_form_initial(group_id))

    return render(request, 'create_post.html', {'form': form})

@login_required
def toggle_like(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    context = toggle_post_like_for_user(post, request.user)
    return render(request, 'partials/like_button.html', context)

# --- UTILITIES ---

@login_required
def toggle_follow(request, username):
    """
    Tactical Toggle: Manages the follower-followed relationship 
    and triggers automated notifications via signals.
    """
    target_user = get_object_or_404(User, username=username)
    
    if target_user == request.user:
        return JsonResponse({"error": "Self-following is prohibited."}, status=400)

    # Query the dedicated Follow model
    follow_qs = Follow.objects.filter(follower=request.user, followed=target_user)
    
    if follow_qs.exists():
        # Termination of following relationship
        follow_qs.delete()
        #follow_qs.delete()
       # request.user.following.remove(target_user) # Keep M2M in sync
        is_following = False
    else:
        # Establishment of new following relationship
        # This create() call triggers the post_save signal in signals.py
        Follow.objects.get_or_create(follower=request.user, followed=target_user)
        #request.user.following.add(target_user) # Keep M2M in sync
        is_following = True
    invalidate_home_feed_context(request.user.id)
    invalidate_home_feed_context(target_user.id)

    return JsonResponse({
        "is_following": is_following,
        "follower_count": get_followers_count(target_user),
    })

@login_required
def add_comment(request, post_id):
    """
    Handle adding a new comment to a post.
    """
    if request.method != 'POST':
        return HttpResponse("", status=405)
    
    post = get_object_or_404(Post, id=post_id)
    handle_add_comment_request(request, post)
    return redirect('post_details', post_id=post_id)


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
    show_all_comments = request.GET.get("all_comments") == "1"
    comments_context = build_comments_context(post, request.user, show_all_comments=show_all_comments)
    
    # Check if the current user has liked this specific post
    is_liked = post.likes.filter(user=request.user).exists()
    
    return render(request, 'post_detail.html', {
        'post': post,
        'is_liked': is_liked,
        **comments_context,
    })


@login_required
def post_comments_panel(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    show_all_comments = request.GET.get("all_comments") == "1"
    context = build_comments_context(post, request.user, show_all_comments=show_all_comments)
    return render(request, 'partials/post_comments_section.html', context)


@login_required
def toggle_comment_like(request, comment_id):
    if request.method != "POST":
        return HttpResponse("", status=405)

    comment = get_object_or_404(Comment.objects.select_related('post'), id=comment_id)
    context = toggle_comment_like_for_user(comment, request.user)
    return render(request, 'partials/comment_like_button.html', context)


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
    invalidate_home_feed_context(request.user.id)
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
        return redirect('groups_detail', group_id=group.id)
    
    return redirect('groups_detail', group_id=group.id)

@login_required
def search_results(request):
    context = build_search_context(request.user, request.GET.get('q', ''))
    
    # Check if it's an AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render(request, 'partials/search_results_content.html', context)
    return render(request, 'search_results.html', context)


@login_required
def follow_user(request, user_id):
    """
    Handle following/unfollowing a user via AJAX.
    Returns JSON response with success status.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
    
    try:
        target_user = get_object_or_404(User, id=user_id)
        
        # Prevent following yourself
        if target_user.id == request.user.id:
            return JsonResponse({'success': False, 'message': 'You cannot follow yourself'}, status=400)
        
        # Check if already following
        follow_qs = Follow.objects.filter(follower=request.user, followed=target_user)
        
        if follow_qs.exists():
            # Already following, so unfollow
            follow_qs.delete()
            message = 'Unfollowed successfully'
            is_following = False
        else:
            # Not following, so follow
            Follow.objects.create(follower=request.user, followed=target_user)
            
            # Create notification for the followed user
            Notifications.objects.create(
                recipient=target_user,
                sender=request.user,
                notification_type=Notifications.FOLLOW,
                msg=f"started following you"
            )
            invalidate_unread_count_cache(target_user.id)
            
            message = 'Followed successfully'
            is_following = True
        
        # Invalidate feed cache for the follower
        invalidate_home_feed_context(request.user.id)
        
        # Invalidate friend suggestions cache so followed user is removed from suggestions
        from core.services.friend_suggestion_service import invalidate_friend_suggestions_cache
        invalidate_friend_suggestions_cache(request.user.id)
        
        return JsonResponse({
            'success': True,
            'message': message,
            'is_following': is_following,
            'user_id': user_id
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return render(request, 'search_results.html', context)
