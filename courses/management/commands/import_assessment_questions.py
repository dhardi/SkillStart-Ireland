import json
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import (
    BaseCommand,
    CommandError,
)
from django.db import transaction

from courses.models import (
    AnswerOption,
    Course,
    CourseAssessment,
    Question,
)


class Command(BaseCommand):
    help = (
        "Imports assessment questions and answer options "
        "from a JSON file."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "json_file",
            type=str,
            help=(
                "JSON filename inside courses/fixtures, "
                "or the complete path to the JSON file."
            ),
        )

    def handle(self, *args, **options):
        json_file = options["json_file"]

        file_path = self.get_json_file_path(
            json_file,
        )

        data = self.load_json(
            file_path,
        )

        course_slug = data.get(
            "course_slug",
        )

        assessment_title = data.get(
            "assessment_title",
        )

        questions_data = data.get(
            "questions",
        )

        if not course_slug:
            raise CommandError(
                "The JSON file must contain 'course_slug'."
            )

        if not questions_data:
            raise CommandError(
                "The JSON file must contain a non-empty "
                "'questions' list."
            )

        try:
            course = Course.objects.get(
                slug=course_slug,
            )
        except Course.DoesNotExist as error:
            raise CommandError(
                (
                    f"No course was found with the slug "
                    f"'{course_slug}'."
                )
            ) from error

        try:
            assessment = CourseAssessment.objects.get(
                course=course,
            )
        except CourseAssessment.DoesNotExist as error:
            raise CommandError(
                (
                    "This course does not have an assessment. "
                    "Create and publish the assessment in the "
                    "Django Admin before importing questions."
                )
            ) from error

        if (
            assessment_title
            and assessment.title != assessment_title
        ):
            self.stdout.write(
                self.style.WARNING(
                    (
                        "The assessment title in the JSON does "
                        "not exactly match the title in the database."
                    )
                )
            )

            self.stdout.write(
                f"JSON title: {assessment_title}"
            )

            self.stdout.write(
                f"Database title: {assessment.title}"
            )

        created_questions = 0
        updated_questions = 0
        imported_answers = 0

        with transaction.atomic():
            for question_data in questions_data:
                result = self.import_question(
                    assessment=assessment,
                    question_data=question_data,
                )

                if result == "created":
                    created_questions += 1
                else:
                    updated_questions += 1

                imported_answers += 4

        assessment.refresh_from_db()

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "========================================"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "SkillStart Ireland assessment import"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                "========================================"
            )
        )

        self.stdout.write(
            f"Course: {course.title}"
        )

        self.stdout.write(
            f"Assessment: {assessment.title}"
        )

        self.stdout.write(
            f"Questions created: {created_questions}"
        )

        self.stdout.write(
            f"Questions updated: {updated_questions}"
        )

        self.stdout.write(
            f"Answer options imported: {imported_answers}"
        )

        self.stdout.write(
            (
                "Published questions: "
                f"{assessment.published_question_count}"
            )
        )

        if assessment.is_ready:
            self.stdout.write(
                self.style.SUCCESS(
                    "Assessment ready: YES"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Assessment ready: NO"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Import completed successfully."
            )
        )

    def get_json_file_path(self, json_file):
        supplied_path = Path(
            json_file,
        )

        if supplied_path.is_file():
            return supplied_path

        fixture_path = (
            Path(__file__)
            .resolve()
            .parents[2]
            / "fixtures"
            / json_file
        )

        if fixture_path.is_file():
            return fixture_path

        raise CommandError(
            (
                f"The JSON file '{json_file}' was not found.\n"
                f"Expected location: {fixture_path}"
            )
        )

    def load_json(self, file_path):
        try:
            with file_path.open(
                "r",
                encoding="utf-8",
            ) as json_file:
                return json.load(
                    json_file,
                )

        except json.JSONDecodeError as error:
            raise CommandError(
                (
                    "The JSON file is invalid. "
                    f"Line {error.lineno}, "
                    f"column {error.colno}: "
                    f"{error.msg}"
                )
            ) from error

        except OSError as error:
            raise CommandError(
                (
                    "The JSON file could not be opened: "
                    f"{error}"
                )
            ) from error

    def import_question(
        self,
        assessment,
        question_data,
    ):
        order = question_data.get(
            "order",
        )

        text = question_data.get(
            "text",
            "",
        ).strip()

        explanation = question_data.get(
            "explanation",
            "",
        ).strip()

        is_published = question_data.get(
            "is_published",
            True,
        )

        answers = question_data.get(
            "answers",
            [],
        )

        self.validate_question_data(
            order=order,
            text=text,
            answers=answers,
        )

        question, created = (
            Question.objects.update_or_create(
                assessment=assessment,
                order=order,
                defaults={
                    "text": text,
                    "explanation": explanation,
                    "is_published": is_published,
                },
            )
        )

        # Recreates the four answers to ensure that
        # the JSON remains the source of truth.
        question.answer_options.all().delete()

        for answer_data in sorted(
            answers,
            key=lambda answer: answer["order"],
        ):
            answer = AnswerOption(
                question=question,
                order=answer_data["order"],
                text=answer_data["text"].strip(),
                is_correct=answer_data["is_correct"],
            )

            try:
                answer.save()
            except ValidationError as error:
                raise CommandError(
                    (
                        f"Question {order}: "
                        f"{'; '.join(error.messages)}"
                    )
                ) from error

        if not question.is_ready:
            raise CommandError(
                (
                    f"Question {order} is not ready after "
                    "the import."
                )
            )

        return (
            "created"
            if created
            else "updated"
        )

    def validate_question_data(
        self,
        order,
        text,
        answers,
    ):
        if not isinstance(order, int) or order < 1:
            raise CommandError(
                "Every question must have a positive "
                "integer 'order'."
            )

        if not text:
            raise CommandError(
                f"Question {order} has no text."
            )

        if len(answers) != 4:
            raise CommandError(
                (
                    f"Question {order} must contain "
                    "exactly four answers."
                )
            )

        answer_orders = [
            answer.get("order")
            for answer in answers
        ]

        if sorted(answer_orders) != [
            1,
            2,
            3,
            4,
        ]:
            raise CommandError(
                (
                    f"Question {order} must use answer "
                    "orders 1, 2, 3 and 4."
                )
            )

        correct_answer_count = sum(
            1
            for answer in answers
            if answer.get("is_correct") is True
        )

        if correct_answer_count != 1:
            raise CommandError(
                (
                    f"Question {order} must contain "
                    "exactly one correct answer."
                )
            )

        for answer in answers:
            answer_text = answer.get(
                "text",
                "",
            ).strip()

            if not answer_text:
                raise CommandError(
                    (
                        f"Question {order} contains "
                        "an answer without text."
                    )
                )

            if not isinstance(
                answer.get("is_correct"),
                bool,
            ):
                raise CommandError(
                    (
                        f"Question {order} contains an "
                        "invalid 'is_correct' value."
                    )
                )