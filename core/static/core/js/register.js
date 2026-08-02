document.addEventListener("DOMContentLoaded", function () {
    const passwordToggles = document.querySelectorAll(
        ".register-password-toggle"
    );

    passwordToggles.forEach(function (passwordToggle) {
        const targetId = passwordToggle.dataset.passwordTarget;
        const passwordInput = document.getElementById(targetId);

        if (!passwordInput) {
            return;
        }

        passwordToggle.addEventListener("click", function () {
            const passwordIsVisible =
                passwordInput.type === "text";

            passwordInput.type = passwordIsVisible
                ? "password"
                : "text";

            passwordToggle.textContent = passwordIsVisible
                ? "Show"
                : "Hide";

            passwordToggle.setAttribute(
                "aria-pressed",
                String(!passwordIsVisible)
            );

            passwordInput.focus();
        });
    });
});