// TV Display - Autonomous, passive case monitoring dashboard
// No user interaction - designed for 55" TV display from ~10 ft

const API_URL = "/cases";
const REFRESH_INTERVAL = 60_000; // 60 seconds
const NO_DATA_RELOAD_THRESHOLD = 5 * 60 * 1000; // 5 minutes
const FRESHNESS_AMBER_THRESHOLD = 90_000; // 90 seconds
const FRESHNESS_RED_THRESHOLD = 180_000; // 3 minutes

const elements = {
  clock: document.getElementById("clock"),
  liveIndicator: document.getElementById("live-indicator"),
  liveDot: document.getElementById("live-dot"),
  liveLabel: document.getElementById("live-label"),
  caseCount: document.getElementById("case-count"),
  casesTbody: document.getElementById("cases-tbody"),
  deadlinesContainer: document.getElementById("deadlines-container"),
  deadlineCount: document.getElementById("deadline-count"),
};

const state = {
  cases: [],
  lastSuccessfulFetch: null,
  isFetching: false,
  refreshTimer: null,
  clockTimer: null,
};

// Initialize
init();

function init() {
  startClock();
  loadCases();
  scheduleRefresh();
  scheduleNoDataCheck();
}

// === Clock Management ===

function startClock() {
  updateClock();
  state.clockTimer = setInterval(updateClock, 1000);
}

function updateClock() {
  if (!elements.clock) return;
  const now = new Date();
  const hours = now.getHours();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  const ampm = hours >= 12 ? "PM" : "AM";
  const displayHours = hours % 12 || 12;
  
  elements.clock.textContent = 
    `${String(displayHours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")} ${ampm}`;
  
  updateFreshnessIndicator();
}

function updateFreshnessIndicator() {
  if (!state.lastSuccessfulFetch || !elements.liveIndicator || !elements.liveDot || !elements.liveLabel) return;
  
  const elapsed = Date.now() - state.lastSuccessfulFetch;
  
  if (elapsed < FRESHNESS_AMBER_THRESHOLD) {
    // Green - fresh data
    elements.liveIndicator.style.background = "rgba(52, 211, 153, 0.1)";
    elements.liveIndicator.style.borderColor = "rgba(52, 211, 153, 0.3)";
    elements.liveDot.style.background = "var(--color-emerald)";
    elements.liveLabel.textContent = "Live";
  } else if (elapsed < FRESHNESS_RED_THRESHOLD) {
    // Amber - aging data
    elements.liveIndicator.style.background = "rgba(251, 191, 36, 0.1)";
    elements.liveIndicator.style.borderColor = "rgba(251, 191, 36, 0.3)";
    elements.liveDot.style.background = "var(--color-amber)";
    elements.liveLabel.textContent = "Aging";
  } else {
    // Red - stale data
    elements.liveIndicator.style.background = "rgba(255, 107, 107, 0.1)";
    elements.liveIndicator.style.borderColor = "rgba(255, 107, 107, 0.3)";
    elements.liveDot.style.background = "var(--color-rose)";
    elements.liveLabel.textContent = "Stale";
  }
}

// === Data Loading ===

async function loadCases() {
  // Guard against overlapping fetches
  if (state.isFetching) {
    console.warn("Fetch already in progress, skipping...");
    return;
  }
  
  state.isFetching = true;
  
  try {
    const response = await fetch(API_URL, { cache: "no-cache" });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const data = await response.json();
    const cases = Array.isArray(data.cases) ? data.cases : [];
    
    state.cases = cases;
    state.lastSuccessfulFetch = Date.now();
    
    renderCases(cases);
    renderDeadlines(cases);
    updateCaseCount(cases.length);
    
  } catch (error) {
    console.error("Failed to load cases:", error);
  } finally {
    state.isFetching = false;
  }
}

function scheduleRefresh() {
  if (state.refreshTimer) {
    clearInterval(state.refreshTimer);
  }
  state.refreshTimer = setInterval(() => {
    loadCases();
  }, REFRESH_INTERVAL);
}

function scheduleNoDataCheck() {
  // Check every minute if we need to reload due to no data
  setInterval(() => {
    if (!state.lastSuccessfulFetch) return;
    
    const elapsed = Date.now() - state.lastSuccessfulFetch;
    if (elapsed > NO_DATA_RELOAD_THRESHOLD) {
      console.warn("No successful data fetch for >5 minutes, reloading page...");
      window.location.reload();
    }
  }, 60_000);
}

// === Rendering ===

