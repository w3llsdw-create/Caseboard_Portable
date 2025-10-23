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
    alert: "bg-amber-500/20 text-amber-300",
    wait: "bg-slate-500/20 text-slate-300",
    neutral: "bg-white/10 text-slate-200",
};

const ATTENTION_LABELS = {
    waiting: "Waiting",
    needs_attention: "Needs Attention",
};

const STATUS_DETAILS = {
    open: { label: "Active", tone: "active" },
    filed: { label: "Filed", tone: "active" },
    "pre-filing": { label: "Pre-Filing", tone: "wait" },
    closed: { label: "Closed", tone: "neutral" },
};

const COLUMN_DEFS = [
    {
        id: "case_number",
        createCell: (item) => {
            const td = document.createElement("td");
            td.className = "sticky left-0 z-30 w-32 px-4 py-2 md:px-5 font-semibold text-slate-100 tabular-nums bg-midnight/80 backdrop-blur";
            td.textContent = item.case_number || "—";
            return td;
        /* globals localStorage navigator */

                currentCases = payload.cases || [];
                const stats = summarize(currentCases);
                const deadlines = rankDeadlines(currentCases);

                renderStats(stats);
                renderPractice(stats);
                renderDeadlines(deadlines);
                renderCases(currentCases);

                if (payload.meta?.saved_at) {
                    const snap = new Date(payload.meta.saved_at);
                    lastSync.textContent = `Snapshot ${snap.toLocaleString()}`;
                } else {
                    lastSync.textContent = `Updated ${timestamp.toLocaleTimeString()}`;
                }

                const remembered = localStorage.getItem(STORAGE_KEYS.LAST_VIEW);
                if (remembered && currentCases.some((c) => c.case_number === remembered)) {
                    openDrawer(remembered);
                }
            } catch (error) {
                console.error("Dashboard load failed", error);
                lastSync.textContent = `Sync failed ${timestamp.toLocaleTimeString()}`;
            } finally {
                if (manual) btnRefresh.disabled = false;
            }
        }

        function scheduleRefresh() {
            if (refreshTimer) clearInterval(refreshTimer);
            refreshTimer = setInterval(() => loadDashboard(false), REFRESH_INTERVAL);
        }

        document.addEventListener("click", (event) => {
            const target = event.target;
            if (!(target instanceof HTMLElement)) return;
            if (target.dataset.action === "open") {
                const row = target.closest("tr");
                if (!row) return;
                openDrawer(row.dataset.caseId || "");
            }
        });

        drawerClose.addEventListener("click", () => {
            closeDrawer();
            localStorage.removeItem(STORAGE_KEYS.LAST_VIEW);
        });

        btnRefresh.addEventListener("click", () => loadDashboard(true));
        btnKiosk.addEventListener("click", () => setKioskMode(!kioskMode));
        btnPip.addEventListener("click", () => togglePiP());
        pipHide.addEventListener("click", () => togglePiP(false));
        pipSizeButtons.forEach((button) => button.addEventListener("click", () => persistPiP(button.dataset.size)));

        let dragStart = null;
        pipFrame.addEventListener("pointerdown", (event) => {
            dragStart = {
                x: event.clientX,
                y: event.clientY,
                rect: pip.getBoundingClientRect(),
            };
            pipFrame.setPointerCapture(event.pointerId);
        });

        pipFrame.addEventListener("pointermove", (event) => {
            if (!dragStart) return;
            const dx = event.clientX - dragStart.x;
            const dy = event.clientY - dragStart.y;
            pip.style.right = "auto";
            pip.style.bottom = "auto";
            pip.style.left = `${dragStart.rect.left + dx}px`;
            pip.style.top = `${dragStart.rect.top + dy}px`;
        });

        pipFrame.addEventListener("pointerup", () => {
            dragStart = null;
        });

        document.addEventListener("keydown", (event) => {
            if (event.key === "Escape" && !drawer.classList.contains("hidden")) {
                closeDrawer();
            }
        });

        restorePiP();
        loadDashboard(false);
        scheduleRefresh();
        container.appendChild(textWrap);
        elements.chips.appendChild(container);
    });
}

