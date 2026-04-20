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
                if (targetLayout === 'a') {
                    layoutA.classList.remove('hidden');
                    layoutA.classList.add('active');
                    layoutB.classList.add('hidden');
                    layoutB.classList.remove('active');
                } else {
                    layoutA.classList.add('hidden');
                    layoutA.classList.remove('active');
                    layoutB.classList.remove('hidden');
                    layoutB.classList.add('active');
                    chatInput.focus();
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
});