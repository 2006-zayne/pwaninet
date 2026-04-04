from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Post, Unit, Course ,Year ,User
from .forms import PwaniSignupForm ,PostForm
from django.contrib.auth import get_user_model

# Create your views here.

User = get_user_model()

def register_view(request):
    if request.method == 'POST':
        form = PwaniSignupForm(request.POST)
        if form.is_valid():#Validates the error in the form.

            form.save()#creates the user in the DB.

            return redirect('login')# Redirects to the login page.
           
    else:
        form = PwaniSignupForm()
    return render(request, 'register.html', {'form': form})


@login_required
def post_list_view(request):
    user = request.user


    # MISSION: Only show units for the user's specific Course and Year
    if user.course and user.year:
        units = Unit.objects.filter(course=user.course, year=user.year)
        posts = Post.objects.filter(course=user.course, unit__year=user.year).order_by('-date')
    else:
        units = Unit.objects.none()
        posts = Post.objects.none()
        
    context = {
        'posts': posts,
        'units': units,
        'title': 'PwaniNet Command Feed'
    }
    return render(request, 'home.html', context)


@login_required
def unit_posts_view(request, unit_id):
    # Find the specific unit or return a 404 Error
    target_unit = get_object_or_404(Unit, id=unit_id)
    
    # Filter posts to ONLY show this unit
    posts = Post.objects.filter(unit=target_unit).order_by('-date')

    context = {
        'unit': target_unit,
        'posts': posts
    }
    return render(request, 'unit_detail.html', context)




@login_required
def create_post_view(request):
   if request.method == 'POST':
       
       form = PostForm(request.POST ,user= request.user )

       if form.is_valid():
           post =form.save(commit=False)
           post.author = request.user
          #post.content = post.content

           if post.unit:
               post.course = post.unit.course

           post.save()

           return redirect('home')
       
   else:
        form = PostForm(user = request.user)

        return render(request, 'create_post.html' , {'form' : form})
   


def load_years(request):
    course_id = request.GET.get('course')
    # To see if the ID is arriving
    print(f"DEBUG: Loading years for Course ID: {course_id}")
    
    years = Year.objects.filter(course_id=course_id).order_by('level')
    
    # Return the partial HTML for filtering the year
    return render(request, 'partials/year_options.html', {'years': years})

@login_required
def profile_view(request ,username):

    # FiNDS  the user who posted or returns a 404 not found error.
    target_user = get_object_or_404(User,username=username)

    #We gather all the posts the user has ever posted.
    user_posts = target_user.posts.all().order_by('-date')

    #The briefcase with the data we want to see.
    context ={
        'profile_user': target_user,
        'posts' : user_posts,
    }

    return render(request, 'profile.html' ,context)
