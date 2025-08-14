from django.contrib import admin
from .models import Category, Tag, Job


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'created_at')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}  # Automatically generate slug
    ordering = ('-created_at',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'slug', 'created_date')
    search_fields = ('title',)
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_date',)


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'organization', 'category', 'location', 'salary', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'category', 'tags')
    search_fields = ('title', 'description', 'location', 'organization__email')
    prepopulated_fields = {'slug': ('title',)}
    raw_id_fields = ('organization',)
    autocomplete_fields = ('tags',)
    filter_horizontal = ('jobSeekers_who_apply',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
