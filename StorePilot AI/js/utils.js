"use strict";

/**
 * StorePilot AI — Frontend Utility & Theme Engine Module
 * A presentation support utility module for preparing, formatting backend data,
 * and managing system-wide UI themes seamlessly.
 */
(function () {
    /**
     * Finds the first matching DOM element based on a CSS selector.
     * @param {string} selector - The CSS selector string.
     * @param {Document|Element} [parent=document] - The parent node to search within.
     * @returns {Element|null} The matched element or null if not found or invalid.
     */
    function select(selector, parent = document) {
        try {
            return parent.querySelector(selector) || null;
        } catch (e) {
            return null;
        }
    }

    /**
     * Finds all matching DOM elements based on a CSS selector and returns them as a clean array.
     * @param {string} selector - The CSS selector string.
     * @param {Document|Element} [parent=document] - The parent node to search within.
     * @returns {Element[]} An array of matched elements, or an empty array if invalid.
     */
    function selectAll(selector, parent = document) {
        try {
            return Array.from(parent.querySelectorAll(selector));
        } catch (e) {
            return [];
        }
    }

    /**
     * Safely sets the textContent of a DOM element to prevent cross-site scripting (XSS).
     * @param {Element|null} element - The target DOM element.
     * @param {*} value - The value to display as text.
     */
    function setText(element, value) {
        if (!element) return;
        if (value === null || value === undefined) {
            element.textContent = "";
        } else {
            element.textContent = String(value);
        }
    }

    /**
     * Safely converts any input value into a finite numeric value.
     * @param {*} value - The input to convert.
     * @param {*} [fallback=null] - The fallback value if conversion fails.
     * @returns {number|*} A finite number or the specified fallback.
     */
    function toNumber(value, fallback = null) {
        if (value === null || value === undefined || value === "") return fallback;
        const num = Number(value);
        return Number.isFinite(num) ? num : fallback;
    }

    /**
     * Formats a numeric value using the Indonesian locale (id-ID) formatting standard.
     * @param {*} value - The number to format.
     * @returns {string} Formatted number string or "-" if unavailable or invalid.
     */
    function formatNumber(value) {
        const num = toNumber(value);
        if (num === null) return "-";
        return new Intl.NumberFormat("id-ID").format(num);
    }

    /**
     * Formats a decimal number with Indonesian comma notation up to specified fraction digits.
     * @param {*} value - The number to format.
     * @param {number} [maximumFractionDigits=1] - Maximum allowed fractional digits.
     * @returns {string} Formatted decimal string or "-" if unavailable or invalid.
     */
    function formatDecimal(value, maximumFractionDigits = 1) {
        const num = toNumber(value);
        if (num === null) return "-";
        return new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: maximumFractionDigits
        }).format(num);
    }

    /**
     * Formats a pre-calculated percentage value using Indonesian locale decimal comma settings.
     * @param {*} value - The pre-calculated percentage value.
     * @param {boolean} [showPositiveSign=true] - Whether to prepend a "+" sign to positive values.
     * @returns {string} Formatted percentage string or "-" if unavailable or invalid.
     */
    function formatPercentage(value, showPositiveSign = true) {
        const num = toNumber(value);
        if (num === null) return "-";

        const formattedNum = new Intl.NumberFormat("id-ID", {
            maximumFractionDigits: 10
        }).format(Math.abs(num));

        if (num > 0) {
            return (showPositiveSign ? "+" : "") + formattedNum + "%";
        } else if (num < 0) {
            return "-" + formattedNum + "%";
        } else {
            return "0%";
        }
    }

    /**
     * Formats a date-time value using the Indonesian locale standard in a 24-hour format.
     * @param {*} value - A valid date string, timestamp, or Date object.
     * @returns {string} Formatted date-time string or "-" if invalid or unavailable.
     */
    function formatDateTime(value) {
        if (value === null || value === undefined || value === "") return "-";
        const date = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(date.getTime())) return "-";

        try {
            return new Intl.DateTimeFormat("id-ID", {
                day: "numeric",
                month: "numeric",
                year: "numeric",
                hour: "numeric",
                minute: "numeric",
                hour12: false
            }).format(date);
        } catch (e) {
            return "-";
        }
    }

    /**
     * Formats a time-only value using the Indonesian locale standard in a 24-hour format.
     * @param {*} value - A valid date string, timestamp, or Date object.
     * @returns {string} Formatted time string or "-" if invalid or unavailable.
     */
    function formatTime(value) {
        if (value === null || value === undefined || value === "") return "-";
        const date = value instanceof Date ? value : new Date(value);
        if (Number.isNaN(date.getTime())) return "-";

        try {
            return new Intl.DateTimeFormat("id-ID", {
                hour: "numeric",
                minute: "numeric",
                hour12: false
            }).format(date);
        } catch (e) {
            return "-";
        }
    }

    /**
     * Normalizes a status string into a consistent lowercase, hyphen-delimited slug format.
     * @param {*} value - The status string to normalize.
     * @returns {string} Normalized string slug or "unknown".
     */
    function normalizeStatus(value) {
        if (value === null || value === undefined || value === "") return "unknown";
        let str = String(value).trim().toLowerCase();
        if (str === "") return "unknown";
        return str.replace(/[\s_]+/g, "-").replace(/-+/g, "-");
    }

    /**
     * Validates and normalizes an input severity level string into supported system bounds.
     * @param {*} value - The severity value to check.
     * @returns {string} One of 'critical', 'high', 'medium', 'low', 'normal', or 'unknown'.
     */
    function normalizeSeverity(value) {
        if (value === null || value === undefined || value === "") return "unknown";
        const str = String(value).trim().toLowerCase();
        const supported = ["critical", "high", "medium", "low", "normal"];
        return supported.includes(str) ? str : "unknown";
    }

    /**
     * Maps an input severity code to a standardized, visible Indonesian text label.
     * @param {*} value - The severity value.
     * @returns {string} Standardized uppercase Indonesian string label.
     */
    function getSeverityLabel(value) {
        const sev = normalizeSeverity(value);
        switch (sev) {
            case "critical": return "KRITIS";
            case "high": return "TINGGI";
            case "medium": return "SEDANG";
            case "low": return "RENDAH";
            case "normal": return "NORMAL";
            default: return "TIDAK DIKETAHUI";
        }
    }

    /**
     * Maps a normalized status slug to a localized Indonesian description label.
     * @param {*} value - The status string to check.
     * @returns {string} Standardized uppercase Indonesian text label.
     */
    function getStatusLabel(value) {
        const status = normalizeStatus(value);
        switch (status) {
            case "pending": return "MENUNGGU";
            case "pending-approval": return "MENUNGGU PERSETUJUAN";
            case "approved": return "DISETUJUI";
            case "in-progress": return "SEDANG DIKERJAKAN";
            case "completed": return "SELESAI";
            case "rejected": return "DITOLAK";
            case "active": return "AKTIF";
            case "ready": return "SIAP";
            case "running": return "SEDANG BERJALAN";
            case "failed": return "GAGAL";
            default: return "TIDAK DIKETAHUI";
        }
    }

    /**
     * Escapes critical HTML special characters to shield dynamic UI updates from injection.
     * @param {*} value - Unescaped raw string content.
     * @returns {string} Safe HTML-escaped string expression.
     */
    function escapeHTML(value) {
        if (value === null || value === undefined) return "";
        return String(value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    /**
     * Safely bounds a numeric value between a set minimum and maximum constraint range.
     * @param {*} value - The target numeric parameter.
     * @param {*} min - The bottom boundary restriction limit.
     * @param {*} max - The upper boundary restriction limit.
     * @returns {number|null} Constrained number value, or null if logic parameters fail.
     */
    function clamp(value, min, max) {
        const n = toNumber(value);
        const mn = toNumber(min);
        const mx = toNumber(max);

        if (n === null || mn === null || mx === null) return null;
        if (mn > mx) return null;

        return Math.min(Math.max(n, mn), mx);
    }

    /**
     * Delays execution callback routines until specified milliseconds have elapsed.
     * @param {Function} callback - Trigger target function.
     * @param {number} [delay=250] - Threshold duration timeframe in milliseconds.
     * @returns {Function} Wrapped debouncer utility tracking call updates.
     */
    function debounce(callback, delay = 250) {
        if (typeof callback !== "function") {
            throw new TypeError("Callback harus berupa fungsi");
        }

        let timeoutId;

        return function (...args) {
            const context = this;
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                callback.apply(context, args);
            }, delay);
        };
    }

    /**
     * Safely wraps JSON string conversion parsing to insulate runtime errors.
     * @param {string} value - Raw text feed string input source.
     * @param {*} [fallback=null] - Desired conversion return asset in case of failures.
     * @returns {*|null} Resulting Object map collection array array layout or configured default fallback.
     */
    function safeJSONParse(value, fallback = null) {
        try {
            if (value === null || value === undefined) return fallback;
            return JSON.parse(value);
        } catch (e) {
            return fallback;
        }
    }

    /**
     * Generates a structural isolated unique ID prefix string sequence to track runtime UI element bindings.
     * @param {string} [prefix="sp"] - Targeted string marker block label.
     * @returns {string} Random alpha-numeric identifier hash sequence.
     */
    function generateClientId(prefix = "sp") {
        const pfx = prefix ? String(prefix) : "sp";
        if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
            return `${pfx}-${crypto.randomUUID()}`;
        }
        const rand = Math.random().toString(36).substring(2, 11);
        return `${pfx}-${Date.now()}-${rand}`;
    }

    /**
     * Verifies if a variable string field parameter value is blank, undefined or null.
     * @param {*} value - Target asset item block to evaluate.
     * @returns {boolean} True if completely blank or whitespace string layout, false otherwise.
     */
    function isEmptyValue(value) {
        if (value === null || value === undefined) return true;
        if (typeof value === "string" && value.trim() === "") return true;
        return false;
    }

    // Catatan: Manajemen tema (dark/light) sepenuhnya ditangani oleh
    // initializeThemeController() di app.js. Sebelumnya terdapat ThemeManager
    // terpisah di file ini yang otomatis berjalan saat skrip dimuat dan menimpa
    // innerHTML tombol #theme-toggle (menghapus <span id="theme-icon">),
    // sehingga bentrok dengan app.js dan memaksa tiap halaman menambahkan
    // skrip "clone & replace" duplikat sebagai solusi sementara. Kode tersebut
    // telah dihapus agar hanya ada satu sumber kebenaran untuk logika tema.

    // Expose all utility components exactly as requested into the public browser scope
    window.StorePilotUtils = {
        select,
        selectAll,
        setText,
        toNumber,
        formatNumber,
        formatDecimal,
        formatPercentage,
        formatDateTime,
        formatTime,
        normalizeStatus,
        normalizeSeverity,
        getSeverityLabel,
        getStatusLabel,
        escapeHTML,
        clamp,
        debounce,
        safeJSONParse,
        generateClientId,
        isEmptyValue
    };
})();