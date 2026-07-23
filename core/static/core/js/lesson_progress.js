document.addEventListener("DOMContentLoaded", function () {
    const lessonSection = document.querySelector(
        ".lesson-detail-section"
    );

    if (!lessonSection) {
        return;
    }

    const courseSlug = lessonSection.dataset.courseSlug;
    const currentLessonId =
        lessonSection.dataset.currentLessonId;

    const storageKey =
        `skillstart-course-progress-${courseSlug}`;

    const completionButton = document.getElementById(
        "lesson-completion-button"
    );

    const completionButtonText = document.querySelector(
        ".lesson-completion-button-text"
    );

    const progressSummary = document.getElementById(
        "lesson-progress-summary"
    );

    const progressPercentage = document.getElementById(
        "lesson-progress-percentage"
    );

    const progressBar = document.getElementById(
        "lesson-progress-bar"
    );

    const progressFill = document.getElementById(
        "lesson-progress-fill"
    );

    const sidebarLessons = Array.from(
        document.querySelectorAll(
            "[data-sidebar-lesson-id]"
        )
    );

    if (
        !completionButton ||
        !completionButtonText ||
        !progressSummary ||
        !progressPercentage ||
        !progressBar ||
        !progressFill
    ) {
        console.error(
            "Some lesson progress elements were not found."
        );

        return;
    }

    function getCompletedLessons() {
        try {
            const savedProgress =
                localStorage.getItem(storageKey);

            if (!savedProgress) {
                return [];
            }

            const parsedProgress =
                JSON.parse(savedProgress);

            if (!Array.isArray(parsedProgress)) {
                return [];
            }

            return parsedProgress.map(String);
        } catch (error) {
            console.error(
                "Could not read course progress:",
                error
            );

            return [];
        }
    }

    function saveCompletedLessons(completedLessons) {
        try {
            localStorage.setItem(
                storageKey,
                JSON.stringify(completedLessons)
            );
        } catch (error) {
            console.error(
                "Could not save course progress:",
                error
            );
        }
    }

    function updateProgressDisplay() {
        const completedLessons =
            getCompletedLessons();

        const totalLessons =
            sidebarLessons.length;

        const completedCount =
            sidebarLessons.filter(function (item) {
                return completedLessons.includes(
                    item.dataset.sidebarLessonId
                );
            }).length;

        const percentage = totalLessons > 0
            ? Math.round(
                (completedCount / totalLessons) * 100
            )
            : 0;

        progressSummary.textContent =
            `${completedCount} of ${totalLessons} ` +
            `lesson${totalLessons === 1 ? "" : "s"} completed`;

        progressPercentage.textContent =
            `${percentage}%`;

        progressFill.style.width =
            `${percentage}%`;

        progressBar.setAttribute(
            "aria-valuenow",
            String(percentage)
        );

        sidebarLessons.forEach(function (sidebarLesson) {
            const lessonId =
                sidebarLesson.dataset.sidebarLessonId;

            const isCompleted =
                completedLessons.includes(lessonId);

            sidebarLesson.classList.toggle(
                "completed",
                isCompleted
            );
        });

        const currentLessonCompleted =
            completedLessons.includes(
                String(currentLessonId)
            );

        completionButton.classList.toggle(
            "completed",
            currentLessonCompleted
        );

        completionButton.setAttribute(
            "aria-pressed",
            currentLessonCompleted
                ? "true"
                : "false"
        );

        completionButtonText.textContent =
            currentLessonCompleted
                ? "Completed"
                : "Mark as completed";
    }

    completionButton.addEventListener(
        "click",
        function () {
            const completedLessons =
                getCompletedLessons();

            const currentId =
                String(currentLessonId);

            const lessonIndex =
                completedLessons.indexOf(currentId);

            if (lessonIndex === -1) {
                completedLessons.push(currentId);
            } else {
                completedLessons.splice(
                    lessonIndex,
                    1
                );
            }

            saveCompletedLessons(completedLessons);
            updateProgressDisplay();
        }
    );

    updateProgressDisplay();
});