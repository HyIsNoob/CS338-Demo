/**
 * AI Evaluation Hub - App Logic v2.0
 * Models: GPT2 Small/Medium Finetune + SpikeGPT 4 variants
 */

// CONFIGURATION
const API_BASE_URL = "https://unmoldered-patellate-angela.ngrok-free.dev";

const EVAL_RESULTS = {
    gpt2_small:     { label:'GPT-2 Small (124M)',       color:'#6ee7b7', validJson:99.98,  intentAcc:96.52, argsExact:68.30, f1:96.48, imgDir:'GPT2_Small'    },
    gpt2_medium:    { label:'GPT-2 Medium (355M)',      color:'#fcd34d', validJson:100.00, intentAcc:96.78, argsExact:67.76, f1:96.78, imgDir:'GPT2_Medium'   },
    spike_ep78_hq:  { label:'SpikeGPT Ep78 +HeadQK',   color:'#fbbf24', validJson:95.98,  intentAcc:84.64, argsExact:1.78,  f1:86.55, imgDir:'78_Scratch'    },
    spike_ep78_nohq:{ label:'SpikeGPT Ep78 NoHeadQK',  color:'#f9a8d4', validJson:100.00, intentAcc:86.62, argsExact:0.00,  f1:86.59, imgDir:'78_NoHeadQK'   },
    spike_ep220_hq: { label:'SpikeGPT Ep220 Scratch',  color:'#a7f3d0', validJson:91.52,  intentAcc:81.24, argsExact:4.68,  f1:84.63, imgDir:'220_Scratch'   },
    spike_ft220_hq: { label:'SpikeGPT FT Ep220 +HQ',   color:'#c4b5fd', validJson:99.80,  intentAcc:94.10, argsExact:13.94, f1:94.15, imgDir:'220_Finetune'  },
};

// ==========================================
// BACKEND STATUS CHECK (global — gọi từ onclick)
// ==========================================
async function checkBackendStatus() {
    const dot  = document.getElementById('backendStatusDot');
    const text = document.getElementById('backendStatusText');
    if (!dot || !text) return;

    dot.style.background = '#F59E0B';
    dot.style.boxShadow  = '0 0 0 3px rgba(245,158,11,0.3)';
    text.textContent = 'Đang kiểm tra...';

    try {
        const res = await fetch(API_BASE_URL + '/health', {
            method: 'GET',
            headers: { 'ngrok-skip-browser-warning': 'true' },
            signal: AbortSignal.timeout(8000)
        });
        if (res.ok) {
            dot.style.background = '#10B981';
            dot.style.boxShadow  = '0 0 0 3px rgba(16,185,129,0.3)';
            text.textContent = 'Backend: Online ✓';
        } else {
            throw new Error(`HTTP ${res.status}`);
        }
    } catch (err) {
        dot.style.background = '#EF4444';
        dot.style.boxShadow  = '0 0 0 3px rgba(239,68,68,0.3)';
        text.textContent = err.name === 'TimeoutError' ? 'Timeout — Chưa chạy' : 'Backend: Offline ✗';
        console.warn('Backend check:', err.message);
    }
}
window.addEventListener('load', () => setTimeout(checkBackendStatus, 1500));

