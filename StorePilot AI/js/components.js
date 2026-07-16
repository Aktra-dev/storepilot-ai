"use strict";

/**
 * StorePilot AI — Frontend Component Renderer Module
 * Converts backend-provided data items into safe, sanitized HTML component presentations.
 */
(function () {
    // Verify and establish dependency with the utility module
    const Utils = window.StorePilotUtils;
    if (!Utils) {
        throw new Error("StorePilotUtils dependency tidak ditemukan. Pastikan utils.js dimuat sebelum components.js.");
    }

    /**
     * Internal helper to safely compile dynamic operational metadata arrays.
     * @param {Array} items - Array of metadata records containing label and value attributes.
     * @returns {string} Pure sanitized HTML element string block.
     */
    function renderContextItems(items) {
        if (!Array.isArray(items) || items.length === 0) return "";
        return items
            .map(item => {
                const lbl = item.label ? Utils.escapeHTML(item.label) : "";
                const val = item.value !== undefined && item.value !== null ? Utils.escapeHTML(item.value) : "";
                return `
                <div class="task-meta-item">
                    <span class="task-meta-label">${lbl}</span>
                    <span class="task-meta-value">${val}</span>
                </div>`;
            })
            .join("");
    }

    /**
     * Renders a consistent operational severity element badge presentation.
     * @param {string} severity - Raw severity code parameter value.
     * @returns {string} Safe HTML badge expression string.
     */
    function renderSeverityBadge(severity) {
        const normalized = Utils.normalizeSeverity(severity);
        const label = Utils.getSeverityLabel(severity);
        return `<span class="severity-badge severity-${normalized}">${label}</span>`;
    }

    /**
     * Renders a consistent operational status element badge presentation.
     * @param {string} status - Raw status code parameter value.
     * @returns {string} Safe HTML badge expression string.
     */
    function renderStatusBadge(status) {
        const normalized = Utils.normalizeStatus(status);
        const allowedClasses = [
            "pending", "pending-approval", "approved", "in-progress", 
            "completed", "rejected", "active", "ready", "running", "failed"
        ];
        const safeStatusClass = allowedClasses.includes(normalized) ? normalized : "unknown";
        const label = Utils.getStatusLabel(status);
        
        return `<span class="status-badge status-${safeStatusClass}">${label}</span>`;
    }

    /**
     * Renders a consistent presentation-bound task priority level identifier badge.
     * @param {string} priority - Priority ranking code.
     * @returns {string} Safe HTML badge representation string.
     */
    function renderPriorityBadge(priority) {
        if (!priority) return `<span class="task-priority priority-unknown">TIDAK DIKETAHUI</span>`;
        
        const rawPriority = String(priority).trim().toLowerCase();
        let label = "TIDAK DIKETAHUI";
        let safePriority = "unknown";

        if (rawPriority === "urgent") {
            label = "MENDESAK";
            safePriority = "urgent";
        } else if (rawPriority === "high") {
            label = "TINGGI";
            safePriority = "high";
        } else if (rawPriority === "medium") {
            label = "SEDANG";
            safePriority = "medium";
        } else if (rawPriority === "low") {
            label = "RENDAH";
            safePriority = "low";
        }

        return `<span class="task-priority priority-${safePriority}">${label}</span>`;
    }

    /**
     * Renders a sanitized high-level visual dashboard monitoring overview metric card item.
     * @param {Object} metric - Configured presentation attributes mapping layout.
     * @returns {string} Structured sanitized card element block.
     */
    function renderMetricCard(metric) {
        if (!metric) return "";
        
        const allowedVariants = ["critical", "high", "primary", "success", "neutral"];
        const rawVariant = metric.variant ? String(metric.variant).toLowerCase() : "neutral";
        const variant = allowedVariants.includes(rawVariant) ? rawVariant : "neutral";

        const label = metric.label ? Utils.escapeHTML(metric.label) : "";
        const value = (metric.value !== null && metric.value !== undefined) ? Utils.escapeHTML(metric.value) : "-";
        const context = metric.context ? Utils.escapeHTML(metric.context) : "";

        return `
        <div class="metric-card metric-${variant}">
            <div class="metric-card-header">
                <span class="metric-card-label">${label}</span>
            </div>
            <div class="metric-card-value">${value}</div>
            ${context ? `<div class="metric-card-context">${context}</div>` : ""}
        </div>`;
    }

    /**
     * Generates a clean template response element block when zero records exist.
     * @param {Object} [options={}] - Text overrides configurations block.
     * @returns {string} HTML component string layout block.
     */
    function renderEmptyState(options = {}) {
        const title = options.title ? Utils.escapeHTML(options.title) : "Belum ada data";
        const description = options.description ? Utils.escapeHTML(options.description) : "Belum ada informasi yang dapat ditampilkan.";
        
        return `
        <div class="empty-state">
            <h3>${title}</h3>
            <p>${description}</p>
        </div>`;
    }

    /**
     * Generates a standardized component rendering to indicate connection or request failure.
     * @param {Object} [options={}] - Custom text boundary description options mapping.
     * @returns {string} Sanitized interface string block.
     */
    function renderErrorState(options = {}) {
        const title = options.title ? Utils.escapeHTML(options.title) : "Data tidak dapat dimuat";
        const description = options.description ? Utils.escapeHTML(options.description) : "Terjadi kesalahan saat memuat informasi. Silakan coba kembali.";
        
        return `
        <div class="empty-state error-state">
            <h3>${title}</h3>
            <p>${description}</p>
        </div>`;
    }

    /**
     * Renders an individual smart monitoring operational anomaly finding card card layout.
     * @param {Object} finding - System operational condition finding model dataset item.
     * @returns {string} Valid dynamic HTML representation wrapper.
     */
    function renderFindingCard(finding) {
        if (!finding) return "";

        const severity = Utils.normalizeSeverity(finding.severity);
        const type = finding.type ? Utils.escapeHTML(finding.type) : "";
        const title = finding.title ? Utils.escapeHTML(finding.title) : "";
        const description = finding.description ? Utils.escapeHTML(finding.description) : "";
        const productName = finding.product_name ? Utils.escapeHTML(finding.product_name) : "";
        const proposedAction = finding.proposed_action ? Utils.escapeHTML(finding.proposed_action) : "";
        
        const hasId = finding.id !== undefined && finding.id !== null;
        const idAttribute = hasId ? `data-finding-id="${Utils.escapeHTML(finding.id)}"` : "";

        const hasConfidence = finding.ai_confidence !== undefined && finding.ai_confidence !== null;
        const confidenceValue = hasConfidence ? Utils.formatPercentage(finding.ai_confidence, false) : "";

        return `
        <div class="finding-card finding-${severity}" ${idAttribute}>
            <div class="finding-header">
                <span class="finding-type">${type}</span>
                ${renderSeverityBadge(finding.severity)}
            </div>
            <div class="finding-content">
                <h3 class="finding-title">${title}</h3>
                <p class="finding-description">${description}</p>
                ${productName ? `<p class="finding-product"><strong>Produk:</strong> ${productName}</p>` : ""}
            </div>
            ${proposedAction ? `
            <div class="finding-action">
                <span class="finding-action-label">REKOMENDASI AI</span>
                <span class="finding-action-content">${proposedAction}</span>
            </div>` : ""}
            <div class="finding-footer">
                ${hasConfidence ? `
                <div class="finding-confidence">
                    <span>Tingkat Keyakinan AI: <strong>${confidenceValue}</strong></span>
                </div>` : ""}
                <button type="button" class="button button-secondary" data-action="finding-detail" ${idAttribute}>Lihat Detail</button>
            </div>
        </div>`;
    }

    /**
     * Compiles an individual tactical action review submission container block.
     * @param {Object} task - Action review task proposition descriptor item record.
     * @returns {string} Safe dynamic sanitized component component string.
     */
    function renderApprovalCard(task) {
        if (!task) return "";

        const title = task.title ? Utils.escapeHTML(task.title) : "";
        const description = task.description ? Utils.escapeHTML(task.description) : "";
        const sourceFinding = task.source_finding ? Utils.escapeHTML(task.source_finding) : "";
        const assignedRole = task.assigned_role ? Utils.escapeHTML(task.assigned_role) : "";
        
        const hasId = task.id !== undefined && task.id !== null;
        const idAttribute = hasId ? `data-task-id="${Utils.escapeHTML(task.id)}"` : "";

        const hasConfidence = task.ai_confidence !== undefined && task.ai_confidence !== null;
        const confidenceValue = hasConfidence ? Utils.formatPercentage(task.ai_confidence, false) : "";

        return `
        <div class="task-card approval-card" ${idAttribute}>
            <div class="task-card-header">
                <span class="task-source-label">TUGAS YANG DIUSULKAN AI</span>
                <div class="task-badges">
                    ${renderPriorityBadge(task.priority)}
                    ${renderStatusBadge(task.status)}
                </div>
            </div>
            <div class="task-card-body">
                <h3 class="task-title">${title}</h3>
                <p class="task-description">${description}</p>
                
                <div class="task-meta">
                    ${assignedRole ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Penanggung Jawab</span>
                        <span class="task-meta-value">${assignedRole}</span>
                    </div>` : ""}
                    ${sourceFinding ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Sumber Temuan</span>
                        <span class="task-meta-value">${sourceFinding}</span>
                    </div>` : ""}
                    ${task.severity ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Tingkat Keparahan</span>
                        <span class="task-meta-value">${Utils.getSeverityLabel(task.severity)}</span>
                    </div>` : ""}
                    ${hasConfidence ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Tingkat Keyakinan AI</span>
                        <span class="task-meta-value">${confidenceValue}</span>
                    </div>` : ""}
                    ${Array.isArray(task.operational_context) ? renderContextItems(task.operational_context) : ""}
                </div>
            </div>
            ${hasId ? `
            <div class="task-actions">
                <button type="button" class="button button-primary" data-action="approve" ${idAttribute}>Setujui</button>
                <button type="button" class="button button-secondary" data-action="reject" ${idAttribute}>Tolak</button>
                <button type="button" class="button button-ghost" data-action="task-detail" ${idAttribute}>Lihat Detail</button>
            </div>` : ""}
        </div>`;
    }

    /**
     * Formats an operational milestone step tracking index mapping visualization row block.
     * @param {Array} timeline - Ordered chronological operational context steps list collection.
     * @returns {string} Sanitized timeline timeline row segment element tree framework.
     */
    function renderTaskTimeline(timeline) {
        if (!Array.isArray(timeline) || timeline.length === 0) return "";

        const allowedStates = ["complete", "active", "pending", "rejected"];

        const stepsHtml = timeline
            .map(item => {
                if (!item) return "";
                const rawState = item.state ? String(item.state).toLowerCase() : "unknown";
                const safeState = allowedStates.includes(rawState) ? rawState : "unknown";
                const label = item.label ? Utils.escapeHTML(item.label) : "";
                const value = item.value ? Utils.escapeHTML(item.value) : "";

                return `
                <div class="timeline-item timeline-state-${safeState}">
                    <div class="timeline-label">${label}</div>
                    <div class="timeline-value">${value}</div>
                </div>`;
            })
            .join("");

        return `<div class="task-timeline">${stepsHtml}</div>`;
    }

    /**
     * Formats an actionable assignment execution overview state tracking element layout card.
     * @param {Object} task - Core dynamic task details payload entity record.
     * @returns {string} Safe tracking item context template interface markup frame.
     */
    function renderTaskMonitoringCard(task) {
        if (!task) return "";

        const statusSlug = Utils.normalizeStatus(task.status);
        const title = task.title ? Utils.escapeHTML(task.title) : "";
        const description = task.description ? Utils.escapeHTML(task.description) : "";
        const assignedRole = task.assigned_role ? Utils.escapeHTML(task.assigned_role) : "";
        const sourceFinding = task.source_finding ? Utils.escapeHTML(task.source_finding) : "";
        
        const hasId = task.id !== undefined && task.id !== null;
        const idAttribute = hasId ? `data-task-id="${Utils.escapeHTML(task.id)}"` : "";

        // Formulate manager text segments based on explicit field inputs
        const managerName = task.manager_name ? Utils.escapeHTML(task.manager_name) : "";
        const managerActionLabel = task.manager_action_label ? Utils.escapeHTML(task.manager_action_label) : "";
        const managerActionTime = task.manager_action_time ? Utils.escapeHTML(task.manager_action_time) : "";
        
        let managerSummaryText = "";
        if (managerName || managerActionLabel || managerActionTime) {
            const fragments = [];
            if (managerName) fragments.push(managerName);
            if (managerActionLabel) fragments.push(`(${managerActionLabel})`);
            if (managerActionTime) fragments.push(managerActionTime);
            managerSummaryText = fragments.join(" ");
        }

        return `
        <div class="task-card task-monitoring-card task-${statusSlug}" ${idAttribute}>
            <div class="task-card-header">
                <div class="task-badges">
                    ${renderPriorityBadge(task.priority)}
                    ${renderStatusBadge(task.status)}
                </div>
            </div>
            <div class="task-card-body">
                <h3 class="task-title">${title}</h3>
                <p class="task-description">${description}</p>
                
                <div class="task-meta">
                    ${assignedRole ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Penanggung Jawab</span>
                        <span class="task-meta-value">${assignedRole}</span>
                    </div>` : ""}
                    ${sourceFinding ? `
                    <div class="task-meta-item">
                        <span class="task-meta-label">Sumber Temuan</span>
                        <span class="task-meta-value">${sourceFinding}</span>
                    </div>` : ""}
                    ${managerSummaryText ? `
                    <div class="task-meta-item task-manager-info">
                        <span class="task-meta-label">Manajer</span>
                        <span class="task-meta-value">${managerSummaryText}</span>
                    </div>` : ""}
                </div>

                ${Array.isArray(task.timeline) && task.timeline.length > 0 ? renderTaskTimeline(task.timeline) : ""}

                ${task.completion_note ? `
                <div class="task-note task-completion-note">
                    <strong>Catatan Selesai:</strong> ${Utils.escapeHTML(task.completion_note)}
                </div>` : ""}

                ${task.rejection_note ? `
                <div class="task-note task-rejection-note">
                    <strong>Alasan Penolakan:</strong> ${Utils.escapeHTML(task.rejection_note)}
                </div>` : ""}
            </div>
            ${hasId ? (() => {
                let actionText = "";
                let actionSlug = "";
                let actionButtonClass = "button-primary";

                if (statusSlug === "approved") {
                    actionText = "MULAI TUGAS";
                    actionSlug = "start";
                } else if (statusSlug === "in-progress") {
                    actionText = "TANDAI SELESAI";
                    actionSlug = "complete";
                } else if (statusSlug === "completed" || statusSlug === "rejected") {
                    actionText = "LIHAT DETAIL";
                    actionSlug = "task-detail";
                    actionButtonClass = "button-secondary";
                }

                if (actionText) {
                    return `
                    <div class="task-actions task-execution-action">
                        <button type="button" class="button ${actionButtonClass}" data-action="${actionSlug}" ${idAttribute}>${actionText}</button>
                    </div>`;
                }
                return "";
            })() : ""}
        </div>`;
    }

    /**
     * Formats an individual structured inventory storage inspection metrics log line element.
     * @param {Object} item - Current operational batch data storage balance data entity.
     * @returns {string} Pure compiled tabular table row script component item string.
     */
    function renderInventoryRow(item) {
        if (!item) return "<tr><td colspan='7'>-</td></tr>";

        const productName = item.product_name ? Utils.escapeHTML(item.product_name) : "-";
        const sku = item.sku ? Utils.escapeHTML(item.sku) : "-";
        const expiryDisplay = item.expiry_display ? Utils.escapeHTML(item.expiry_display) : "-";

        const currentStockText = (item.current_stock !== null && item.current_stock !== undefined) 
            ? `${Utils.formatNumber(item.current_stock)} unit` 
            : "-";
            
        const averageSalesText = (item.average_sales !== null && item.average_sales !== undefined) 
            ? `${Utils.formatDecimal(item.average_sales)} unit/hari` 
            : "-";
            
        const estimatedStockDaysText = (item.estimated_stock_days !== null && item.estimated_stock_days !== undefined) 
            ? `${Utils.formatDecimal(item.estimated_stock_days)} hari` 
            : "-";

        const hasId = item.id !== undefined && item.id !== null;
        const idAttribute = hasId ? `data-item-id="${Utils.escapeHTML(item.id)}"` : "";

        return `
        <tr ${idAttribute}>
            <td>${productName}</td>
            <td>${sku}</td>
            <td>${currentStockText}</td>
            <td>${averageSalesText}</td>
            <td>${estimatedStockDaysText}</td>
            <td>${expiryDisplay}</td>
            <td>${renderSeverityBadge(item.severity)}</td>
        </tr>`;
    }

    /**
     * Formats a product sales trend metric comparison line row object wrapper.
     * @param {Object} item - Product performance analytics item tracking object record dataset.
     * @returns {string} Sanitized table row structural node item entry script.
     */
    function renderSalesRow(item) {
        if (!item) return "<tr><td colspan='6'>-</td></tr>";

        const productName = item.product_name ? Utils.escapeHTML(item.product_name) : "-";
        const recentSalesText = (item.recent_sales !== null && item.recent_sales !== undefined) ? Utils.formatNumber(item.recent_sales) : "-";
        const historicalAverageText = (item.historical_average !== null && item.historical_average !== undefined) ? Utils.formatNumber(item.historical_average) : "-";
        
        let changeClass = "";
        let percentageText = "-";
        
        if (item.percentage_change !== null && item.percentage_change !== undefined) {
            percentageText = Utils.formatPercentage(item.percentage_change, true);
            if (item.percentage_change > 0) {
                changeClass = "sales-change-positive";
            } else if (item.percentage_change < 0) {
                changeClass = "sales-change-negative";
            }
        }

        const hasId = item.id !== undefined && item.id !== null;
        const idAttribute = hasId ? `data-item-id="${Utils.escapeHTML(item.id)}"` : "";

        let fillDataAttribute = "";
        let fillStyleAttribute = "";
        if (item.percentage_change !== null && item.percentage_change !== undefined) {
            fillDataAttribute = `data-percentage-change="${Utils.escapeHTML(item.percentage_change)}"`;
            const clampedWidth = Math.max(0, Math.min(100, Math.abs(Number(item.percentage_change)) || 0));
            fillStyleAttribute = `style="width: ${clampedWidth}%"`;
        }

        const statusPresentationContent = item.anomaly_label 
            ? Utils.escapeHTML(item.anomaly_label) 
            : renderSeverityBadge(item.severity);

        return `
        <tr ${idAttribute}>
            <td>${productName}</td>
            <td>${recentSalesText}</td>
            <td>${historicalAverageText}</td>
            <td class="${changeClass}">${percentageText}</td>
            <td>
                <div class="sales-comparison">
                    <div class="sales-comparison-values">
                        <span>Aktual: ${recentSalesText}</span>
                        <span>Histori: ${historicalAverageText}</span>
                    </div>
                    <div class="sales-change-bar">
                        <div class="sales-change-fill" ${fillDataAttribute} ${fillStyleAttribute}></div>
                    </div>
                </div>
            </td>
            <td>${statusPresentationContent}</td>
        </tr>`;
    }

    // Export interface targets perfectly to the dedicated global browser contract space
    window.StorePilotComponents = {
        renderSeverityBadge,
        renderStatusBadge,
        renderPriorityBadge,
        renderMetricCard,
        renderEmptyState,
        renderErrorState,
        renderFindingCard,
        renderApprovalCard,
        renderTaskTimeline,
        renderTaskMonitoringCard,
        renderInventoryRow,
        renderSalesRow
    };
})();