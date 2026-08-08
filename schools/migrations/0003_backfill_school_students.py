from django.db import migrations


def backfill_school_students(apps, schema_editor):
    Enrollment = apps.get_model(
        "accounts",
        "Enrollment",
    )

    SchoolStudent = apps.get_model(
        "schools",
        "SchoolStudent",
    )

    existing_relationships = (
        Enrollment.objects
        .filter(school_id__isnull=False)
        .values_list(
            "school_id",
            "user_id",
        )
        .distinct()
    )

    memberships = [
        SchoolStudent(
            school_id=school_id,
            user_id=user_id,
            is_active=True,
        )
        for school_id, user_id
        in existing_relationships
    ]

    SchoolStudent.objects.bulk_create(
        memberships,
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        (
            "schools",
            "0002_schoolstudent",
        ),
        (
            "accounts",
            "0008_enrollment_school",
        ),
    ]

    operations = [
        migrations.RunPython(
            backfill_school_students,
            migrations.RunPython.noop,
        ),
    ]