function updateCaseCount(count) {
  if (!elements.caseCount) return;
  elements.caseCount.textContent = `${count} ${count === 1 ? "Case" : "Cases"}`;
}

function renderCases(cases) {
  if (!elements.casesTbody) return;
  
  const fragment = document.createDocumentFragment();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  cases.forEach((caseItem, index) => {
    const row = createCaseRow(caseItem, index, today);
    fragment.appendChild(row);
  });
  
  elements.casesTbody.replaceChildren(fragment);
}

function createCaseRow(caseItem, index, today) {
  const row = document.createElement("tr");
  
  // Determine urgency state based on next deadline
  const { urgencyState, accentColor } = getUrgencyState(caseItem, today);
  
  // Add pulse animation for overdue items
  if (urgencyState === "overdue") {
    row.classList.add("overdue-pulse");
  }
  
  // Accent bar
  const accentBar = document.createElement("div");
  accentBar.className = `accent-bar ${accentColor}`;
  row.appendChild(accentBar);
  
  // Case Number (sticky)
  const caseNumCell = document.createElement("td");
  caseNumCell.className = "sticky-col tabular";
  caseNumCell.textContent = caseItem.case_number || "—";
  row.appendChild(caseNumCell);
  
  // Case Name
  const nameCell = document.createElement("td");
  nameCell.className = "case-name";
  nameCell.textContent = caseItem.case_name || "—";
  row.appendChild(nameCell);
  
  // Type
  const typeCell = document.createElement("td");
  typeCell.textContent = caseItem.case_type || "—";
  row.appendChild(typeCell);
  
  // Stage
  const stageCell = document.createElement("td");
  stageCell.textContent = caseItem.stage || "—";
  row.appendChild(stageCell);
  
  // Status badge
  const statusCell = document.createElement("td");
  const statusBadge = createStatusBadge(caseItem.status);
  statusCell.appendChild(statusBadge);
  row.appendChild(statusCell);
  
  // Paralegal
  const paralegalCell = document.createElement("td");
  paralegalCell.textContent = caseItem.paralegal || "—";
  row.appendChild(paralegalCell);
  
  // Current Focus
  const focusCell = document.createElement("td");
  const focus = caseItem.current_task || "—";
  focusCell.textContent = focus.length > 120 ? focus.slice(0, 117) + "..." : focus;
  row.appendChild(focusCell);
  
  // Next Due
  const dueCell = document.createElement("td");
  dueCell.style.textAlign = "right";
  dueCell.className = "tabular";
  dueCell.innerHTML = formatNextDue(caseItem, today);
  row.appendChild(dueCell);
  
  return row;
}

function getUrgencyState(caseItem, today) {
  const nextDeadline = getNextDeadline(caseItem, today);
  
  if (!nextDeadline) {
    return {
      urgencyState: "none",
      accentColor: "bg-slate-600/30",
    };
  }
  
  const dueDate = new Date(nextDeadline.due_date + "T00:00:00");
  const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
  
  if (diffDays < 0) {
    return {
      urgencyState: "overdue",
      accentColor: "bg-rose",
    };
  } else if (diffDays === 0) {
    return {
      urgencyState: "today",
      accentColor: "bg-amber",
    };
  } else if (diffDays <= 3) {
    return {
      urgencyState: "soon",
      accentColor: "bg-orange",
    };
  } else if (caseItem.attention === "needs_attention") {
    return {
      urgencyState: "attention",
      accentColor: "bg-copper",
    };
  }
  
  return {
    urgencyState: "normal",
    accentColor: "bg-slate-600/30",
  };
}

function createStatusBadge(status) {
  const badge = document.createElement("span");
  badge.className = "badge";
  
  const statusLower = (status || "").toLowerCase();
  
  switch (statusLower) {
    case "open":
    case "filed":
      badge.classList.add("bg-emerald-low");
      badge.textContent = statusLower === "open" ? "Active" : "Filed";
      break;
    case "pre-filing":
      badge.classList.add("bg-slate-low");
      badge.textContent = "Pre-Filing";
      break;
    case "closed":
    case "archived":
      badge.classList.add("bg-slate-lower");
      badge.textContent = statusLower === "closed" ? "Closed" : "Archived";
      break;
    default:
      badge.classList.add("bg-slate-low");
      badge.textContent = status || "—";
  }
  
  return badge;
}

