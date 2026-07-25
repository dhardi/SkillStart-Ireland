document.addEventListener("DOMContentLoaded", function () {
    const completionButton = document.getElementById(
        "lesson-completion-button"
    );

    if (!completionButton) {
        return;
    }

    const completeUrl =
        completionButton.dataset.completeUrl;

    if (!completeUrl) {
        return;
    }

    const completionButtonText =
        completionButton.querySelector(
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

    function getCookie(cookieName) {
        const cookies = document.cookie
            ? document.cookie.split(";")
            : [];

        for (const cookie of cookies) {
            const trimmedCookie = cookie.trim();

            if (
                trimmedCookie.startsWith(
                    `${cookieName}=`
                )
            ) {
                return decodeURIComponent(
                    trimmedCookie.substring(
                        cookieName.length + 1
                    )
                );
            }
        }

        return null;
    }

    completionButton.addEventListener(
        "click",
        async function () {
            completionButton.disabled = true;

            if (completionButtonText) {
                completionButtonText.textContent =
                    "Saving...";
            }

            try {
                const response = await fetch(
                    completeUrl,
                    {
                        method: "POST",
                        headers: {
                            "X-CSRFToken": getCookie(
                                "csrftoken"
                            ),
                            "X-Requested-With":
                                "XMLHttpRequest",
                        },
                    }
                );

                if (!response.ok) {
                    throw new Error(
                        "Could not save lesson progress."
                    );
                }

                const data = await response.json();

                completionButton.classList.add(
                    "completed"
                );

                completionButton.setAttribute(
                    "aria-pressed",
                    "true"
                );

                if (completionButtonText) {
                    completionButtonText.textContent =
                        "Completed";
                }

                const sidebarLesson =
                    document.querySelector(
                        `[data-sidebar-lesson-id="${data.lesson_id}"]`
                    );

                if (sidebarLesson) {
                    sidebarLesson.classList.add(
                        "completed"
                    );
                }

                if (progressSummary) {
                    progressSummary.textContent =
                        `${data.completed_count} of ` +
                        `${data.total_lessons} ` +
                        `lesson` +
                        `${data.total_lessons === 1 ? "" : "s"} ` +
                        `completed`;
                }

                if (progressPercentage) {
                    progressPercentage.textContent =
                        `${data.percentage}%`;
                }

                if (progressFill) {
                    progressFill.style.width =
                        `${data.percentage}%`;
                }

                if (progressBar) {
                    progressBar.setAttribute(
                        "aria-valuenow",
                        String(data.percentage)
                    );
                }
            } catch (error) {
                console.error(error);

                completionButton.disabled = false;

                if (completionButtonText) {
                    completionButtonText.textContent =
                        "Try again";
                }
            }
        }
    );
});