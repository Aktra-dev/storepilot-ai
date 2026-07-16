"use strict";

/**
 * StorePilot AI — Frontend API Service Layer
 * Generic HTTP client wrapper for future backend integration.
 */
(function () {
    // ==================================================
    // PRIVATE CONFIGURATION
    // ==================================================
    const config = {
        baseUrl: "http://localhost:8000",
        timeout: 15000
    };

    // ==================================================
    // TOKEN MANAGEMENT
    // ==================================================
    function getToken() {
        return localStorage.getItem("access_token");
    }

    function getRefreshToken() {
        return localStorage.getItem("refresh_token");
    }

    function setTokens(accessToken, refreshToken) {
        localStorage.setItem("access_token", accessToken);
        if (refreshToken) localStorage.setItem("refresh_token", refreshToken);
    }

    function clearTokens() {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("user");
    }

    function isLoggedIn() {
        return !!getToken();
    }

    // ==================================================
    // AUTO INJECT JWT + REFRESH TOKEN
    // ==================================================
    let isRefreshing = false;
    let failedQueue = [];

    function processQueue(error) {
        failedQueue.forEach(({ resolve, reject }) => {
            error ? reject(error) : resolve();
        });
        failedQueue = [];
    }

    // ==================================================
    // API ERROR CLASS
    // ==================================================
    class StorePilotAPIError extends Error {
        /**
         * @param {string} message - Error message
         * @param {Object} options - Additional error properties
         */
        constructor(message, options = {}) {
            super(message, options);
            this.name = "StorePilotAPIError";
            this.status = options.status;
            this.code = options.code;
            this.details = options.details;
        }
    }

    // ==================================================
    // CONFIGURE API
    // ==================================================
    /**
     * Updates and returns the current API configuration.
     * @param {Object} options - Configuration overrides
     * @returns {Object} A copy of the updated configuration
     */
    function configure(options = {}) {
        if (options.baseUrl !== undefined) {
            config.baseUrl = String(options.baseUrl).trim().replace(/\/+$/, "");
        }
        
        if (typeof options.timeout === "number" && options.timeout > 0 && Number.isFinite(options.timeout)) {
            config.timeout = options.timeout;
        }
        
        return getConfig();
    }

    // ==================================================
    // GET CONFIGURATION
    // ==================================================
    /**
     * Returns a safe copy of the current configuration.
     * @returns {Object} Configuration object
     */
    function getConfig() {
        return {
            baseUrl: config.baseUrl,
            timeout: config.timeout
        };
    }

    // ==================================================
    // BUILD URL
    // ==================================================
    /**
     * Internal helper to build absolute or relative URLs safely.
     * @param {string} path - The request path
     * @returns {string} The constructed URL
     */
    function buildUrl(path) {
        if (typeof path !== "string" || path.trim() === "") {
            throw new Error("Path must be a non-empty string");
        }
        
        const trimmedPath = path.trim();
        
        // Return as-is if it's already a fully qualified URL
        if (/^https?:\/\//i.test(trimmedPath)) {
            return trimmedPath;
        }
        
        // Return relative same-origin path if no baseUrl is configured
        if (!config.baseUrl) {
            return trimmedPath;
        }
        
        // Combine configured baseUrl and path
        const normalizedPath = trimmedPath.startsWith("/") ? trimmedPath : `/${trimmedPath}`;
        return `${config.baseUrl}${normalizedPath}`;
    }

    /**
     * Internal helper to determine if a body is a plain JavaScript object
     * @param {*} value - The body payload to check
     * @returns {boolean} True if plain object
     */
    function isPlainObject(value) {
        return value !== null && typeof value === "object" && value.constructor === Object;
    }

    // ==================================================
    // REQUEST FUNCTION
    // ==================================================
    /**
     * Core HTTP request wrapper using fetch().
     * @param {string} path - The endpoint path
     * @param {Object} options - Fetch options including method, headers, body, signal, timeout
     * @returns {Promise<any>} The parsed JSON or text response
     */
    async function request(path, options = {}) {
        // 1. Auto-inject JWT unless explicitly disabled
        const headers = new Headers(options.headers || {});
        const noAuth = options.noAuth || false;

        if (!noAuth) {
            const token = getToken();
            if (token) {
                headers.set("Authorization", `Bearer ${token}`);
            }
        }
        
        // Set default Accept header
        if (!headers.has("Accept")) {
            headers.set("Accept", "application/json");
        }

        // 2. Try the request
        const exec = async () => {
            return await _request(path, { ...options, headers });
        };

        try {
            return await exec();
        } catch (error) {
            // 3. If 401 Unauthorized, try to refresh the token
            if (error instanceof StorePilotAPIError && error.status === 401 && !noAuth) {
                if (!isRefreshing) {
                    isRefreshing = true;
                    try {
                        const refreshToken = getRefreshToken();
                        if (!refreshToken) throw new Error("No refresh token");

                        const refreshResponse = await _request("/auth/refresh", {
                            method: "POST",
                            body: { refresh_token: refreshToken },
                            noAuth: true
                        });

                        const newAccess = refreshResponse.access_token || refreshResponse.accessToken;
                        const newRefresh = refreshResponse.refresh_token || refreshResponse.refreshToken;
                        setTokens(newAccess, newRefresh);

                        processQueue(null);

                        // Retry original request with new token
                        headers.set("Authorization", `Bearer ${newAccess}`);
                        return await _request(path, { ...options, headers });
                    } catch (refreshError) {
                        processQueue(refreshError);
                        clearTokens();
                        // Redirect to login
                        window.location.href = "/index.html";
                        throw new StorePilotAPIError("Sesi telah berakhir. Silakan login ulang.", { code: "SESSION_EXPIRED" });
                    } finally {
                        isRefreshing = false;
                    }
                } else {
                    // Another refresh is in progress, queue this request
                    return new Promise((resolve, reject) => {
                        failedQueue.push({ resolve, reject });
                    }).then(() => {
                        headers.set("Authorization", `Bearer ${getToken()}`);
                        return _request(path, { ...options, headers });
                    });
                }
            }
            throw error;
        }
    }

    /**
     * Internal low-level request function (no auth logic).
     */
    async function _request(path, options = {}) {
        const url = buildUrl(path);
        const method = (options.method || "GET").toUpperCase();
        const headers = new Headers(options.headers || {});
        
        // Set default Accept header
        if (!headers.has("Accept")) {
            headers.set("Accept", "application/json");
        }

        let body = options.body;

        // Auto-stringify plain objects and set Content-Type
        if (body !== undefined && isPlainObject(body)) {
            body = JSON.stringify(body);
            if (!headers.has("Content-Type")) {
                headers.set("Content-Type", "application/json");
            }
        }

        const controller = new AbortController();
        const fetchOptions = {
            method,
            headers,
            signal: controller.signal
        };

        if (body !== undefined && method !== "GET" && method !== "HEAD") {
            fetchOptions.body = body;
        }

        const timeoutLimit = (typeof options.timeout === "number" && options.timeout > 0 && Number.isFinite(options.timeout))
            ? options.timeout
            : config.timeout;

        let timeoutId;
        let externalAbortHandler;
        let abortReason = null;

        const setupAbort = () => {
            timeoutId = setTimeout(() => {
                abortReason = "TIMEOUT";
                controller.abort();
            }, timeoutLimit);

            if (options.signal) {
                if (options.signal.aborted) {
                    abortReason = "EXTERNAL_ABORT";
                    controller.abort();
                } else {
                    externalAbortHandler = () => {
                        abortReason = "EXTERNAL_ABORT";
                        controller.abort();
                    };
                    options.signal.addEventListener("abort", externalAbortHandler);
                }
            }
        };

        const cleanupAbort = () => {
            clearTimeout(timeoutId);
            if (options.signal && externalAbortHandler) {
                options.signal.removeEventListener("abort", externalAbortHandler);
            }
        };

        setupAbort();

        try {
            const response = await fetch(url, fetchOptions);
            cleanupAbort();

            // Handle 204 No Content
            if (response.status === 204) {
                return null;
            }

            // Handle Non-Successful HTTP Responses
            if (!response.ok) {
                let errorMessage = "Permintaan ke layanan backend gagal.";
                let errorCode;
                let errorDetails;

                try {
                    const errorBody = await response.text();
                    if (errorBody) {
                        try {
                            const jsonError = JSON.parse(errorBody);
                            if (jsonError && jsonError.detail) {  
                                errorMessage = jsonError.detail;
                            } else if (jsonError && jsonError.message) {
                                errorMessage = jsonError.message;
                            }
                            if (jsonError && jsonError.code) {
                                errorCode = jsonError.code;
                            }
                            if (jsonError && jsonError.details) {
                                errorDetails = jsonError.details;
                            }
                        } catch (parseErr) {
                            // Non-JSON error body, ignore and use default message
                        }
                    }
                } catch (readErr) {
                    // Cannot read error body, ignore
                }

                throw new StorePilotAPIError(errorMessage, {
                    status: response.status,
                    code: errorCode,
                    details: errorDetails
                });
            }

            // Handle Successful Responses
            const contentType = response.headers.get("Content-Type") || "";
            if (contentType.includes("application/json")) {
                return await response.json();
            } else {
                return await response.text();
            }

        } catch (error) {
            cleanupAbort();

            if (error instanceof StorePilotAPIError) {
                throw error;
            }

            if (error.name === "AbortError" || abortReason !== null) {
                if (abortReason === "TIMEOUT") {
                    throw new StorePilotAPIError("Waktu permintaan ke layanan backend habis.", { 
                        code: "REQUEST_TIMEOUT", 
                        cause: error 
                    });
                } else {
                    throw new StorePilotAPIError("Permintaan dibatalkan.", { 
                        code: "REQUEST_ABORTED", 
                        cause: error 
                    });
                }
            }

            throw new StorePilotAPIError("Tidak dapat terhubung ke layanan backend.", { 
                code: "NETWORK_ERROR", 
                cause: error 
            });
        }
    }

    // ==================================================
    // GENERIC HTTP HELPERS
    // ==================================================
    
    function get(path, options = {}) {
        return request(path, { ...options, method: "GET" });
    }

    function post(path, body, options = {}) {
        return request(path, { ...options, method: "POST", body });
    }

    function put(path, body, options = {}) {
        return request(path, { ...options, method: "PUT", body });
    }

    function patch(path, body, options = {}) {
        return request(path, { ...options, method: "PATCH", body });
    }

    function remove(path, options = {}) {
        return request(path, { ...options, method: "DELETE" });
    }

    // ==================================================
    // API ENDPOINTS (correctly mapped to backend routes)
    // ==================================================
    
    // Auth
    function login(email, password) {
        return request("/api/v1/auth/login", {
            method: "POST",
            body: { email, password },
            noAuth: true
        });
    }

    function register(data) {
        return request("/api/v1/auth/register", {
            method: "POST",
            body: data,
            noAuth: true
        });
    }

    function getMe() {
        return request("/api/v1/auth/me");
    }

    function refreshToken(refreshToken) {
        return _request("/api/v1/auth/refresh", {
            method: "POST",
            body: { refresh_token: refreshToken },
            noAuth: true
        });
    }

    function logout() {
        return request("/api/v1/auth/logout", { method: "POST" });
    }

    // Products (v1)
    function getProducts(skip = 0, limit = 50) {
        return request(`/api/v1/products?skip=${skip}&limit=${limit}`);
    }

    function getProduct(id) {
        return request(`/api/v1/products/${id}`);
    }

    function createProduct(data) {
        return request("/api/v1/products", { method: "POST", body: data });
    }

    function updateProduct(id, data) {
        return request(`/api/v1/products/${id}`, { method: "PATCH", body: data });
    }

    function deleteProduct(id) {
        return request(`/api/v1/products/${id}`, { method: "DELETE" });
    }

    function searchProducts(q) {
        return request(`/api/v1/products/search?q=${encodeURIComponent(q)}`);
    }

    // Inventory (v1)
    function getInventory(skip = 0, limit = 50) {
        return request(`/api/v1/inventory?skip=${skip}&limit=${limit}`);
    }

    function getInventoryItem(id) {
        return request(`/api/v1/inventory/${id}`);
    }

    function createInventory(data) {
        return request("/api/v1/inventory", { method: "POST", body: data });
    }

    function updateInventory(id, data) {
        return request(`/api/v1/inventory/${id}`, { method: "PATCH", body: data });
    }

    function adjustStock(id, data) {
        return request(`/api/v1/inventory/${id}/adjust`, { method: "POST", body: data });
    }

    function deleteInventory(id) {
        return request(`/api/v1/inventory/${id}`, { method: "DELETE" });
    }

    function getInventoryAlerts() {
        return request("/api/v1/inventory/alerts");
    }

    function getProductStock(productId) {
        return request(`/api/v1/inventory/stock/${productId}`);
    }

    // Sales (v1)
    function getSales(params = {}) {
        const q = new URLSearchParams(params).toString();
        return request(`/api/v1/sales${q ? '?' + q : ''}`);
    }

    function getSale(id) {
        return request(`/api/v1/sales/${id}`);
    }

    function createSale(data) {
        return request("/api/v1/sales", { method: "POST", body: data });
    }

    function updateSale(id, data) {
        return request(`/api/v1/sales/${id}`, { method: "PATCH", body: data });
    }

    function deleteSale(id) {
        return request(`/api/v1/sales/${id}`, { method: "DELETE" });
    }

    function getSalesSummary() {
        return request("/api/v1/sales/summary");
    }

    function getDailySales(start, end) {
        const q = new URLSearchParams();
        if (start) q.set("start_date", start);
        if (end) q.set("end_date", end);
        return request(`/api/v1/sales/daily?${q.toString()}`);
    }

    // Dashboard (not under v1 - mounted at /api/dashboard)
    function getDashboardSummary() {
        return request("/api/dashboard");
    }

    function getInventoryRisks() {
        return request("/api/dashboard/inventory-risks");
    }

    function getSalesAnomalies() {
        return request("/api/dashboard/sales-anomalies");
    }

    function getRecentFindings(limit = 10) {
        return request(`/api/dashboard/recent-findings?limit=${limit}`);
    }

    // Tasks (not under v1 - mounted at /api/tasks)
    function getTasks(status) {
        const q = status ? `?status=${status}` : '';
        return request(`/api/tasks${q}`);
    }

    function getTask(id) {
        return request(`/api/tasks/${id}`);
    }

    function approveTask(taskId, managerId, note) {
        return request(`/api/tasks/${taskId}/approve`, {
            method: "POST",
            body: { manager_id: managerId, note }
        });
    }

    function rejectTask(taskId, managerId, note) {
        return request(`/api/tasks/${taskId}/reject`, {
            method: "POST",
            body: { manager_id: managerId, note }
        });
    }

    function startTask(taskId) {
        return request(`/api/tasks/${taskId}/start`, { method: "POST" });
    }

    function completeTask(taskId) {
        return request(`/api/tasks/${taskId}/complete`, { method: "POST" });
    }

    // Operations (not under v1 - mounted at /api/operations)
    function runAnalysis() {
        return request("/api/operations/analyze", { method: "POST" });
    }

    function getAnalysisStatus() {
        return request("/api/operations/status");
    }

    // ==================================================
    // GLOBAL EXPORT
    // ==================================================
    window.StorePilotAPI = {
        StorePilotAPIError,
        configure,
        getConfig,
        request,
        _request,
        get,
        post,
        put,
        patch,
        remove,
        // Token helpers
        getToken,
        getRefreshToken,
        setTokens,
        clearTokens,
        isLoggedIn,
        // Auth API
        login,
        register,
        getMe,
        refreshToken,
        logout,
        // Products API
        getProducts,
        getProduct,
        createProduct,
        updateProduct,
        deleteProduct,
        searchProducts,
        // Inventory API
        getInventory,
        getInventoryItem,
        createInventory,
        updateInventory,
        adjustStock,
        deleteInventory,
        getInventoryAlerts,
        getProductStock,
        // Sales API
        getSales,
        getSale,
        createSale,
        updateSale,
        deleteSale,
        getSalesSummary,
        getDailySales,
        // Dashboard API
        getDashboardSummary,
        getInventoryRisks,
        getSalesAnomalies,
        getRecentFindings,
        // Tasks API
        getTasks,
        getTask,
        approveTask,
        rejectTask,
        startTask,
        completeTask,
        // Operations API
        runAnalysis,
        getAnalysisStatus
    };
})();