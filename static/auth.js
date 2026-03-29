const signinForm = document.getElementById("signinForm");
const authFeedback = document.getElementById("authFeedback");

function setFeedback(message, isError = false) {
    if (!authFeedback) return;
    authFeedback.textContent = message;
    authFeedback.classList.toggle("is-error", isError);
}

async function submitAuth(url, payload) {
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const result = await response.json();
    if (!response.ok || result.status !== "success") {
        throw new Error(result.message || "Something went wrong.");
    }
    return result;
}

signinForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFeedback("Opening your store access...");

    try {
        const result = await submitAuth("/login", {
            name: document.getElementById("loginName").value.trim(),
        });
        setFeedback("Login successful. Redirecting...");
        window.location.href = result.redirect;
    } catch (error) {
        setFeedback(error.message, true);
    }
});
