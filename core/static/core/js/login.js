document.addEventListener("DOMContentLoaded", function () {
    const passwordInput = document.getElementById(
        "id_password"
    );

    const passwordToggle = document.getElementById(
        "login-password-toggle"
    );

    if (!passwordInput || !passwordToggle) {
        return;
    }

    passwordToggle.addEventListener(
        "click",
        function () {
            const passwordIsVisible =
                passwordInput.type === "text";

            passwordInput.type =
                passwordIsVisible
                    ? "password"
                    : "text";

            passwordToggle.textContent =
                passwordIsVisible
                    ? "Show password"
                    : "Hide password";

            passwordToggle.setAttribute(
                "aria-pressed",
                String(!passwordIsVisible)
            );

            passwordInput.focus();
        }
    );
});