"use strict";

/**
 * StorePilot AI — Frontend Application Controller
 * Coordinates UI behavior, page initialization, and prepares integration boundaries for the backend API.
 */
(function () {
    // ==================================================
    // DEPENDENCIES
    // ==================================================
    const Utils = window.StorePilotUtils;
    const Components = window.StorePilotComponents;
    const API = window.StorePilotAPI;

    if (!Utils || !Components || !API) {
        throw new Error("Initialization Error: StorePilot dependencies (Utils, Components, API) must be loaded before app.js.");
    }

    // ==================================================
    // CURRENT PAGE DETECTION
    // ==================================================
    /**
     * Determines the current active application page based on the URL path.
     * @returns {string} The identified page slug or 'unknown'.
     */
    function getCurrentPage() {
        const path = window.location.pathname.toLowerCase();
        
        if (path.endsWith("/") || path.endsWith("index.html")) {
            return "login";
        }
        if (path.includes("dashboard.html")) return "dashboard";
        if (path.includes("analysis.html")) return "analysis";
        if (path.includes("findings.html")) return "findings";
        if (path.includes("approvals.html")) return "approvals";
        if (path.includes("tasks.html")) return "tasks";
        if (path.includes("inventory.html")) return "inventory";
        if (path.includes("sales.html")) return "sales";
        
        return "unknown";
    }

    // ==================================================
    // MOBILE NAVIGATION CONTROLLER
    // ==================================================
    /**
     * Binds click events and manages attributes for the mobile menu drawer interaction.
     */
    function initializeMobileNavigation() {
        const mobileMenuButton = document.getElementById("mobileMenuButton");
        const sidebar = document.getElementById("sidebar");
        const sidebarOverlay = document.getElementById("sidebarOverlay");

        if (!mobileMenuButton || !sidebar || !sidebarOverlay) return;

        const toggleMenu = (open) => {
            mobileMenuButton.setAttribute("aria-expanded", open ? "true" : "false");
            if (open) {
                sidebar.classList.add("open");
                sidebarOverlay.classList.add("visible");
            } else {
                sidebar.classList.remove("open");
                sidebarOverlay.classList.remove("visible");
            }
        };

        mobileMenuButton.addEventListener("click", () => {
            const isExpanded = mobileMenuButton.getAttribute("aria-expanded") === "true";
            toggleMenu(!isExpanded);
        });

        sidebarOverlay.addEventListener("click", () => toggleMenu(false));
    }

    // ==================================================
    // GLOBAL THEME CONTROLLER (DARK / LIGHT MODE) - *BARU*
    // ==================================================
    /**
     * Mengatur tombol ganti tema (Gelap/Terang) di semua halaman dan menyimpannya di memori browser.
     */
    function initializeThemeController() {
        const themeToggleBtn = document.getElementById("theme-toggle");
        const themeIcon = document.getElementById("theme-icon");
        const themeText = document.getElementById("theme-text");

        // Helper untuk memperbarui icon & text tombol
        function updateToggleButton(theme) {
            if (!themeIcon) return;
            if (theme === "dark") {
                themeIcon.textContent = "☀️";
                if (themeText) themeText.textContent = "Terang";
            } else {
                themeIcon.textContent = "🌙";
                if (themeText) themeText.textContent = "Gelap";
            }
        }

        // 1. Ambil tema aktif saat halaman dimuat, lalu sesuaikan icon tombolnya
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        updateToggleButton(currentTheme);

        // 2. Tambah event listener klik jika tombol tema ada di halaman ini
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener("click", () => {
                const activeTheme = document.documentElement.getAttribute("data-theme") || "light";
                const newTheme = activeTheme === "dark" ? "light" : "dark";

                // Terapkan ke HTML tag
                document.documentElement.setAttribute("data-theme", newTheme);
                
                // Simpan ke memori browser (localStorage) agar saat pindah halaman tetap gelap/terang
                localStorage.setItem("theme", newTheme);

                // Update icon tombol
                updateToggleButton(newTheme);
            });
        }
    }

    // ==================================================
    // REUSABLE UI STATE RENDERING FUNCTIONS
    // ==================================================
    /**
     * Renders a safe, unified loading state into the target container.
     * @param {HTMLElement} container - The target DOM container.
     * @param {Object} [options] - Configuration overrides.
     */
    function renderLoadingState(container, options = {}) {
        if (!container) return;
        const title = options.title || "Memuat data";
        const description = options.description || "Mohon tunggu sementara informasi sedang dimuat.";

        const safeTitle = Utils && typeof Utils.escapeHTML === "function" ? Utils.escapeHTML(title) : title;
        const safeDesc = Utils && typeof Utils.escapeHTML === "function" ? Utils.escapeHTML(description) : description;

        container.innerHTML = `
            <div class="empty-state loading-state">
                <div class="loading-spinner" aria-hidden="true"></div>
                <h3 class="empty-state-title">${safeTitle}</h3>
                <p class="empty-state-description">${safeDesc}</p>
            </div>
        `;
    }

    /**
     * Renders an empty state indicating no data was returned from a successful request.
     * @param {HTMLElement} container - The target DOM container.
     * @param {Object} [options] - Configuration overrides passed to Components.
     */
    function renderEmptyState(container, options = {}) {
        if (!container) return;
        if (Components && typeof Components.renderEmptyState === "function") {
            container.innerHTML = Components.renderEmptyState(options);
        } else {
            const title = options.title || "Tidak ada data";
            const description = options.description || "Belum ada informasi yang tersedia saat ini.";
            container.innerHTML = `
                <div class="empty-state">
                    <h3>${title}</h3>
                    <p>${description}</p>
                </div>
            `;
        }
    }

    /**
     * Renders a safe error state preventing raw details exposure to the user.
     * @param {HTMLElement} container - The target DOM container.
     * @param {Object} [options] - Configuration overrides passed to Components.
     */
    function renderErrorState(container, options = {}) {
        if (!container) return;
        
        const safeOptions = {
            title: options.title || "Data tidak dapat dimuat",
            description: options.description || "Terjadi kesalahan saat memuat informasi. Silakan coba kembali."
        };

        if (Components && typeof Components.renderErrorState === "function") {
            container.innerHTML = Components.renderErrorState(safeOptions);
        } else {
            container.innerHTML = `
                <div class="empty-state error-state">
                    <h3>${safeOptions.title}</h3>
                    <p>${safeOptions.description}</p>
                </div>
            `;
        }
    }

    // ==================================================
    // REUSABLE STATE CONTROLLER
    // ==================================================
    /**
     * Coordinates rendering of a specific frontend state into a single container.
     * @param {HTMLElement} container - Target container element.
     * @param {string} state - The structural state name ('loading', 'empty', 'error').
     * @param {Object} [options] - Contextual overrides.
     * @returns {boolean} True if rendered successfully; false otherwise.
     */
    function setContainerState(container, state, options = {}) {
        if (!container) return false;

        switch (state) {
            case "loading":
                renderLoadingState(container, options);
                return true;
            case "empty":
                renderEmptyState(container, options);
                return true;
            case "error":
                renderErrorState(container, options);
                return true;
            default:
                return false;
        }
    }

    /**
     * Internal helper to batch update multiple containers simultaneously.
     * @param {Array<HTMLElement>} containers - Array of target containers.
     * @param {string} state - Selected structural state.
     * @param {Object} [options] - Contextual configuration.
     * @returns {number} The count of elements successfully updated.
     */
    function setMultipleContainerStates(containers, state, options = {}) {
        if (!Array.isArray(containers)) return 0;
        let count = 0;

        containers.forEach(container => {
            if (container && setContainerState(container, state, options)) {
                count++;
            }
        });

        return count;
    }

    // ==================================================
    // API ERROR TO SAFE UI MAPPING
    // ==================================================
    /**
     * Translates backend/network error details into clean user-facing labels.
     * @param {Error} error - Received error object.
     * @returns {Object} Clean title and description properties for UI presentation.
     */
    function getSafeErrorState(error) {
        const defaultState = {
            title: "Data tidak dapat dimuat",
            description: "Terjadi kesalahan saat memuat informasi. Silakan coba kembali."
        };

        if (!error) return defaultState;

        if (API && API.StorePilotAPIError && error instanceof API.StorePilotAPIError) {
            if (error.code === "NETWORK_ERROR") {
                return {
                    title: "Layanan backend tidak terhubung",
                    description: "Tidak dapat terhubung ke layanan backend. Periksa koneksi layanan dan coba kembali."
                };
            }
            if (error.code === "REQUEST_TIMEOUT") {
                return {
                    title: "Permintaan terlalu lama",
                    description: "Layanan backend membutuhkan waktu terlalu lama untuk merespons. Silakan coba kembali."
                };
            }
            if (error.code === "REQUEST_ABORTED") {
                return {
                    title: "Permintaan dibatalkan",
                    description: "Proses pemuatan data telah dibatalkan."
                };
            }
            return {
                title: "Data tidak dapat dimuat",
                description: "Terjadi kesalahan saat memuat informasi dari layanan backend."
            };
        }

        return defaultState;
    }

    // ==================================================
    // PAGE TARGET RESOLUTION INTERNAL HELPER
    // ==================================================
    /**
     * Maps an individual page slug to its respective target container elements.
     * @param {string} page - Active page key.
     * @returns {Array<HTMLElement>} Valid, filtered active DOM targets.
     */
    function getPageStateContainers(page) {
        let selectors = [];

        switch (page) {
            case "dashboard":
                selectors = ["#operationalStatus", "#dashboardMetrics", "#operationalRiskList", "#aiIntelligencePanel", "#proposedActionList"];
                break;
            case "analysis":
                selectors = ["#analysisProgress", "#analysisResult", "#analysisSummary", "#analysisResultActions"];
                break;
            case "findings":
                selectors = ["#findingsSummary", "#findingsList"];
                break;
            case "approvals":
                selectors = ["#approvalSummary", "#approvalList"];
                break;
            case "tasks":
                selectors = ["#taskSummary", "#taskList"];
                break;
            case "inventory":
                selectors = ["#inventorySummary", "#inventoryEmptyState", "#inventoryIntelligence"];
                break;
            case "sales":
                selectors = ["#salesSummary", "#salesEmptyState", "#salesIntelligence"];
                break;
            default:
                return [];
        }

        return selectors
            .map(sel => document.querySelector(sel))
            .filter(el => el !== null);
    }

    // ==================================================
    // GLOBAL PAGE STATE HELPER
    // ==================================================
    /**
     * Programmatically triggers a UI state update for all containers on the current active page.
     * @param {string} state - Desired UI state.
     * @param {Object} [options] - Content customization configuration.
     * @returns {number} Amount of successfully adjusted page component targets.
     */
    function setCurrentPageState(state, options = {}) {
        const currentPage = getCurrentPage();
        const containers = getPageStateContainers(currentPage);
        return setMultipleContainerStates(containers, state, options);
    }

    // ==================================================
    // APPROVAL ACTION CONFIRMATION HELPER
    // ==================================================
    /**
     * Manages browser-native confirmation prompts prior to executing manager task choices.
     * @param {string} action - Identified task directive ("approve", "reject").
     * @returns {boolean} Indicator showing if the active user permitted the directive loop.
     */
    function requestActionConfirmation(action) {
        if (action === "approve") {
            return window.confirm("Setujui tugas ini?\n\nTindakan ini akan diteruskan sebagai keputusan manajer setelah layanan backend terhubung.");
        } 
        
        if (action === "reject") {
            return window.confirm("Tolak tugas ini?\n\nTindakan ini akan diteruskan sebagai keputusan manajer setelah layanan backend terhubung.");
        }
        
        return false;
    }

    /**
     * Routes approval commands and validates explicit task ID parameters ahead of execution.
     * @param {string} action - Evaluated workflow string ('approve' | 'reject').
     * @param {string} taskId - Associated operational task record.
     * @returns {boolean} Resolution flag demonstrating successful structural evaluation and confirmation block passage.
     */
    function handleApprovalAction(action, taskId) {
        if (action !== "approve" && action !== "reject") return false;
        if (Utils.isEmptyValue(taskId)) return false;

        const normalizedTaskId = String(taskId).trim();
        if (normalizedTaskId === "") return false;

        const userConfirmed = requestActionConfirmation(action);
        if (!userConfirmed) return false;

        // Backend approval/rejection request will be connected after the real endpoint contract is available.
        return true;
    }

    // ==================================================
    // CORE PAGE INITIALIZATION ROUTERS
    // ==================================================
    /**
     * Synchronizes each sales comparison bar's visual width with its
     * data-percentage-change attribute. renderSalesRow() already sets this
     * inline when a row is first created; this function exists to keep bars
     * correct if their markup is ever updated by other means later.
     */
    function applySalesComparisonWidths() {
        const fills = Utils.selectAll(".sales-change-fill[data-percentage-change]");
        fills.forEach(fill => {
            const raw = fill.getAttribute("data-percentage-change");
            const num = Utils.toNumber(raw, 0);
            const clampedWidth = Utils.clamp(Math.abs(num), 0, 100);
            fill.style.width = `${clampedWidth === null ? 0 : clampedWidth}%`;
        });
    }

    function initializeDashboardPage() {
        // Router hook for dashboard page logic mapping
    }

    function initializeAnalysisPage() {
        // Router hook for analysis page logic mapping
    }

    function initializeFindingsPage() {
        // Router hook for findings page logic mapping
    }

    /**
     * Enforces explicit approval container event-delegated listener patterns.
     */
    function initializeApprovalsPage() {
        const approvalList = document.getElementById("approvalList");
        if (!approvalList) return;

        // Verify if initialization has already happened to prevent stacked events.
        if (approvalList.dataset.initialized === "true") return;
        approvalList.dataset.initialized = "true";

        approvalList.addEventListener("click", function(event) {
            const actionTarget = event.target.closest("[data-action]");
            if (!actionTarget) return;

            const action = actionTarget.getAttribute("data-action");
            const taskId = actionTarget.getAttribute("data-task-id");

            if (action === "approve" || action === "reject") {
                handleApprovalAction(action, taskId);
            } 
            else if (action === "task-detail") {
                // Future operational data binding hook. No arbitrary detail logic generated.
            }
        });
    }

    function initializeTasksPage() {
        // Router hook for tasks page logic mapping
    }

    function initializeInventoryPage() {
        // Router hook for inventory page logic mapping
    }

    function initializeSalesPage() {
        applySalesComparisonWidths();
    }

    /**
     * Dispatches proper module handlers depending on page scope.
     */
    function initializeCurrentPage() {
        const page = getCurrentPage();
        switch (page) {
            case "dashboard":
                initializeDashboardPage();
                break;
            case "analysis":
                initializeAnalysisPage();
                break;
            case "findings":
                initializeFindingsPage();
                break;
            case "approvals":
                initializeApprovalsPage();
                break;
            case "tasks":
                initializeTasksPage();
                break;
            case "inventory":
                initializeInventoryPage();
                break;
            case "sales":
                initializeSalesPage();
                break;
        }
    }

    // ==================================================
    // APPLICATION INITIALIZATION
    // ==================================================
    /**
     * Universal bootstrap function triggering necessary global application directives.
     */
    function initializeApp() {
        initializeThemeController(); // <--- *BARU: Menjalankan sistem tema di semua halaman*
        initializeMobileNavigation();
        initializeCurrentPage();
    }

    // ==================================================
    // DOM READY GUARD
    // ==================================================
    let hasInitialized = false;

    function handleDOMReady() {
        if (hasInitialized) return;
        hasInitialized = true;
        initializeApp();
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", handleDOMReady);
    } else {
        handleDOMReady();
    }

    // ==================================================
    // GLOBAL EXPORT
    // ==================================================
    window.StorePilotApp = {
        getCurrentPage,
        initializeMobileNavigation,
        initializeThemeController, // <--- *BARU*
        renderLoadingState,
        renderEmptyState,
        renderErrorState,
        setContainerState,
        getSafeErrorState,
        setCurrentPageState,
        requestActionConfirmation,
        applySalesComparisonWidths,
        initializeDashboardPage,
        initializeAnalysisPage,
        initializeFindingsPage,
        initializeApprovalsPage,
        initializeTasksPage,
        initializeInventoryPage,
        initializeSalesPage,
        initializeCurrentPage,
        initializeApp
    };

})();