function renderPracticeMix(stats) {
    elements.practice.replaceChildren();
    const entries = Array.from(stats.byType.entries()).sort((a, b) => b[1] - a[1]);
    if (elements.practiceMeta) {
        elements.practiceMeta.textContent = `${entries.length} categories`;
    }

    const total = Math.max(stats.total, 1);

    entries.forEach(([label, count]) => {
        const wrapper = document.createElement("div");
        wrapper.className = "flex flex-col gap-1 py-2";

        const header = document.createElement("div");
        header.className = "flex items-center justify-between text-sm";
        const name = document.createElement("span");
        name.className = "font-medium text-slate-100";
        name.textContent = label;
        const meta = document.createElement("span");
        meta.className = "text-slate-300 tabular-nums";
        const pct = Math.round((count / total) * 100);
        meta.textContent = `${count} • ${pct}%`;

        header.appendChild(name);
        header.appendChild(meta);

        const bar = document.createElement("div");
        bar.className = "h-1.5 w-full rounded-full bg-white/10";
        const fill = document.createElement("div");
        fill.className = "h-full rounded-full bg-gradient-to-r from-indigo-400 to-sky-400";
        fill.style.width = `${Math.max(6, pct)}%`;
        bar.appendChild(fill);

        wrapper.appendChild(header);
        wrapper.appendChild(bar);
        elements.practice.appendChild(wrapper);
    });

    if (entries.length === 0) {
        const empty = document.createElement("p");
        empty.className = "py-4 text-sm text-slate-300";
        empty.textContent = "No practice mix recorded.";
        elements.practice.appendChild(empty);
    }
}

function computeDeadlines(cases) {
    const today = new Date();
    const items = [];

    cases.forEach((caseItem) => {
        const relevant = (caseItem.deadlines || []).filter(
            (deadline) => deadline && !deadline.resolved && deadline.due_date,
        );

        relevant.forEach((deadline) => {
            const due = new Date(`${deadline.due_date}T00:00:00`);
            if (Number.isNaN(due.getTime())) return;
            items.push({ caseItem, deadline, due });
        });
    });

    items.sort((a, b) => a.due - b.due);
    const upcoming = items.slice(0, 6).map((entry) => {
        const diffDays = Math.round((entry.due - today) / 86_400_000);
        let tone = "border-white/10 text-slate-200";
        if (diffDays < 0) tone = "border-rose-400/40 text-rose-200";
        else if (diffDays === 0) tone = "border-amber-400/40 text-amber-200";
        else if (diffDays <= 3) tone = "border-orange-400/40 text-orange-200";

        return {
            ...entry,
            diffDays,
            dueLabel: formatDate(entry.deadline.due_date),
            badge: diffDays < 0 ? `${Math.abs(diffDays)}d late` : diffDays === 0 ? "Due today" : `In ${diffDays}d`,
            tone,
        };
    });

    return { upcoming, total: items.length };
}

