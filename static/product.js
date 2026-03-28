const mainImage = document.getElementById("mainImage");
const thumbButtons = document.querySelectorAll(".thumb-btn");
const paymentModal = document.getElementById("paymentModal");
const buyNowBtn = document.getElementById("buyNowBtn");
const closePaymentModal = document.getElementById("closePaymentModal");
const submitPaymentBtn = document.getElementById("submitPaymentBtn");
const paymentFeedback = document.getElementById("paymentFeedback");
const paymentForm = document.querySelector(".payment-form");
const paymentQrImage = document.getElementById("paymentQrImage");
const paymentAmountInline = document.getElementById("paymentAmountInline");
const fullNameInput = document.getElementById("fullNameInput");
const paymentStatusPopup = document.getElementById("paymentStatusPopup");
const closeStatusPopup = document.getElementById("closeStatusPopup");
const instructionLevelsSection = document.getElementById("instructionLevelsSection");
const unlockLevel1Card = document.getElementById("unlockLevel1");
const unlockLevel2Card = document.getElementById("unlockLevel2");
const unlockLevel3Card = document.getElementById("unlockLevel3");
const level3Congrats = document.getElementById("level3Congrats");
const level1InstructionFlow = document.getElementById("level1InstructionFlow");
const level1EmailRow = document.getElementById("level1EmailRow");
const level2InstructionFlow = document.getElementById("level2InstructionFlow");
const level2InstructionImage = document.getElementById("level2InstructionImage");
const level2InstructionNextBtn = document.getElementById("level2InstructionNextBtn");
const level2CodeRow = document.getElementById("level2CodeRow");
const level2Timer = document.getElementById("level2Timer");
const instructionImage = document.getElementById("instructionImage");
const instructionCopy = document.getElementById("instructionCopy");
const instructionNextBtn = document.getElementById("instructionNextBtn");
const level3Timer = document.getElementById("level3Timer");

let selectedLevel = window.productData?.nextPaymentLevel || 1;
let level2RefreshTimer = null;
let level2RefreshTimeout = null;
let level2CountdownTimer = null;
let level3RefreshTimer = null;
let level3RefreshTimeout = null;
let level3CountdownTimer = null;
let instructionStep = 0;
let paymentStatusPollTimer = null;
let currentApprovedLevel = Number(window.productData?.approvedLevel || 0);

const levelDescriptions = {
    1: "Shows account email only.",
    2: "Shows the protected partial access code with blur.",
    3: "Shows the full live code and refreshes it every 60 seconds.",
};
const levelAmounts = {
    1: Number(window.productData?.paymentAmounts?.[1] || 399),
    2: Number(window.productData?.paymentAmounts?.[2] || 899),
    3: Number(window.productData?.paymentAmounts?.[3] || 1399),
};
const instructionSteps = [
    "Step 1: click Next to continue the email setup instruction.",
    "Step 2: click Next once more to finish and reveal the email.",
];

function setPaymentFeedback(message, isError = false) {
    paymentFeedback.textContent = message;
    paymentFeedback.classList.toggle("is-error", isError);
}

function buildPaymentQr(level) {
    const amount = levelAmounts[level];
    return `https://api.qrserver.com/v1/create-qr-code/?size=360x360&data=${encodeURIComponent(buildPaymentLink(level))}`;
}

function buildPaymentLink(level) {
    const amount = levelAmounts[level];
    const params = new URLSearchParams({
        pa: window.productData.paymentUpiId,
        pn: window.productData.paymentUpiName,
        am: String(amount),
        cu: "INR",
    });

    return `upi://pay?${params.toString()}`;
}

function isMobileDevice() {
    return /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent);
}

function openUpiApp(level = selectedLevel) {
    window.location.href = buildPaymentLink(level);
}

function updateStage(level) {
    const amount = levelAmounts[level];
    selectedLevel = level;
    if (submitPaymentBtn) {
        submitPaymentBtn.textContent = `Pay Rs. ${amount}`;
    }
    if (paymentQrImage) {
        paymentQrImage.src = buildPaymentQr(level);
    }
    if (paymentAmountInline) {
        paymentAmountInline.textContent = `This QR opens a direct payment of Rs. ${amount}.`;
    }
}

function completeFlow() {
    if (paymentForm) {
        paymentForm.classList.add("hidden");
    }
}

