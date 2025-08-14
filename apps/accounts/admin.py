from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    # Clean list view
    list_display = ('id', 'email', 'get_display_name', 'role', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'organization_name')
    ordering = ('-date_joined',)
    readonly_fields = ['date_joined']  # Make these fields read-only
    
    # Clean detail view - removed date_joined from editable fields
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile Info', {'fields': (
            ('first_name', 'last_name'), 
            ('organization_name', 'website'),
            'role'
        )}),
        ('Status', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    
    # Clean add form
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role'),
        }),
    )
    
    def get_display_name(self, obj):
        if obj.role == User.Role.ORGANIZATION:
            return obj.organization_name
        return f"{obj.first_name} {obj.last_name}"
    get_display_name.short_description = 'Name'