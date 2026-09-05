"""
Web views for PwaniNet Release Center UI.

Thin views that delegate business logic to services.
All release management UI endpoints are here.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from .models import Release, ReleaseItem, UserReleaseView
from .services import ReleaseService
from .selectors import ReleaseSelector
from .forms import CreateReleaseForm, ReleaseForm, PublishReleaseForm, ArchiveReleaseForm, ReleaseItemForm
from .permissions import CanManageRelease, CanPublishRelease, CanArchiveRelease


@login_required
def release_list(request):
    """
    List all releases.
    Shows all releases with filtering and pagination.
    """
    # Get all releases ordered by build number (newest first)
    all_releases = Release.objects.all().order_by('-build_number')
    
    context = {
        'releases': all_releases,
        'release_content_partial': 'releases/partials/list_content.html',
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/list.html', context)


@login_required
def dashboard(request):
    """
    Release Center dashboard.
    Shows current release, statistics, draft releases, and published releases.
    """
    # Get statistics
    statistics = ReleaseService.get_release_statistics()
    
    # Get current release
    current_release = ReleaseService.get_current_release()
    
    # Get draft and published releases
    draft_releases = list(ReleaseSelector.drafts().order_by('-created_at'))
    published_releases = list(ReleaseSelector.published().order_by('-published_at'))
    
    # Get archived releases (only for users with manage permission)
    if request.user.has_perm('releases.manage_release'):
        archived_releases = list(ReleaseSelector.archived().order_by('-updated_at'))
    else:
        archived_releases = []
    
    # Get environment info
    environment = getattr(settings, 'APP_ENVIRONMENT', 'unknown')
    debug = settings.DEBUG
    database_engine = settings.DATABASES['default']['ENGINE']
    
    context = {
        'statistics': statistics,
        'current_release': current_release,
        'draft_releases': draft_releases,
        'published_releases': published_releases,
        'archived_releases': archived_releases,
        'environment': environment,
        'debug': debug,
        'database_engine': database_engine,
        'release_content_partial': 'releases/partials/dashboard_content.html',
    }
    
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/dashboard.html', context)


@login_required
@permission_required('releases.manage_release', raise_exception=True)
def create_release(request):
    """
    Create a new release.
    """
    if request.method == 'POST':
        form = CreateReleaseForm(request.POST)
        if form.is_valid():
            try:
                # Create draft release
                release = ReleaseService.create_draft(
                    title=form.cleaned_data['release_title'],
                    summary=form.cleaned_data['release_summary'],
                    release_type=form.cleaned_data['release_type'],
                    release_channel=form.cleaned_data['release_channel'],
                    created_by=request.user,
                    minimum_supported_version=form.cleaned_data.get('minimum_supported_version'),
                    mandatory_update=form.cleaned_data['mandatory_update']
                )
                
                # Add release items if provided
                item_count = 0
                while f'item_category_{item_count}' in request.POST:
                    category = request.POST.get(f'item_category_{item_count}')
                    title = request.POST.get(f'item_title_{item_count}')
                    description = request.POST.get(f'item_description_{item_count}')
                    
                    if title:
                        # Create the release item
                        item = ReleaseService.add_release_item(
                            release=release,
                            category=category,
                            title=title,
                            description=description,
                            display_order=item_count
                        )
                        
                        # Handle multiple image uploads for this item
                        images = request.FILES.getlist(f'item_images_{item_count}')
                        for i, image_file in enumerate(images):
                            from .models import ReleaseItemImage
                            ReleaseItemImage.objects.create(
                                release_item=item,
                                image=image_file,
                                display_order=i
                            )
                    item_count += 1
                
                # Check if user wants to publish immediately
                action = request.POST.get('action', 'draft')
                if action == 'publish':
                    ReleaseService.publish_release(release, request.user)
                    messages.success(request, f'Release {release.version} published successfully.')
                else:
                    messages.success(request, f'Draft release {release.version} created successfully.')
                
                if request.headers.get('HX-Request'):
                    response = HttpResponse(status=204)
                    response['HX-Redirect'] = reverse('release_dashboard')
                    return response
                return redirect('release_dashboard')
                
            except Exception as e:
                messages.error(request, f'Error creating release: {str(e)}')
    else:
        form = CreateReleaseForm()
    
    context = {
        'form': form,
        'release_content_partial': 'releases/partials/create_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/create.html', context)


@login_required
@permission_required('releases.manage_release', raise_exception=True)
def edit_release(request, release_id):
    """
    Edit an existing release.
    """
    release = get_object_or_404(Release.objects.prefetch_related('items__images'), id=release_id)
    
    # Check permission
    if not CanManageRelease().has_object_permission(request, None, release):
        messages.error(request, 'You do not have permission to edit this release.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    if request.method == 'POST':
        form = ReleaseForm(request.POST, instance=release)
        if form.is_valid():
            form.save()
            messages.success(request, f'Release {release.version} updated successfully.')
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=204)
                response['HX-Redirect'] = reverse('release_dashboard')
                return response
            return redirect('release_dashboard')
    else:
        form = ReleaseForm(instance=release)
    
    context = {
        'form': form,
        'release': release,
        'release_content_partial': 'releases/partials/edit_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/edit.html', context)


@login_required
def detail_release(request, release_id):
    """
    View release details.
    Tracks that the user has viewed this release.
    Allows viewing archived releases for users with manage permission.
    """
    release = get_object_or_404(Release.objects.prefetch_related('items__images'), id=release_id)
    
    # Only show published releases unless user has manage permission
    # Archived releases can only be viewed by users with manage permission
    if release.status == 'ARCHIVED' and not request.user.has_perm('releases.manage_release'):
        messages.error(request, 'Release not found.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    if not release.published and not request.user.has_perm('releases.manage_release'):
        messages.error(request, 'Release not found.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    # Track that the user has viewed this release (only for published releases)
    if request.user.is_authenticated and release.published:
        UserReleaseView.objects.get_or_create(
            user=request.user,
            release=release
        )
    
    context = {
        'release': release,
        'release_content_partial': 'releases/partials/detail_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/detail.html', context)


@login_required
@permission_required('releases.publish_release', raise_exception=True)
def publish_release(request, release_id):
    """
    Publish a release.
    """
    release = get_object_or_404(Release, id=release_id)
    
    # Check permission
    if not CanPublishRelease().has_object_permission(request, None, release):
        messages.error(request, 'You do not have permission to publish this release.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    if request.method == 'POST':
        form = PublishReleaseForm(request.POST)
        if form.is_valid():
            try:
                ReleaseService.publish_release(release, request.user)
                
                # Check if user wants to set as current
                if form.cleaned_data.get('set_as_current'):
                    ReleaseService.set_current_release(release)
                
                messages.success(request, f'Release {release.version} published successfully.')
                if request.headers.get('HX-Request'):
                    response = HttpResponse(status=204)
                    response['HX-Redirect'] = reverse('release_dashboard')
                    return response
                return redirect('release_dashboard')
            except Exception as e:
                messages.error(request, f'Error publishing release: {str(e)}')
    else:
        form = PublishReleaseForm()
    
    context = {
        'form': form,
        'release': release,
        'release_content_partial': 'releases/partials/publish_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/publish.html', context)


@login_required
@permission_required('releases.archive_release', raise_exception=True)
def archive_release(request, release_id):
    """
    Archive a release.
    """
    release = get_object_or_404(Release, id=release_id)
    
    # Check permission
    if not CanArchiveRelease().has_object_permission(request, None, release):
        messages.error(request, 'You do not have permission to archive this release.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    if request.method == 'POST':
        form = ArchiveReleaseForm(request.POST)
        if form.is_valid():
            try:
                ReleaseService.archive_release(release)
                messages.success(request, f'Release {release.version} archived successfully.')
                if request.headers.get('HX-Request'):
                    response = HttpResponse(status=204)
                    response['HX-Redirect'] = reverse('release_dashboard')
                    return response
                return redirect('release_dashboard')
            except Exception as e:
                messages.error(request, f'Error archiving release: {str(e)}')
    else:
        form = ArchiveReleaseForm()
    
    context = {
        'form': form,
        'release': release,
        'release_content_partial': 'releases/partials/archive_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/archive.html', context)


@login_required
@permission_required('releases.manage_release', raise_exception=True)
def set_current_release(request, release_id):
    """
    Mark a release as the current release.
    """
    release = get_object_or_404(Release, id=release_id)
    
    if release.status != 'PUBLISHED':
        messages.error(request, 'Only published releases can be marked as current.')
        if request.headers.get('HX-Request'):
            response = HttpResponse(status=204)
            response['HX-Redirect'] = reverse('release_dashboard')
            return response
        return redirect('release_dashboard')
    
    try:
        ReleaseService.set_current_release(release)
        messages.success(request, f'Release {release.version} marked as current.')
    except Exception as e:
        messages.error(request, f'Error setting current release: {str(e)}')
    
    if request.headers.get('HX-Request'):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('release_dashboard')
        return response
    return redirect('release_dashboard')


@login_required
@permission_required('releases.manage_release', raise_exception=True)
def add_release_item(request, release_id):
    """
    Add an item to a release.
    """
    release = get_object_or_404(Release, id=release_id)
    
    if request.method == 'POST':
        form = ReleaseItemForm(request.POST, request.FILES)
        if form.is_valid():
            # Create the release item
            item = ReleaseService.add_release_item(
                release=release,
                category=form.cleaned_data['category'],
                title=form.cleaned_data['title'],
                description=form.cleaned_data['description'],
                display_order=form.cleaned_data['display_order']
            )
            
            # Handle multiple image uploads
            images = request.FILES.getlist('images')
            for i, image_file in enumerate(images):
                from .models import ReleaseItemImage
                ReleaseItemImage.objects.create(
                    release_item=item,
                    image=image_file,
                    display_order=i
                )
            
            messages.success(request, f'Release item added successfully with {len(images)} image(s).')
            if request.headers.get('HX-Request'):
                response = HttpResponse(status=204)
                response['HX-Redirect'] = reverse('release_edit', kwargs={'release_id': release.id})
                return response
            return redirect('release_edit', release_id=release.id)
    else:
        form = ReleaseItemForm()
    
    context = {
        'form': form,
        'release': release,
        'release_content_partial': 'releases/partials/add_item_content.html',
    }
    if request.headers.get('HX-Request'):
        return render(request, 'releases/partials/releases_navigation_partial.html', context)
    return render(request, 'releases/add_item.html', context)


@login_required
@permission_required('releases.manage_release', raise_exception=True)
def delete_release_item(request, item_id):
    """
    Delete a release item.
    """
    item = get_object_or_404(ReleaseItem, id=item_id)
    release_id = item.release.id
    item.delete()
    messages.success(request, 'Release item deleted successfully.')
    if request.headers.get('HX-Request'):
        response = HttpResponse(status=204)
        response['HX-Redirect'] = reverse('release_edit', kwargs={'release_id': release_id})
        return response
    return redirect('release_edit', release_id=release_id)