function renderDeadlines(deadlines) {
    elements.deadlines.replaceChildren();

    if (!deadlines.upcoming.length) {
        const empty = document.createElement("p");
        empty.className = "py-6 text-sm text-slate-300";
        empty.textContent = "No upcoming deadlines logged.";
        elements.deadlines.appendChild(empty);
        if (elements.deadlineMeta) {
            elements.deadlineMeta.textContent = "0 upcoming";
        }
        return;
    }

    if (elements.deadlineMeta) {
        elements.deadlineMeta.textContent = `${deadlines.upcoming.length} of ${deadlines.total}`;
    }

    deadlines.upcoming.forEach((entry) => {
        const card = document.createElement("article");
        card.className = `border-l-4 ${entry.tone} px-3 py-3 md:px-4 md:py-4`;

        const header = document.createElement("div");
        header.className = "flex items-start justify-between gap-3";

        const left = document.createElement("div");
        const caseName = document.createElement("p");
        caseName.className = "font-semibold text-slate-100";
        caseName.textContent = entry.caseItem.case_name || entry.caseItem.case_number || "—";
        const desc = document.createElement("p");
        desc.className = "text-xs text-slate-300";
        desc.textContent = entry.deadline.description || "—";

        left.appendChild(caseName);
        left.appendChild(desc);

        const right = document.createElement("div");
        right.className = "text-right";
        const badge = document.createElement("p");
        badge.className = "text-xs uppercase tracking-[0.25em] text-slate-200";
        badge.textContent = entry.badge;
        const dueDate = document.createElement("p");
        dueDate.className = "text-xs text-slate-400 tabular-nums";
        dueDate.textContent = entry.dueLabel;

        right.appendChild(badge);
        right.appendChild(dueDate);

        header.appendChild(left);
        header.appendChild(right);
        card.appendChild(header);
        elements.deadlines.appendChild(card);
    });
}

function renderCases(cases) {
    const tbody = elements.casesBody;
    const existing = new Map();
    Array.from(tbody.children).forEach((row) => {
        if (row instanceof HTMLTableRowElement) {
            existing.set(row.dataset.caseId || "", row);
        }
    });

    const fragment = document.createDocumentFragment();

    cases.forEach((item, index) => {
        const key = item.id || item.case_number || `case-${index}`;
        const row = existing.get(key);
        if (row) {
            updateRow(row, item, index);
            existing.delete(key);
            fragment.appendChild(row);
        } else {
            fragment.appendChild(buildRow(item, index, key));
        }
    });

    existing.forEach((row) => row.remove());
    tbody.appendChild(fragment);
    if (elements.caseCount) {
        elements.caseCount.textContent = `${cases.length} Cases`;
    }
}

function buildRow(item, index, key) {
    const row = document.createElement("tr");
    row.dataset.caseId = key;
    applyRowStyling(row, index);

    COLUMN_DEFS.forEach((column) => {
        row.appendChild(column.createCell(item));
    });

    row.classList.add("transition-colors", "hover:ring-1", "hover:ring-white/10");
    return row;
}

function updateRow(row, item, index) {
    row.dataset.caseId = item.id || row.dataset.caseId;
    applyRowStyling(row, index);

    COLUMN_DEFS.forEach((column, columnIndex) => {
        const cell = row.children[columnIndex];
        if (cell) column.updateCell(cell, item);
    });
}

function applyRowStyling(row, index) {
    row.className = "border-b border-white/5 text-sm leading-5 transition-colors hover:bg-white/10 hover:ring-1 hover:ring-white/10";
    row.classList.remove("bg-white/5", "bg-white/10");
    row.classList.add(index % 2 === 0 ? "bg-white/5" : "bg-white/10");
}

function createAttentionBadge(attention) {
    const badge = document.createElement("span");
    badge.className = "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs uppercase tracking-[0.25em]";

    if (attention === "needs_attention") {
        badge.className += ` ${BADGE_TONES.alert}`;
        badge.textContent = ATTENTION_LABELS.needs_attention;
    } else {
        badge.className += ` ${BADGE_TONES.wait}`;
        badge.textContent = ATTENTION_LABELS.waiting;
    }

    return badge;
}

function createStatusBadge(status) {
    const badge = document.createElement("span");
    badge.className = "inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs uppercase tracking-[0.25em]";

    const details = STATUS_DETAILS[status] || { label: status || "—", tone: "neutral" };
    badge.className += ` ${BADGE_TONES[details.tone] || BADGE_TONES.neutral}`;
    badge.textContent = details.label || "—";

    return badge;
}

