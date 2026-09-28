/**
 * TCVIA Framework — Frontend Application
 * Connects to Flask backend at /api/*
 * Clean Enterprise Architecture with White-Background Aesthetic
 */
class App {
    constructor() {
        this.init();
    }

    init() {
        this.setupRouter();
        this.setupNavigation();
        this.setupFileUploads();
        this.setupEventListeners();
        this.fetchDashboardStats();
    }

    // ─── Router & Navigation ──────────────────────────────────────────
    setupRouter() {
        const handleRoute = () => {
            const hash = window.location.hash || '#dashboard';
            const pageId = hash.replace('#', '');
            this.navigate(pageId, false);
        };
        window.addEventListener('hashchange', handleRoute);
        handleRoute();
    }

    setupNavigation() {
        document.querySelectorAll('.nav-item').forEach(item => {
            if (item.getAttribute('href')?.startsWith('#')) {
                item.addEventListener('click', () => {
                    const pageId = item.getAttribute('href').replace('#', '');
                    this.navigate(pageId);
                });
            }
        });
    }

    navigate(pageId, setHash = true) {
        if (setHash) window.location.hash = pageId;

        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

        const page = document.getElementById(`page-${pageId}`);
        const nav = document.getElementById(`nav-${pageId}`);

        if (page) page.classList.add('active');
        if (nav) nav.classList.add('active');

        const titleMap = {
            'dashboard': 'Dashboard',
            'data-integrity': 'Data Integrity Scanner',
            'model-integrity': 'Model Integrity Assessor',
            'inference-provenance': 'Inference Provenance Chain',
            'distribution-shift': 'Distribution Shift Analyzer',
            'full-audit': 'Full Integrity Audit',
            'reports': 'Assurance Reports'
        };
        const titleEl = document.getElementById('page-title');
        if (titleEl) {
            titleEl.innerText = titleMap[pageId] || 'Dashboard';
        }

        // Auto-load data for certain pages
        if (pageId === 'reports') this.loadReports();
        if (pageId === 'inference-provenance') this.loadChain();
        if (pageId === 'dashboard') this.fetchDashboardStats();
    }

    // ─── API Client ───────────────────────────────────────────────────
    async apiCall(endpoint, method = 'GET', body = null) {
        this.showLoading();
        try {
            const options = { method };
            if (body) {
                if (body instanceof FormData) {
                    options.body = body;
                } else {
                    options.headers = { 'Content-Type': 'application/json' };
                    options.body = JSON.stringify(body);
                }
            }
            const res = await fetch(`/api/${endpoint}`, options);
            const data = await res.json();
            if (!res.ok) {
                throw new Error(data.error || `API error ${res.status}`);
            }
            return data;
        } catch (error) {
            this.showToast(error.message, 'error');
            throw error;
        } finally {
            this.hideLoading();
        }
    }