function startPaymentStatusPolling() {
    if (!window.productData?.accountId || paymentStatusPollTimer) return;

    const pollStatus = async () => {
        try {
            const response = await fetch(`/payment_status/${window.productData.accountId}`, {
                headers: { Accept: "application/json" },
            });
            const result = await response.json();

            if (!response.ok || result.status !== "success") {
                return;
            }

            const approvedLevel = Number(result.approved_level || 0);
            const latestStatus = String(result.latest_payment_status || "").toLowerCase();
            const latestNote = String(result.latest_payment_note || "").trim();

            if (approvedLevel > currentApprovedLevel) {
                currentApprovedLevel = approvedLevel;
                window.productData.approvedLevel = approvedLevel;
                window.productData.nextPaymentLevel = Number(result.next_payment_level || selectedLevel);
                window.productData.unlock = result.unlock || window.productData.unlock;
                unlockLevel(approvedLevel, window.productData.unlock);

                if (approvedLevel < 3) {
                    updateStage(window.productData.nextPaymentLevel || (approvedLevel + 1));
                } else {
                    completeFlow();
                }

                setPaymentFeedback(latestNote || `Level ${approvedLevel} approved successfully.`);
            }

            if (latestStatus === "approved" || latestStatus === "rejected") {
                clearInterval(paymentStatusPollTimer);
                paymentStatusPollTimer = null;
            }
        } catch {
            // Keep polling quietly so temporary fetch issues do not break the product flow.
        }
    };

    paymentStatusPollTimer = setInterval(pollStatus, 3000);
    pollStatus();
}

function openModal() {
    paymentModal.classList.remove("hidden");
    document.body.style.overflow = "hidden";
}

function closeModal() {
    paymentModal.classList.add("hidden");
    document.body.style.overflow = "";
}

function rotateFullCode(seed) {
    const source = String(seed || "FFSTORE");
    let hash = 0;
    const windowStamp = Math.floor(Date.now() / 60000);

    for (let index = 0; index < source.length; index += 1) {
        hash = ((hash * 41) + source.charCodeAt(index) + windowStamp) % 10000000;
    }

    return String(Math.abs(hash)).padStart(7, "0").slice(-7);
}

function rotateLevel2Code(seed) {
    const source = String(seed || "FFSTORE");
    let hash = 0;
    const windowStamp = Math.floor(Date.now() / 120000);

    for (let index = 0; index < source.length; index += 1) {
        hash = ((hash * 31) + source.charCodeAt(index) + windowStamp) % 10000000;
    }

    const code = String(Math.abs(hash)).padStart(7, "0").slice(-7);
    return `${code.slice(0, 4)}***`;
}

function updateCountdown(timerElement, refreshWindow) {
    if (!timerElement) return;
    const remainder = Date.now() % refreshWindow;
    const remainingMs = remainder === 0 ? 0 : refreshWindow - remainder;
    const remainingSeconds = Math.max(1, Math.ceil(remainingMs / 1000));
    timerElement.textContent = `${remainingSeconds}s`;
}

function scheduleAlignedLevel2Refresh(renderLevel2Code) {
    if (level2RefreshTimeout) clearTimeout(level2RefreshTimeout);
    if (level2RefreshTimer) clearInterval(level2RefreshTimer);
    if (level2CountdownTimer) clearInterval(level2CountdownTimer);

    const refreshWindow = 120000;
    const runLevel2Refresh = () => {
        renderLevel2Code();
        const remainder = Date.now() % refreshWindow;
        const nextDelay = remainder === 0 ? refreshWindow : refreshWindow - remainder;
        level2RefreshTimeout = setTimeout(runLevel2Refresh, nextDelay);
    };

    updateCountdown(level2Timer, refreshWindow);
    level2CountdownTimer = setInterval(() => updateCountdown(level2Timer, refreshWindow), 1000);
    const remainder = Date.now() % refreshWindow;
    const delay = remainder === 0 ? refreshWindow : refreshWindow - remainder;
    level2RefreshTimeout = setTimeout(runLevel2Refresh, delay);
}