function formatNextDue(caseItem) {
    const deadlines = (caseItem.deadlines || []).filter((deadline) => deadline && !deadline.resolved && deadline.due_date);
    if (!deadlines.length) return "—";

    const sorted = deadlines
        .map((deadline) => ({ ...deadline, due: new Date(`${deadline.due_date}T00:00:00`) }))
        .filter((deadline) => !Number.isNaN(deadline.due.getTime()))
        .sort((a, b) => a.due - b.due);

    if (!sorted.length) return "—";

    const next = sorted[0];
    const today = new Date();
    const diffDays = Math.round((next.due - today) / 86_400_000);
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
    elements.lastSync.textContent = `Snapshot: ${parsed.toLocaleString()}`;
}

function totalIcon() {
    return '<svg viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path d="M4 4h12v2H4V4zm0 5h12v2H4V9zm0 5h12v2H4v-2z" /></svg>';
}

function pulseIcon() {
    return '<svg viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path d="M3 11h3l1.5-5 3 10 2-6H17" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>';
}

function alertIcon() {
    return '<svg viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path d="M9.401 3.173a1 1 0 011.198 0l6.4 4.8A1 1 0 0116.4 10H3.6a1 1 0 01-.599-2l6.4-4.8zM10 11a1 1 0 100 2 1 1 0 000-2z" /></svg>';
}

function archiveIcon() {
    return '<svg viewBox="0 0 20 20" fill="currentColor" class="h-4 w-4"><path d="M4 4h12a1 1 0 011 1v2H3V5a1 1 0 011-1zm-1 5h14v6a1 1 0 01-1 1H4a1 1 0 01-1-1V9zm4 2v2h6v-2H7z" /></svg>';
}

function restorePipPreferences() {
    try {
        const stored = localStorage.getItem(PIP_STORAGE_KEY);
        if (!stored) return;
        const parsed = JSON.parse(stored);
        if (parsed && typeof parsed === "object") {
            if (parsed.size && ["sm", "md", "lg"].includes(parsed.size)) {
                state.pipSize = parsed.size;
            }
            if (typeof parsed.visible === "boolean") {
                state.pipVisible = parsed.visible;
            }
        }
    } catch (error) {
        console.warn("Failed to restore PiP settings", error);
    }
}

function persistPipPreferences() {
    const payload = {
        size: state.pipSize,
        visible: state.pipVisible,
    };
    try {
        localStorage.setItem(PIP_STORAGE_KEY, JSON.stringify(payload));
    } catch (error) {
        console.warn("Unable to persist PiP settings", error);
    }
}

function applyPipSize(size) {
    const iframe = elements.pipFrame?.querySelector("iframe");
    if (!iframe) return;
    const sizes = {
        sm: ["w-[300px]", "h-[169px]"],
        md: ["w-[380px]", "h-[214px]"],
        lg: ["w-[480px]", "h-[270px]"],
    };
    Object.values(sizes).flat().forEach((cls) => iframe.classList.remove(cls));
    (sizes[size] || sizes.md).forEach((cls) => iframe.classList.add(cls));
}

function setPipSize(size) {
    state.pipSize = size;
    applyPipSize(size);
    persistPipPreferences();
}

function applyPipVisibility(isVisible) {
    if (!elements.pipFrame) return;
    if (isVisible) {
        elements.pipFrame.classList.remove("hidden");
        if (elements.pipToggle) elements.pipToggle.textContent = "Hide";
    } else {
        elements.pipFrame.classList.add("hidden");
        if (elements.pipToggle) elements.pipToggle.textContent = "Show";
    }
    if (elements.pipToggle) {
        elements.pipToggle.setAttribute("aria-pressed", String(!isVisible));
    }
}

function togglePipVisibility() {
    state.pipVisible = !state.pipVisible;
    applyPipVisibility(state.pipVisible);
    persistPipPreferences();
}

loadDashboard(false);
setInterval(() => loadDashboard(false), REFRESH_INTERVAL);
