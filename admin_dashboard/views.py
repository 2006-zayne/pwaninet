from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import FeedbackTicket, FeedbackReply, UserDailyActivity
from notifications.events.publisher import EventPublisher
from notifications.events.registry import EventSources, EventTypes
from django.contrib.auth import get_user_model
from posts.models import Report
from groups.models import Group
from posts.models import Post

from django.db.models import Count
from django.db.models.functions import TruncDate
from datetime import timedelta
import json

User = get_user_model()

def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    unread_feedback_count = FeedbackTicket.objects.filter(status=FeedbackTicket.Status.UNREAD).count()
    open_tickets_count = FeedbackTicket.objects.filter(status__in=[FeedbackTicket.Status.OPEN, FeedbackTicket.Status.IN_PROGRESS]).count()
    
    total_users = User.objects.count()
    pending_reports = Report.objects.filter(status=Report.Status.PENDING).count()
    
    recent_feedback = FeedbackTicket.objects.filter(status=FeedbackTicket.Status.UNREAD).order_by('-created_at')[:5]
    
    # Generate data for the last 14 days
    now = timezone.now()
    today = timezone.localdate(now)
    active_since = now - timedelta(minutes=5)
    online_users = UserDailyActivity.objects.filter(
        activity_date=today,
        last_seen_at__gte=active_since,
    ).values('user_id').distinct().count()
    daily_active_users = UserDailyActivity.objects.filter(
        activity_date=today,
    ).values('user_id').distinct().count()
    fourteen_days_ago = today - timedelta(days=13)
    
    # 1. User Growth (New signups per day)
    growth_qs = User.objects.filter(date_joined__date__gte=fourteen_days_ago, date_joined__date__lte=today)\
        .annotate(day=TruncDate('date_joined', tzinfo=timezone.get_current_timezone()))\
        .values('day')\
        .annotate(count=Count('id'))\
        .order_by('day')
        
    growth_dict = {str(item['day']): item['count'] for item in growth_qs}
    
    # 2. Daily active users from authenticated request heartbeats.
    active_qs = UserDailyActivity.objects.filter(
        activity_date__gte=fourteen_days_ago,
        activity_date__lte=today,
    ).values('activity_date').annotate(count=Count('user_id', distinct=True)).order_by('activity_date')

    active_dict = {str(item['activity_date']): item['count'] for item in active_qs}
    
    # Fill in missing days
    labels = []
    growth_data = []
    active_data = []
    for i in range(14):
        d = fourteen_days_ago + timedelta(days=i)
        d_str = str(d)
        labels.append(d.strftime('%b %d'))
        growth_data.append(growth_dict.get(d_str, 0))
        active_data.append(active_dict.get(d_str, 0))
    
    context = {
        'unread_feedback_count': unread_feedback_count,
        'open_tickets_count': open_tickets_count,
        'total_users': total_users,
        'online_users': online_users,
        'daily_active_users': daily_active_users,
        'pending_reports': pending_reports,
        'recent_feedback': recent_feedback,
        'chart_labels': json.dumps(labels),
        'growth_data': json.dumps(growth_data),
        'active_data': json.dumps(active_data),
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'admin_dashboard/partials/dashboard_content.html', context)
    return render(request, 'admin_dashboard/dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def feedback_inbox(request):
    status_filter = request.GET.get('status')
    tickets = FeedbackTicket.objects.all().order_by('-created_at')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
        
    context = {
        'tickets': tickets,
        'current_filter': status_filter
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'admin_dashboard/partials/inbox_content.html', context)
    return render(request, 'admin_dashboard/inbox.html', context)


@login_required
@user_passes_test(is_admin)
def feedback_detail(request, ticket_id):
    ticket = get_object_or_404(FeedbackTicket, id=ticket_id)
    
    if ticket.status == FeedbackTicket.Status.UNREAD:
        ticket.status = FeedbackTicket.Status.OPEN
        ticket.save()
        
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            reply = FeedbackReply.objects.create(
                ticket=ticket,
                sender=request.user,
                message=message
            )
            ticket.status = FeedbackTicket.Status.IN_PROGRESS
            ticket.save()
            
            # Send notification
            EventPublisher.publish(
                event_type="admin.feedback.replied",
                source=EventSources.ADMIN.value,
                action="replied",
                target_type="FeedbackTicket",
                target_id=str(ticket.id),
                actor=request.user,
                context_type="Feedback",
                context_id=str(ticket.id),
                metadata={
                    "user_id": ticket.sender.id,
                    "ticket_id": str(ticket.id),
                    "context_name": ticket.subject
                }
            )
            
            messages.success(request, "Reply sent successfully.")
            return redirect('admin_dashboard:feedback_detail', ticket_id=ticket.id)
            
    context = {
        'ticket': ticket,
        'replies': ticket.replies.all()
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'admin_dashboard/partials/ticket_detail_content.html', context)
    return render(request, 'admin_dashboard/ticket_detail.html', context)


@login_required
def submit_feedback(request):
    if request.method == 'POST':
        subject = request.POST.get('subject', '').strip()
        category = request.POST.get('category', FeedbackTicket.Category.OTHER)
        message = request.POST.get('message', '').strip()
        current_url = request.POST.get('current_url', '').strip()[:500]
        device_info = request.META.get('HTTP_USER_AGENT', '')

        error_message = None
        if not subject:
            error_message = 'Add a short subject so we can identify your feedback.'
        elif len(subject) > 255:
            error_message = 'Keep the subject under 256 characters.'
        elif not message:
            error_message = 'Write a message before submitting.'
        elif len(message) > 10000:
            error_message = 'Keep your message under 10,000 characters.'
        elif category not in FeedbackTicket.Category.values:
            category = FeedbackTicket.Category.OTHER

        if error_message:
            return render(request, 'admin_dashboard/partials/feedback_composer.html', {
                'error_message': error_message,
                'category_choices': FeedbackTicket.Category.choices,
                'form_values': {
                    'category': category,
                    'subject': subject,
                    'message': message,
                    'current_url': current_url,
                },
            })

        ticket = FeedbackTicket.objects.create(
            sender=request.user,
            subject=subject,
            category=category,
            message=message,
            current_url=current_url,
            device_info=device_info,
        )
        EventPublisher.publish(
            event_type=EventTypes.ADMIN_FEEDBACK_SUBMITTED.value,
            source=EventSources.ADMIN.value,
            action='submitted',
            target_type='FeedbackTicket',
            target_id=str(ticket.id),
            actor=request.user,
            context_type='FeedbackTicket',
            context_id=str(ticket.id),
            audience='ADMINISTRATORS',
            metadata={
                'ticket_id': str(ticket.id),
                'context_name': ticket.subject,
            },
        )
        return render(request, 'admin_dashboard/partials/feedback_composer.html', {
            'submitted': True,
            'category_choices': FeedbackTicket.Category.choices,
        })

    return render(request, 'admin_dashboard/partials/feedback_composer.html', {
        'category_choices': FeedbackTicket.Category.choices,
    })


@login_required
def user_feedback_view(request, ticket_id):
    ticket = get_object_or_404(FeedbackTicket, id=ticket_id, sender=request.user)
    
    if request.method == 'POST':
        message = request.POST.get('message')
        if message:
            FeedbackReply.objects.create(
                ticket=ticket,
                sender=request.user,
                message=message
            )
            # Reopen ticket for admins
            ticket.status = FeedbackTicket.Status.OPEN
            ticket.save()
            return redirect('admin_dashboard:user_feedback_view', ticket_id=ticket.id)
            
    context = {
        'ticket': ticket,
        'replies': ticket.replies.all()
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'admin_dashboard/partials/user_feedback_content.html', context)
    return render(request, 'admin_dashboard/user_feedback.html', context)
