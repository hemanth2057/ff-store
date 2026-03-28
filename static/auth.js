const authTabs = document.querySelectorAll("#authTabs .tab-btn");
const signinForm = document.getElementById("signinForm");
const signupForm = document.getElementById("signupForm");
const authFeedback = document.getElementById("authFeedback");
const authTitle = document.getElementById("authTitle");
const authEyebrow = document.getElementById("authEyebrow");

function setFeedback(message, isError = false) {
    if (!authFeedback) return;
    authFeedback.textContent = message;
    authFeedback.classList.toggle("is-error", isError);
}

function switchTab(tabName) {
    authTabs.forEach((tab) => {
        tab.classList.toggle("is-active", tab.dataset.tab === tabName);
    });
    signinForm.classList.toggle("hidden", tabName !== "signin");
    signupForm.classList.toggle("hidden", tabName !== "signup");

    if (authTitle) {
        authTitle.textContent = tabName === "signup" ? "Create Player Account" : "Player Sign In";
    }
    if (authEyebrow) {
        authEyebrow.textContent = tabName === "signup" ? "Sign Up" : "Sign In";
    }

    setFeedback("");
}

authTabs.forEach((tab) => {
    tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

switchTab("signup");

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
    setFeedback("Signing you in...");

    try {
        const result = await submitAuth("/login", {
            email: document.getElementById("loginEmail").value.trim(),
            password: document.getElementById("loginPassword").value,
        });
        setFeedback("Login successful. Redirecting...");
        window.location.href = result.redirect;
    } catch (error) {
        setFeedback(error.message, true);
    }
});

signupForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    setFeedback("Creating your account...");

    try {
        const result = await submitAuth("/signup", {
            name: document.getElementById("signupName").value.trim(),
            email: document.getElementById("signupEmail").value.trim(),
            password: document.getElementById("signupPassword").value,
        });
        setFeedback("Signup successful. Redirecting...");
        window.location.href = result.redirect;
    } catch (error) {
        setFeedback(error.message, true);
    }
});
