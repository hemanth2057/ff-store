const searchBox = document.getElementById("searchBox");
const productCards = document.querySelectorAll(".product-card");
const productGrid = document.getElementById("productGrid");
const mobileMenuBtn = document.getElementById("mobileMenuBtn");
const closeMobileMenu = document.getElementById("closeMobileMenu");
const mobileSideMenu = document.getElementById("mobileSideMenu");
const sideMenuOverlay = document.getElementById("sideMenuOverlay");
const sellAccountModal = document.getElementById("sellAccountModal");
const openSellAccountModal = document.getElementById("openSellAccountModal");
const closeSellAccountModal = document.getElementById("closeSellAccountModal");
const buyedAccountsBtn = document.getElementById("buyedAccountsBtn");
const buyedAccountsBadge = document.getElementById("buyedAccountsBadge");

if (productGrid) {
    const shuffledCards = Array.from(productGrid.querySelectorAll(".product-card"));

    for (let index = shuffledCards.length - 1; index > 0; index -= 1) {
        const randomIndex = Math.floor(Math.random() * (index + 1));
        const currentCard = shuffledCards[index];
        shuffledCards[index] = shuffledCards[randomIndex];
        shuffledCards[randomIndex] = currentCard;
    }

    shuffledCards.forEach((card) => {
        productGrid.appendChild(card);
    });
}

searchBox?.addEventListener("input", (event) => {
    const query = event.target.value.trim().toLowerCase();

    productCards.forEach((card) => {
        const haystack = card.dataset.search || "";
        const matched = haystack.includes(query);
        card.classList.toggle("hidden", !matched);
    });
});

function setMenuState(open) {
    if (!mobileSideMenu || !sideMenuOverlay || !mobileMenuBtn) return;

    mobileSideMenu.classList.toggle("hidden", !open);
    sideMenuOverlay.classList.toggle("hidden", !open);
    mobileSideMenu.setAttribute("aria-hidden", open ? "false" : "true");
    mobileMenuBtn.setAttribute("aria-expanded", open ? "true" : "false");
    document.body.style.overflow = open ? "hidden" : "";
}

mobileMenuBtn?.addEventListener("click", () => setMenuState(true));
closeMobileMenu?.addEventListener("click", () => setMenuState(false));
sideMenuOverlay?.addEventListener("click", () => setMenuState(false));

function setSellModalState(open) {
    if (!sellAccountModal) return;

    sellAccountModal.classList.toggle("hidden", !open);
    sellAccountModal.setAttribute("aria-hidden", open ? "false" : "true");
    document.body.style.overflow = open ? "hidden" : "";
}

openSellAccountModal?.addEventListener("click", () => setSellModalState(true));
closeSellAccountModal?.addEventListener("click", () => setSellModalState(false));
sellAccountModal?.addEventListener("click", (event) => {
    if (event.target === sellAccountModal) {
        setSellModalState(false);
    }
});

if (buyedAccountsBtn && buyedAccountsBadge) {
    const historyCount = buyedAccountsBtn.dataset.historyCount || "0";
    const seenKey = "ffstore.buyedAccountsBadgeSeen";
    const seenCount = window.sessionStorage.getItem(seenKey);

    if (seenCount === historyCount) {
        buyedAccountsBadge.classList.add("hidden");
    }

    buyedAccountsBtn.addEventListener("click", () => {
        buyedAccountsBadge.classList.add("hidden");
        window.sessionStorage.setItem(seenKey, historyCount);
    });
}
