from django.db import models


class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    slug = models.SlugField(max_length=120, unique=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Course(models.Model):
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="courses",
    )
    title = models.CharField(max_length=150)
    description = models.TextField()
    slug = models.SlugField(max_length=170, unique=True)
    image = models.ImageField(
        upload_to="courses/",
        blank=True,
        null=True,
    )
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
        
class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )
    title = models.CharField(max_length=150)
    content = models.TextField()
    order = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False)

    class Meta:
        ordering = ("order",)

    def __str__(self):
        return f"{self.course.title} - {self.title}"