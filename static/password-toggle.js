const eyeIcon = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M12 5C6.5 5 2.1 8.5 1 12c1.1 3.5 5.5 7 11 7s9.9-3.5 11-7c-1.1-3.5-5.5-7-11-7Zm0 11a4 4 0 1 1 0-8 4 4 0 0 1 0 8Z" fill="currentColor"></path>
    <circle cx="12" cy="12" r="2.2" fill="currentColor"></circle>
</svg>
`;

const eyeOffIcon = `
<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
    <path d="M3.3 4.7 19.3 20.7l1.4-1.4-2.5-2.5c2-1.4 3.6-3.2 4.3-4.8-1.1-3.5-5.5-7-11-7-2 0-3.8.5-5.3 1.2L4.7 3.3 3.3 4.7Zm8.7 3.3a4 4 0 0 1 4 4c0 .8-.2 1.5-.6 2.1l-5.5-5.5c.6-.4 1.3-.6 2.1-.6Zm-8 4c.7 2.2 2.8 4.4 5.7 5.7l-1.6-1.6A4 4 0 0 1 7 12c0-.3 0-.7.1-1L4 7.9C3.2 9 2.5 10.4 2 12Zm6.9-.8 3.9 3.9c-.7.5-1.7.9-2.8.9a4 4 0 0 1-1.1-7.8Z" fill="currentColor"></path>
</svg>
`;

document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    const target = document.getElementById(button.dataset.target || "");
    if (!target) return;

    const updateState = () => {
        const shown = target.type === "text";
        button.innerHTML = shown ? eyeOffIcon : eyeIcon;
        button.setAttribute("aria-label", shown ? "Hide password" : "Show password");
        button.setAttribute("aria-pressed", shown ? "true" : "false");
    };

    button.addEventListener("click", () => {
        target.type = target.type === "password" ? "text" : "password";
        updateState();
    });

    updateState();
});

document.querySelectorAll("[data-secret-toggle]").forEach((button) => {
    const target = document.querySelector(button.dataset.target || "");
    if (!target) return;

    const updateState = () => {
        const secret = target.dataset.secretValue || "";
        const masked = target.dataset.maskedValue || "********";
        const shown = target.dataset.revealed === "true";

        target.textContent = shown && secret ? secret : masked;
        button.innerHTML = shown ? eyeOffIcon : eyeIcon;
        button.setAttribute("aria-label", shown ? "Hide password" : "Show password");
        button.setAttribute("aria-pressed", shown ? "true" : "false");
        button.disabled = !secret;
        button.classList.toggle("is-disabled", !secret);
    };

    button.addEventListener("click", () => {
        if (!target.dataset.secretValue) return;
        target.dataset.revealed = target.dataset.revealed === "true" ? "false" : "true";
        updateState();
    });

    updateState();
});
