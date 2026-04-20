/**
 * Enterprise Neo-Brutalism - App Logic
 */

// CONFIGURATION
const API_BASE_URL = "https://unmoldered-patellate-angela.ngrok-free.dev"; 

document.addEventListener('DOMContentLoaded', () => {
    
    // --- STATE ---
    let currentMode = "1";
    let currentLayout = "a";

    // --- DOM ELEMENTS (SIDEBAR) ---
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const navItems = document.querySelectorAll('.nav-item');
    const layoutA = document.getElementById('layout-a');
    const layoutB = document.getElementById('layout-b');
    const layoutC = document.getElementById('layout-c');

    // Sidebar Toggle Logic
    sidebarToggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
    });

    // --- DOM ELEMENTS (LAYOUT A - DASHBOARD) ---
    const dashInput = document.getElementById('dashboardInput');
    const dashExecuteBtn = document.getElementById('dashboardExecuteBtn');
    const promptChips = document.querySelectorAll('.chip');
    const dashLoading = document.getElementById('dashboardLoading');
    const detailBtns = document.querySelectorAll('.detail-btn');
    
    // --- DOM ELEMENTS (LAYOUT B - CHAT) ---
    const chatInput = document.getElementById('chatInput');
    const chatSendBtn = document.getElementById('chatSendBtn');
    const chatHistory = document.getElementById('chatHistory');

    // --- DOM ELEMENTS (MODAL) ---
    const modal = document.getElementById('detailModal');
    const closeModalBtn = document.getElementById('closeModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalRaw = document.getElementById('modalRaw');
    const modalTool = document.getElementById('modalTool');

    // --- DOM ELEMENTS (LAYOUT C - CHATBOT AGENCY) ---
    const agencyChatInput = document.getElementById('agencyChatInput');
    const agencyChatSendBtn = document.getElementById('agencyChatSendBtn');
    const agencyChatHistory = document.getElementById('agencyChatHistory');
    const agencyModelSelect = document.getElementById('agencyModelSelect');
    const resetAgencyChatBtn = document.getElementById('resetAgencyChatBtn');

    // Store latest responses for modal viewing
    let latestDashboardData = {};

    // ==========================================
    // 1. SIDEBAR EVENT LISTENERS & ROUTING
    // ==========================================
    navItems.forEach(btn => {
        btn.addEventListener('click', (e) => {
            // Update active state in UI
            navItems.forEach(b => b.classList.remove('active'));
            e.currentTarget.classList.add('active');
            
            // Update internal state
            const previousMode = currentMode;
            currentMode = e.currentTarget.dataset.mode;
            const targetLayout = e.currentTarget.dataset.layout;

            // Switch Layouts
            if (targetLayout !== currentLayout) {
                currentLayout = targetLayout;
                
                // Hide all layouts
                layoutA.classList.add('hidden');
                layoutA.classList.remove('active');
                layoutB.classList.add('hidden');
                layoutB.classList.remove('active');
                layoutC.classList.add('hidden');
                layoutC.classList.remove('active');
                
                // Show target
                if (targetLayout === 'a') {
                    layoutA.classList.remove('hidden');
                    layoutA.classList.add('active');
                } else if (targetLayout === 'b') {
                    layoutB.classList.remove('hidden');
                    layoutB.classList.add('active');
                    chatInput.focus();
                } else if (targetLayout === 'c') {
                    layoutC.classList.remove('hidden');
                    layoutC.classList.add('active');
                    agencyChatInput.focus();
                    loadAgencyHistory();
                }
            }

            // Gộp phần reset: Reset kết quả cũ khi đổi mode (bất kể layout có đổi hay không)
            if (currentMode !== previousMode) {
                dashInput.value = '';
                latestDashboardData = {};
                renderDashboard({});
            }
        });
    });

    // ==========================================
    // 2. LAYOUT A: DASHBOARD LOGIC
    // ==========================================
    
    // Handle sample prompt chips
    promptChips.forEach(chip => {
        chip.addEventListener('click', () => {
            dashInput.value = chip.dataset.prompt;
            dashInput.focus();
        });
    });

    // Execute Button
    dashExecuteBtn.addEventListener('click', executeDashboard);
    dashInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeDashboard();
    });

    async function executeDashboard() {
        const query = dashInput.value.trim();
        if (!query) return;

        dashLoading.classList.remove('hidden');

        try {
            let endpoint = "/api/generate_pretrain";
            if (currentMode === "2") endpoint = "/api/generate_scratch";
            
            const response = await fetch(API_BASE_URL + endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true" 
                },
                body: JSON.stringify({ message: query })
            });

            if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
            
            const data = await response.json();
            latestDashboardData = data;
            renderDashboard(data);

        } catch (error) {
            console.error("Dashboard API Error:", error);
            alert("Lỗi kết nối đến Backend. Vui lòng kiểm tra Console.");
        } finally {
            dashLoading.classList.add('hidden');
        }
    }

    function renderDashboard(data) {
        const models = ['gpt2_medium', 'gpt2_small', 'spikegpt'];

        models.forEach(modelId => {
            const modelData = data[modelId];
            const colEl = document.getElementById(`col-${modelId}`);
            
            if (!modelData) {
                if (colEl) {
                    colEl.classList.add('dimmed');
                    const sI = colEl.querySelector('.success-icon');
                    const eI = colEl.querySelector('.error-icon');
                    if (sI) sI.classList.add('hidden');
                    if (eI) eI.classList.add('hidden');
                    const tb = colEl.querySelector('.time-val');
                    if (tb) tb.textContent = '--s';
                    const tbox = colEl.querySelector('.json-out');
                    const ebox = colEl.querySelector('.exec-out');
                    if (tbox) tbox.textContent = '';
                    if (ebox) ebox.textContent = '';
                }
                return;
            }
            if (colEl) colEl.classList.remove('dimmed');

            // Elements inside column
            const timeBadge = colEl.querySelector('.time-val');
            const rawBox = colEl.querySelector('.raw-out');
            const toolBox = colEl.querySelector('.json-out');
            const execBox = colEl.querySelector('.exec-out');
            const successIcon = colEl.querySelector('.success-icon');
            const errorIcon = colEl.querySelector('.error-icon');
            
            // Base rendering
            timeBadge.textContent = modelData.time || '--s';
            rawBox.textContent = modelData.text || '';
            successIcon.classList.add('hidden');
            errorIcon.classList.add('hidden');

            // Handle Function Calling
            if (modelData.is_tool) {
                // Formatting JSON nicely
                const toolInfo = {
                    name: modelData.tool_name,
                    arguments: modelData.tool_args
                };
                toolBox.textContent = JSON.stringify(toolInfo, null, 2);
                
                if (modelData.execution_result && !modelData.execution_result.error) {
                    execBox.textContent = JSON.stringify(modelData.execution_result, null, 2);
                    successIcon.classList.remove('hidden');
                } else {
                    execBox.textContent = modelData.execution_result ? JSON.stringify(modelData.execution_result, null, 2) : `Error: Cannot execute system logic.`;
                    errorIcon.classList.remove('hidden');
                }

                // Remove dimming
                colEl.querySelector('.tool-block').classList.remove('dimmed');
                colEl.querySelector('.exec-block').classList.remove('dimmed');
            } else {
                // Dim down function calling blocks if not triggered
                toolBox.textContent = "// No function called";
                execBox.textContent = "// N/A";
                colEl.querySelector('.tool-block').classList.add('dimmed');
                colEl.querySelector('.exec-block').classList.add('dimmed');
                // Consider no tool called as an error? Or just leave it without ticks
                errorIcon.classList.remove('hidden');
            }
        });
    }

    // Modal Handling
    detailBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const targetModel = e.currentTarget.dataset.target;
            const data = latestDashboardData[targetModel];
            if (!data) return;

            modalTitle.textContent = `Chi tiết: ${targetModel.toUpperCase()}`;
            modalRaw.textContent = data.text || '';
            
            let parsedStr = `// Tool Detection Status: ${data.is_tool}\n\n`;
            if (data.is_tool) {
                parsedStr += `[TOOL NAME]:\n${data.tool_name}\n\n`;
                parsedStr += `[ARGUMENTS]:\n${JSON.stringify(data.tool_args, null, 2)}\n\n`;
                parsedStr += `[EXECUTION RESULT]:\n${JSON.stringify(data.execution_result, null, 2)}`;
            } else {
                parsedStr += `No tool parsed from raw output.`;
            }
            modalTool.textContent = parsedStr;

            modal.classList.remove('hidden');
        });
    });

    closeModalBtn.addEventListener('click', () => modal.classList.add('hidden'));
    modal.addEventListener('click', (e) => {
        if(e.target === modal) modal.classList.add('hidden');
    });

    // ==========================================
    // 3. LAYOUT B: CHAT LOGIC
    // ==========================================
    
    chatSendBtn.addEventListener('click', executeChat);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeChat();
    });

    async function executeChat() {
        const message = chatInput.value.trim();
        if (!message) return;

        // Add user bubble
        appendChatBubble(message, 'user');
        chatInput.value = '';

        // Add Loading bubble
        const loadingId = appendChatBubble('...', 'ai', true);

        try {
            const endpoint = "/api/chat_spike";
            const response = await fetch(API_BASE_URL + endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true" 
                },
                body: JSON.stringify({ message: message })
            });

            if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
            
            const data = await response.json();
            
            // Remove loading and append real answer
            removeChatBubble(loadingId);
            
            // Handle output specific to mode 3
            if (data.spikegpt && data.spikegpt.text) {
                appendChatBubble(data.spikegpt.text, 'ai');
            } else {
                appendChatBubble(" Lỗi: Không nhận được phản hồi từ SpikeGPT.", 'ai');
            }

        } catch (error) {
            console.error("Chat API Error:", error);
            removeChatBubble(loadingId);
            appendChatBubble(" Lỗi kết nối đến Backend.", 'ai');
        }
    }

    function appendChatBubble(text, sender, isLoading = false) {
        const bubbleId = 'msg-' + Date.now();
        const wrapper = document.createElement('div');
        wrapper.className = `chat-bubble ${sender}`;
        wrapper.id = bubbleId;
        
        let icon = sender === 'user' ? 'user' : 'bot';
        let extraClass = isLoading ? 'animate-pulse' : '';

        wrapper.innerHTML = `
            <div class="bubble-avatar"><i data-lucide="${icon}"></i></div>
            <div class="bubble-content ${extraClass}">${text}</div>
        `;
        
        chatHistory.appendChild(wrapper);
        lucide.createIcons(); // Render the new icon
        chatHistory.scrollTop = chatHistory.scrollHeight;

        return bubbleId;
    }

    function removeChatBubble(id) {
        const el = document.getElementById(id);
        if (el) el.remove();
    }

    // ==========================================
    // 4. LAYOUT C: CHATBOT AGENCY (Mode 4)
    // ==========================================

    let agencyModelEndpointMap = {
        'gpt2_medium_pre': { endpoint: '/api/generate_pretrain', key: 'gpt2_medium' },
        'gpt2_medium_scr': { endpoint: '/api/generate_scratch', key: 'gpt2_medium' },
        'gpt2_small_pre': { endpoint: '/api/generate_pretrain', key: 'gpt2_small' },
        'gpt2_small_scr': { endpoint: '/api/generate_scratch', key: 'gpt2_small' },
        'spikegpt_pre': { endpoint: '/api/generate_pretrain', key: 'spikegpt' },
        'spikegpt_scr': { endpoint: '/api/generate_scratch', key: 'spikegpt' },
    };

    agencyModelSelect.addEventListener('change', () => {
        resetAgencyChat();
    });

    resetAgencyChatBtn.addEventListener('click', () => {
        resetAgencyChat();
    });

    function resetAgencyChat() {
        const selectedText = agencyModelSelect.options[agencyModelSelect.selectedIndex].text;
        agencyChatHistory.innerHTML = `
            <div class="chat-bubble ai">
                <div class="bubble-avatar"><i data-lucide="bot"></i></div>
                <div class="bubble-content">Hệ thống đã chuyển sang mô hình <strong>${selectedText}</strong>. Lịch sử đã được xoá.</div>
            </div>
        `;
        lucide.createIcons();
        localStorage.removeItem('agencyChatHistory');
    }

    agencyChatSendBtn.addEventListener('click', executeAgencyChat);
    agencyChatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') executeAgencyChat();
    });

    async function executeAgencyChat() {
        const message = agencyChatInput.value.trim();
        if (!message) return;

        // Add user bubble
        appendAgencyBubble(message, 'user');
        agencyChatInput.value = '';

        // Add Loading bubble
        const loadingId = appendAgencyBubble('...', 'ai', true);

        try {
            const selectedModel = agencyModelSelect.value;
            const routeInfo = agencyModelEndpointMap[selectedModel];
            
            const response = await fetch(API_BASE_URL + routeInfo.endpoint, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "ngrok-skip-browser-warning": "true" 
                },
                body: JSON.stringify({ message: message }) // SINGLE-TURN
            });

            if (!response.ok) throw new Error(`HTTP Error: ${response.status}`);
            
            const fullData = await response.json();
            const modelData = fullData[routeInfo.key];
            
            removeAgencyBubble(loadingId);
            
            if (modelData) {
                // Determine user-friendly text message based on tool execution
                let botMessage = modelData.text || "...";
                if (modelData.is_tool && modelData.execution_result && modelData.execution_result.message) {
                    botMessage = modelData.execution_result.message;
                }
                
                // Print Bot Bubble (Text Message)
                appendAgencyBubble(botMessage, 'ai');

                // If Tool was called, render interactive E-commerce Card
                if (modelData.is_tool) {
                    renderEcommerceCard(modelData.tool_name, modelData.execution_result);
                }
            } else {
                appendAgencyBubble(" Lỗi: Phản hồi không tồn tại.", 'ai');
            }

            saveAgencyHistory();

        } catch (error) {
            console.error("Agency API Error:", error);
            removeAgencyBubble(loadingId);
            appendAgencyBubble(" Lỗi kết nối đến Backend: " + error.message, 'ai');
        }
    }

    function appendAgencyBubble(text, sender, isLoading = false) {
        const bubbleId = 'a-msg-' + Date.now();
        const wrapper = document.createElement('div');
        wrapper.className = `chat-bubble ${sender}`;
        wrapper.id = bubbleId;
        
        let icon = sender === 'user' ? 'user' : 'bot';
        let extraClass = isLoading ? 'animate-pulse' : '';

        wrapper.innerHTML = `
            <div class="bubble-avatar"><i data-lucide="${icon}"></i></div>
            <div class="bubble-content ${extraClass}">${text}</div>
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
        
        let headerHtml = '';
        let bodyHtml = '';

        // Xử lý Lỗi (Error State)
        if (execResult.error) {
            headerHtml = `
                <div class="card-header-neo" style="background: var(--c-pink);">
                    <i data-lucide="x-circle"></i>
                    <span>Lỗi hệ thống</span>
                </div>
            `;
            bodyHtml = `
                <div class="card-body-neo">
                    <div style="color: #991B1B; font-weight: 600;">⚠️ ${execResult.error}</div>
                </div>
            `;
        } else {
            // Success State (Neo-Brutalism E-commerce UI)
            switch(toolName) {
                case 'create_order':
                case 'get_order':
                    headerHtml = `
                        <div class="card-header-neo" style="background: var(--c-yellow);">
                            <i data-lucide="shopping-cart"></i>
                            <span>Thông tin đơn hàng</span>
                        </div>
                    `;
                    let statusBadge = `<span class="badge-neo-warning">${execResult.status || execResult.current_status || 'UNKNOWN'}</span>`;
                    if (execResult.status === 'confirmed' || execResult.current_status === 'confirmed') {
                        statusBadge = `<span class="badge-neo-success">${execResult.status || execResult.current_status}</span>`;
                    }
                    bodyHtml = `
                        <div class="card-body-neo">
                            <div class="card-row">
                                <strong>Mã đơn:</strong>
                                <span>#${execResult.order_id || 'N/A'}</span>
                            </div>
                            <div class="card-row">
                                <strong>Trạng thái:</strong>
                                ${statusBadge}
                            </div>
                            <div class="card-row">
                                <strong>Tổng tiền:</strong>
                                <span style="font-weight: 700; font-size: 1.1rem; color: #b91c1c;">$${execResult.total_price || 0}</span>
                            </div>
                        </div>
                    `;
                    break;
                case 'check_inventory':
                    headerHtml = `
                        <div class="card-header-neo" style="background: var(--c-mint);">
                            <i data-lucide="package"></i>
                            <span>Trạng thái sản phẩm</span>
                        </div>
                    `;
                    let stockStatus = execResult.stock > 0 
                        ? `<span class="badge-neo-success">Còn hàng (${execResult.stock})</span>`
                        : `<span class="badge-neo-danger">Hết hàng</span>`;
                        
                    bodyHtml = `
                        <div class="card-body-neo">
                            <div class="card-row">
                                <strong>Sản phẩm:</strong>
                                <span>${execResult.product_name || 'N/A'}</span>
                            </div>
                            <div class="card-row">
                                <strong>Tồn kho:</strong>
                                ${stockStatus}
                            </div>
                            <div class="card-row">
                                <strong>Giá:</strong>
                                <span style="font-weight: 700;">$${execResult.price || 0}</span>
                            </div>
                        </div>
                    `;
                    break;
                case 'delete_order':
                    headerHtml = `
                        <div class="card-header-neo" style="background: var(--c-pink);">
                            <i data-lucide="trash-2"></i>
                            <span>Yêu cầu hủy đơn</span>
                        </div>
                    `;
                    bodyHtml = `
                        <div class="card-body-neo">
                            <div class="card-row">
                                <strong>Mã đơn:</strong>
                                <span>#${execResult.order_id || 'N/A'}</span>
                            </div>
                            <div class="card-row">
                                <strong>Trạng thái:</strong>
                                <span class="badge-neo-danger" style="background: #fff;">Đã hủy thành công</span>
                            </div>
                        </div>
                    `;
                    break;
                case 'revenue_analysis':
                    headerHtml = `
                        <div class="card-header-neo" style="background: var(--c-blue);">
                            <i data-lucide="bar-chart-2"></i>
                            <span>Báo cáo doanh thu</span>
                        </div>
                    `;
                    bodyHtml = `
                        <div class="card-body-neo">
                            <div class="card-row">
                                <strong>Tổng số đơn:</strong>
                                <span>${execResult.total_valid_orders || 0} đơn</span>
                            </div>
                            <div class="card-row" style="flex-direction: column; align-items: flex-start; gap: 8px;">
                                <strong>Tổng Doanh Thu:</strong>
                                <span style="font-weight: 900; font-size: 1.5rem; color: #166534;">$${execResult.total_revenue || 0}</span>
                            </div>
                        </div>
                    `;
                    break;
                default:
                    // Fallback for unknown tools
                    headerHtml = `
                        <div class="card-header-neo" style="background: var(--c-gray);">
                            <i data-lucide="settings"></i>
                            <span>Hệ thống</span>
                        </div>
                    `;
                    bodyHtml = `
                        <div class="card-body-neo">
                            <span>Đã thực thi tác vụ: <strong>${toolName}</strong></span>
                        </div>
                    `;
            }
        }

        wrapper.innerHTML = headerHtml + bodyHtml;

        // Container để căn chỉnh card nằm bên trái (giống Chat AI)
        const outerWrapper = document.createElement('div');
        outerWrapper.style.display = 'flex';
        outerWrapper.style.justifyContent = 'flex-start';
        outerWrapper.style.width = '100%';
        outerWrapper.style.paddingLeft = '50px'; // Lùi vào một chút cho hợp với Avatar AI
        outerWrapper.appendChild(wrapper);

        agencyChatHistory.appendChild(outerWrapper);
        lucide.createIcons();
        agencyChatHistory.scrollTop = agencyChatHistory.scrollHeight;
 
        saveAgencyHistory();
    }

    // Removed appendToolCard in favor of renderEcommerceCard

    // LocalStorage utilities
    function saveAgencyHistory() {
        const htmlContent = agencyChatHistory.innerHTML;
        localStorage.setItem('agencyChatHistory', htmlContent);
        localStorage.setItem('agencyChatModel', agencyModelSelect.value);
    }

    function loadAgencyHistory() {
        const savedHistory = localStorage.getItem('agencyChatHistory');
        const savedModel = localStorage.getItem('agencyChatModel');
        
        if (savedModel && agencyModelSelect.querySelector(`option[value="${savedModel}"]`)) {
            agencyModelSelect.value = savedModel;
        }
        
        if (savedHistory && savedHistory.trim() !== '') {
            agencyChatHistory.innerHTML = savedHistory;
            lucide.createIcons(); // Re-bind icons
            agencyChatHistory.scrollTop = agencyChatHistory.scrollHeight;
        }
    }
});