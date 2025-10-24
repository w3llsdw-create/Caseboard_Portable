const API_URL = "/cases";
const REFRESH_INTERVAL = 60_000;

const STORAGE_KEYS = {
    LAST_CASE: "caseboard:last-case",
    PIP: "caseboard:pip",
    KIOSK: "caseboard:kiosk",
};

const PIP_SIZES = {
    sm: ["w-[300px]", "h-[169px]"],
    md: ["w-[380px]", "h-[214px]"],
    lg: ["w-[480px]", "h-[270px]"],
};

const ACTIVE_STATUSES = new Set(["open", "filed", "pre-filing"]);

const STATUS_BADGES = {
    open: { label: "Active", tone: "bg-emeraldA/15 text-emerald-200" },
    filed: { label: "Filed", tone: "bg-emeraldA/15 text-emerald-200" },
    "pre-filing": { label: "Pre-Filing", tone: "bg-slate-500/20 text-slate-200" },
    closed: { label: "Closed", tone: "bg-slate-600/20 text-slate-300" },
    archived: { label: "Archived", tone: "bg-slate-600/20 text-slate-300" },
};

const elements = {
    lastSync: document.getElementById("last-sync"),
    statChips: document.getElementById("stat-chips"),
    practiceMeta: document.getElementById("practice-meta"),
    practiceList: document.getElementById("practice-list"),
    deadlineMeta: document.getElementById("deadline-meta"),
    deadlinesList: document.getElementById("deadlines-list"),
    caseCount: document.getElementById("case-count"),
    casesBody: document.getElementById("cases-body"),
    drawer: document.getElementById("drawer"),
    drawerClose: document.getElementById("drawer-close"),
    drawerNumber: document.getElementById("drawer-number"),
    drawerName: document.getElementById("drawer-name"),
    drawerType: document.getElementById("drawer-type"),
    drawerStage: document.getElementById("drawer-stage"),
    drawerStatus: document.getElementById("drawer-status"),
    drawerParalegal: document.getElementById("drawer-paralegal"),
    drawerFocus: document.getElementById("drawer-focus"),
    drawerNextDue: document.getElementById("drawer-nextdue"),
    drawerDeadlines: document.getElementById("drawer-deadlines"),
    drawerCopy: document.getElementById("drawer-copy"),
    drawerMail: document.getElementById("drawer-mail"),
    drawerDownload: document.getElementById("drawer-download"),
    btnRefresh: document.getElementById("btn-refresh"),
    btnKiosk: document.getElementById("btn-kiosk"),
    btnPiP: document.getElementById("btn-pip"),
    pip: document.getElementById("pip"),
    pipFrame: document.getElementById("pip-frame"),
    pipHide: document.getElementById("pip-hide"),
    pipSizeButtons: Array.from(document.querySelectorAll("#pip button[data-size]")),
};

const state = {
    cases: [],
    refreshTimer: null,
    lastCaseKey: null,
    kiosk: false,
    pipVisible: true,
    pipSize: "md",
    dragStart: null,
};

init();

function init() {
    restorePreferences();
    bindEvents();
    applyPipSize(state.pipSize);
    applyPipVisibility(state.pipVisible);
    applyKioskMode(state.kiosk);
    loadDashboard();
    scheduleRefresh();
}

function bindEvents() {
    if (elements.btnRefresh) {
        elements.btnRefresh.addEventListener("click", () => loadDashboard(true));
    }

    if (elements.btnKiosk) {
        elements.btnKiosk.addEventListener("click", toggleKioskMode);
    }

    if (elements.btnPiP) {
        elements.btnPiP.addEventListener("click", () => togglePiP());
    }

    if (elements.pipHide) {
        elements.pipHide.addEventListener("click", () => togglePiP(false));
    }

    elements.pipSizeButtons.forEach((button) => {
        button.addEventListener("click", () => setPipSize(button.dataset.size || "md"));
    });

    if (elements.pipFrame) {
        elements.pipFrame.addEventListener("pointerdown", startDrag);
        elements.pipFrame.addEventListener("pointermove", dragPiP);
        elements.pipFrame.addEventListener("pointerup", endDrag);
        elements.pipFrame.addEventListener("pointercancel", endDrag);
    }

    if (elements.drawerClose) {
        elements.drawerClose.addEventListener("click", closeDrawer);
    }

    if (elements.drawerCopy) {
        elements.drawerCopy.addEventListener("click", copyCaseId);
    }

    if (elements.drawerDownload) {
        elements.drawerDownload.addEventListener("click", downloadCaseJson);
    }

    if (elements.btnPiP && elements.btnPiP instanceof HTMLElement) {
        elements.btnPiP.setAttribute("aria-pressed", String(state.pipVisible));
    }

    document.addEventListener("click", handleGlobalClick);
    document.addEventListener("keydown", handleKeydown);
}

