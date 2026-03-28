const generateAiCopyBtn = document.getElementById("generateAiCopyBtn");
const listingTitleInput = document.getElementById("listingTitleInput");
const listingDescriptionInput = document.getElementById("listingDescriptionInput");
const listingPriceInput = document.getElementById("listingPriceInput");
const adminAiFeedback = document.getElementById("adminAiFeedback");
const selectAllAccounts = document.getElementById("selectAllAccounts");
const accountCheckboxes = document.querySelectorAll(".account-checkbox");

function setAdminAiFeedback(message, isError = false) {
    if (!adminAiFeedback) return;
    adminAiFeedback.textContent = message;
    adminAiFeedback.classList.toggle("is-error", isError);
}

function hashSeed(value) {
    let hash = 0;
    const source = String(value || "FFSTORE");

    for (let index = 0; index < source.length; index += 1) {
        hash = ((hash * 31) + source.charCodeAt(index)) >>> 0;
    }

    return hash;
}

function selectVariant(seed, items, shift = 0) {
    if (!items.length) return "";
    return items[(seed + shift) % items.length];
}

function pickTemplate(price, titleHint) {
    const titleSeed = (titleHint || "").trim();
    const planLabel = price === "499" ? "Rs. 499" : "Rs. 399";
    const planProfile = price === "499"
        ? {
            titleLead: ["Premium", "Trusted", "Elite", "Secure", "Exclusive", "High Value", "Priority", "Professional"],
            titleCore: ["Shared Access", "Recovery Ready", "Account Recovery", "Login Access", "Game Access", "Premium Access"],
            titleTail: ["Account", "Profile", "Plan", "Bundle", "Listing", "Package", "Edition"],
            openers: ["Trusted", "Professional", "Premium", "Secure", "Verified-style", "Buyer-focused", "Store-ready", "Reliable"],
            middles: ["shared access flow", "recovery-ready setup", "level-based unlock structure", "clean payment journey", "premium purchase flow", "account detail presentation"],
            trustPoints: ["clear buyer guidance", "stronger trust presentation", "polished access details", "professional unlock steps", "cleaner delivery structure", "confident storefront wording"],
            closers: ["built for serious buyers.", "designed for premium listings.", "ready for a professional storefront.", "made to improve buyer confidence.", "prepared for a smoother recovery handoff.", "optimized for clear account details."],
        }
        : {
            titleLead: ["Trusted", "Secure", "Starter", "Professional", "Reliable", "Smart", "Clean", "Buyer Ready"],
            titleCore: ["Shared Access", "Recovery Ready", "Entry Access", "Starter Recovery", "Login Access", "Account Access"],
            titleTail: ["Account", "Plan", "Listing", "Package", "Bundle", "Profile", "Option"],
            openers: ["Reliable", "Professional", "Secure", "Trusted", "Buyer-friendly", "Store-ready", "Clean", "Balanced"],
            middles: ["shared access flow", "entry recovery setup", "fixed unlock payment structure", "simple premium storefront flow", "guided account access process", "clean purchase journey"],
            trustPoints: ["clear account details", "strong buyer trust", "simple unlock guidance", "professional payment steps", "clean access presentation", "consistent recovery flow"],
            closers: ["built for everyday buyers.", "designed for cleaner listings.", "made for simple premium presentation.", "ready for mobile and desktop storefronts.", "optimized for trust and clarity.", "prepared for a smoother purchase flow."],
        };

    const seed = hashSeed(`${price}|${titleSeed || Date.now()}`);
    const titleOptions = [];

    for (let leadIndex = 0; leadIndex < planProfile.titleLead.length; leadIndex += 1) {
        for (let coreIndex = 0; coreIndex < planProfile.titleCore.length; coreIndex += 1) {
            for (let tailIndex = 0; tailIndex < planProfile.titleTail.length; tailIndex += 1) {
                titleOptions.push(`${planProfile.titleLead[leadIndex]} ${planProfile.titleCore[coreIndex]} ${planProfile.titleTail[tailIndex]}`);
            }
        }
    }

    const description = `${selectVariant(seed, planProfile.openers)} ${planLabel} account with a ${selectVariant(seed, planProfile.middles, 3)} and ${selectVariant(seed, planProfile.trustPoints, 7)}. ${selectVariant(seed, planProfile.openers, 11)} listing ${selectVariant(seed, planProfile.closers, 17)}`;

    return {
        title: titleSeed || titleOptions[seed % titleOptions.length],
        description,
    };
}

generateAiCopyBtn?.addEventListener("click", () => {
    const price = listingPriceInput?.value || "";
    const title = listingTitleInput?.value || "";

    if (!price) {
        setAdminAiFeedback("Choose the plan price first.", true);
        return;
    }

    generateAiCopyBtn.disabled = true;
    setAdminAiFeedback("Generating trusted listing title and details from 1000+ combinations...");

    const generated = pickTemplate(price, title);

    if (listingTitleInput) {
        listingTitleInput.value = generated.title;
    }
    if (listingDescriptionInput) {
        listingDescriptionInput.value = generated.description;
    }

    setAdminAiFeedback("Account title and details generated successfully.");
    generateAiCopyBtn.disabled = false;
});

selectAllAccounts?.addEventListener("change", () => {
    accountCheckboxes.forEach((checkbox) => {
        checkbox.checked = selectAllAccounts.checked;
    });
});

accountCheckboxes.forEach((checkbox) => {
    checkbox.addEventListener("change", () => {
        if (!selectAllAccounts) return;
        selectAllAccounts.checked = Array.from(accountCheckboxes).every((item) => item.checked);
    });
});
