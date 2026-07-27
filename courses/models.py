from django.db import models
from urllib.parse import parse_qs, urlparse

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

    title = models.CharField(
        max_length=150,
    )

    description = models.TextField()

    slug = models.SlugField(
        max_length=170,
        unique=True,
    )

    image = models.ImageField(
        upload_to="courses/",
        blank=True,
        null=True,
    )

    is_free = models.BooleanField(
        default=True,
    )

    price = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
    )

    currency = models.CharField(
        max_length=3,
        default="EUR",
    )

    is_published = models.BooleanField(
        default=False,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    def __str__(self):
        return self.title

    
    def __str__(self):
        return self.title
        
class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
    )

    title = models.CharField(
        max_length=150,
    )

    content = models.TextField(
        blank=True,
    )

    image = models.ImageField(
        upload_to="lessons/images/",
        blank=True,
        null=True,
    )

    video_url = models.URLField(
        blank=True,
    )

    order = models.PositiveIntegerField(
        default=1,
    )

    is_published = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ("order",)

    @property
    def youtube_video_id(self):
        if not self.video_url:
            return None

        parsed_url = urlparse(self.video_url)
        hostname = parsed_url.hostname or ""

        if hostname in {
            "youtu.be",
            "www.youtu.be",
        }:
            return parsed_url.path.lstrip("/").split("/")[0]

        if hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
        }:
            if parsed_url.path == "/watch":
                return parse_qs(
                    parsed_url.query
                ).get("v", [None])[0]

            if parsed_url.path.startswith("/embed/"):
                return parsed_url.path.split(
                    "/embed/"
                )[1].split("/")[0]

            if parsed_url.path.startswith("/shorts/"):
                return parsed_url.path.split(
                    "/shorts/"
                )[1].split("/")[0]

        return None

    def __str__(self):
        return f"{self.course.title} - {self.title}"