function getNextDeadline(caseItem, today) {
  if (!Array.isArray(caseItem.deadlines)) return null;
  
  const upcoming = caseItem.deadlines
    .filter(d => d && !d.resolved && d.due_date)
    .map(d => ({
      ...d,
      dueDate: new Date(d.due_date + "T00:00:00"),
    }))
    .filter(d => !isNaN(d.dueDate.getTime()))
    .sort((a, b) => a.dueDate - b.dueDate);
  
  return upcoming.length > 0 ? upcoming[0] : null;
}

function formatNextDue(caseItem, today) {
  const nextDeadline = getNextDeadline(caseItem, today);
  
  if (!nextDeadline) {
    return '<span class="text-slate-500">—</span>';
  }
  
  const dueDate = nextDeadline.dueDate;
  const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
  const dateStr = formatDate(nextDeadline.due_date);
  
  let color = "text-slate-300";
  let suffix = "";
  
  if (diffDays < 0) {
    color = "text-rose-400";
    suffix = ` (${Math.abs(diffDays)}d late)`;
  } else if (diffDays === 0) {
    color = "text-amber-400";
    suffix = " (today)";
  } else if (diffDays <= 3) {
    color = "text-orange-400";
    suffix = ` (${diffDays}d)`;
  } else {
    suffix = ` (${diffDays}d)`;
  }
  
  return `<span class="${color}">${dateStr}${suffix}</span>`;
}

function formatDate(dateStr) {
  if (!dateStr) return "—";
  
  const date = new Date(dateStr + "T00:00:00");
  if (isNaN(date.getTime())) return "—";
  
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function renderDeadlines(cases) {
  if (!elements.deadlinesContainer) return;
  
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  
  // Collect all unresolved deadlines
  const allDeadlines = [];
  
  cases.forEach(caseItem => {
    if (!Array.isArray(caseItem.deadlines)) return;
    
    caseItem.deadlines
      .filter(d => d && !d.resolved && d.due_date)
      .forEach(deadline => {
        const dueDate = new Date(deadline.due_date + "T00:00:00");
        if (isNaN(dueDate.getTime())) return;
        
        const diffDays = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));
        
        allDeadlines.push({
          caseItem,
          deadline,
          dueDate,
          diffDays,
        });
      });
  });
  
  // Sort by due date
  allDeadlines.sort((a, b) => a.dueDate - b.dueDate);
  
  // Take top 10
  const topDeadlines = allDeadlines.slice(0, 10);
  
  if (!elements.deadlineCount) return;
  elements.deadlineCount.textContent = `${topDeadlines.length}`;
  
  if (topDeadlines.length === 0) {
    const empty = document.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "No upcoming deadlines";
    elements.deadlinesContainer.replaceChildren(empty);
    return;
  }
  
  const fragment = document.createDocumentFragment();
  
  topDeadlines.forEach(({ caseItem, deadline, dueDate, diffDays }) => {
    const card = createDeadlineCard(caseItem, deadline, diffDays);
    fragment.appendChild(card);
  });
  
  elements.deadlinesContainer.replaceChildren(fragment);
}

function createDeadlineCard(caseItem, deadline, diffDays) {
  const card = document.createElement("article");
  card.className = "deadline-card";
  
  // Add shimmer for due-today items
  if (diffDays === 0) {
    card.classList.add("due-today-shimmer");
  }
  
  // Case name
  const caseName = document.createElement("h3");
  caseName.className = "deadline-case-name";
  caseName.textContent = caseItem.case_name || caseItem.case_number || "—";
  card.appendChild(caseName);
  
  // Deadline description
  const desc = document.createElement("p");
  desc.className = "deadline-desc";
  desc.textContent = deadline.description || "No description";
  card.appendChild(desc);
  
  // Date and urgency
  const meta = document.createElement("div");
  meta.className = "deadline-meta";
  
  const date = document.createElement("span");
  date.className = "tabular deadline-date";
  date.textContent = formatDate(deadline.due_date);
  
  const urgency = document.createElement("span");
  urgency.className = "badge";
  
  if (diffDays < 0) {
    urgency.classList.add("bg-rose-low");
    urgency.textContent = `${Math.abs(diffDays)}d Late`;
  } else if (diffDays === 0) {
    urgency.classList.add("bg-amber-low");
    urgency.textContent = "Due Today";
  } else if (diffDays <= 3) {
    urgency.classList.add("bg-orange-low");
    urgency.textContent = `${diffDays}d`;
  } else {
    urgency.classList.add("bg-slate-low");
    urgency.textContent = `${diffDays}d`;
  }
  
  meta.appendChild(date);
  meta.appendChild(urgency);
  card.appendChild(meta);
  
  return card;
}