function scheduleAlignedLevel3Refresh(renderLevel3Code) {
    if (level3RefreshTimeout) clearTimeout(level3RefreshTimeout);
    if (level3RefreshTimer) clearInterval(level3RefreshTimer);
    if (level3CountdownTimer) clearInterval(level3CountdownTimer);

    const refreshWindow = 60000;
    const runLevel3Refresh = () => {
        renderLevel3Code();
        const remainder = Date.now() % refreshWindow;
        const nextDelay = remainder === 0 ? refreshWindow : refreshWindow - remainder;
        level3RefreshTimeout = setTimeout(runLevel3Refresh, nextDelay);
    };

    updateCountdown(level3Timer, refreshWindow);
    level3CountdownTimer = setInterval(() => updateCountdown(level3Timer, refreshWindow), 1000);
    const remainder = Date.now() % refreshWindow;
    const delay = remainder === 0 ? refreshWindow : refreshWindow - remainder;
    level3RefreshTimeout = setTimeout(runLevel3Refresh, delay);
}

function renderInstructionStep() {
    if (!instructionImage || !instructionCopy || !instructionNextBtn) return;

    instructionImage.src = window.productData.instructionImages[instructionStep];
    instructionCopy.textContent = instructionSteps[instructionStep];
    instructionNextBtn.textContent = instructionStep === instructionSteps.length - 1 ? "Show Email" : "Next";
}

function showInstructionStage(approvedLevel) {
    const cards = [unlockLevel1Card, unlockLevel2Card, unlockLevel3Card];
    cards.forEach((card) => card?.classList.add("hidden"));

    if (!instructionLevelsSection) return;

    if (approvedLevel <= 0) {
        instructionLevelsSection.classList.add("hidden");
        return;
    }

    instructionLevelsSection.classList.remove("hidden");

    if (approvedLevel === 1) {
        unlockLevel1Card?.classList.remove("hidden");
        unlockLevel2Card?.classList.remove("hidden");
        return;
    }

    if (approvedLevel === 2) {
        unlockLevel1Card?.classList.remove("hidden");
        unlockLevel2Card?.classList.remove("hidden");
        unlockLevel3Card?.classList.remove("hidden");
        return;
    }

    unlockLevel1Card?.classList.remove("hidden");
    unlockLevel3Card?.classList.remove("hidden");
}

function unlockLevel(level, unlockData) {
    if (level >= 1) {
        document.querySelector('[data-field="level1_email"]').textContent = unlockData.level1_email;
        instructionStep = 0;
        if (level1InstructionFlow) {
            level1InstructionFlow.classList.remove("hidden");
            renderInstructionStep();
        }
        if (level1EmailRow) {
            level1EmailRow.classList.add("hidden");
        }
        document.getElementById("unlockLevel1").classList.add("is-unlocked");
    }

    if (level >= 2) {
        const partial = document.querySelector('[data-field="level2_code"]');
        const renderLevel2Code = () => {
            partial.textContent = rotateLevel2Code(unlockData.level3_seed);
        };

        renderLevel2Code();
        if (level2CodeRow) {
            level2CodeRow.classList.add("hidden");
        }
        if (level2InstructionFlow) {
            level2InstructionFlow.classList.remove("hidden");
        }
        if (level2InstructionImage && window.productData.level2InstructionImage) {
            level2InstructionImage.src = window.productData.level2InstructionImage;
        }
        document.getElementById("unlockLevel2").classList.add("is-unlocked");
        scheduleAlignedLevel2Refresh(renderLevel2Code);
    }

    if (level >= 3) {
        const fullCodeEl = document.querySelector('[data-field="level3_seed"]');
        const renderCode = () => {
            fullCodeEl.textContent = rotateFullCode(unlockData.level3_seed);
        };

        if (level2InstructionFlow) {
            level2InstructionFlow.classList.add("hidden");
        }
        if (level2CodeRow) {
            level2CodeRow.classList.add("hidden");
        }
        if (unlockLevel2Card) {
            unlockLevel2Card.classList.add("hidden");
        }
        renderCode();
        document.getElementById("unlockLevel3").classList.add("is-unlocked");
        level3Congrats?.classList.remove("hidden");
        scheduleAlignedLevel3Refresh(renderCode);
    }

    showInstructionStage(level);
}

thumbButtons.forEach((button) => {
    button.addEventListener("click", () => {
        mainImage.src = button.dataset.image;
        thumbButtons.forEach((thumb) => thumb.classList.remove("is-active"));
        button.classList.add("is-active");
    });
});