function restorePreferences() {
    try {
        const storedCase = localStorage.getItem(STORAGE_KEYS.LAST_CASE);
        if (storedCase) state.lastCaseKey = storedCase;
    } catch (error) {
        console.warn("Unable to restore last case", error);
    }

    try {
        const pipPayload = localStorage.getItem(STORAGE_KEYS.PIP);
        if (pipPayload) {
            const parsed = JSON.parse(pipPayload);
            if (parsed && typeof parsed === "object") {
                if (typeof parsed.visible === "boolean") {
                    state.pipVisible = parsed.visible;
                }
                if (parsed.size && Object.hasOwn(PIP_SIZES, parsed.size)) {
                    state.pipSize = parsed.size;
                }
            }
        }
    } catch (error) {
        console.warn("Unable to restore PiP settings", error);
    }

    try {
        const kioskPref = localStorage.getItem(STORAGE_KEYS.KIOSK);
        if (kioskPref) {
            state.kiosk = kioskPref === "1";
        }
    } catch (error) {
        console.warn("Unable to restore kiosk mode", error);
    }
}

async function loadDashboard(manual = false) {
    if (!elements.lastSync) return;
    const timestamp = new Date();

    if (elements.btnRefresh && manual) {
        elements.btnRefresh.disabled = true;
        elements.btnRefresh.textContent = "Refreshing…";
    }

    elements.lastSync.textContent = manual ? "Refreshing…" : "Loading cases…";

    try {
        const response = await fetch(API_URL, { cache: "no-cache" });
        if (!response.ok) {
            throw new Error(`Request failed with status ${response.status}`);
        }

        const payload = await response.json();
        const cases = Array.isArray(payload.cases) ? payload.cases : [];
        state.cases = cases;

        const stats = summarizeCases(cases);
        const deadlines = computeDeadlines(cases);

        renderStats(stats);
        renderPractice(stats);
        renderDeadlines(deadlines);
        renderCases(cases);
        updateSnapshotTime(payload.meta?.saved_at, payload.generated_at);

        if (state.lastCaseKey) {
            const match = findCase(state.lastCaseKey);
            if (match) {
                openDrawer(state.lastCaseKey, match);
            } else {
                state.lastCaseKey = null;
            }
        }

        if (elements.caseCount) {
            elements.caseCount.textContent = `${cases.length} Cases`;
        }

        elements.lastSync.textContent = `Updated ${timestamp.toLocaleTimeString()}`;
    } catch (error) {
        console.error("Dashboard load failed", error);
        elements.lastSync.textContent = `Sync failed ${timestamp.toLocaleTimeString()}`;
    } finally {
        if (elements.btnRefresh) {
            elements.btnRefresh.disabled = false;
            elements.btnRefresh.textContent = "Refresh";
        }
    }
}

function scheduleRefresh() {
    if (state.refreshTimer) {
        clearInterval(state.refreshTimer);
    }
    state.refreshTimer = setInterval(() => loadDashboard(false), REFRESH_INTERVAL);
}

function summarizeCases(cases) {
    const stats = {
        total: cases.length,
        active: 0,
        needsAttention: 0,
        closed: 0,
        byType: new Map(),
    };

    cases.forEach((caseItem) => {
        const status = (caseItem.status || "").toLowerCase();
        if (ACTIVE_STATUSES.has(status)) {
            stats.active += 1;
        }
        if (status === "closed" || status === "archived") {
            stats.closed += 1;
        }
        if ((caseItem.attention || "waiting") === "needs_attention") {
            stats.needsAttention += 1;
        }
        const key = caseItem.case_type || "Unclassified";
        stats.byType.set(key, (stats.byType.get(key) || 0) + 1);
    });

    return stats;
}

