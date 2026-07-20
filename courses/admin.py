from django.contrib import admin

from .models import Category, Course, Lesson


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}


class LessonInline(admin.TabularInline):
    model = Lesson
    extra = 1
    fields = (
        "title",
        "order",
        "is_published",
        "content",
    )
    ordering = ("order",)


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
    inlines = [LessonInline]


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