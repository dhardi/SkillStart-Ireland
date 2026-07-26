document.addEventListener("DOMContentLoaded", function () {
    const lessonSection = document.querySelector(
        ".lesson-detail-section"
    );

    if (!lessonSection) {
        return;
    }

    const completeUrl =
        lessonSection.dataset.completeUrl;

    const currentLessonId =
        lessonSection.dataset.currentLessonId;

    const hasVideo =
        lessonSection.dataset.hasVideo === "true";

    let currentLessonCompleted =
        lessonSection.dataset.isCompleted === "true";

    const nextLessonLink = document.querySelector(
        ".lesson-navigation-link-next"
    );

    const completionStatus = document.getElementById(
        "lesson-completion-status"
    );

    const completionMessage = document.getElementById(
        "lesson-completion-message"
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

    const youtubePlayerElement =
        document.getElementById(
            "lesson-youtube-player"
        );

    let lessonIsBeingSaved = false;

    /*
     * Uma lesson que já foi concluída anteriormente
     * não precisa ficar bloqueada novamente.
     */
    let videoHasEnded = currentLessonCompleted;

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

    function lockNextLesson() {
        if (!nextLessonLink) {
            return;
        }

        nextLessonLink.classList.add("locked");

        nextLessonLink.setAttribute(
            "aria-disabled",
            "true"
        );
    }

    function unlockNextLesson() {
        if (!nextLessonLink) {
            return;
        }

        nextLessonLink.classList.remove("locked");

        nextLessonLink.removeAttribute(
            "aria-disabled"
        );
    }

    function showVideoRequiredMessage() {
        if (completionStatus) {
            completionStatus.textContent =
                "Watch the video to continue";
        }

        if (completionMessage) {
            completionMessage.textContent =
                "The next lesson will be unlocked " +
                "when the video finishes.";
        }
    }

    function updateProgressDisplay(data) {
        const sidebarLesson = document.querySelector(
            `[data-sidebar-lesson-id="${currentLessonId}"]`
        );

        if (sidebarLesson) {
            sidebarLesson.classList.add(
                "completed"
            );
        }

        if (completionStatus) {
            completionStatus.textContent =
                "Lesson completed";
        }

        if (completionMessage) {
            completionMessage.textContent =
                "Your progress has been saved.";
        }

        if (progressSummary) {
            const lessonWord =
                data.total_lessons === 1
                    ? "lesson"
                    : "lessons";

            progressSummary.textContent =
                `${data.completed_count} of ` +
                `${data.total_lessons} ` +
                `${lessonWord} completed`;
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
    }

    async function completeCurrentLesson() {
        if (currentLessonCompleted) {
            return null;
        }

        if (!completeUrl) {
            return null;
        }

        if (lessonIsBeingSaved) {
            return null;
        }

        lessonIsBeingSaved = true;

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

            currentLessonCompleted = true;

            updateProgressDisplay(data);

            return data;
        } finally {
            lessonIsBeingSaved = false;
        }
    }

    /*
     * Lessons com vídeo começam bloqueadas,
     * exceto quando já foram concluídas.
     */
    if (
        hasVideo &&
        !currentLessonCompleted
    ) {
        lockNextLesson();
        showVideoRequiredMessage();
    }

    if (nextLessonLink) {
        nextLessonLink.addEventListener(
            "click",
            async function (event) {
                /*
                 * Vídeo ainda não terminou:
                 * não permite avançar.
                 */
                if (
                    hasVideo &&
                    !videoHasEnded &&
                    !currentLessonCompleted
                ) {
                    event.preventDefault();

                    showVideoRequiredMessage();

                    return;
                }

                /*
                 * Usuário não está autenticado.
                 * Não existe progresso para salvar.
                 */
                if (!completeUrl) {
                    return;
                }

                /*
                 * Lesson já concluída:
                 * segue o link normalmente.
                 */
                if (currentLessonCompleted) {
                    return;
                }

                event.preventDefault();

                const destination =
                    nextLessonLink.href;

                nextLessonLink.classList.add(
                    "saving"
                );

                nextLessonLink.setAttribute(
                    "aria-disabled",
                    "true"
                );

                try {
                    await completeCurrentLesson();

                    window.location.href =
                        destination;
                } catch (error) {
                    console.error(error);

                    nextLessonLink.classList.remove(
                        "saving"
                    );

                    if (
                        !hasVideo ||
                        videoHasEnded
                    ) {
                        unlockNextLesson();
                    }

                    if (completionStatus) {
                        completionStatus.textContent =
                            "Progress could not be saved";
                    }

                    if (completionMessage) {
                        completionMessage.textContent =
                            "Please check your connection " +
                            "and try again.";
                    }
                }
            }
        );
    }

    function initializeYouTubePlayer() {
        if (
            !youtubePlayerElement ||
            !youtubePlayerElement.dataset
                .youtubeVideoId
        ) {
            return;
        }

        const videoId =
            youtubePlayerElement.dataset
                .youtubeVideoId;

        new YT.Player(
            "lesson-youtube-player",
            {
                videoId: videoId,

                playerVars: {
                    rel: 0,
                    modestbranding: 1,
                },

                events: {
                    onStateChange:
                        handleYouTubeStateChange,
                },
            }
        );
    }

    async function handleYouTubeStateChange(
        event
    ) {
        if (
            event.data !==
            YT.PlayerState.ENDED
        ) {
            return;
        }

        videoHasEnded = true;

        /*
         * O vídeo terminou, então o aluno
         * já pode avançar.
         */
        unlockNextLesson();

        if (!completeUrl) {
            if (completionStatus) {
                completionStatus.textContent =
                    "Video completed";
            }

            if (completionMessage) {
                completionMessage.textContent =
                    "Sign in to save your progress.";
            }

            return;
        }

        try {
            await completeCurrentLesson();

            unlockNextLesson();
        } catch (error) {
            console.error(
                "Could not save progress after video:",
                error
            );

            /*
             * O botão continua liberado porque
             * o aluno assistiu ao vídeo.
             *
             * Ao clicar em Next, o sistema
             * tentará salvar novamente.
             */
            unlockNextLesson();

            if (completionStatus) {
                completionStatus.textContent =
                    "Video completed";
            }

            if (completionMessage) {
                completionMessage.textContent =
                    "Your progress could not be saved. " +
                    "Click Next lesson to try again.";
            }
        }
    }

    if (youtubePlayerElement) {
        /*
         * Caso a API do YouTube já tenha
         * terminado de carregar.
         */
        if (
            window.YT &&
            typeof window.YT.Player === "function"
        ) {
            initializeYouTubePlayer();
        } else {
            /*
             * A API chama esta função global
             * quando estiver pronta.
             */
            window.onYouTubeIframeAPIReady =
                initializeYouTubePlayer;
        }
    }
});