function renderStats(stats) {
    if (!elements.statChips) return;
    const items = [
        {
            label: "Total",
            value: stats.total,
            tone: "bg-white/10 text-slate-100",
            icon: iconLedger(),
        },
        {
            label: "Active",
            value: stats.active,
            tone: "bg-emeraldA/15 text-emerald-200",
            icon: iconPulse(),
        },
        {
            label: "Needs Attention",
            value: stats.needsAttention,
            tone: "bg-amber-500/15 text-amber-200",
            icon: iconAlert(),
        },
        {
            label: "Closed/Archived",
            value: stats.closed,
            tone: "bg-slate-600/20 text-slate-200",
            icon: iconArchive(),
        },
    ];

    const fragment = document.createDocumentFragment();
    items.forEach((item) => {
        const card = document.createElement("article");
        card.className = `flex flex-col gap-2 rounded-2xl border border-white/10 px-4 py-3 shadow-glass backdrop-blur ${item.tone}`;

        const label = document.createElement("p");
        label.className = "text-[11px] uppercase tracking-[0.3em] text-slate-200";
        label.textContent = item.label;

        const value = document.createElement("div");
        value.className = "flex items-baseline gap-2";
        value.innerHTML = `${item.icon}<span class="text-2xl font-semibold tabular">${item.value}</span>`;

        card.appendChild(label);
        card.appendChild(value);
        fragment.appendChild(card);
    });

    elements.statChips.replaceChildren(fragment);
}

function renderPractice(stats) {
    if (!elements.practiceList) return;
    const entries = Array.from(stats.byType.entries()).sort((a, b) => b[1] - a[1]);
    if (elements.practiceMeta) {
        elements.practiceMeta.textContent = entries.length
            ? `${entries.length} categories`
            : "No categories";
    }

    if (!entries.length) {
        const empty = document.createElement("p");
        empty.className = "py-6 text-sm text-slate-300";
        empty.textContent = "No practice mix recorded.";
        elements.practiceList.replaceChildren(empty);
        return;
    }

    const total = Math.max(stats.total, 1);
    const fragment = document.createDocumentFragment();

    entries.forEach(([label, count]) => {
        const wrapper = document.createElement("div");
        wrapper.className = "flex flex-col gap-2 py-2";

        const header = document.createElement("div");
        header.className = "flex items-center justify-between text-sm";
        const name = document.createElement("span");
        name.className = "font-medium text-slate-100";
        name.textContent = label;
        const meta = document.createElement("span");
        meta.className = "text-slate-300 tabular";
        const pct = Math.round((count / total) * 100);
        meta.textContent = `${count} • ${pct}%`;

        header.appendChild(name);
        header.appendChild(meta);

        const bar = document.createElement("div");
        bar.className = "h-1.5 w-full rounded-full bg-white/10";
        const fill = document.createElement("div");
        fill.className = "h-full rounded-full bg-gradient-to-r from-copper via-copper2 to-emeraldA";
        fill.style.width = `${Math.max(6, pct)}%`;
        bar.appendChild(fill);

        wrapper.appendChild(header);
        wrapper.appendChild(bar);
        fragment.appendChild(wrapper);
    });

    elements.practiceList.replaceChildren(fragment);
}

function computeDeadlines(cases) {
    const today = new Date();
    const entries = [];

    cases.forEach((caseItem) => {
        const relevant = Array.isArray(caseItem.deadlines)
            ? caseItem.deadlines.filter((item) => item && !item.resolved && item.due_date)
            : [];

        relevant.forEach((deadline) => {
            const due = new Date(`${deadline.due_date}T00:00:00`);
            if (Number.isNaN(due.getTime())) return;
            entries.push({ caseItem, deadline, due });
        });
    });

    entries.sort((a, b) => a.due - b.due);

    const upcoming = entries.slice(0, 6).map((entry) => {
        const diffMs = entry.due.getTime() - today.getTime();
        const diffDays = Math.round(diffMs / 86_400_000);
        const dueLabel = formatDate(entry.deadline.due_date);
        let badge = `In ${diffDays}d`;
        let tone = "border-white/10 text-slate-200";

        if (diffDays < 0) {
            badge = `${Math.abs(diffDays)}d late`;
            tone = "border-rose-400/40 text-rose-200";
        } else if (diffDays === 0) {
            badge = "Due today";
            tone = "border-amber-400/40 text-amber-200";
        } else if (diffDays <= 3) {
            tone = "border-orange-400/40 text-orange-200";
        }

        return {
            ...entry,
            diffDays,
            dueLabel,
            badge,
            tone,
        };
    });

    return {
        upcoming,
        total: entries.length,
    };
}

