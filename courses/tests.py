from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import (
    AssessmentAttempt,
    AttemptQuestion,
    Certificate,
    Enrollment,
    LessonProgress,
    StudentAnswer,
)
from courses.models import (
    AnswerOption,
    Category,
    Course,
    CourseAssessment,
    Lesson,
    Question,
)


User = get_user_model()


class StudentCourseFlowTests(TestCase):
    """
    Integration tests for the complete student course flow.

    Covered flow:
    - Login and enrolment
    - Lesson access protection
    - Lesson progress
    - Assessment release
    - Assessment attempts
    - Passing and failing results
    - Certificate creation and ownership
    """

    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="StrongPass123!",
        )

        cls.other_student = User.objects.create_user(
            username="other-student",
            email="other@example.com",
            password="StrongPass123!",
        )

        cls.category = Category.objects.create(
            name="Workplace Safety",
            description="Workplace safety courses.",
            slug="workplace-safety",
        )

        cls.course = Course.objects.create(
            category=cls.category,
            title="Test Safety Course",
            description="Course used by automated tests.",
            slug="test-safety-course",
            is_published=True,
        )

        cls.lesson_one = Lesson.objects.create(
            course=cls.course,
            title="Lesson One",
            content="First lesson content.",
            order=1,
            is_published=True,
        )

        cls.lesson_two = Lesson.objects.create(
            course=cls.course,
            title="Lesson Two",
            content="Second lesson content.",
            order=2,
            is_published=True,
        )

        cls.assessment = CourseAssessment.objects.create(
            course=cls.course,
            title="Final Test",
            passing_score=80,
            questions_per_attempt=2,
            maximum_attempts=3,
            shuffle_questions=False,
            shuffle_answers=False,
            is_published=True,
        )

        cls.question_one = cls._create_question(
            assessment=cls.assessment,
            order=1,
            text="What is the correct answer to question one?",
        )

        cls.question_two = cls._create_question(
            assessment=cls.assessment,
            order=2,
            text="What is the correct answer to question two?",
        )

    @classmethod
    def _create_question(
        cls,
        assessment,
        order,
        text,
    ):
        question = Question.objects.create(
            assessment=assessment,
            text=text,
            explanation="Test explanation.",
            order=order,
            is_published=True,
        )

        for option_order in range(1, 5):
            AnswerOption.objects.create(
                question=question,
                text=f"Option {option_order}",
                order=option_order,
                is_correct=option_order == 1,
            )

        return question

    def _login(self, user=None):
        self.client.force_login(
            user or self.student,
        )

    def _create_enrollment(self):
        enrollment, _ = Enrollment.objects.get_or_create(
            user=self.student,
            course=self.course,
        )

        return enrollment

    def _complete_all_lessons(self, enrollment):
        for lesson in (
            self.lesson_one,
            self.lesson_two,
        ):
            LessonProgress.objects.update_or_create(
                enrollment=enrollment,
                lesson=lesson,
                defaults={
                    "completed": True,
                    "completed_at": timezone.now(),
                },
            )

    def _create_attempt(self, enrollment):
        attempt = AssessmentAttempt.objects.create(
            enrollment=enrollment,
            assessment=self.assessment,
            attempt_number=1,
            total_questions=2,
        )

        attempt_question_one = AttemptQuestion.objects.create(
            attempt=attempt,
            question=self.question_one,
            position=1,
        )

        attempt_question_two = AttemptQuestion.objects.create(
            attempt=attempt,
            question=self.question_two,
            position=2,
        )

        return (
            attempt,
            attempt_question_one,
            attempt_question_two,
        )

    def test_course_detail_shows_correct_button_states(self):
        course_url = reverse(
            "courses:course_detail",
            kwargs={
                "slug": self.course.slug,
            },
        )

        anonymous_response = self.client.get(
            course_url,
        )

        self.assertEqual(
            anonymous_response.status_code,
            200,
        )
        self.assertFalse(
            anonymous_response.context["is_enrolled"],
        )

        self._login()

        not_enrolled_response = self.client.get(
            course_url,
        )

        self.assertFalse(
            not_enrolled_response.context["is_enrolled"],
        )

        enrollment = self._create_enrollment()

        start_response = self.client.get(
            course_url,
        )

        self.assertTrue(
            start_response.context["is_enrolled"],
        )
        self.assertEqual(
            start_response.context["course_button_text"],
            "Start course",
        )
        self.assertEqual(
            start_response.context["course_button_lesson"],
            self.lesson_one,
        )

        LessonProgress.objects.create(
            enrollment=enrollment,
            lesson=self.lesson_one,
            completed=True,
            completed_at=timezone.now(),
        )

        resume_response = self.client.get(
            course_url,
        )

        self.assertEqual(
            resume_response.context["course_button_text"],
            "Resume course",
        )
        self.assertEqual(
            resume_response.context["course_button_lesson"],
            self.lesson_two,
        )

        LessonProgress.objects.create(
            enrollment=enrollment,
            lesson=self.lesson_two,
            completed=True,
            completed_at=timezone.now(),
        )

        review_response = self.client.get(
            course_url,
        )

        self.assertEqual(
            review_response.context["course_button_text"],
            "Review lessons",
        )
        self.assertEqual(
            review_response.context["course_button_lesson"],
            self.lesson_two,
        )

    def test_enrolment_requires_login(self):
        response = self.client.post(
            reverse(
                "courses:enroll_course",
                kwargs={
                    "course_slug": self.course.slug,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            302,
        )
        self.assertIn(
            reverse("accounts:login"),
            response.url,
        )
        self.assertFalse(
            Enrollment.objects.filter(
                user=self.student,
                course=self.course,
            ).exists(),
        )

    def test_enrolment_is_created_only_once(self):
        self._login()

        enrol_url = reverse(
            "courses:enroll_course",
            kwargs={
                "course_slug": self.course.slug,
            },
        )

        expected_lesson_url = reverse(
            "courses:lesson_detail",
            kwargs={
                "course_slug": self.course.slug,
                "lesson_id": self.lesson_one.id,
            },
        )

        first_response = self.client.post(
            enrol_url,
        )

        self.assertRedirects(
            first_response,
            expected_lesson_url,
        )
        self.assertEqual(
            Enrollment.objects.filter(
                user=self.student,
                course=self.course,
            ).count(),
            1,
        )

        second_response = self.client.post(
            enrol_url,
        )

        self.assertRedirects(
            second_response,
            expected_lesson_url,
        )
        self.assertEqual(
            Enrollment.objects.filter(
                user=self.student,
                course=self.course,
            ).count(),
            1,
        )

    def test_course_without_lessons_cannot_be_enrolled(self):
        empty_course = Course.objects.create(
            category=self.category,
            title="Empty Course",
            description="Course without lessons.",
            slug="empty-course",
            is_published=True,
        )

        self._login()

        response = self.client.post(
            reverse(
                "courses:enroll_course",
                kwargs={
                    "course_slug": empty_course.slug,
                },
            ),
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:course_detail",
                kwargs={
                    "slug": empty_course.slug,
                },
            ),
        )
        self.assertFalse(
            Enrollment.objects.filter(
                user=self.student,
                course=empty_course,
            ).exists(),
        )

    def test_lesson_access_is_protected(self):
        lesson_url = reverse(
            "courses:lesson_detail",
            kwargs={
                "course_slug": self.course.slug,
                "lesson_id": self.lesson_one.id,
            },
        )

        anonymous_response = self.client.get(
            lesson_url,
        )

        self.assertEqual(
            anonymous_response.status_code,
            302,
        )
        self.assertIn(
            reverse("accounts:login"),
            anonymous_response.url,
        )

        self._login()

        not_enrolled_response = self.client.get(
            lesson_url,
        )

        self.assertRedirects(
            not_enrolled_response,
            reverse(
                "courses:course_detail",
                kwargs={
                    "slug": self.course.slug,
                },
            ),
        )

        self._create_enrollment()

        enrolled_response = self.client.get(
            lesson_url,
        )

        self.assertEqual(
            enrolled_response.status_code,
            200,
        )
        self.assertEqual(
            enrolled_response.context["lesson"],
            self.lesson_one,
        )

    def test_non_enrolled_student_cannot_complete_lesson(self):
        self._login()

        response = self.client.post(
            reverse(
                "courses:mark_lesson_completed",
                kwargs={
                    "course_slug": self.course.slug,
                    "lesson_id": self.lesson_one.id,
                },
            ),
        )

        self.assertEqual(
            response.status_code,
            403,
        )
        self.assertFalse(
            response.json()["success"],
        )
        self.assertFalse(
            Enrollment.objects.filter(
                user=self.student,
                course=self.course,
            ).exists(),
        )
        self.assertEqual(
            LessonProgress.objects.count(),
            0,
        )

    def test_lesson_progress_reaches_one_hundred_percent(self):
        self._login()
        enrollment = self._create_enrollment()

        first_response = self.client.post(
            reverse(
                "courses:mark_lesson_completed",
                kwargs={
                    "course_slug": self.course.slug,
                    "lesson_id": self.lesson_one.id,
                },
            ),
        )

        self.assertEqual(
            first_response.status_code,
            200,
        )
        self.assertEqual(
            first_response.json()["completed_count"],
            1,
        )
        self.assertEqual(
            first_response.json()["percentage"],
            50,
        )
        self.assertFalse(
            first_response.json()["all_lessons_completed"],
        )

        first_progress = LessonProgress.objects.get(
            enrollment=enrollment,
            lesson=self.lesson_one,
        )

        self.assertTrue(
            first_progress.completed,
        )
        self.assertIsNotNone(
            first_progress.completed_at,
        )

        second_response = self.client.post(
            reverse(
                "courses:mark_lesson_completed",
                kwargs={
                    "course_slug": self.course.slug,
                    "lesson_id": self.lesson_two.id,
                },
            ),
        )

        self.assertEqual(
            second_response.status_code,
            200,
        )
        self.assertEqual(
            second_response.json()["completed_count"],
            2,
        )
        self.assertEqual(
            second_response.json()["percentage"],
            100,
        )
        self.assertTrue(
            second_response.json()["all_lessons_completed"],
        )

    def test_assessment_is_locked_until_all_lessons_are_complete(self):
        self._login()
        enrollment = self._create_enrollment()

        assessment_url = reverse(
            "courses:assessment_detail",
            kwargs={
                "course_slug": self.course.slug,
            },
        )

        locked_response = self.client.get(
            assessment_url,
        )

        self.assertEqual(
            locked_response.status_code,
            200,
        )
        self.assertFalse(
            locked_response.context["lessons_completed"],
        )
        self.assertFalse(
            locked_response.context["can_start"],
        )

        self._complete_all_lessons(
            enrollment,
        )

        unlocked_response = self.client.get(
            assessment_url,
        )

        self.assertTrue(
            unlocked_response.context["lessons_completed"],
        )
        self.assertTrue(
            unlocked_response.context["can_start"],
        )

    def test_non_enrolled_student_cannot_access_assessment(self):
        self._login()

        response = self.client.get(
            reverse(
                "courses:assessment_detail",
                kwargs={
                    "course_slug": self.course.slug,
                },
            ),
        )

        self.assertRedirects(
            response,
            reverse(
                "courses:course_detail",
                kwargs={
                    "slug": self.course.slug,
                },
            ),
        )

    def test_assessment_attempt_starts_only_after_lessons(self):
        self._login()
        enrollment = self._create_enrollment()

        start_url = reverse(
            "courses:start_assessment",
            kwargs={
                "course_slug": self.course.slug,
            },
        )

        locked_response = self.client.post(
            start_url,
        )

        self.assertRedirects(
            locked_response,
            reverse(
                "courses:assessment_detail",
                kwargs={
                    "course_slug": self.course.slug,
                },
            ),
        )
        self.assertEqual(
            AssessmentAttempt.objects.count(),
            0,
        )

        self._complete_all_lessons(
            enrollment,
        )

        started_response = self.client.post(
            start_url,
        )

        attempt = AssessmentAttempt.objects.get(
            enrollment=enrollment,
            assessment=self.assessment,
        )

        self.assertRedirects(
            started_response,
            reverse(
                "courses:assessment_attempt",
                kwargs={
                    "course_slug": self.course.slug,
                    "attempt_id": attempt.id,
                    "position": 1,
                },
            ),
        )
        self.assertEqual(
            attempt.attempt_questions.count(),
            2,
        )
        self.assertFalse(
            attempt.is_completed,
        )

    def test_passing_assessment_completes_course_and_creates_certificate(
        self,
    ):
        enrollment = self._create_enrollment()
        self._complete_all_lessons(
            enrollment,
        )

        (
            attempt,
            attempt_question_one,
            attempt_question_two,
        ) = self._create_attempt(
            enrollment,
        )

        StudentAnswer.objects.create(
            attempt_question=attempt_question_one,
            selected_option=(
                self.question_one.correct_answer
            ),
        )

        StudentAnswer.objects.create(
            attempt_question=attempt_question_two,
            selected_option=(
                self.question_two.correct_answer
            ),
        )

        attempt.calculate_result()

        attempt.refresh_from_db()
        enrollment.refresh_from_db()

        self.assertTrue(
            attempt.is_completed,
        )
        self.assertTrue(
            attempt.is_passed,
        )
        self.assertEqual(
            attempt.correct_answers,
            2,
        )
        self.assertEqual(
            attempt.score_percentage,
            Decimal("100.00"),
        )
        self.assertTrue(
            enrollment.is_completed,
        )
        self.assertIsNotNone(
            enrollment.completed_at,
        )

        certificate = Certificate.objects.get(
            enrollment=enrollment,
        )

        self.assertEqual(
            certificate.assessment_attempt,
            attempt,
        )
        self.assertTrue(
            certificate.certificate_number.startswith(
                "SSI-",
            ),
        )

    def test_failed_assessment_does_not_create_certificate(self):
        enrollment = self._create_enrollment()
        self._complete_all_lessons(
            enrollment,
        )

        (
            attempt,
            attempt_question_one,
            attempt_question_two,
        ) = self._create_attempt(
            enrollment,
        )

        StudentAnswer.objects.create(
            attempt_question=attempt_question_one,
            selected_option=(
                self.question_one.correct_answer
            ),
        )

        wrong_option = (
            self.question_two.answer_options
            .filter(
                is_correct=False,
            )
            .first()
        )

        StudentAnswer.objects.create(
            attempt_question=attempt_question_two,
            selected_option=wrong_option,
        )

        attempt.calculate_result()

        attempt.refresh_from_db()
        enrollment.refresh_from_db()

        self.assertTrue(
            attempt.is_completed,
        )
        self.assertFalse(
            attempt.is_passed,
        )
        self.assertEqual(
            attempt.score_percentage,
            Decimal("50.00"),
        )
        self.assertFalse(
            enrollment.is_completed,
        )
        self.assertFalse(
            Certificate.objects.filter(
                enrollment=enrollment,
            ).exists(),
        )

    def test_certificate_is_visible_only_to_its_owner(self):
        enrollment = self._create_enrollment()
        self._complete_all_lessons(
            enrollment,
        )

        (
            attempt,
            attempt_question_one,
            attempt_question_two,
        ) = self._create_attempt(
            enrollment,
        )

        StudentAnswer.objects.create(
            attempt_question=attempt_question_one,
            selected_option=(
                self.question_one.correct_answer
            ),
        )
        StudentAnswer.objects.create(
            attempt_question=attempt_question_two,
            selected_option=(
                self.question_two.correct_answer
            ),
        )

        attempt.calculate_result()

        certificate = Certificate.objects.get(
            enrollment=enrollment,
        )

        certificate_url = reverse(
            "courses:certificate_detail",
            kwargs={
                "certificate_number": (
                    certificate.certificate_number
                ),
            },
        )

        self._login(
            self.other_student,
        )

        other_student_response = self.client.get(
            certificate_url,
        )

        self.assertEqual(
            other_student_response.status_code,
            404,
        )

        self._login(
            self.student,
        )

        owner_response = self.client.get(
            certificate_url,
        )

        self.assertEqual(
            owner_response.status_code,
            200,
        )
        self.assertEqual(
            owner_response.context["certificate"],
            certificate,
        )
