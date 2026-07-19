from django.contrib import admin

from .models import Category, Course, Lesson


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "is_published",
        "created_at",
    )
    list_filter = (
        "category",
        "is_published",
    )
    search_fields = (
        "title",
        "description",
    )
    prepopulated_fields = {
        "slug": ("title",),
    }


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "is_published",
    )
    list_filter = (
        "course",
        "is_published",
    )
    search_fields = (
        "title",
        "content",
    )
    ordering = (
        "course",
        "order",
    )