function renderDeadlines(deadlines) {
    if (!elements.deadlinesList) return;

    if (elements.deadlineMeta) {
        const count = deadlines.upcoming.length;
        elements.deadlineMeta.textContent = count ? `${count} of ${deadlines.total}` : "0 upcoming";
    }

    if (!deadlines.upcoming.length) {
        const empty = document.createElement("p");
        empty.className = "py-6 text-sm text-slate-300";
        empty.textContent = "No upcoming deadlines logged.";
        elements.deadlinesList.replaceChildren(empty);
        return;
    }

    const fragment = document.createDocumentFragment();
    deadlines.upcoming.forEach((entry) => {
        const card = document.createElement("article");
        card.className = `border-l-4 ${entry.tone} px-4 py-4`;

        const header = document.createElement("div");
        header.className = "flex items-start justify-between gap-4";

        const left = document.createElement("div");
        const title = document.createElement("p");
        title.className = "font-semibold text-slate-100";
        title.textContent = entry.caseItem.case_name || entry.caseItem.case_number || "—";
        const desc = document.createElement("p");
        desc.className = "text-xs text-slate-300";
        desc.textContent = entry.deadline.description || "—";
        left.appendChild(title);
        left.appendChild(desc);

        const right = document.createElement("div");
        right.className = "text-right";
        const badge = document.createElement("p");
        badge.className = "text-xs uppercase tracking-[0.25em] text-slate-200";
        badge.textContent = entry.badge;
        const due = document.createElement("p");
        due.className = "text-xs text-slate-400 tabular";
        due.textContent = entry.dueLabel;
        right.appendChild(badge);
        right.appendChild(due);

        header.appendChild(left);
        header.appendChild(right);
        card.appendChild(header);
        fragment.appendChild(card);
    });

    elements.deadlinesList.replaceChildren(fragment);
}

function renderCases(cases) {
    if (!elements.casesBody) return;
    const fragment = document.createDocumentFragment();

    cases.forEach((caseItem, index) => {
        const key = caseKey(caseItem, index);
        const row = document.createElement("tr");
        row.dataset.caseId = key;
        row.className = index % 2 === 0 ? "bg-white/5" : "bg-white/10";
        row.classList.add(
            "border-b",
            "border-white/5",
            "text-sm",
            "leading-5",
            "transition",
            "duration-200",
            "hover:bg-white/15",
            "hover:ring-1",
            "hover:ring-white/10",
        );

        row.appendChild(cellCaseNumber(caseItem));
        row.appendChild(cellCaseName(caseItem));
        row.appendChild(bodyCell(caseItem.case_type || "—"));
        row.appendChild(bodyCell(caseItem.stage || "—"));
        row.appendChild(cellAttention(caseItem.attention));
        row.appendChild(cellStatus(caseItem.status));
        row.appendChild(bodyCell(caseItem.paralegal || "—"));
        row.appendChild(cellFocus(caseItem.current_task));
        row.appendChild(cellNextDue(caseItem));
        row.appendChild(cellActions(key));

        fragment.appendChild(row);
    });

    elements.casesBody.replaceChildren(fragment);
}

function cellCaseNumber(caseItem) {
    const cell = document.createElement("td");
    cell.className = "sticky left-0 z-40 w-28 bg-ink2/90 px-4 py-3 font-semibold text-slate-100 tabular";
    cell.textContent = caseItem.case_number || "—";
    return cell;
}

function cellCaseName(caseItem) {
    const cell = document.createElement("td");
    cell.className = "sticky left-28 z-30 min-w-[240px] bg-ink2/80 px-4 py-3 font-medium text-slate-100";
    cell.textContent = caseItem.case_name || "—";
    return cell;
}

function bodyCell(value) {
    const cell = document.createElement("td");
    cell.className = "px-4 py-3 text-slate-200";
    cell.textContent = value || "—";
    return cell;
}

function cellFocus(value) {
    const cell = document.createElement("td");
    cell.className = "min-w-[260px] px-4 py-3 text-slate-200";
    const content = (value || "—").trim();
    cell.textContent = content.length > 140 ? `${content.slice(0, 137)}…` : content || "—";
    return cell;
}

function cellAttention(attention) {
    const cell = document.createElement("td");
    cell.className = "px-4 py-3";
    const badge = document.createElement("span");
    badge.className = "inline-flex items-center rounded-full px-3 py-1 text-xs uppercase tracking-[0.25em]";

    if (attention === "needs_attention") {
        badge.classList.add("bg-rose-500/15", "text-rose-200");
        badge.textContent = "Needs Attention";
    } else {
        badge.classList.add("bg-slate-500/20", "text-slate-200");
        badge.textContent = "Waiting";
    }

    cell.appendChild(badge);
    return cell;
}