buyNowBtn?.addEventListener("click", () => {
    if (isMobileDevice()) {
        openUpiApp(selectedLevel);
        setTimeout(openModal, 500);
        return;
    }

    openModal();
});
closePaymentModal?.addEventListener("click", closeModal);
paymentModal?.addEventListener("click", (event) => {
    if (event.target === paymentModal) closeModal();
});
closeStatusPopup?.addEventListener("click", () => {
    paymentStatusPopup?.classList.add("hidden");
});
level2InstructionNextBtn?.addEventListener("click", () => {
    if (level2InstructionFlow) {
        level2InstructionFlow.classList.add("hidden");
    }
    if (level2CodeRow) {
        level2CodeRow.classList.remove("hidden");
    }
});
instructionNextBtn?.addEventListener("click", () => {
    if (instructionStep < instructionSteps.length - 1) {
        instructionStep += 1;
        renderInstructionStep();
        return;
    }

    if (level1InstructionFlow) {
        level1InstructionFlow.classList.add("hidden");
    }
    if (level1EmailRow) {
        level1EmailRow.classList.remove("hidden");
    }
});

submitPaymentBtn?.addEventListener("click", async () => {
    const fullName = fullNameInput?.value.trim() || "";
    const utr = document.getElementById("utrInput").value.trim();
    if (fullName.length < 3) {
        setPaymentFeedback("Enter full name before submitting payment.", true);
        return;
    }
    if (!/^\d{12}$/.test(utr)) {
        setPaymentFeedback("Enter a valid 12-digit UTR number.", true);
        return;
    }

    setPaymentFeedback("Verifying payment...");

    try {
        const response = await fetch("/submit_payment", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                account_id: window.productData.accountId,
                full_name: fullName,
                utr,
                level: selectedLevel,
            }),
        });

        const result = await response.json();
        if (!response.ok || result.status !== "success") {
            throw new Error(result.message || "Payment verification failed.");
        }

        setPaymentFeedback(result.message || `Payment of Rs. ${levelAmounts[result.level]} submitted for review.`);
        document.getElementById("utrInput").value = "";
        startPaymentStatusPolling();
    } catch (error) {
        setPaymentFeedback(error.message, true);
    }
});

if (window.productData.approvedLevel > 0) {
    currentApprovedLevel = Number(window.productData.approvedLevel || 0);
    unlockLevel(window.productData.approvedLevel, window.productData.unlock);
    if (window.productData.approvedLevel < 3) {
        updateStage(window.productData.nextPaymentLevel || (window.productData.approvedLevel + 1));
    } else {
        completeFlow();
    }
} else {
    updateStage(window.productData.nextPaymentLevel || 1);
}

if ((window.productData.paymentPopup?.tone || "").toLowerCase() !== "approved") {
    startPaymentStatusPolling();
}

if (window.productData.paymentPopup && paymentStatusPopup) {
    setTimeout(() => {
        paymentStatusPopup.classList.add("is-visible");
    }, 250);
}

const canvas = document.getElementById("particleCanvas");
if (canvas) {
    const ctx = canvas.getContext("2d");
    const particles = [];
    const particleCount = 60;

    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }

    function createParticle() {
        return {
            x: Math.random() * canvas.width,
            y: Math.random() * canvas.height,
            size: Math.random() * 2.6 + 0.5,
            speedX: (Math.random() - 0.5) * 0.5,
            speedY: (Math.random() - 0.5) * 0.5,
        };
    }

    function initParticles() {
        particles.length = 0;
        for (let i = 0; i < particleCount; i += 1) {
            particles.push(createParticle());
        }
    }

    function animateParticles() {
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        particles.forEach((particle) => {
            particle.x += particle.speedX;
            particle.y += particle.speedY;

            if (particle.x < 0 || particle.x > canvas.width) particle.speedX *= -1;
            if (particle.y < 0 || particle.y > canvas.height) particle.speedY *= -1;

            ctx.beginPath();
            ctx.fillStyle = "rgba(0, 194, 255, 0.6)";
            ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
            ctx.fill();
        });

        requestAnimationFrame(animateParticles);
    }

    resizeCanvas();
    initParticles();
    animateParticles();
    window.addEventListener("resize", () => {
        resizeCanvas();
        initParticles();
    });
}