document.addEventListener('DOMContentLoaded', () => {


    // --- STATE ---
    let currentMode = "1";
    let currentLayout = "a";
    let latestGpt2Data = {};
    let latestSpikeData = {};

    // --- DOM ELEMENTS (SIDEBAR) ---
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const navItems = document.querySelectorAll('.nav-item');
    const layoutA = document.getElementById('layout-a');
    const layoutB = document.getElementById('layout-b');
    const layoutC = document.getElementById('layout-c');
    const layoutD = document.getElementById('layout-d');

    // Sidebar Toggle
    sidebarToggleBtn.addEventListener('click', () => sidebar.classList.toggle('collapsed'));

    // --- DOM ELEMENTS (LAYOUT A - GPT2) ---
    const dashInput = document.getElementById('dashboardInput');
    const dashExecuteBtn = document.getElementById('dashboardExecuteBtn');
    const dashLoading = document.getElementById('dashboardLoading');

    // --- DOM ELEMENTS (LAYOUT B - SpikeGPT) ---
    const spikeInput = document.getElementById('spikeInput');
    const spikeExecuteBtn = document.getElementById('spikeExecuteBtn');
    const spikeLoading = document.getElementById('spikeLoading');

    // --- DOM ELEMENTS (LAYOUT C - AGENCY) ---
    const agencyChatInput = document.getElementById('agencyChatInput');
    const agencyChatSendBtn = document.getElementById('agencyChatSendBtn');
    const agencyChatHistory = document.getElementById('agencyChatHistory');
    const agencyModelSelect = document.getElementById('agencyModelSelect');
    const resetAgencyChatBtn = document.getElementById('resetAgencyChatBtn');

    // --- DOM ELEMENTS (MODAL) ---
    const modal = document.getElementById('detailModal');
    const closeModalBtn = document.getElementById('closeModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalRaw = document.getElementById('modalRaw');
    const modalTool = document.getElementById('modalTool');

    // ==========================================
    // 1. SIDEBAR ROUTING
    // ==========================================
    navItems.forEach(btn => {
        btn.addEventListener('click', (e) => {
            navItems.forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');

            const previousMode = currentMode;
            currentMode = e.currentTarget.dataset.mode;
            const targetLayout = e.currentTarget.dataset.layout;

            if (targetLayout !== currentLayout) {
                currentLayout = targetLayout;
                [layoutA, layoutB, layoutC, layoutD].forEach(l => {
                    l.classList.add('hidden'); l.classList.remove('active');
                });
                if (targetLayout === 'a') { layoutA.classList.remove('hidden'); layoutA.classList.add('active'); }
                else if (targetLayout === 'b') { layoutB.classList.remove('hidden'); layoutB.classList.add('active'); }
                else if (targetLayout === 'c') { layoutC.classList.remove('hidden'); layoutC.classList.add('active'); agencyChatInput.focus(); loadAgencyHistory(); }
                else if (targetLayout === 'd') { layoutD.classList.remove('hidden'); layoutD.classList.add('active'); initEvalResults(); }
            }

            if (currentMode !== previousMode) {
                dashInput.value = '';
                spikeInput.value = '';
                latestGpt2Data = {};
                latestSpikeData = {};
                // Reset all cards to idle state (no renderDashboard needed)
                [...GPT2_MODELS, ...SPIKE_MODELS].forEach(id => {
                    const col = document.getElementById(`col-${id}`);
                    if (!col) return;
                    col.classList.remove('dimmed');
                    col.querySelector('.time-val').textContent = '--s';
                    col.querySelector('.json-out').textContent = '';
                    col.querySelector('.exec-out').textContent = '';
                    col.querySelector('.success-icon')?.classList.add('hidden');
                    col.querySelector('.error-icon')?.classList.add('hidden');
                });
            }
        });
    });

    // ==========================================
    // 2. PROMPT CHIPS
    // ==========================================
    document.querySelectorAll('.chip:not(.spike-chip)').forEach(chip => {
        chip.addEventListener('click', () => { dashInput.value = chip.dataset.prompt; dashInput.focus(); });
    });
    document.querySelectorAll('.spike-chip').forEach(chip => {
        chip.addEventListener('click', () => { spikeInput.value = chip.dataset.prompt; spikeInput.focus(); });
    });

    // ==========================================
    // 3. LAYOUT A: GPT-2 DASHBOARD
    // ==========================================
    dashExecuteBtn.addEventListener('click', executeGpt2Dashboard);
    dashInput.addEventListener('keypress', e => { if (e.key === 'Enter') executeGpt2Dashboard(); });

    async function executeGpt2Dashboard() {
        const query = dashInput.value.trim();
        if (!query) return;
        latestGpt2Data = {};
        GPT2_MODELS.forEach(id => setCardLoading(id, true));
        GPT2_MODELS.forEach(modelId => {
            fetchModelSingle(modelId, query).then(data => {
                latestGpt2Data[modelId] = data;
                renderCard(modelId, data);
            }).catch(err => {
                console.error(modelId, err);
                setCardLoading(modelId, false);
            });
        });
    }

    // ==========================================
    // 4. LAYOUT B: SpikeGPT DASHBOARD
    // ==========================================
    spikeExecuteBtn.addEventListener('click', executeSpikeDashboard);
    spikeInput.addEventListener('keypress', e => { if (e.key === 'Enter') executeSpikeDashboard(); });

    async function executeSpikeDashboard() {
        const query = spikeInput.value.trim();
        if (!query) return;
        latestSpikeData = {};
        SPIKE_MODELS.forEach(id => setCardLoading(id, true));
        SPIKE_MODELS.forEach(modelId => {
            fetchModelSingle(modelId, query).then(data => {
                latestSpikeData[modelId] = data;
                renderCard(modelId, data);
            }).catch(err => {
                console.error(modelId, err);
                setCardLoading(modelId, false);
            });
        });
    }

    async function fetchModelSingle(modelKey, message) {
        const res = await fetch(API_BASE_URL + '/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
            body: JSON.stringify({ message, model_key: modelKey })
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        return json[modelKey];
    }

    // ==========================================
    // 5. SHARED RENDER FUNCTIONS
    // ==========================================
    const GPT2_MODELS   = ['gpt2_small', 'gpt2_medium'];
    const SPIKE_MODELS  = ['spike_ep78_hq', 'spike_ep78_nohq', 'spike_ep220_hq', 'spike_ft220_hq'];

    function setCardLoading(modelId, isLoading) {
        const overlay = document.getElementById(`cloading-${modelId}`);
        const colEl   = document.getElementById(`col-${modelId}`);
        if (overlay) overlay.classList.toggle('hidden', !isLoading);
        if (colEl)   colEl.classList.toggle('dimmed',   isLoading);
        if (isLoading) lucide.createIcons();
    }

    function renderCard(modelId, modelData) {
        setCardLoading(modelId, false);
        const colEl = document.getElementById(`col-${modelId}`);
        if (!colEl || !modelData) return;
        colEl.classList.remove('dimmed');
        colEl.querySelector('.time-val').textContent   = modelData.time || '--s';
        colEl.querySelector('.raw-out').textContent    = modelData.text || '';
        colEl.querySelector('.success-icon')?.classList.add('hidden');
        colEl.querySelector('.error-icon')?.classList.add('hidden');
        if (modelData.is_tool) {
            colEl.querySelector('.json-out').textContent = JSON.stringify({ name: modelData.tool_name, arguments: modelData.tool_args }, null, 2);
            if (modelData.execution_result && !modelData.execution_result.error) {
                colEl.querySelector('.exec-out').textContent = JSON.stringify(modelData.execution_result, null, 2);
                colEl.querySelector('.success-icon')?.classList.remove('hidden');
            } else {
                colEl.querySelector('.exec-out').textContent = JSON.stringify(modelData.execution_result ?? {}, null, 2);
                colEl.querySelector('.error-icon')?.classList.remove('hidden');
            }
            colEl.querySelector('.tool-block').classList.remove('dimmed');
            colEl.querySelector('.exec-block').classList.remove('dimmed');
        } else {
            colEl.querySelector('.json-out').textContent = '// No function called';
            colEl.querySelector('.exec-out').textContent = `// Raw: ${modelData.text || '(empty)'}`;
            colEl.querySelector('.tool-block').classList.add('dimmed');
            colEl.querySelector('.exec-block').classList.add('dimmed');
            colEl.querySelector('.error-icon')?.classList.remove('hidden');
        }
    }


    // ==========================================
    // 6. MODAL (Detail View)
    // ==========================================
    document.querySelectorAll('.detail-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetModel = e.currentTarget.dataset.target;
            const isSpike = SPIKE_MODELS.includes(targetModel);
            const data = isSpike ? latestSpikeData[targetModel] : latestGpt2Data[targetModel];
            if (!data) return;

            modalTitle.textContent = `Chi tiết: ${targetModel.toUpperCase()}`;
            modalRaw.textContent = data.text || '';
            let parsedStr = `// Tool Detection: ${data.is_tool}\n\n`;
            if (data.is_tool) {
                parsedStr += `[TOOL NAME]:\n${data.tool_name}\n\n`;
                parsedStr += `[ARGUMENTS]:\n${JSON.stringify(data.tool_args, null, 2)}\n\n`;
                parsedStr += `[EXECUTION RESULT]:\n${JSON.stringify(data.execution_result, null, 2)}`;
            } else {
                parsedStr += 'No tool parsed from raw output.';
            }
            modalTool.textContent = parsedStr;
            modal.classList.remove('hidden');
        });
    });

    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', e => { if (e.target === modal) modal.classList.add('hidden'); });

    // ==========================================
    // 7. LAYOUT C: CHATBOT AGENCY
    // ==========================================
    agencyModelSelect.addEventListener('change', resetAgencyChat);
    resetAgencyChatBtn.addEventListener('click', resetAgencyChat);

    function resetAgencyChat() {
        const selectedText = agencyModelSelect.options[agencyModelSelect.selectedIndex].text;
        agencyChatHistory.innerHTML = `
            <div class="chat-bubble ai">
                <div class="bubble-avatar"><i data-lucide="bot"></i></div>
                <div class="bubble-content">Đã chuyển sang mô hình <strong>${selectedText}</strong>. Lịch sử đã được xoá.</div>
            </div>
        `;
        lucide.createIcons();
        localStorage.removeItem('agencyChatHistory');
    }

    agencyChatSendBtn.addEventListener('click', executeAgencyChat);
    agencyChatInput.addEventListener('keypress', e => { if (e.key === 'Enter') executeAgencyChat(); });

    async function executeAgencyChat() {
        const message = agencyChatInput.value.trim();
        if (!message) return;

        appendAgencyBubble(message, 'user');
        agencyChatInput.value = '';
        const loadingId = appendAgencyBubble('...', 'ai', true);

        try {
            const selectedModel = agencyModelSelect.value;
            const response = await fetch(API_BASE_URL + '/api/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'ngrok-skip-browser-warning': 'true' },
                body: JSON.stringify({ message: message, model_key: selectedModel })
            });
            if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);

            const fullData = await response.json();
            const modelData = fullData[selectedModel];

            removeAgencyBubble(loadingId);

            if (modelData) {
                let botMessage = modelData.text || '...';
                if (modelData.is_tool && modelData.execution_result?.message) {
                    botMessage = modelData.execution_result.message;
                }
                appendAgencyBubble(botMessage, 'ai');
                if (modelData.is_tool) {
                    renderEcommerceCard(modelData.tool_name, modelData.execution_result);
                }
            } else {
                appendAgencyBubble('⚠️ Lỗi: Phản hồi không tồn tại.', 'ai');
            }
            saveAgencyHistory();

        } catch (error) {
            console.error('Agency API Error:', error);
            removeAgencyBubble(loadingId);
            appendAgencyBubble('⚠️ Lỗi kết nối đến Backend: ' + error.message, 'ai');
        }
    }

    function appendAgencyBubble(text, sender, isLoading = false) {
        const bubbleId = 'a-msg-' + Date.now();
        const wrapper = document.createElement('div');
        wrapper.className = `chat-bubble ${sender}`;
        wrapper.id = bubbleId;
        wrapper.innerHTML = `
            <div class="bubble-avatar"><i data-lucide="${sender === 'user' ? 'user' : 'bot'}"></i></div>
            <div class="bubble-content ${isLoading ? 'animate-pulse' : ''}">${text}</div>
        `;
        agencyChatHistory.appendChild(wrapper);
        lucide.createIcons();
        agencyChatHistory.scrollTop = agencyChatHistory.scrollHeight;
        if (!isLoading) saveAgencyHistory();
        return bubbleId;
    }

    function removeAgencyBubble(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    function renderEcommerceCard(toolName, execResult) {
        if (!execResult) return;
        const wrapper = document.createElement('div');
        wrapper.className = 'ecommerce-card';
        let headerHtml = '', bodyHtml = '';

        if (execResult.error) {
            headerHtml = `<div class="card-header-neo" style="background:var(--c-pink);"><i data-lucide="x-circle"></i><span>Lỗi hệ thống</span></div>`;
            bodyHtml   = `<div class="card-body-neo"><div style="color:#991B1B;font-weight:600;">⚠️ ${execResult.error}</div></div>`;
        } else {
            switch(toolName) {
                case 'create_order':
                case 'get_order':
                    headerHtml = `<div class="card-header-neo" style="background:var(--c-yellow);"><i data-lucide="shopping-cart"></i><span>Thông tin đơn hàng</span></div>`;
                    bodyHtml = `<div class="card-body-neo">
                        <div class="card-row"><strong>Mã đơn:</strong><span>#${execResult.order_id || 'N/A'}</span></div>
                        <div class="card-row"><strong>Trạng thái:</strong><span class="badge-neo-warning">${execResult.status || execResult.current_status || 'N/A'}</span></div>
                        <div class="card-row"><strong>Tổng tiền:</strong><span style="font-weight:700;color:#b91c1c;">${execResult.total_price || 0}</span></div>
                    </div>`;
                    break;
                case 'check_inventory':
                    headerHtml = `<div class="card-header-neo" style="background:var(--c-mint);"><i data-lucide="package"></i><span>Trạng thái sản phẩm</span></div>`;
                    const stockBadge = execResult.stock > 0 ? `<span class="badge-neo-success">Còn hàng (${execResult.stock})</span>` : `<span class="badge-neo-danger">Hết hàng</span>`;
                    bodyHtml = `<div class="card-body-neo">
                        <div class="card-row"><strong>Sản phẩm:</strong><span>${execResult.product_name || 'N/A'}</span></div>
                        <div class="card-row"><strong>Tồn kho:</strong>${stockBadge}</div>
                        <div class="card-row"><strong>Giá:</strong><span style="font-weight:700;">${execResult.price || 0}</span></div>
                    </div>`;
                    break;
                case 'delete_order':
                    headerHtml = `<div class="card-header-neo" style="background:var(--c-pink);"><i data-lucide="trash-2"></i><span>Hủy đơn hàng</span></div>`;
                    bodyHtml = `<div class="card-body-neo">
                        <div class="card-row"><strong>Trạng thái:</strong><span class="badge-neo-danger">Đã hủy thành công</span></div>
                    </div>`;
                    break;
                case 'update_order':
                    headerHtml = `<div class="card-header-neo" style="background:var(--c-mint);"><i data-lucide="edit"></i><span>Cập nhật đơn hàng</span></div>`;
                    bodyHtml = `<div class="card-body-neo">
                        <div class="card-row"><strong>Kết quả:</strong><span>${execResult.message || 'Đã cập nhật'}</span></div>
                    </div>`;
                    break;
                case 'revenue_analysis':
                    headerHtml = `<div class="card-header-neo" style="background:#93c5fd;"><i data-lucide="bar-chart-2"></i><span>Báo cáo doanh thu</span></div>`;
                    bodyHtml = `<div class="card-body-neo">
                        <div class="card-row"><strong>Tổng số đơn:</strong><span>${execResult.total_valid_orders || 0} đơn</span></div>
                        <div class="card-row" style="flex-direction:column;align-items:flex-start;gap:8px;">
                            <strong>Tổng Doanh Thu:</strong>
                            <span style="font-weight:900;font-size:1.5rem;color:#166534;">${execResult.total_revenue || 0}</span>
                        </div>
                    </div>`;
                    break;
                default:
                    headerHtml = `<div class="card-header-neo" style="background:var(--c-gray);"><i data-lucide="settings"></i><span>Hệ thống</span></div>`;
                    bodyHtml = `<div class="card-body-neo"><span>Đã thực thi: <strong>${toolName}</strong></span></div>`;
            }
        }

        wrapper.innerHTML = headerHtml + bodyHtml;
        const outerWrapper = document.createElement('div');
        outerWrapper.style.cssText = 'display:flex;justify-content:flex-start;width:100%;padding-left:50px;';
        outerWrapper.appendChild(wrapper);
        agencyChatHistory.appendChild(outerWrapper);
        lucide.createIcons();
        agencyChatHistory.scrollTop = agencyChatHistory.scrollHeight;
        saveAgencyHistory();
    }

    function saveAgencyHistory() {
        localStorage.setItem('agencyChatHistory', agencyChatHistory.innerHTML);
        localStorage.setItem('agencyChatModel', agencyModelSelect.value);
    }

    // ==========================================
    // 9. MODE 4: EVAL RESULTS DASHBOARD
    // ==========================================
    let evalChartsInit = false;
    function initEvalResults() {
        if (evalChartsInit) return; // only init once
        evalChartsInit = true;

        const keys   = Object.keys(EVAL_RESULTS);
        const labels = keys.map(k => EVAL_RESULTS[k].label);
        const colors = keys.map(k => EVAL_RESULTS[k].color);
        const makeChart = (id, title, dataKey) => {
            const ctx = document.getElementById(id);
            if (!ctx) return;
            new Chart(ctx, {
                type: 'bar',
                data: { labels, datasets: [{ label: title, data: keys.map(k => EVAL_RESULTS[k][dataKey]), backgroundColor: colors, borderColor: '#111', borderWidth: 2 }] },
                options: {
                    responsive: true,
                    plugins: { legend: { display: false }, title: { display: true, text: title, font: { size: 13, weight: 'bold' } } },
                    scales: { y: { beginAtZero: true, max: 100, ticks: { callback: v => v + '%' } } }
                }
            });
        };
        makeChart('chart-intent',   'Intent Accuracy (%)',  'intentAcc');
        makeChart('chart-f1',       'F1 Score (%)',          'f1');
        makeChart('chart-validjson','Valid JSON (%)',         'validJson');
        makeChart('chart-args',     'Args Exact Match (%)',  'argsExact');

        // Summary table
        const tbody = document.getElementById('eval-table-body');
        if (tbody) {
            const maxIntent = Math.max(...keys.map(k => EVAL_RESULTS[k].intentAcc));
            const maxF1     = Math.max(...keys.map(k => EVAL_RESULTS[k].f1));
            const maxArgs   = Math.max(...keys.map(k => EVAL_RESULTS[k].argsExact));
            tbody.innerHTML = keys.map((k, i) => {
                const d = EVAL_RESULTS[k];
                const hi = (val, max) => val === max ? `<strong style="color:#059669">${val}%</strong>` : `${val}%`;
                return `<tr style="border-bottom:1px solid #e5e7eb;${i%2===0?'background:#f9fafb':''}">
                    <td style="padding:10px 16px;font-weight:600;">
                        <span style="display:inline-block;width:12px;height:12px;background:${d.color};border:1px solid #555;border-radius:2px;margin-right:8px;"></span>${d.label}
                    </td>
                    <td style="padding:10px 16px;text-align:center;">${d.validJson}%</td>
                    <td style="padding:10px 16px;text-align:center;">${hi(d.intentAcc, maxIntent)}</td>
                    <td style="padding:10px 16px;text-align:center;">${hi(d.argsExact, maxArgs)}</td>
                    <td style="padding:10px 16px;text-align:center;">${hi(d.f1, maxF1)}</td>
                </tr>`;
            }).join('');
        }

        // Image gallery tabs
        const imgTabs = document.getElementById('img-tabs');
        const imgPerf = document.getElementById('img-performance');
        const imgConf = document.getElementById('img-confusion');
        if (imgTabs && imgPerf && imgConf) {
            const setImages = (modelKey) => {
                const dir = EVAL_RESULTS[modelKey].imgDir;
                imgPerf.src = `eval_results/${dir}/overall_performance.png`;
                imgConf.src = `eval_results/${dir}/intent_confusion_matrix.png`;
            };
            imgTabs.innerHTML = keys.map((k, i) =>
                `<button class="chip img-tab-btn${i===0?' active':''}" data-model="${k}">${EVAL_RESULTS[k].label}</button>`
            ).join('');
            imgTabs.querySelectorAll('.img-tab-btn').forEach(btn => {
                btn.addEventListener('click', () => {
                    imgTabs.querySelectorAll('.img-tab-btn').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    setImages(btn.dataset.model);
                });
            });
            setImages(keys[0]);
        }
    }

});