function cellStatus(status) {
    const cell = document.createElement("td");
    cell.className = "px-4 py-3";
    const badge = document.createElement("span");
    badge.className = "inline-flex items-center rounded-full px-3 py-1 text-xs uppercase tracking-[0.25em]";
    const meta = STATUS_BADGES[(status || "").toLowerCase()] || {
        label: status || "—",
        tone: "bg-white/10 text-slate-200",
    };
    meta.tone.split(" ").forEach((cls) => badge.classList.add(cls));
    badge.textContent = meta.label;
    cell.appendChild(badge);
    return cell;
}

function cellNextDue(caseItem) {
    const cell = document.createElement("td");
    cell.className = "px-4 py-3 text-right text-slate-200 tabular";
    cell.textContent = formatNextDue(caseItem);
    return cell;
}

function cellActions(key) {
    const cell = document.createElement("td");
    cell.className = "px-4 py-3 text-right";
    const button = document.createElement("button");
    button.className = "rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs uppercase tracking-[0.3em] text-slate-200 hover:bg-white/20";
    button.textContent = "View";
    button.dataset.action = "open";
    button.dataset.caseId = key;
    cell.appendChild(button);
    return cell;
}

function formatNextDue(caseItem) {
    const deadlines = Array.isArray(caseItem.deadlines) ? caseItem.deadlines : [];
    const upcoming = deadlines
        .filter((item) => item && !item.resolved && item.due_date)
        .map((item) => ({ ...item, due: new Date(`${item.due_date}T00:00:00`) }))
        .filter((item) => !Number.isNaN(item.due.getTime()))
        .sort((a, b) => a.due - b.due);

    if (!upcoming.length) {
        return "—";
    }

    const next = upcoming[0];
    const today = new Date();
    const diffDays = Math.round((next.due.getTime() - today.getTime()) / 86_400_000);
    const label = formatDate(next.due_date);
    if (diffDays < 0) return `${label} (${Math.abs(diffDays)}d late)`;
    if (diffDays === 0) return `${label} (today)`;
    return `${label} (${diffDays}d)`;
}

