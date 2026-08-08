from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import (
    Enrollment,
    StudentProfile,
)
from courses.models import Category, Course

from .forms import (
    SchoolEnrollmentForm,
    SchoolStudentCreateForm,
)
from .models import (
    School,
    SchoolAdministrator,
    SchoolStudent,
)


User = get_user_model()


class SchoolPortalTestCase(TestCase):
    def setUp(self):
        """
        Create two completely separate schools so that
        the tests can verify tenant isolation.
        """

        self.category = Category.objects.create(
            name="Workplace Safety",
            slug="workplace-safety",
        )

        self.course_a = Course.objects.create(
            category=self.category,
            title="Manual Handling",
            description="Manual handling training.",
            slug="manual-handling-test",
            is_published=True,
        )

        self.course_b = Course.objects.create(
            category=self.category,
            title="Food Safety",
            description="Food safety training.",
            slug="food-safety-test",
            is_published=True,
        )

        # -------------------------------------------------
        # School A
        # -------------------------------------------------

        self.school_a = School.objects.create(
            name="School A",
            slug="school-a",
            contact_email="schoola@example.com",
            student_limit=10,
            subscription_active=True,
            is_active=True,
        )

        self.admin_a = User.objects.create_user(
            username="admin_a",
            email="admina@example.com",
            password="TestPassword123!",
        )

        self.school_admin_a = (
            SchoolAdministrator.objects.create(
                user=self.admin_a,
                school=self.school_a,
            )
        )

        self.student_a = User.objects.create_user(
            username="student_a",
            first_name="Student",
            last_name="Alpha",
            email="studenta@example.com",
            password="TestPassword123!",
        )

        StudentProfile.objects.update_or_create(
            user=self.student_a,
            defaults={
                "preferred_language": "en",
            },
        )

        self.membership_a = SchoolStudent.objects.create(
            school=self.school_a,
            user=self.student_a,
            is_active=True,
        )

        self.enrollment_a = Enrollment.objects.create(
            user=self.student_a,
            course=self.course_a,
            school=self.school_a,
        )

        # -------------------------------------------------
        # School B
        # -------------------------------------------------

        self.school_b = School.objects.create(
            name="School B",
            slug="school-b",
            contact_email="schoolb@example.com",
            student_limit=10,
            subscription_active=True,
            is_active=True,
        )

        self.admin_b = User.objects.create_user(
            username="admin_b",
            email="adminb@example.com",
            password="TestPassword123!",
        )

        self.school_admin_b = (
            SchoolAdministrator.objects.create(
                user=self.admin_b,
                school=self.school_b,
            )
        )

        self.student_b = User.objects.create_user(
            username="student_b",
            first_name="Student",
            last_name="Beta",
            email="studentb@example.com",
            password="TestPassword123!",
        )

        StudentProfile.objects.update_or_create(
            user=self.student_b,
            defaults={
                "preferred_language": "en",
            },
        )

        self.membership_b = SchoolStudent.objects.create(
            school=self.school_b,
            user=self.student_b,
            is_active=True,
        )

        self.enrollment_b = Enrollment.objects.create(
            user=self.student_b,
            course=self.course_b,
            school=self.school_b,
        )

    # -----------------------------------------------------
    # ACCESS CONTROL
    # -----------------------------------------------------

    def test_school_administrator_can_access_dashboard(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse("schools:dashboard")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        self.assertEqual(
            response.context["school"],
            self.school_a,
        )

    def test_normal_user_cannot_access_school_portal(self):
        normal_user = User.objects.create_user(
            username="normal_user",
            email="normal@example.com",
            password="TestPassword123!",
        )

        self.client.force_login(normal_user)

        response = self.client.get(
            reverse("schools:dashboard")
        )

        self.assertRedirects(
            response,
            reverse("accounts:dashboard"),
        )

    # -----------------------------------------------------
    # SCHOOL ISOLATION
    # -----------------------------------------------------

    def test_school_student_list_only_contains_own_students(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse("schools:student_list")
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        student_ids = [
            row["user"].pk
            for row in response.context["student_rows"]
        ]

        self.assertIn(
            self.student_a.pk,
            student_ids,
        )

        self.assertNotIn(
            self.student_b.pk,
            student_ids,
        )

    def test_school_cannot_access_student_from_another_school(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse(
                "schools:student_detail",
                args=[self.student_b.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

    def test_student_detail_contains_only_current_school_enrollments(
        self,
    ):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse(
                "schools:student_detail",
                args=[self.student_a.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            200,
        )

        enrollment_ids = [
            row["enrollment"].pk
            for row in response.context["enrollment_rows"]
        ]

        self.assertIn(
            self.enrollment_a.pk,
            enrollment_ids,
        )

        self.assertNotIn(
            self.enrollment_b.pk,
            enrollment_ids,
        )

    # -----------------------------------------------------
    # STUDENT CREATION
    # -----------------------------------------------------

    def test_school_can_create_student_with_profile_and_enrollment(
        self,
    ):
        form = SchoolStudentCreateForm(
            data={
                "first_name": "New",
                "last_name": "Student",
                "email": "newstudent@example.com",
                "phone_number": "0871234567",
                "preferred_language": "en",
                "course": self.course_a.pk,
            },
            school=self.school_a,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        student, enrollment = form.save()

        self.assertTrue(
            User.objects.filter(
                pk=student.pk,
            ).exists()
        )

        self.assertEqual(
            student.email,
            "newstudent@example.com",
        )

        self.assertFalse(
            student.has_usable_password()
        )

        self.assertTrue(
            StudentProfile.objects.filter(
                user=student,
            ).exists()
        )

        profile = StudentProfile.objects.get(
            user=student
        )

        self.assertEqual(
            profile.phone_number,
            "0871234567",
        )

        self.assertEqual(
            profile.preferred_language,
            "en",
        )

        membership = SchoolStudent.objects.get(
            school=self.school_a,
            user=student,
        )

        self.assertTrue(
            membership.is_active
        )

        self.assertEqual(
            enrollment.user,
            student,
        )

        self.assertEqual(
            enrollment.school,
            self.school_a,
        )

        self.assertEqual(
            enrollment.course,
            self.course_a,
        )

    def test_student_creation_rejects_duplicate_email(self):
        form = SchoolStudentCreateForm(
            data={
                "first_name": "Duplicate",
                "last_name": "Student",
                "email": self.student_a.email,
                "phone_number": "",
                "preferred_language": "en",
                "course": self.course_b.pk,
            },
            school=self.school_a,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "email",
            form.errors,
        )

    # -----------------------------------------------------
    # STUDENT LIMIT
    # -----------------------------------------------------

    def test_school_cannot_create_student_when_limit_reached(self):
        limited_school = School.objects.create(
            name="Limited School",
            slug="limited-school",
            student_limit=1,
            subscription_active=True,
            is_active=True,
        )

        existing_student = User.objects.create_user(
            username="limited_student",
            email="limited@example.com",
            password="TestPassword123!",
        )

        SchoolStudent.objects.create(
            school=limited_school,
            user=existing_student,
            is_active=True,
        )

        Enrollment.objects.create(
            user=existing_student,
            course=self.course_a,
            school=limited_school,
        )

        form = SchoolStudentCreateForm(
            data={
                "first_name": "Second",
                "last_name": "Student",
                "email": "second@example.com",
                "phone_number": "",
                "preferred_language": "en",
                "course": self.course_b.pk,
            },
            school=limited_school,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "This school has reached its current student limit.",
            form.non_field_errors(),
        )

    # -----------------------------------------------------
    # EXISTING STUDENT ENROLLMENT
    # -----------------------------------------------------

    def test_school_can_enroll_existing_student(self):
        existing_student = User.objects.create_user(
            username="existing_student",
            first_name="Existing",
            last_name="Student",
            email="existing@example.com",
            password="TestPassword123!",
        )

        form = SchoolEnrollmentForm(
            data={
                "student_email": existing_student.email,
                "course": self.course_b.pk,
            },
            school=self.school_a,
        )

        self.assertTrue(
            form.is_valid(),
            form.errors,
        )

        enrollment = form.save()

        self.assertEqual(
            enrollment.user,
            existing_student,
        )

        self.assertEqual(
            enrollment.course,
            self.course_b,
        )

        self.assertEqual(
            enrollment.school,
            self.school_a,
        )

        membership = SchoolStudent.objects.get(
            school=self.school_a,
            user=existing_student,
        )

        self.assertTrue(
            membership.is_active
        )

    def test_duplicate_course_enrollment_is_rejected(self):
        form = SchoolEnrollmentForm(
            data={
                "student_email": self.student_a.email,
                "course": self.course_a.pk,
            },
            school=self.school_a,
        )

        self.assertFalse(
            form.is_valid()
        )

        self.assertIn(
            "This student is already enrolled in the selected course.",
            form.non_field_errors(),
        )

    # -----------------------------------------------------
    # STUDENT MEMBERSHIP STATUS
    # -----------------------------------------------------

    def test_school_can_deactivate_student_membership(self):
        self.client.force_login(self.admin_a)

        response = self.client.post(
            reverse(
                "schools:student_deactivate",
                args=[self.student_a.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "schools:student_detail",
                args=[self.student_a.pk],
            ),
        )

        self.membership_a.refresh_from_db()
        self.student_a.refresh_from_db()

        self.assertFalse(
            self.membership_a.is_active
        )

        self.assertIsNotNone(
            self.membership_a.deactivated_at
        )

        # The global student account must remain active.
        self.assertTrue(
            self.student_a.is_active
        )

        # Training history must remain untouched.
        self.assertTrue(
            Enrollment.objects.filter(
                pk=self.enrollment_a.pk,
            ).exists()
        )

    def test_student_deactivate_requires_post(self):
        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse(
                "schools:student_deactivate",
                args=[self.student_a.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.membership_a.refresh_from_db()

        self.assertTrue(
            self.membership_a.is_active
        )

    def test_school_cannot_deactivate_student_from_another_school(
        self,
    ):
        self.client.force_login(self.admin_a)

        response = self.client.post(
            reverse(
                "schools:student_deactivate",
                args=[self.student_b.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.membership_b.refresh_from_db()

        self.assertTrue(
            self.membership_b.is_active
        )

    def test_school_can_reactivate_student_membership(self):
        self.membership_a.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.post(
            reverse(
                "schools:student_reactivate",
                args=[self.student_a.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "schools:student_detail",
                args=[self.student_a.pk],
            ),
        )

        self.membership_a.refresh_from_db()

        self.assertTrue(
            self.membership_a.is_active
        )

        self.assertIsNone(
            self.membership_a.deactivated_at
        )

    def test_student_reactivate_requires_post(self):
        self.membership_a.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse(
                "schools:student_reactivate",
                args=[self.student_a.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            405,
        )

        self.membership_a.refresh_from_db()

        self.assertFalse(
            self.membership_a.is_active
        )

    def test_school_cannot_reactivate_student_from_another_school(
        self,
    ):
        self.membership_b.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.post(
            reverse(
                "schools:student_reactivate",
                args=[self.student_b.pk],
            )
        )

        self.assertEqual(
            response.status_code,
            404,
        )

        self.membership_b.refresh_from_db()

        self.assertFalse(
            self.membership_b.is_active
        )

    def test_reactivation_is_blocked_when_student_limit_is_reached(
        self,
    ):
        self.membership_a.deactivate()

        self.school_a.student_limit = 1
        self.school_a.save(
            update_fields=[
                "student_limit",
            ]
        )

        capacity_student = User.objects.create_user(
            username="capacity_student",
            email="capacity@example.com",
            password="TestPassword123!",
        )

        SchoolStudent.objects.create(
            school=self.school_a,
            user=capacity_student,
            is_active=True,
        )

        self.assertEqual(
            self.school_a.active_student_count,
            1,
        )

        self.client.force_login(self.admin_a)

        response = self.client.post(
            reverse(
                "schools:student_reactivate",
                args=[self.student_a.pk],
            )
        )

        self.assertRedirects(
            response,
            reverse(
                "schools:student_detail",
                args=[self.student_a.pk],
            ),
        )

        self.membership_a.refresh_from_db()

        self.assertFalse(
            self.membership_a.is_active
        )

        self.assertIsNotNone(
            self.membership_a.deactivated_at
        )

    def test_inactive_student_is_hidden_from_default_student_list(
        self,
    ):
        self.membership_a.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse("schools:student_list")
        )

        student_ids = [
            row["user"].pk
            for row in response.context["student_rows"]
        ]

        self.assertNotIn(
            self.student_a.pk,
            student_ids,
        )

        self.assertEqual(
            response.context["status_filter"],
            "active",
        )

    def test_inactive_student_appears_in_inactive_filter(self):
        self.membership_a.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse("schools:student_list"),
            {
                "status": "inactive",
            },
        )

        student_ids = [
            row["user"].pk
            for row in response.context["student_rows"]
        ]

        self.assertIn(
            self.student_a.pk,
            student_ids,
        )

        self.assertNotIn(
            self.student_b.pk,
            student_ids,
        )

        self.assertEqual(
            response.context["status_filter"],
            "inactive",
        )

    def test_all_filter_shows_active_and_inactive_school_students(
        self,
    ):
        inactive_student = User.objects.create_user(
            username="inactive_school_a",
            email="inactive-school-a@example.com",
            password="TestPassword123!",
        )

        inactive_membership = SchoolStudent.objects.create(
            school=self.school_a,
            user=inactive_student,
            is_active=True,
        )

        inactive_membership.deactivate()

        self.client.force_login(self.admin_a)

        response = self.client.get(
            reverse("schools:student_list"),
            {
                "status": "all",
            },
        )

        student_ids = [
            row["user"].pk
            for row in response.context["student_rows"]
        ]

        self.assertIn(
            self.student_a.pk,
            student_ids,
        )

        self.assertIn(
            inactive_student.pk,
            student_ids,
        )

        self.assertNotIn(
            self.student_b.pk,
            student_ids,
        )

        self.assertEqual(
            response.context["status_filter"],
            "all",
        )