    // ─── UI Helpers ───────────────────────────────────────────────────
    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.remove('hidden');
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) overlay.classList.add('hidden');
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:1.2rem;margin-left:12px;line-height:1">&times;</button>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.25s ease forwards';
            setTimeout(() => toast.remove(), 250);
        }, 4000);
    }

    animateValue(el, start, end, duration) {
        if (typeof el === 'string') el = document.getElementById(el);
        if (!el) return;
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            el.innerHTML = Math.floor(progress * (end - start) + start);
            if (progress < 1) window.requestAnimationFrame(step);
        };
        window.requestAnimationFrame(step);
    }

    severityClass(sev) {
        const s = (sev || 'info').toUpperCase();
        if (s === 'CRITICAL' || s === 'HIGH' || s === 'FAIL') return 'error';
        if (s === 'MEDIUM' || s === 'WARN') return 'warning';
        if (s === 'LOW') return 'info';
        if (s === 'PASS') return 'success';
        return 'info';
    }

    // ─── File Upload Setup ────────────────────────────────────────────
    setupFileUploads() {
        const zones = [
            'data-upload-zone', 'model-upload-zone',
            'ref-upload-zone', 'inc-upload-zone',
            'audit-data-zone', 'audit-model-zone'
        ];

        zones.forEach(zoneId => {
            const zone = document.getElementById(zoneId);
            if (!zone) return;
            const input = zone.querySelector('input[type="file"]');
            if (!input) return;

            zone.addEventListener('click', () => input.click());
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                zone.classList.add('drag-over');
            });
            zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                zone.classList.remove('drag-over');
                if (e.dataTransfer.files.length) {
                    input.files = e.dataTransfer.files;
                    const p = zone.querySelector('p');
                    if (p) p.innerText = `${e.dataTransfer.files.length} file(s) selected`;
                }
            });
            input.addEventListener('change', () => {
                if (input.files.length) {
                    const p = zone.querySelector('p');
                    if (p) p.innerText = `${input.files.length} file(s) selected`;
                }
            });
        });
    }

    // ─── Event Listeners ──────────────────────────────────────────────
    setupEventListeners() {
        document.getElementById('btn-run-demo')?.addEventListener('click', () => this.runDemo());
        document.getElementById('btn-scan-data')?.addEventListener('click', () => this.handleDataScan());
        document.getElementById('btn-scan-model')?.addEventListener('click', () => this.handleModelScan());
        document.getElementById('btn-check-drift')?.addEventListener('click', () => this.handleDriftCheck());
        document.getElementById('btn-run-audit')?.addEventListener('click', () => this.handleFullAudit());
        document.getElementById('btn-create-inference')?.addEventListener('click', () => this.handleCreateInference());
        document.getElementById('btn-verify-chain')?.addEventListener('click', () => this.handleVerifyChain());
    }

    // ─── Run Demo ─────────────────────────────────────────────────────
    async runDemo() {
        try {
            const res = await this.apiCall('run-demo', 'POST');
            this.showToast(res.message || 'Demo dataset and model generated!', 'success');
            this.fetchDashboardStats();
        } catch (e) { /* toast already shown */ }
    }

    // ─── Dashboard ────────────────────────────────────────────────────
    async fetchDashboardStats() {
        try {
            const stats = await this.apiCall('stats');
            this.animateValue('stat-scans', 0, stats.total_scans || 0, 600);
            this.animateValue('stat-threats', 0, stats.threats_found || 0, 600);
            this.animateValue('stat-models', 0, stats.models_verified || 0, 600);
            this.animateValue('stat-reports', 0, stats.reports_generated || 0, 600);

            const timeline = document.getElementById('activity-timeline');
            if (timeline && stats.recent_activity && stats.recent_activity.length > 0) {
                timeline.innerHTML = stats.recent_activity.map(a => `
                    <li>
                        <div class="activity-time">${new Date(a.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}</div>
                        <div class="activity-text">
                            <span class="badge bg-${this.severityClass(a.severity)}" style="font-size:0.72rem;padding:2px 6px;margin-right:8px">${a.severity}</span>
                            <span>${a.details}</span>
                        </div>
                    </li>
                `).join('');
            } else if (timeline) {
                timeline.innerHTML = '<li class="text-muted" style="padding:16px 0;text-align:center;">No recent activity. Click "Run Demo Pipeline" to execute a baseline audit.</li>';
            }
        } catch (e) { /* silent on dashboard load */ }
    }

    // ─── Data Integrity Scan ──────────────────────────────────────────
    async handleDataScan() {
        try {
            const formatEl = document.querySelector('input[name="data-format"]:checked');
            const format = formatEl ? formatEl.value : 'coco';
            const fileInput = document.getElementById('data-file');

            const formData = new FormData();
            formData.append('format', format);
            if (fileInput && fileInput.files.length > 0) {
                for (const f of fileInput.files) formData.append('files', f);
            }

            const result = await this.apiCall('scan-data', 'POST', formData);
            const resDiv = document.getElementById('data-results');
            resDiv.classList.remove('hidden');

            // Summary bar
            const summary = document.getElementById('data-summary');
            const sc = result.severity_counts || {};
            summary.innerHTML = `
                <span class="badge bg-info" style="margin-right:6px">Total Issues: ${result.total_findings}</span>
                ${sc.CRITICAL ? `<span class="badge bg-error" style="margin-right:6px">Critical: ${sc.CRITICAL}</span>` : ''}
                ${sc.HIGH ? `<span class="badge bg-error" style="margin-right:6px">High: ${sc.HIGH}</span>` : ''}
                ${sc.MEDIUM ? `<span class="badge bg-warning" style="margin-right:6px">Medium: ${sc.MEDIUM}</span>` : ''}
                ${sc.LOW ? `<span class="badge bg-info" style="margin-right:6px">Low: ${sc.LOW}</span>` : ''}
                <span class="text-muted" style="margin-left:auto;font-size:0.82rem;font-weight:500;">Audited ${result.total_samples} samples</span>
            `;

            // Findings table
            const tbody = document.querySelector('#data-table tbody');
            tbody.innerHTML = result.findings.map(f => `
                <tr>
                    <td><code>${f.sample_id || 'N/A'}</code></td>
                    <td style="font-weight:500;">${f.finding_type || f.check || 'N/A'}</td>
                    <td><span class="badge bg-${this.severityClass(f.severity)}">${(f.severity || 'INFO').toUpperCase()}</span></td>
                    <td style="font-variant-numeric:tabular-nums">${f.confidence ? (f.confidence * 100).toFixed(0) + '%' : 'N/A'}</td>
                    <td class="text-muted" style="font-size:0.82rem">${f.evidence || f.value || 'N/A'}</td>
                    <td><span class="badge bg-${f.recommendation?.includes('Quarantine') ? 'error' : 'warning'}">${f.recommendation || 'Review'}</span></td>
                </tr>
            `).join('');

            this.showToast(`Data scan complete: ${result.total_findings} findings`, 'success');
        } catch (e) { /* toast shown */ }
    }

    // ─── Model Integrity Scan ─────────────────────────────────────────
    async handleModelScan() {
        try {
            const accessToggle = document.getElementById('model-access-mode');
            const accessMode = accessToggle && accessToggle.checked ? 'black-box' : 'white-box';
            const fileInput = document.getElementById('model-file');

            const formData = new FormData();
            formData.append('access_mode', accessMode);
            if (fileInput && fileInput.files.length > 0) {
                formData.append('model', fileInput.files[0]);
            }

            const result = await this.apiCall('scan-model', 'POST', formData);
            document.getElementById('model-results').classList.remove('hidden');

            // Model digest
            document.getElementById('model-digest').innerText = result.digest || 'N/A';

            // Assessment badge
            const badge = document.getElementById('model-assessment');
            badge.innerText = result.overall_status === 'PASS' ? 'INTEGRITY VERIFIED — PASS' : 'ANOMALY DETECTED — FLAGGED';
            badge.className = `badge badge-lg bg-${result.overall_status === 'PASS' ? 'success' : 'error'}`;

            // Behavioral info
            document.getElementById('model-behavior').innerHTML = `
                <div style="display:flex;flex-direction:column;gap:10px;font-size:0.88rem;color:var(--text-secondary);">
                    <div><span style="color:var(--text-muted);font-weight:600;display:block;font-size:0.75rem;text-transform:uppercase;margin-bottom:2px">Cryptographic Fingerprint</span><code style="word-break:break-all;">${result.fingerprint || 'N/A'}</code></div>
                    <div><span style="color:var(--text-muted);font-weight:600;display:block;font-size:0.75rem;text-transform:uppercase;margin-bottom:2px">Model Path / Source</span><span>${result.model_path || 'N/A'}</span></div>
                    <div><span style="color:var(--text-muted);font-weight:600;display:block;font-size:0.75rem;text-transform:uppercase;margin-bottom:4px">Inspection Access Mode</span><span class="badge bg-info">${result.access_mode.toUpperCase()}</span></div>
                </div>
            `;

            // Weight statistics
            const weightsDiv = document.getElementById('model-weights');
            const sparsity = parseFloat(result.sparsity) || 0;
            weightsDiv.innerHTML = `
                <div class="weight-bar">
                    <span>Weight Sparsity Ratio</span>
                    <div class="progress-bar"><div class="progress-fill" style="width:${Math.min(sparsity * 100, 100)}%;"></div></div>
                    <span style="font-weight:700;font-variant-numeric:tabular-nums">${(sparsity * 100).toFixed(2)}%</span>
                </div>
                <div style="font-size:0.8rem;color:var(--text-muted);margin-top:4px;">Expected baseline sparsity for dense vision models is < 15.00%. Zero-weight anomalies suggest backdoor masks.</div>
                ${result.findings.filter(f => f.check === 'WEIGHT_STATISTICS' && f.status === 'FAIL').map(f => `
                    <div class="badge bg-error mt-2">${f.component}: ${f.issue}</div>
                `).join('')}
            `;

            this.showToast(`Model assessment: ${result.overall_status}`, result.overall_status === 'PASS' ? 'success' : 'warning');
        } catch (e) { /* toast shown */ }
    }

    // ─── Inference Provenance ─────────────────────────────────────────
    async handleCreateInference() {
        try {
            const result = await this.apiCall('inference/create', 'POST');
            this.showToast(`Inference recorded | Ledger height: ${result.chain_length}`, 'success');
            this.loadChain();
        } catch (e) { /* toast shown */ }
    }

    async handleVerifyChain() {
        try {
            const result = await this.apiCall('inference/verify', 'POST');
            const bar = document.getElementById('chain-status');
            bar.className = `chain-status-bar ${result.chain_valid ? 'valid' : 'invalid'}`;
            bar.innerHTML = result.chain_valid
                ? `✓ Cryptographic Ledger Intact — All ${result.chain_length} blocks verified against HMAC-SHA256 signatures.`
                : '✗ Chain Broken — Tampering detected in inference sequence!';
            this.showToast(result.message, result.chain_valid ? 'success' : 'error');
        } catch (e) { /* toast shown */ }
    }

    async loadChain() {
        try {
            const result = await this.apiCall('inference/chain');
            const vis = document.getElementById('chain-vis');

            if (!result.chain || result.chain.length === 0) {
                vis.innerHTML = '<p class="text-muted" style="text-align:center;padding:2.5rem;width:100%;">No inference records in ledger. Click "Record Test Inference" to generate verifiable transactions.</p>';
                return;
            }

            vis.innerHTML = result.chain.map((node, i) => `
                <div class="chain-node">
                    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;padding-bottom:8px;border-bottom:1px solid var(--border-color);">
                        <span class="badge bg-info" style="font-size:0.75rem">Block #${i + 1}</span>
                        <span class="text-muted" style="font-size:0.72rem">${node.timestamp}</span>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:8px;font-size:0.78rem;">
                        <div><span style="color:var(--text-muted);font-weight:600;display:block;margin-bottom:2px">Input Hash</span><code>${node.input_hash}</code></div>
                        <div><span style="color:var(--text-muted);font-weight:600;display:block;margin-bottom:2px">Output Hash</span><code>${node.output_hash}</code></div>
                        <div><span style="color:var(--text-muted);font-weight:600;display:block;margin-bottom:2px">HMAC Signature</span><code>${node.hmac}</code></div>
                        <div><span style="color:var(--text-muted);font-weight:600;display:block;margin-bottom:2px">Block Hash</span><code>${node.entry_hash}</code></div>
                    </div>
                </div>
                ${i < result.chain.length - 1 ? '<div class="chain-link"></div>' : ''}
            `).join('');

            // Update status bar
            const bar = document.getElementById('chain-status');
            if (result.chain_valid) {
                bar.className = 'chain-status-bar valid';
                bar.innerHTML = `✓ Cryptographic Ledger Intact — ${result.chain_length} blocks verified with HMAC-SHA256 signatures.`;
            }
        } catch (e) { /* silent */ }
    }

    // ─── Distribution Shift ───────────────────────────────────────────
    async handleDriftCheck() {
        try {
            const refInput = document.getElementById('ref-files');
            const incInput = document.getElementById('inc-files');

            const formData = new FormData();
            if (refInput && refInput.files.length > 0) {
                for (const f of refInput.files) formData.append('reference', f);
            }
            if (incInput && incInput.files.length > 0) {
                for (const f of incInput.files) formData.append('incoming', f);
            }

            const result = await this.apiCall('check-drift', 'POST', formData);
            document.getElementById('drift-results').classList.remove('hidden');

            // Risk score gauge
            const scorePercent = Math.round(result.risk_score * 100);
            document.getElementById('drift-score').innerText = `${scorePercent}%`;

            const gaugeFill = document.getElementById('drift-gauge-fill');
            const offset = 188.5 - (188.5 * scorePercent / 100);
            gaugeFill.style.strokeDashoffset = offset;
            gaugeFill.style.stroke = scorePercent > 70 ? 'var(--error)' : scorePercent > 30 ? 'var(--warning)' : 'var(--success)';

            // Shift type badge
            const typeBadge = document.getElementById('drift-type');
            typeBadge.innerText = (result.shift_type || 'Nominal').toUpperCase();
            typeBadge.className = `badge badge-lg bg-${scorePercent > 70 ? 'error' : scorePercent > 30 ? 'warning' : 'success'}`;

            // Characteristics
            document.getElementById('drift-chars').innerHTML = `
                <div style="display:flex;flex-direction:column;gap:10px;">
                    <div><strong>Distribution Z-Score:</strong> <code>${result.z_score.toFixed(2)}</code></div>
                    <div><strong>Baseline Samples:</strong> <span style="font-weight:600">${result.reference_count}</span></div>
                    <div><strong>Operational Samples:</strong> <span style="font-weight:600">${result.incoming_count}</span></div>
                    <div><strong>Anomaly Trigger:</strong> ${result.suspicious ? '<span class="badge bg-error">SUSPICIOUS SHIFT</span>' : '<span class="badge bg-success">NOMINAL</span>'}</div>
                </div>
            `;

            // Recommendation
            document.getElementById('drift-rec').innerText = result.recommendation;

            this.showToast(`Drift analysis: Risk ${scorePercent}%`, scorePercent > 70 ? 'error' : 'success');
        } catch (e) { /* toast shown */ }
    }

    // ─── Full Audit ───────────────────────────────────────────────────
    async handleFullAudit() {
        const progressCard = document.getElementById('audit-progress-card');
        progressCard.classList.remove('hidden');

        const steps = ['data', 'model', 'inference', 'drift', 'report'];
        const stepLabels = {
            data: 'Data Integrity',
            model: 'Model Integrity',
            inference: 'Inference Provenance',
            drift: 'Distribution Shift',
            report: 'Generating Report'
        };

        // Reset all steps
        steps.forEach(s => {
            const el = document.querySelector(`.step[data-step="${s}"]`);
            if (el) {
                el.classList.remove('active', 'complete');
                el.querySelector('.step-icon').innerHTML = steps.indexOf(s) + 1;
            }
        });

        // Animate step 1 as active
        const firstStep = document.querySelector('.step[data-step="data"]');
        if (firstStep) firstStep.classList.add('active');

        try {
            const result = await this.apiCall('full-audit', 'POST');

            // Animate through each step
            for (let i = 0; i < steps.length; i++) {
                const step = steps[i];
                const el = document.querySelector(`.step[data-step="${step}"]`);
                if (!el) continue;

                el.classList.remove('active');
                const stepResult = result.steps[step === 'data' ? 'data_integrity' :
                    step === 'model' ? 'model_integrity' :
                    step === 'inference' ? 'inference_provenance' :
                    step === 'drift' ? 'distribution_shift' : 'report'];

                if (stepResult && stepResult.status === 'complete') {
                    el.classList.add('complete');
                    el.querySelector('.step-icon').innerHTML = '✓';
                } else if (stepResult && stepResult.status === 'skipped') {
                    el.classList.add('complete');
                    el.querySelector('.step-icon').innerHTML = '–';
                }

                // Brief visual delay
                await new Promise(r => setTimeout(r, 250));

                if (i + 1 < steps.length) {
                    const next = document.querySelector(`.step[data-step="${steps[i + 1]}"]`);
                    if (next) next.classList.add('active');
                }
            }

            // Summary
            const summaryDiv = document.getElementById('audit-summary');
            const di = result.steps.data_integrity;
            const mi = result.steps.model_integrity;
            const ds = result.steps.distribution_shift;

            summaryDiv.innerHTML = `
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin-top:20px">
                    <div class="card" style="padding:16px;text-align:center;margin-bottom:0">
                        <div class="text-muted" style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Data Findings</div>
                        <div style="font-size:1.75rem;font-weight:700;color:var(--error);margin-top:4px">${di?.findings || 0}</div>
                    </div>
                    <div class="card" style="padding:16px;text-align:center;margin-bottom:0">
                        <div class="text-muted" style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Model Status</div>
                        <div style="font-size:1.75rem;font-weight:700;color:var(--${mi?.overall === 'PASS' ? 'success' : 'error'});margin-top:4px">${mi?.overall || 'N/A'}</div>
                    </div>
                    <div class="card" style="padding:16px;text-align:center;margin-bottom:0">
                        <div class="text-muted" style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Drift Risk</div>
                        <div style="font-size:1.75rem;font-weight:700;color:var(--${(ds?.risk_score || 0) > 0.5 ? 'error' : 'success'});margin-top:4px">${ds ? Math.round(ds.risk_score * 100) + '%' : 'N/A'}</div>
                    </div>
                    <div class="card" style="padding:16px;text-align:center;margin-bottom:0">
                        <div class="text-muted" style="font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em">Compliance Artifact</div>
                        <div style="margin-top:10px">
                            <a href="#reports" class="badge bg-success" style="font-size:0.85rem;padding:6px 12px;text-decoration:none">${result.report_id || 'Generated'} ↗</a>
                        </div>
                    </div>
                </div>
            `;

            this.showToast('Full audit complete — report compiled!', 'success');
        } catch (e) {
            document.getElementById('audit-summary').innerHTML = `
                <div class="badge bg-error badge-lg" style="margin-top:1rem">Audit Failed</div>
                <p class="text-muted mt-2">Please click "Run Demo Pipeline" first to initialize baseline assets.</p>
            `;
        }
    }

    // ─── Reports ──────────────────────────────────────────────────────
    async loadReports() {
        try {
            const result = await this.apiCall('reports');
            const tbody = document.querySelector('#reports-table tbody');

            if (!result.reports || result.reports.length === 0) {
                tbody.innerHTML = '<tr><td colspan="4" class="text-muted" style="text-align:center;padding:2.5rem">No governance reports found. Run a Full Integrity Audit to generate certified reports.</td></tr>';
                return;
            }

            tbody.innerHTML = result.reports.map(r => `
                <tr>
                    <td><code>${r.id}</code></td>
                    <td style="font-size:0.85rem;color:var(--text-secondary);">${new Date(r.created_at).toLocaleString()}</td>
                    <td>
                        <span class="badge bg-${this.severityClass(r.severity?.HIGH > 0 || r.severity?.CRITICAL > 0 ? 'HIGH' : 'INFO')}">
                            ${r.finding_count} findings
                        </span>
                    </td>
                    <td>
                        <a href="/api/download-report/${r.id}/json" class="btn btn-outline" style="padding:4px 10px;font-size:0.78rem;margin-right:6px">JSON</a>
                        <a href="/api/download-report/${r.id}/html" target="_blank" class="btn btn-outline" style="padding:4px 10px;font-size:0.78rem">View HTML</a>
                    </td>
                </tr>
            `).join('');
        } catch (e) { /* silent */ }
    }
}

// Initialize application on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new App();
});