function formatDate(value) {
    if (!value) return "—";
    const parsed = new Date(`${value}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return "—";
    return parsed.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

function updateSnapshotTime(savedAt, generatedAt) {
    if (!elements.lastSync) return;
    const source = savedAt || generatedAt;
    if (!source) {
        elements.lastSync.textContent = "Snapshot unavailable";
        return;
    }
    const parsed = new Date(source);
    if (Number.isNaN(parsed.getTime())) {
        elements.lastSync.textContent = "Snapshot unavailable";
        return;
    }
    elements.lastSync.textContent = `Snapshot ${parsed.toLocaleString()}`;
}

function handleGlobalClick(event) {
    const target = event.target;
    if (!(target instanceof HTMLElement)) return;

    if (target.dataset.action === "open") {
        const key = target.dataset.caseId || extractCaseId(target);
        if (!key) return;
        const match = findCase(key);
        if (match) {
            openDrawer(key, match);
        }
        return;
    }

    if (target.matches("#cases-body tr")) {
        const key = target.dataset.caseId;
        if (!key) return;
        const match = findCase(key);
        if (match) openDrawer(key, match);
    }
}

function handleKeydown(event) {
    if (event.key === "Escape" && elements.drawer && !elements.drawer.classList.contains("hidden")) {
        closeDrawer();
    }
}

function findCase(key) {
    return state.cases.find(
        (item) => item.id === key || item.case_number === key || caseKey(item) === key,
    );
}

function openDrawer(key, caseItem) {
    if (!elements.drawer) return;
    elements.drawer.classList.remove("hidden");
    elements.drawerNumber.textContent = caseItem.case_number || "—";
    elements.drawerName.textContent = caseItem.case_name || "—";
    elements.drawerType.textContent = caseItem.case_type || "—";
    elements.drawerStage.textContent = caseItem.stage || "—";
    elements.drawerStatus.textContent = caseItem.status || "—";
    elements.drawerParalegal.textContent = caseItem.paralegal || "—";
    elements.drawerFocus.textContent = caseItem.current_task || "—";
    elements.drawerNextDue.textContent = formatNextDue(caseItem);

    renderDrawerDeadlines(caseItem);
    updateDrawerLinks(caseItem);

    state.lastCaseKey = key;
    persistLastCase(key);
}

function renderDrawerDeadlines(caseItem) {
    if (!elements.drawerDeadlines) return;
    const deadlines = Array.isArray(caseItem.deadlines) ? caseItem.deadlines : [];

    if (!deadlines.length) {
        const empty = document.createElement("li");
        empty.className = "text-sm text-slate-300";
        empty.textContent = "No deadlines recorded.";
        elements.drawerDeadlines.replaceChildren(empty);
        return;
    }

    const fragment = document.createDocumentFragment();
    deadlines.forEach((deadline) => {
        const item = document.createElement("li");
        item.className = "rounded-lg border border-white/10 px-3 py-2 text-sm text-slate-200";
        const due = deadline.due_date ? formatDate(deadline.due_date) : "—";
        const resolved = deadline.resolved ? " • resolved" : "";
        item.textContent = `${due} • ${deadline.description || "No description"}${resolved}`;
        fragment.appendChild(item);
    });
    elements.drawerDeadlines.replaceChildren(fragment);
}

function closeDrawer() {
    if (!elements.drawer) return;
    elements.drawer.classList.add("hidden");
    state.lastCaseKey = null;
    try {
        localStorage.removeItem(STORAGE_KEYS.LAST_CASE);
    } catch (error) {
        console.warn("Unable to remove last case", error);
    }
}

function copyCaseId() {
    const match = findCase(state.lastCaseKey);
    if (!match) return;
    navigator.clipboard?.writeText(match.id || match.case_number).catch(console.error);
}

function downloadCaseJson() {
    const match = findCase(state.lastCaseKey);
    if (!match) return;
    const blob = new Blob([JSON.stringify(match, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${match.case_number || "case"}.json`;
    a.click();
    URL.revokeObjectURL(url);
}

function toggleKioskMode() {
    state.kiosk = !state.kiosk;
    applyKioskMode(state.kiosk);
    try {
        localStorage.setItem(STORAGE_KEYS.KIOSK, state.kiosk ? "1" : "0");
    } catch (error) {
        console.warn("Unable to save kiosk mode", error);
    }
}

function applyKioskMode(enabled) {
    if (enabled) {
        document.documentElement.requestFullscreen?.();
    } else if (document.fullscreenElement) {
        document.exitFullscreen?.();
    }
}

function togglePiP(show) {
    const newVisible = show !== undefined ? show : !state.pipVisible;
    state.pipVisible = newVisible;
    applyPipVisibility(newVisible);
    savePipPreferences();
}

function applyPipVisibility(visible) {
    if (!elements.pip) return;
    if (visible) {
        elements.pip.classList.remove("hidden");
    } else {
        elements.pip.classList.add("hidden");
    }
    if (elements.btnPiP) {
        elements.btnPiP.setAttribute("aria-pressed", String(visible));
    }
}

function setPipSize(size) {
    if (!Object.hasOwn(PIP_SIZES, size)) return;
    state.pipSize = size;
    applyPipSize(size);
    savePipPreferences();
}

function applyPipSize(size) {
    const iframe = elements.pipFrame?.querySelector("iframe");
    if (!iframe) return;
    Object.values(PIP_SIZES).flat().forEach((cls) => iframe.classList.remove(cls));
    (PIP_SIZES[size] || PIP_SIZES.md).forEach((cls) => iframe.classList.add(cls));
}

function savePipPreferences() {
    try {
        localStorage.setItem(STORAGE_KEYS.PIP, JSON.stringify({ size: state.pipSize, visible: state.pipVisible }));
    } catch (error) {
        console.warn("Unable to save PiP preferences", error);
    }
}

function startDrag(event) {
    if (!elements.pip) return;
    state.dragStart = {
        x: event.clientX,
        y: event.clientY,
        rect: elements.pip.getBoundingClientRect(),
    };
    elements.pipFrame?.setPointerCapture(event.pointerId);
}

function dragPiP(event) {
    if (!state.dragStart || !elements.pip) return;
    const dx = event.clientX - state.dragStart.x;
    const dy = event.clientY - state.dragStart.y;
    elements.pip.style.right = "auto";
    elements.pip.style.bottom = "auto";
    elements.pip.style.left = `${state.dragStart.rect.left + dx}px`;
    elements.pip.style.top = `${state.dragStart.rect.top + dy}px`;
}

function endDrag() {
    state.dragStart = null;
}

function caseKey(caseItem, index) {
    return `${caseItem.case_number || index}-${caseItem.id || index}`;
}

function iconLedger() {
    return '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>';
}

function iconPulse() {
    return '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>';
}

function iconAlert() {
    return '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>';
}

function iconArchive() {
    return '<svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>';
}
