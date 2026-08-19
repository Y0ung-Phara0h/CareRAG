/* CareRAG — Client-Side Web Application Controller */
document.addEventListener("DOMContentLoaded", () => {
    let currentSessionId = null;
    let currentLang = "en";

    // i18n Dictionary
    const i18n = {
        en: {
            default_title: "New Clinical Consultation",
            new_consultation: "+ New Consultation",
            past_consultations: "Past Consultations",
            engine_active: "Hybrid Engine Active",
            hero_title: "CareRAG Medical Decision Engine",
            hero_sub: "Ask a grounded clinical question based strictly on uploaded medical guidelines and guidelines PDFs.",
            input_placeholder: "Type a clinical question (e.g. 'What is the target blood pressure threshold for high-risk patients?')...",
            btn_send: "Send Inquiry",
            export_md: "📄 Export MD",
            export_json: "📊 Export JSON",
            drawer_title: "Citation Evidence Details",
            drawer_doc: "Source Document:",
            drawer_page: "Page Number:",
            drawer_sec: "Section:",
            drawer_excerpt: "Grounded Evidence Excerpt:",
            no_sessions: "No past sessions",
            confidence_badge: "Confidence",
            modal_delete_title: "Delete Consultation?",
            modal_delete_sub: "Are you sure you want to delete this consultation? All associated messages and data will be permanently removed.",
            modal_btn_cancel: "Cancel",
            modal_btn_delete: "Delete"
        },
        ar: {
            default_title: "استشارة طبية جديدة",
            new_consultation: "+ استشارة جديدة",
            past_consultations: "الاستشارات السابقة",
            engine_active: "المساعد الذكي نشط",
            hero_title: "مستشارك الطبي CareRAG",
            hero_sub: "اطرح سؤالاً طبياً موثقاً بالكامل استناداً إلى الإرشادات والملفات الطبية المرفقة.",
            input_placeholder: "اكتب سؤالاً طبياً (مثال: 'ما هي مستويات ضغط الدم المستهدفة لدى المرضى الأكثر عرضة للمخاطر؟')...",
            btn_send: "إرسال الاستفسار",
            export_md: "📄 إستخراج بصيغة MD",
            export_json: "📊 إستخراج بصيغة JSON",
            drawer_title: "تفاصيل أدلة الاقتباس",
            drawer_doc: "المستند المصدر:",
            drawer_page: "رقم الصفحة:",
            drawer_sec: "القسم:",
            drawer_excerpt: "مقتطف الدليل الموثق:",
            no_sessions: "لا توجد استشارات سابقة",
            confidence_badge: "درجة الثقة",
            modal_delete_title: "حذف الاستشارة؟",
            modal_delete_sub: "هل أنت تأكد من رغبتك في حذف هذه الاستشارة؟ سيتم إزالة جميع الرسائل والبيانات المرتبطة بها نهائياً.",
            modal_btn_cancel: "إلغاء",
            modal_btn_delete: "حذف"
        }
    };

    let pendingDeleteSessionId = null;

    // DOM Elements
    const appContainer = document.getElementById("app-container");
    const btnToggleSidebar = document.getElementById("btn-toggle-sidebar");
    const btnHeaderToggleSidebar = document.getElementById("btn-header-toggle-sidebar");
    const btnThemeToggle = document.getElementById("btn-theme-toggle");
    const themeToggleIcon = document.getElementById("theme-toggle-icon");
    const themeToggleLabel = document.getElementById("theme-toggle-label");
    const btnLangToggle = document.getElementById("btn-lang-toggle");
    const langToggleLabel = document.getElementById("lang-toggle-label");

    const deleteModalOverlay = document.getElementById("delete-modal-overlay");
    const btnCancelDelete = document.getElementById("btn-cancel-delete");
    const btnConfirmDelete = document.getElementById("btn-confirm-delete");

    const drawerOverlay = document.getElementById("citation-drawer-overlay") || document.getElementById("drawer-overlay");
    const citationDrawer = document.getElementById("citation-drawer");
    const btnCloseDrawer = document.getElementById("btn-close-drawer");
    const drawerDocName = document.getElementById("drawer-doc-name");
    const drawerPageNum = document.getElementById("drawer-page-num");
    const drawerSection = document.getElementById("drawer-section");
    const drawerEvidenceText = document.getElementById("drawer-evidence-text");

    const sessionListEl = document.getElementById("session-list");
    const activeTitleEl = document.getElementById("active-session-title");
    const chatViewportEl = document.getElementById("chat-viewport");
    const chatForm = document.getElementById("chat-form");
    const userInput = document.getElementById("user-input");
    const btnNewSession = document.getElementById("btn-new-session");
    const btnExportMd = document.getElementById("btn-export-md");
    const btnExportJson = document.getElementById("btn-export-json");

    // Initialize Theme, Language & Sidebar State from localStorage
    initLayoutState();

    // Initialize Sessions
    fetchSessions();

    // Event Listeners
    if (btnToggleSidebar) btnToggleSidebar.addEventListener("click", toggleSidebar);
    if (btnHeaderToggleSidebar) btnHeaderToggleSidebar.addEventListener("click", toggleSidebar);
    if (btnThemeToggle) btnThemeToggle.addEventListener("click", toggleTheme);
    if (btnLangToggle) btnLangToggle.addEventListener("click", toggleLanguage);

    if (btnNewSession) btnNewSession.addEventListener("click", () => startNewSession());
    if (chatForm) chatForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitQuery();
    });

    if (btnCloseDrawer) btnCloseDrawer.addEventListener("click", hideDrawer);
    if (drawerOverlay) drawerOverlay.addEventListener("click", hideDrawer);

    if (btnExportMd) btnExportMd.addEventListener("click", () => exportSession("markdown"));
    if (btnExportJson) btnExportJson.addEventListener("click", () => exportSession("json"));

    if (btnCancelDelete) btnCancelDelete.addEventListener("click", closeDeleteModal);
    if (btnConfirmDelete) btnConfirmDelete.addEventListener("click", confirmDeleteSession);
    if (deleteModalOverlay) deleteModalOverlay.addEventListener("click", (e) => {
        if (e.target === deleteModalOverlay) closeDeleteModal();
    });

    // --- Layout, Language & Theme State Handlers ---

    function initLayoutState() {
        // Sidebar collapse state
        const savedSidebar = localStorage.getItem("care_rag_sidebar");
        if (savedSidebar === "collapsed") {
            appContainer.classList.add("sidebar-collapsed");
        }

        // Theme state
        const savedTheme = localStorage.getItem("care_rag_theme") || "dark";
        applyTheme(savedTheme);

        // Language state
        const savedLang = localStorage.getItem("care_rag_lang") || "en";
        applyLanguage(savedLang);
    }

    function toggleSidebar() {
        appContainer.classList.toggle("sidebar-collapsed");
        const isCollapsed = appContainer.classList.contains("sidebar-collapsed");
        localStorage.setItem("care_rag_sidebar", isCollapsed ? "collapsed" : "expanded");
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
        const newTheme = currentTheme === "light" ? "dark" : "light";
        applyTheme(newTheme);
    }

    function applyTheme(theme) {
        if (theme === "light") {
            document.documentElement.setAttribute("data-theme", "light");
            themeToggleIcon.textContent = "🌙";
            themeToggleLabel.textContent = "Dark";
        } else {
            document.documentElement.removeAttribute("data-theme");
            themeToggleIcon.textContent = "☀️";
            themeToggleLabel.textContent = "Light";
        }
        localStorage.setItem("care_rag_theme", theme);
    }

    function toggleLanguage() {
        const newLang = currentLang === "en" ? "ar" : "en";
        applyLanguage(newLang);
    }

    function applyLanguage(lang) {
        currentLang = lang;
        localStorage.setItem("care_rag_lang", lang);

        if (lang === "ar") {
            document.documentElement.setAttribute("dir", "rtl");
            langToggleLabel.textContent = "English";
        } else {
            document.documentElement.removeAttribute("dir");
            langToggleLabel.textContent = "العربية";
        }

        // Update all data-i18n text content
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.dataset.i18n;
            if (i18n[lang] && i18n[lang][key]) {
                el.textContent = i18n[lang][key];
            }
        });

        // Update data-i18n-placeholder attributes
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.dataset.i18nPlaceholder;
            if (i18n[lang] && i18n[lang][key]) {
                el.placeholder = i18n[lang][key];
            }
        });
    }

    // --- Core Functions ---

    async function fetchSessions() {
        try {
            const res = await fetch("/api/sessions");
            const sessions = await res.json();
            renderSessionList(sessions);
        } catch (err) {
            console.error("Failed to load sessions:", err);
        }
    }

    function renderSessionList(sessions) {
        sessionListEl.innerHTML = "";
        if (!sessions || sessions.length === 0) {
            sessionListEl.innerHTML = `<div class="session-item-date">${i18n[currentLang].no_sessions}</div>`;
            return;
        }

        sessions.forEach(s => {
            const item = document.createElement("div");
            item.className = `session-item ${s.session_id === currentSessionId ? "active" : ""}`;
            item.innerHTML = `
                <div class="session-item-content">
                    <div class="session-item-title">${escapeHtml(s.title || i18n[currentLang].default_title)}</div>
                    <div class="session-item-date">${new Date(s.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
                <button class="btn-delete-session" title="Delete Consultation" data-id="${s.session_id}">
                    🗑️
                </button>
            `;

            const deleteBtn = item.querySelector(".btn-delete-session");
            deleteBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                openDeleteModal(s.session_id);
            });

            item.addEventListener("click", () => loadSession(s.session_id));
            sessionListEl.appendChild(item);
        });
    }

    function openDeleteModal(sessionId) {
        pendingDeleteSessionId = sessionId;
        deleteModalOverlay.classList.remove("hidden");
        requestAnimationFrame(() => {
            deleteModalOverlay.classList.add("active");
        });
    }

    function closeDeleteModal() {
        deleteModalOverlay.classList.remove("active");
        setTimeout(() => {
            deleteModalOverlay.classList.add("hidden");
            pendingDeleteSessionId = null;
        }, 250);
    }

    async function confirmDeleteSession() {
        if (!pendingDeleteSessionId) return;

        const targetId = pendingDeleteSessionId;
        closeDeleteModal();

        try {
            const res = await fetch(`/api/sessions/${targetId}`, { method: "DELETE" });
            if (res.ok) {
                if (targetId === currentSessionId) {
                    startNewSession();
                } else {
                    fetchSessions();
                }
            } else {
                alert("Failed to delete session.");
            }
        } catch (err) {
            console.error("Delete session error:", err);
            alert("Error deleting session.");
        }
    }

    async function startNewSession() {
        currentSessionId = null;
        setSessionTitle(i18n[currentLang].default_title);
        chatViewportEl.innerHTML = `
            <div class="welcome-hero">
                <div class="hero-icon">🩺</div>
                <h2>${i18n[currentLang].hero_title}</h2>
                <p>${i18n[currentLang].hero_sub}</p>
            </div>
        `;
        fetchSessions();
    }

    async function loadSession(sessionId) {
        try {
            const res = await fetch(`/api/sessions/${sessionId}`);
            if (!res.ok) return;
            const session = await res.json();
            currentSessionId = session.session_id;

            setSessionTitle(session.title || i18n[currentLang].default_title);

            chatViewportEl.innerHTML = "";
            session.messages.forEach(msg => {
                if (msg.role === "user") {
                    appendUserMessage(msg.content);
                } else {
                    appendAssistantCard({
                        recommendation: msg.content,
                        citations: msg.citations || [],
                        confidence: "high"
                    });
                }
            });

            fetchSessions();
        } catch (err) {
            console.error("Error loading session:", err);
        }
    }

    async function submitQuery() {
        const text = userInput.value.trim();
        if (!text) return;

        appendUserMessage(text);
        userInput.value = "";

        // Render Loading Assistant Card
        const loadingCard = document.createElement("div");
        loadingCard.className = "card-assistant";
        loadingCard.innerHTML = `<div class="card-body">🔍 Retrieving clinical guidelines & generating grounded answer...</div>`;
        chatViewportEl.appendChild(loadingCard);
        chatViewportEl.scrollTop = chatViewportEl.scrollHeight;

        try {
            const res = await fetch("/api/query", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: text,
                    session_id: currentSessionId
                })
            });

            const data = await res.json();
            chatViewportEl.removeChild(loadingCard);

            currentSessionId = data.session_id;
            setSessionTitle(text.length > 30 ? text.substring(0, 30) + "..." : text);

            appendAssistantCard(data);
            fetchSessions();
        } catch (err) {
            chatViewportEl.removeChild(loadingCard);
            appendAssistantCard({
                recommendation: `API Request Failed: ${err.message}`,
                citations: [],
                confidence: "insufficient"
            });
        }
    }

    function appendUserMessage(text) {
        const msg = document.createElement("div");
        msg.className = "msg-user";
        msg.textContent = text;
        chatViewportEl.appendChild(msg);
        chatViewportEl.scrollTop = chatViewportEl.scrollHeight;
    }

    function appendAssistantCard(data) {
        const card = document.createElement("div");
        card.className = "card-assistant";

        const confidence = (data.confidence || "insufficient").toLowerCase();

        let citationsHtml = "";
        if (data.citations && data.citations.length > 0) {
            citationsHtml = `<div class="citations-container">`;
            data.citations.forEach((cit, idx) => {
                citationsHtml += `
                    <button class="citation-chip" data-doc="${escapeHtml(cit.document || cit.document_name || 'N/A')}" data-page="${cit.page || cit.page_number || '?'}" data-sec="${escapeHtml(cit.section || 'N/A')}" data-evidence="${escapeHtml(data.evidence || 'N/A')}">
                        📚 ${escapeHtml(cit.document || cit.document_name || 'Doc')} (p.${cit.page || cit.page_number || '?'})
                    </button>
                `;
            });
            citationsHtml += `</div>`;
        }

        card.innerHTML = `
            <div class="card-header">
                <span class="confidence-badge ${confidence}">Confidence: ${confidence}</span>
            </div>
            <div class="card-body">
                ${escapeHtml(data.recommendation)}
            </div>
            ${citationsHtml}
        `;

        chatViewportEl.appendChild(card);
        chatViewportEl.scrollTop = chatViewportEl.scrollHeight;

        // Attach citation click listeners
        card.querySelectorAll(".citation-chip").forEach(chip => {
            chip.addEventListener("click", () => {
                showDrawer(
                    chip.dataset.doc,
                    chip.dataset.page,
                    chip.dataset.sec,
                    chip.dataset.evidence
                );
            });
        });
    }

    const headerSubTitleEl = document.getElementById("header-sub-session-title");

    function setSessionTitle(title) {
        activeTitleEl.textContent = title;
        if (headerSubTitleEl) {
            headerSubTitleEl.textContent = title;
        }
    }

    function showDrawer(doc, page, sec, evidence) {
        drawerDocName.textContent = doc;
        drawerPageNum.textContent = page;
        drawerSection.textContent = sec;
        drawerEvidenceText.textContent = evidence && evidence !== "N/A" ? `"${evidence}"` : "No direct evidence excerpt attached.";

        drawerOverlay.classList.remove("hidden");
        citationDrawer.classList.remove("hidden");

        requestAnimationFrame(() => {
            drawerOverlay.classList.add("active");
            citationDrawer.classList.add("active");
        });
    }

    function hideDrawer() {
        drawerOverlay.classList.remove("active");
        citationDrawer.classList.remove("active");
        setTimeout(() => {
            drawerOverlay.classList.add("hidden");
            citationDrawer.classList.add("hidden");
        }, 350);
    }

    function exportSession(format) {
        if (!currentSessionId) {
            alert("No active session to export.");
            return;
        }
        window.open(`/api/sessions/${currentSessionId}/export?format=${format}`, "_blank");
    }

    function escapeHtml(str) {
        if (!str) return "";
        return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
    }
});
