from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Course, Year ,Post ,Unit ,User ,Notifications ,Groups ,Like ,Follow ,Comment ,PostImage

#Add the course and year fields to the Admin panel.
class TheUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        (None,{'fields':('course','year')}),

        )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        (None, {'fields':('course' ,'year')}),
    )

    list_display = ['first_name','second_name','last_name','username', 'email', 'is_staff']

    list_filter = ['course', 'year', 'is_staff']

admin.site.register(User,TheUserAdmin)

# This makes the models visible in the Admin Panel
admin.site.register(Course)
admin.site.register(Year)
admin.site.register(Post)
admin.site.register(PostImage)
admin.site.register(Unit)
admin.site.register(Notifications)
admin.site.register(Groups)
admin.site.register(Like)
admin.site.register(Follow)
admin.site.register(Comment)