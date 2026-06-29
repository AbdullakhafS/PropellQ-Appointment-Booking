const state = {
  filters: {
    dateFrom: "",
    dateTo: "",
    timeOfDay: "",
    provider: "",
    specialty: "",
    sortBy: "date",
    sortDir: "asc",
  },
  results: {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 1,
    items: [],
    latestLatencyMs: 0,
    metrics: null,
  },
  calendar: {
    view: window.innerWidth < 768 ? "week" : "month",
    anchorDate: new Date().toISOString().slice(0, 10),
    touchStartX: 0,
  },
  selectedSlot: null,
  reservationToken: "",
  reservationExpiresAt: "",
  reservationTimerId: null,
  suggestions: [],
  integrations: {
    google: { connected: false, status: "revoked" },
    outlook: { connected: false, status: "revoked" },
  },
  clinical: {
    patientId: 1,
    profile: null,
    conflicts: [],
    activeTab: "overview",
  },
  coding: {
    patientId: 1,
    suggestions: [],
    allergyConflicts: [],
    conflictQueue: [],
    thresholds: { icd10: 0.70, cpt: 0.75 },
    activeTab: "suggestions",
  },
  // EP-005: RBAC
  rbac: {
    role: "patient",
    permissions: [],
    adminId: "admin-demo",
  },
  // EP-005 US-047: Admin user management
  adminUsers: {
    users: [],
    filter: { query: "", role: "", status: "" },
  },
};

const elements = {
  form: document.getElementById("searchFilters"),
  dateFrom: document.getElementById("dateFrom"),
  dateTo: document.getElementById("dateTo"),
  timeOfDay: document.getElementById("timeOfDay"),
  provider: document.getElementById("provider"),
  providerSuggestions: document.getElementById("providerSuggestions"),
  specialty: document.getElementById("specialty"),
  sortBy: document.getElementById("sortBy"),
  sortDir: document.getElementById("sortDir"),
  filterSummary: document.getElementById("filterSummary"),
  clearFiltersButton: document.getElementById("clearFiltersButton"),
  resultsSummary: document.getElementById("resultsSummary"),
  searchMetricsSummary: document.getElementById("searchMetricsSummary"),
  searchResults: document.getElementById("searchResults"),
  searchEmptyState: document.getElementById("searchEmptyState"),
  previousPageButton: document.getElementById("previousPageButton"),
  nextPageButton: document.getElementById("nextPageButton"),
  paginationLabel: document.getElementById("paginationLabel"),
  expandDateRangeButton: document.getElementById("expandDateRangeButton"),
  clearEmptyStateFiltersButton: document.getElementById("clearEmptyStateFiltersButton"),
  calendarGrid: document.getElementById("calendarGrid"),
  calendarRangeLabel: document.getElementById("calendarRangeLabel"),
  timezoneLabel: document.getElementById("timezoneLabel"),
  calendarFootnote: document.getElementById("calendarFootnote"),
  monthViewButton: document.getElementById("monthViewButton"),
  weekViewButton: document.getElementById("weekViewButton"),
  previousRangeButton: document.getElementById("previousRangeButton"),
  nextRangeButton: document.getElementById("nextRangeButton"),
  selectedSlotDetails: document.getElementById("selectedSlotDetails"),
  bookingSummary: document.getElementById("bookingSummary"),
  checkoutForm: document.getElementById("checkoutForm"),
  reserveSlotButton: document.getElementById("reserveSlotButton"),
  bookNowButton: document.getElementById("bookNowButton"),
  reservationCountdown: document.getElementById("reservationCountdown"),
  checkoutStatusMessage: document.getElementById("checkoutStatusMessage"),
  preferredSlotId: document.getElementById("preferredSlotId"),
  providerDialog: document.getElementById("providerDialog"),
  providerDialogBody: document.getElementById("providerDialogBody"),
  googleBadge: document.getElementById("googleIntegrationBadge"),
  outlookBadge: document.getElementById("outlookIntegrationBadge"),
  connectGoogleButton: document.getElementById("connectGoogleButton"),
  disconnectGoogleButton: document.getElementById("disconnectGoogleButton"),
  connectOutlookButton: document.getElementById("connectOutlookButton"),
  disconnectOutlookButton: document.getElementById("disconnectOutlookButton"),
  integrationStatusMessage: document.getElementById("integrationStatusMessage"),
  processConfirmationsButton: document.getElementById("processConfirmationsButton"),
  processRemindersButton: document.getElementById("processRemindersButton"),
  processSwapsButton: document.getElementById("processSwapsButton"),
  processCalendarSyncButton: document.getElementById("processCalendarSyncButton"),
  refreshMetricsButton: document.getElementById("refreshMetricsButton"),
  dashboardMetrics: document.getElementById("dashboardMetrics"),
  opsStatusMessage: document.getElementById("opsStatusMessage"),
  conflictDialog: document.getElementById("conflictDialog"),
  conflictDialogDismiss: document.getElementById("conflictDialogDismiss"),
  // EP-003: Clinical profile
  loadClinicalProfileButton: document.getElementById("loadClinicalProfileButton"),
  runConflictCheckButton: document.getElementById("runConflictCheckButton"),
  clinicalFileInput: document.getElementById("clinicalFileInput"),
  uploadDocumentButton: document.getElementById("uploadDocumentButton"),
  uploadStatusMessage: document.getElementById("uploadStatusMessage"),
  conflictAlertsContainer: document.getElementById("conflictAlertsContainer"),
  conflictAlertsList: document.getElementById("conflictAlertsList"),
  medicationsBadge: document.getElementById("medicationsBadge"),
  profileOverviewContent: document.getElementById("profileOverviewContent"),
  medicationsList: document.getElementById("medicationsList"),
  allergiesList: document.getElementById("allergiesList"),
  diagnosesList: document.getElementById("diagnosesList"),
  medicationsEmpty: document.getElementById("medicationsEmpty"),
  allergiesEmpty: document.getElementById("allergiesEmpty"),
  diagnosesEmpty: document.getElementById("diagnosesEmpty"),
  clinicalProfileStatus: document.getElementById("clinicalProfileStatus"),
  // EP-003: Coding Review
  generateSuggestionsButton: document.getElementById("generateSuggestionsButton"),
  loadConflictQueueButton: document.getElementById("loadConflictQueueButton"),
  reviewOnlyFilter: document.getElementById("reviewOnlyFilter"),
  codeTypeFilter: document.getElementById("codeTypeFilter"),
  suggestionsList: document.getElementById("suggestionsList"),
  suggestionsEmpty: document.getElementById("suggestionsEmpty"),
  reviewQueueBadge: document.getElementById("reviewQueueBadge"),
  allergyConflictList: document.getElementById("allergyConflictList"),
  allergyConflictEmpty: document.getElementById("allergyConflictEmpty"),
  allergyConflictBadge: document.getElementById("allergyConflictBadge"),
  conflictQueueList: document.getElementById("conflictQueueList"),
  conflictQueueEmpty: document.getElementById("conflictQueueEmpty"),
  conflictQueueBadge: document.getElementById("conflictQueueBadge"),
  icd10ThresholdSlider: document.getElementById("icd10ThresholdSlider"),
  icd10ThresholdValue: document.getElementById("icd10ThresholdValue"),
  cptThresholdSlider: document.getElementById("cptThresholdSlider"),
  cptThresholdValue: document.getElementById("cptThresholdValue"),
  saveIcd10ThresholdButton: document.getElementById("saveIcd10ThresholdButton"),
  saveCptThresholdButton: document.getElementById("saveCptThresholdButton"),
  thresholdRoleInput: document.getElementById("thresholdRoleInput"),
  thresholdHistoryList: document.getElementById("thresholdHistoryList"),
  codingReviewStatus: document.getElementById("codingReviewStatus"),
  // EP-005 US-047: Admin user management
  userSearchInput: document.getElementById("userSearchInput"),
  userRoleFilter: document.getElementById("userRoleFilter"),
  userStatusFilter: document.getElementById("userStatusFilter"),
  loadAdminUsersButton: document.getElementById("loadAdminUsersButton"),
  userListContainer: document.getElementById("userListContainer"),
  userMgmtStatus: document.getElementById("userMgmtStatus"),
  openCreateUserButton: document.getElementById("openCreateUserButton"),
  createUserDialog: document.getElementById("createUserDialog"),
  createUserForm: document.getElementById("createUserForm"),
  cancelCreateUserButton: document.getElementById("cancelCreateUserButton"),
  createUserFormStatus: document.getElementById("createUserFormStatus"),
  editRoleDialog: document.getElementById("editRoleDialog"),
  editRoleUserId: document.getElementById("editRoleUserId"),
  editRoleSelect: document.getElementById("editRoleSelect"),
  editRoleReason: document.getElementById("editRoleReason"),
  editRoleStatus: document.getElementById("editRoleStatus"),
  confirmEditRoleButton: document.getElementById("confirmEditRoleButton"),
  cancelEditRoleButton: document.getElementById("cancelEditRoleButton"),
  editStatusDialog: document.getElementById("editStatusDialog"),
  editStatusUserId: document.getElementById("editStatusUserId"),
  editStatusSelect: document.getElementById("editStatusSelect"),
  editStatusReason: document.getElementById("editStatusReason"),
  editStatusStatus: document.getElementById("editStatusStatus"),
  deactivateConfirmArea: document.getElementById("deactivateConfirmArea"),
  deactivateConfirmCheck: document.getElementById("deactivateConfirmCheck"),
  confirmEditStatusButton: document.getElementById("confirmEditStatusButton"),
  cancelEditStatusButton: document.getElementById("cancelEditStatusButton"),
};

let filterDebounceId;
let suggestionDebounceId;

bootstrap().catch((error) => {
  console.error(error);
  elements.checkoutStatusMessage.textContent = "The booking experience could not be initialized.";
});

async function bootstrap() {
  hydrateFromQuery();
  normalizeDateFilters();
  applyFilterInputs();
  await Promise.all([loadPatientProfile(), loadSpecialties(), loadIntegrations()]);
  bindEvents();
  renderFilterSummary();
  await Promise.all([renderSearchResults(), renderCalendar()]);
  await refreshMetrics();
  await loadClinicalProfile();
  await loadCodingData();
  initRbac();
}

function bindEvents() {
  elements.form.addEventListener("input", onFilterInput);
  elements.clearFiltersButton.addEventListener("click", clearFilters);
  elements.previousPageButton.addEventListener("click", () => changePage(-1));
  elements.nextPageButton.addEventListener("click", () => changePage(1));
  elements.expandDateRangeButton.addEventListener("click", expandDateRange);
  elements.clearEmptyStateFiltersButton.addEventListener("click", clearFilters);
  elements.monthViewButton.addEventListener("click", () => setCalendarView("month"));
  elements.weekViewButton.addEventListener("click", () => setCalendarView("week"));
  elements.previousRangeButton.addEventListener("click", () => shiftCalendar(-1));
  elements.nextRangeButton.addEventListener("click", () => shiftCalendar(1));
  elements.calendarGrid.addEventListener("touchstart", onCalendarTouchStart, { passive: true });
  elements.calendarGrid.addEventListener("touchend", onCalendarTouchEnd, { passive: true });
  elements.reserveSlotButton.addEventListener("click", reserveSelectedSlot);
  elements.checkoutForm.addEventListener("submit", onBookNow);
  elements.connectGoogleButton.addEventListener("click", () => connectProvider("google"));
  elements.connectOutlookButton.addEventListener("click", () => connectProvider("outlook"));
  elements.disconnectGoogleButton.addEventListener("click", () => disconnectProvider("google"));
  elements.disconnectOutlookButton.addEventListener("click", () => disconnectProvider("outlook"));
  elements.processConfirmationsButton.addEventListener("click", () => runOpsJob("/api/jobs/process-confirmations", "Confirmation queue processed."));
  elements.processRemindersButton.addEventListener("click", () => runOpsJob("/api/jobs/process-reminders", "Reminder engine processed."));
  elements.processSwapsButton.addEventListener("click", () => runOpsJob("/api/jobs/process-swaps", "Preferred slot swap engine processed."));
  elements.processCalendarSyncButton.addEventListener("click", () => runOpsJob("/api/jobs/process-calendar-sync", "Calendar sync queue processed."));
  elements.refreshMetricsButton.addEventListener("click", refreshMetrics);
  elements.conflictDialogDismiss.addEventListener("click", returnToCalendarAfterConflict);
  elements.provider.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      clearSuggestions();
    }
  });
  // EP-003: Clinical profile
  elements.loadClinicalProfileButton.addEventListener("click", loadClinicalProfile);
  elements.runConflictCheckButton.addEventListener("click", runClinicalConflictCheck);
  elements.uploadDocumentButton.addEventListener("click", uploadClinicalDocument);
  document.querySelectorAll(".tab-btn[data-tab]").forEach((btn) => {
    btn.addEventListener("click", () => switchClinicalTab(btn.dataset.tab));
  });
  // EP-003: Coding review
  document.querySelectorAll(".tab-btn[data-coding-tab]").forEach((btn) => {
    btn.addEventListener("click", () => switchCodingTab(btn.dataset.codingTab));
  });
  elements.generateSuggestionsButton.addEventListener("click", generateClinicalCodes);
  elements.loadConflictQueueButton.addEventListener("click", loadConflictQueue);
  elements.reviewOnlyFilter.addEventListener("change", renderSuggestions);
  elements.codeTypeFilter.addEventListener("change", renderSuggestions);
  elements.icd10ThresholdSlider.addEventListener("input", () => {
    elements.icd10ThresholdValue.textContent = elements.icd10ThresholdSlider.value + "%";
  });
  elements.cptThresholdSlider.addEventListener("input", () => {
    elements.cptThresholdValue.textContent = elements.cptThresholdSlider.value + "%";
  });
  elements.saveIcd10ThresholdButton.addEventListener("click", () => saveThreshold("icd10"));
  elements.saveCptThresholdButton.addEventListener("click", () => saveThreshold("cpt"));

  // EP-005 US-047: Admin user management events
  if (elements.loadAdminUsersButton) {
    elements.loadAdminUsersButton.addEventListener("click", loadAdminUsers);
  }
  if (elements.openCreateUserButton) {
    elements.openCreateUserButton.addEventListener("click", () => {
      elements.createUserForm.reset();
      elements.createUserFormStatus.textContent = "";
      document.getElementById("newUserIdError").textContent = "";
      document.getElementById("newUserEmailError").textContent = "";
      document.getElementById("newUserRoleError").textContent = "";
      elements.createUserDialog.showModal();
    });
  }
  if (elements.cancelCreateUserButton) {
    elements.cancelCreateUserButton.addEventListener("click", () => elements.createUserDialog.close());
  }
  if (elements.createUserForm) {
    elements.createUserForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      await onCreateUserSubmit();
    });
  }
  if (elements.cancelEditRoleButton) {
    elements.cancelEditRoleButton.addEventListener("click", () => elements.editRoleDialog.close());
  }
  if (elements.confirmEditRoleButton) {
    elements.confirmEditRoleButton.addEventListener("click", onConfirmEditRole);
  }
  if (elements.cancelEditStatusButton) {
    elements.cancelEditStatusButton.addEventListener("click", () => elements.editStatusDialog.close());
  }
  if (elements.confirmEditStatusButton) {
    elements.confirmEditStatusButton.addEventListener("click", onConfirmEditStatus);
  }
  if (elements.editStatusSelect) {
    elements.editStatusSelect.addEventListener("change", () => {
      const isDeactivating = elements.editStatusSelect.value === "inactive";
      elements.deactivateConfirmArea.hidden = !isDeactivating;
      if (!isDeactivating) elements.deactivateConfirmCheck.checked = false;
    });
  }

  let userSearchDebounce;
  if (elements.userSearchInput) {
    elements.userSearchInput.addEventListener("input", () => {
      state.adminUsers.filter.query = elements.userSearchInput.value.trim().toLowerCase();
      clearTimeout(userSearchDebounce);
      userSearchDebounce = setTimeout(renderUserList, 180);
    });
  }
  if (elements.userRoleFilter) {
    elements.userRoleFilter.addEventListener("change", () => {
      state.adminUsers.filter.role = elements.userRoleFilter.value;
      renderUserList();
    });
  }
  if (elements.userStatusFilter) {
    elements.userStatusFilter.addEventListener("change", () => {
      state.adminUsers.filter.status = elements.userStatusFilter.value;
      renderUserList();
    });
  }
}

function hydrateFromQuery() {
  const params = new URLSearchParams(window.location.search);
  ["dateFrom", "dateTo", "timeOfDay", "provider", "specialty"].forEach((key) => {
    if (params.has(key)) {
      state.filters[key] = params.get(key);
    }
  });
  if (params.has("sortBy")) {
    state.filters.sortBy = params.get("sortBy");
  }
  if (params.has("sortDir")) {
    state.filters.sortDir = params.get("sortDir");
  }
  if (params.has("page")) {
    state.results.page = Math.max(1, Number(params.get("page")) || 1);
  }
}

function applyFilterInputs() {
  elements.dateFrom.value = state.filters.dateFrom;
  elements.dateTo.value = state.filters.dateTo;
  elements.timeOfDay.value = state.filters.timeOfDay;
  elements.provider.value = state.filters.provider;
  elements.sortBy.value = state.filters.sortBy;
  elements.sortDir.value = state.filters.sortDir;
}

function normalizeDateFilters() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayIso = today.toISOString().slice(0, 10);
  const currentFrom = state.filters.dateFrom ? new Date(`${state.filters.dateFrom}T00:00:00`) : null;
  const currentTo = state.filters.dateTo ? new Date(`${state.filters.dateTo}T00:00:00`) : null;

  if (!state.filters.dateFrom || Number.isNaN(currentFrom?.getTime()) || currentFrom < today) {
    state.filters.dateFrom = todayIso;
  }

  const minTo = new Date(`${state.filters.dateFrom}T00:00:00`);
  minTo.setDate(minTo.getDate() + 14);
  const minToIso = minTo.toISOString().slice(0, 10);

  if (!state.filters.dateTo || Number.isNaN(currentTo?.getTime()) || currentTo < new Date(`${state.filters.dateFrom}T00:00:00`)) {
    state.filters.dateTo = minToIso;
  }

  state.calendar.anchorDate = state.filters.dateFrom;
}

async function loadPatientProfile() {
  const payload = await fetchJson("/api/patient/profile");
  if (!payload.success) return;
  document.getElementById("firstName").value = payload.data.first_name || "";
  document.getElementById("lastName").value = payload.data.last_name || "";
  document.getElementById("email").value = payload.data.email || "";
  document.getElementById("phone").value = payload.data.phone || "";
  document.getElementById("timezone").value = payload.data.preferred_timezone || Intl.DateTimeFormat().resolvedOptions().timeZone;
  const channels = JSON.parse(payload.data.reminder_channels || "[]");
  document.querySelectorAll('input[name="reminderChannel"]').forEach((checkbox) => {
    checkbox.checked = channels.includes(checkbox.value);
  });
}

async function loadSpecialties() {
  const payload = await fetchJson("/api/appointments/specialties");
  if (!payload.success) return;
  payload.data.forEach((specialty) => {
    const option = document.createElement("option");
    option.value = specialty.name;
    option.textContent = specialty.name;
    elements.specialty.appendChild(option);
  });
  elements.specialty.value = state.filters.specialty;
}

async function loadIntegrations() {
  const payload = await fetchJson("/api/integrations/status");
  if (!payload.success) return;
  state.integrations = payload.data;
  renderIntegrationState();
}

function renderIntegrationState() {
  updateIntegrationBadge("google", state.integrations.google);
  updateIntegrationBadge("outlook", state.integrations.outlook);
}

function updateIntegrationBadge(provider, details) {
  const badge = provider === "google" ? elements.googleBadge : elements.outlookBadge;
  badge.textContent = details.connected ? "Connected" : details.status === "error" ? "Connection Error" : "Not Connected";
  badge.className = `badge ${details.connected ? "badge--success" : details.status === "error" ? "badge--warning" : ""}`;
}

function onFilterInput(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  syncFiltersFromInputs();
  renderFilterSummary();
  if (target.id === "provider") {
    clearTimeout(suggestionDebounceId);
    suggestionDebounceId = setTimeout(loadProviderSuggestions, 220);
  }
  clearTimeout(filterDebounceId);
  filterDebounceId = setTimeout(async () => {
    await Promise.all([renderSearchResults(), renderCalendar()]);
  }, 220);
}

function syncFiltersFromInputs() {
  state.filters.dateFrom = elements.dateFrom.value;
  state.filters.dateTo = elements.dateTo.value;
  state.filters.timeOfDay = elements.timeOfDay.value;
  state.filters.provider = elements.provider.value.trim();
  state.filters.specialty = elements.specialty.value;
  state.filters.sortBy = elements.sortBy.value;
  state.filters.sortDir = elements.sortDir.value;
  state.results.page = 1;
  writeQueryState();
}

function renderFilterSummary() {
  const parts = [];
  if (state.filters.dateFrom || state.filters.dateTo) {
    parts.push(`Date: ${state.filters.dateFrom || "Any"} to ${state.filters.dateTo || "Any"}`);
  }
  if (state.filters.timeOfDay) parts.push(`Time: ${state.filters.timeOfDay}`);
  if (state.filters.provider) parts.push(`Provider: ${state.filters.provider}`);
  if (state.filters.specialty) parts.push(`Specialty: ${state.filters.specialty}`);
  elements.filterSummary.textContent = parts.length ? parts.join(" | ") : "No active filters.";
}

function writeQueryState() {
  const params = new URLSearchParams();
  Object.entries(state.filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  if (state.results.page > 1) {
    params.set("page", String(state.results.page));
  }
  history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
}

async function loadProviderSuggestions() {
  const query = state.filters.provider;
  if (query.length < 2) {
    clearSuggestions();
    return;
  }
  const payload = await fetchJson(`/api/providers/suggest?query=${encodeURIComponent(query)}`);
  clearSuggestions();
  if (!payload.success || !payload.data.length) return;
  payload.data.forEach((provider) => {
    const item = document.createElement("li");
    item.className = "suggestion-item";
    item.setAttribute("role", "option");
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${provider.name} (${provider.specialty})`;
    button.addEventListener("click", async () => {
      elements.provider.value = provider.name;
      state.filters.provider = provider.name;
      state.results.page = 1;
      writeQueryState();
      clearSuggestions();
      await Promise.all([renderSearchResults(), renderCalendar()]);
    });
    item.appendChild(button);
    elements.providerSuggestions.appendChild(item);
  });
  elements.provider.setAttribute("aria-expanded", "true");
}

function clearSuggestions() {
  elements.providerSuggestions.innerHTML = "";
  elements.provider.setAttribute("aria-expanded", "false");
}

async function renderSearchResults() {
  renderFilterSummary();
  const params = new URLSearchParams({
    ...state.filters,
    page: String(state.results.page),
    pageSize: String(state.results.pageSize),
  });
  const payload = await fetchJson(`/api/appointments/search?${params.toString()}`);
  if (!payload.success) {
    elements.searchResults.innerHTML = `<article class="result-card result-card--error"><h3>Search unavailable</h3><p>${payload.error.message}</p></article>`;
    elements.searchEmptyState.hidden = true;
    elements.resultsSummary.textContent = "Search request needs attention.";
    return;
  }

  state.results.items = payload.data.items;
  state.results.total = payload.data.pagination.total;
  state.results.totalPages = payload.data.pagination.totalPages;
  state.results.page = payload.data.pagination.page;
  state.results.latestLatencyMs = payload.meta.latencyMs;
  writeQueryState();

  await refreshSearchMetrics();
  renderSearchSummary();
  renderPagination();

  if (!state.results.items.length) {
    elements.searchResults.innerHTML = "";
    elements.searchEmptyState.hidden = false;
    return;
  }

  elements.searchEmptyState.hidden = true;
  elements.searchResults.innerHTML = state.results.items
    .map(
      (slot) => `
        <article class="result-card" data-provider-id="${slot.provider_id}" data-slot-id="${slot.id}">
          <button type="button" class="result-card__body" data-action="provider" data-provider-id="${slot.provider_id}" data-slot-id="${slot.id}" aria-label="View provider details for ${slot.provider_name}">
            <div class="result-card__eyebrow">${slot.specialty}</div>
            <h3>${slot.provider_name}</h3>
            <p>${slot.appointment_date} | ${slot.start_time} - ${slot.end_time}</p>
            <p>${slot.location}</p>
          </button>
          <div class="result-card__footer">
            <span class="result-card__meta">${slot.duration_minutes} min</span>
            <div class="card-actions">
              <button type="button" class="ghost-btn" data-action="provider" data-provider-id="${slot.provider_id}" data-slot-id="${slot.id}">Provider details</button>
              <button type="button" data-action="book" data-slot-id="${slot.id}">Book Now</button>
            </div>
          </div>
        </article>
      `,
    )
    .join("");

  elements.searchResults.querySelectorAll("button[data-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const slotId = Number(button.getAttribute("data-slot-id"));
      if (button.getAttribute("data-action") === "provider") {
        const providerId = Number(button.getAttribute("data-provider-id"));
        await showProviderDetails(providerId, slotId);
        return;
      }
      await jumpToBooking(slotId);
    });
  });
}

async function refreshSearchMetrics() {
  const payload = await fetchJson("/api/metrics/search");
  if (payload.success) {
    state.results.metrics = payload.data;
  }
}

function renderSearchSummary() {
  const startIndex = state.results.total === 0 ? 0 : (state.results.page - 1) * state.results.pageSize + 1;
  const endIndex = Math.min(state.results.total, state.results.page * state.results.pageSize);
  elements.resultsSummary.textContent = state.results.total
    ? `Showing ${startIndex}-${endIndex} of ${state.results.total} available slots.`
    : "No slots available for the current filters.";

  if (!state.results.metrics) {
    elements.searchMetricsSummary.textContent = `Latest query ${state.results.latestLatencyMs}ms`;
    return;
  }

  const alertSuffix = state.results.metrics.alertBreached ? " Latency alert is currently breached." : "";
  elements.searchMetricsSummary.textContent = `Latest query ${state.results.latestLatencyMs}ms. P95 ${state.results.metrics.p95LatencyMs}ms, empty rate ${state.results.metrics.emptyResultRate}%.${alertSuffix}`;
}

function renderPagination() {
  elements.paginationLabel.textContent = `Page ${state.results.page} of ${state.results.totalPages}`;
  elements.previousPageButton.disabled = state.results.page <= 1;
  elements.nextPageButton.disabled = state.results.page >= state.results.totalPages;
}

function changePage(direction) {
  const nextPage = state.results.page + direction;
  if (nextPage < 1 || nextPage > state.results.totalPages) {
    return;
  }
  state.results.page = nextPage;
  writeQueryState();
  Promise.all([renderSearchResults(), renderCalendar()]);
}

function expandDateRange() {
  const today = new Date().toISOString().slice(0, 10);
  if (!state.filters.dateFrom) {
    state.filters.dateFrom = today;
  }
  const base = state.filters.dateTo || state.filters.dateFrom || today;
  const date = new Date(base);
  date.setDate(date.getDate() + 7);
  state.filters.dateTo = date.toISOString().slice(0, 10);
  applyFilterInputs();
  state.results.page = 1;
  writeQueryState();
  Promise.all([renderSearchResults(), renderCalendar()]);
}

async function jumpToBooking(slotId) {
  await selectSlot(slotId);
  document.getElementById("selectionTitle").scrollIntoView({ behavior: "smooth", block: "start" });
  elements.reserveSlotButton.focus();
}

async function renderCalendar() {
  renderFilterSummary();
  const params = new URLSearchParams({
    ...state.filters,
    view: state.calendar.view,
    anchorDate: state.calendar.anchorDate,
  });
  const payload = await fetchJson(`/api/appointments/calendar?${params.toString()}`);
  if (!payload.success) {
    elements.calendarGrid.innerHTML = `<div class="calendar-empty">${payload.error.message}</div>`;
    return;
  }
  const data = payload.data;
  state.calendar.anchorDate = data.anchorDate;
  elements.calendarRangeLabel.textContent = `${data.rangeStart} to ${data.rangeEnd}`;
  elements.timezoneLabel.textContent = data.timezone;
  elements.calendarFootnote.textContent = data.utcFooter;
  elements.monthViewButton.classList.toggle("is-active", state.calendar.view === "month");
  elements.weekViewButton.classList.toggle("is-active", state.calendar.view === "week");

  const fragment = document.createDocumentFragment();
  data.days.forEach((day) => {
    const article = document.createElement("article");
    article.className = `calendar-day ${day.isCurrentMonth ? "" : "calendar-day--muted"}`;
    const slotsMarkup = day.slots.length
      ? day.slots
          .map((slot) => {
            const tone = slot.status === "available" ? "slot-pill--available" : "slot-pill--booked";
            return `
              <button
                type="button"
                class="slot-pill ${tone}"
                data-slot-id="${slot.id}"
                aria-label="${slot.provider_name} on ${slot.appointment_date} at ${slot.start_time}"
              >
                ${slot.start_time}
              </button>
            `;
          })
          .join("")
      : '<div class="slot-empty">No slots</div>';
    article.innerHTML = `
      <header>
        <span class="calendar-day__label">${day.dayLabel}</span>
        <strong>${day.dayNumber}</strong>
      </header>
      <div class="calendar-slots">${slotsMarkup}</div>
    `;
    fragment.appendChild(article);
  });
  elements.calendarGrid.innerHTML = "";
  elements.calendarGrid.appendChild(fragment);
  document.querySelectorAll(".slot-pill").forEach((button) => {
    button.addEventListener("click", async () => {
      const slotId = Number(button.getAttribute("data-slot-id"));
      await selectSlot(slotId);
    });
  });
}

async function selectSlot(slotId) {
  const payload = await fetchJson(`/api/appointments/${slotId}`);
  if (!payload.success) return;
  state.selectedSlot = payload.data;
  renderSelectedSlot();
  renderBookingSummary();
  await populatePreferredSlots();
}

function renderSelectedSlot() {
  const slot = state.selectedSlot;
  if (!slot) {
    elements.selectedSlotDetails.textContent = "Select a slot from the calendar to view provider details, location, duration, and reserve it for checkout.";
    return;
  }
  const responsiveImage = buildResponsiveImage(slot);
  elements.selectedSlotDetails.innerHTML = `
    <article class="provider-card">
      ${responsiveImage}
      <div>
        <h3>${slot.provider_name}</h3>
        <p><strong>${slot.specialty}</strong> | ${slot.credentials}</p>
        <p>${slot.appointment_date} at ${slot.start_time} - ${slot.end_time}</p>
        <p>${slot.location} | ${slot.duration_minutes} minutes</p>
        <p>${slot.bio || ""}</p>
        <div class="card-actions">
          <button type="button" class="ghost-btn" id="viewProviderDetailsButton">Provider details</button>
        </div>
      </div>
    </article>
  `;
  document.getElementById("viewProviderDetailsButton").addEventListener("click", showProviderDetails);
}

function buildResponsiveImage(slot) {
  if (!slot.photo_url) {
    return "";
  }
  return `
    <img
      class="provider-photo"
      src="${slot.photo_url}"
      srcset="${slot.photo_url}&w=320 320w, ${slot.photo_url}&w=640 640w"
      sizes="(max-width: 767px) 100vw, 320px"
      alt="Portrait of ${slot.provider_name}"
      loading="lazy"
      width="160"
      height="160"
    />
  `;
}

async function showProviderDetails(providerId = state.selectedSlot?.provider_id, slotId = state.selectedSlot?.id) {
  if (!providerId) return;
  if (slotId && (!state.selectedSlot || state.selectedSlot.id !== slotId)) {
    await selectSlot(slotId);
  }
  const payload = await fetchJson(`/api/providers/${providerId}`);
  if (!payload.success) return;
  const provider = payload.data;
  elements.providerDialogBody.innerHTML = `
    <p><strong>${provider.name}</strong></p>
    <p>${provider.specialty} | ${provider.credentials}</p>
    <p>${provider.bio || ""}</p>
    <p>Reviews: ${provider.review_count}</p>
  `;
  elements.providerDialog.showModal();
}

async function populatePreferredSlots() {
  if (!state.selectedSlot) return;
  const params = new URLSearchParams({ specialty: state.selectedSlot.specialty, provider: state.selectedSlot.provider_name, pageSize: "20" });
  const payload = await fetchJson(`/api/appointments/search?${params.toString()}`);
  elements.preferredSlotId.innerHTML = '<option value="">No preferred slot</option>';
  if (!payload.success) return;
  payload.data.items
    .filter((item) => item.id !== state.selectedSlot.id)
    .slice(0, 8)
    .forEach((item) => {
      const option = document.createElement("option");
      option.value = item.id;
      option.textContent = `${item.appointment_date} ${item.start_time} - ${item.location}`;
      elements.preferredSlotId.appendChild(option);
    });
}

function renderBookingSummary() {
  if (!state.selectedSlot) {
    elements.bookingSummary.textContent = "Choose a slot to populate your final summary.";
    return;
  }
  elements.bookingSummary.innerHTML = `
    <p><strong>Provider:</strong> ${state.selectedSlot.provider_name}</p>
    <p><strong>Specialty:</strong> ${state.selectedSlot.specialty}</p>
    <p><strong>Date:</strong> ${state.selectedSlot.appointment_date}</p>
    <p><strong>Time:</strong> ${state.selectedSlot.start_time} - ${state.selectedSlot.end_time}</p>
    <p><strong>Location:</strong> ${state.selectedSlot.location}</p>
    <p><strong>Duration:</strong> ${state.selectedSlot.duration_minutes} minutes</p>
  `;
}

function returnToCalendarAfterConflict() {
  state.selectedSlot = null;
  state.reservationToken = "";
  state.reservationExpiresAt = "";
  clearInterval(state.reservationTimerId);
  elements.reservationCountdown.textContent = "No active reservation";
  elements.checkoutStatusMessage.textContent = "";
  elements.selectedSlotDetails.textContent = "Select a slot from the calendar to view provider details, location, duration, and reserve it for checkout.";
  elements.bookingSummary.textContent = "Choose a slot to populate your final summary.";
  document.getElementById("calendarTitle").scrollIntoView({ behavior: "smooth", block: "start" });
  renderCalendar();
}

async function reserveSelectedSlot() {
  if (!state.selectedSlot) {
    elements.checkoutStatusMessage.textContent = "Select a slot before reserving it.";
    return;
  }
  const payload = {
    idempotencyKey: crypto.randomUUID(),
    preferredSlotId: elements.preferredSlotId.value || null,
  };
  const response = await postJson(`/api/appointments/${state.selectedSlot.id}/checkout`, payload);
  if (!response.success) {
    const code = response.error?.code;
    if (code === "UNAVAILABLE_SLOT" || code === "RESERVED") {
      elements.conflictDialog.showModal();
    } else {
      elements.checkoutStatusMessage.textContent = response.error.message;
    }
    return;
  }
  state.reservationToken = response.data.reservationToken;
  state.reservationExpiresAt = response.data.expiresAt;
  elements.checkoutStatusMessage.textContent = "Slot reserved for 60 seconds. Complete checkout below.";
  startReservationCountdown();
}

function startReservationCountdown() {
  clearInterval(state.reservationTimerId);
  state.reservationTimerId = setInterval(() => {
    const secondsRemaining = Math.max(0, Math.floor((new Date(state.reservationExpiresAt) - new Date()) / 1000));
    elements.reservationCountdown.textContent = secondsRemaining > 0 ? `Reservation expires in ${secondsRemaining}s` : "Reservation expired";
    if (secondsRemaining <= 0) {
      clearInterval(state.reservationTimerId);
      state.reservationToken = "";
    }
  }, 1000);
}

function validateCheckoutForm() {
  const requiredFields = [
    ["firstName", "First name is required."],
    ["lastName", "Last name is required."],
    ["email", "Email is required."],
    ["phone", "Phone is required."],
  ];
  let valid = true;
  requiredFields.forEach(([fieldId, message]) => {
    const field = document.getElementById(fieldId);
    const error = document.getElementById(`${fieldId}Error`);
    if (!field.value.trim()) {
      error.textContent = message;
      field.setAttribute("aria-invalid", "true");
      valid = false;
    } else {
      error.textContent = "";
      field.removeAttribute("aria-invalid");
    }
  });
  return valid;
}

async function onBookNow(event) {
  event.preventDefault();
  if (!validateCheckoutForm()) {
    elements.checkoutStatusMessage.textContent = "Please fix the inline validation errors before booking.";
    return;
  }
  if (!state.reservationToken) {
    elements.checkoutStatusMessage.textContent = "Reserve a slot first so the 60-second checkout lock is active.";
    return;
  }
  const payload = {
    reservationToken: state.reservationToken,
    idempotencyKey: crypto.randomUUID(),
    firstName: document.getElementById("firstName").value.trim(),
    lastName: document.getElementById("lastName").value.trim(),
    email: document.getElementById("email").value.trim(),
    phone: document.getElementById("phone").value.trim(),
    timezone: document.getElementById("timezone").value.trim(),
    notes: document.getElementById("notes").value.trim(),
    preferredSlotId: elements.preferredSlotId.value || null,
    reminderChannels: Array.from(document.querySelectorAll('input[name="reminderChannel"]:checked')).map((checkbox) => checkbox.value),
  };
  const response = await postJson("/api/appointments/book", payload);
  if (!response.success) {
    const code = response.error?.code;
    if (code === "UNAVAILABLE_SLOT" || code === "RESERVATION_EXPIRED") {
      elements.conflictDialog.showModal();
    } else {
      elements.checkoutStatusMessage.textContent = response.error.message;
    }
    return;
  }
  clearInterval(state.reservationTimerId);
  elements.reservationCountdown.textContent = "Booking confirmed";
  elements.checkoutStatusMessage.textContent = "Appointment booked. Processing confirmation email and calendar fan-out now.";
  await runOpsJob("/api/jobs/process-confirmations", "Confirmation delivery completed.", false);
  await runOpsJob("/api/jobs/process-calendar-sync", "Calendar sync processed.", false);
  await refreshMetrics();
  await renderCalendar();
}

async function connectProvider(provider) {
  const payload = await fetchJson(`/api/auth/${provider}/authorize`);
  if (!payload.success) return;
  const callbackResponse = await fetchJson(payload.data.authorizeUrl);
  if (callbackResponse.success) {
    state.integrations = callbackResponse.data.integration;
    renderIntegrationState();
    elements.integrationStatusMessage.textContent = callbackResponse.data.message;
    return;
  }
  elements.integrationStatusMessage.textContent = callbackResponse.error.message;
}

async function disconnectProvider(provider) {
  const response = await postJson(`/api/auth/${provider}/disconnect`, {});
  if (!response.success) return;
  state.integrations = response.data.integration;
  renderIntegrationState();
  elements.integrationStatusMessage.textContent = `${provider[0].toUpperCase() + provider.slice(1)} calendar disconnected.`;
}

async function runOpsJob(endpoint, successMessage, refresh = true) {
  const response = await postJson(endpoint, {});
  if (!response.success) {
    elements.opsStatusMessage.textContent = response.error.message;
    return;
  }
  elements.opsStatusMessage.textContent = successMessage;
  if (refresh) {
    await refreshMetrics();
  }
}

async function refreshMetrics() {
  const payload = await fetchJson("/api/dashboard/metrics");
  if (!payload.success) return;
  const blocks = Object.entries(payload.data).map(([label, values]) => {
    const body = Object.entries(values).length
      ? Object.entries(values)
          .map(([key, count]) => `<li><span>${key}</span><strong>${count}</strong></li>`)
          .join("")
      : '<li><span>No data yet</span><strong>0</strong></li>';
    return `
      <article class="ops-card">
        <h3>${label}</h3>
        <ul>${body}</ul>
      </article>
    `;
  });
  elements.dashboardMetrics.innerHTML = blocks.join("");
}

function setCalendarView(view) {
  state.calendar.view = view;
  renderCalendar();
}

function shiftCalendar(direction) {
  const anchor = new Date(state.calendar.anchorDate);
  anchor.setDate(anchor.getDate() + (state.calendar.view === "week" ? direction * 14 : direction * 28));
  state.calendar.anchorDate = anchor.toISOString().slice(0, 10);
  renderCalendar();
}

function onCalendarTouchStart(event) {
  state.calendar.touchStartX = event.changedTouches[0].clientX;
}

function onCalendarTouchEnd(event) {
  const delta = event.changedTouches[0].clientX - state.calendar.touchStartX;
  if (Math.abs(delta) < 40) return;
  shiftCalendar(delta < 0 ? 1 : -1);
}

function clearFilters() {
  state.filters = { dateFrom: "", dateTo: "", timeOfDay: "", provider: "", specialty: "", sortBy: "date", sortDir: "asc" };
  normalizeDateFilters();
  state.results.page = 1;
  applyFilterInputs();
  elements.specialty.value = "";
  clearSuggestions();
  Promise.all([renderSearchResults(), renderCalendar()]);
}

async function fetchJson(url) {
  const response = await fetch(url);
  return response.json();
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

// ================================================================
// EP-003: 360° Clinical Patient Profile
// ================================================================

async function loadClinicalProfile() {
  const patientId = state.clinical.patientId;
  elements.clinicalProfileStatus.textContent = "Loading profile…";
  try {
    const payload = await fetchJson(`/api/clinical/patients/${patientId}/profile`);
    if (!payload.success) {
      elements.clinicalProfileStatus.textContent = payload.error?.message || "Failed to load profile.";
      return;
    }
    state.clinical.profile = payload.data;
    renderClinicalProfile(payload.data);
    elements.clinicalProfileStatus.textContent = "";
  } catch {
    elements.clinicalProfileStatus.textContent = "Profile could not be loaded.";
  }
}

function renderClinicalProfile(data) {
  renderProfileOverview(data.overview);
  renderProfileTab("medications", data.medications || []);
  renderProfileTab("allergies", data.allergies || []);
  renderProfileTab("diagnoses", data.diagnoses || []);

  const medCount = (data.medications || []).length;
  if (medCount > 0) {
    elements.medicationsBadge.textContent = medCount;
    elements.medicationsBadge.hidden = false;
  } else {
    elements.medicationsBadge.hidden = true;
  }
}

function renderProfileOverview(overview) {
  if (!overview) return;
  const docs = overview.documents || [];
  const docsHtml = docs.length
    ? `<ul class="docs-list">${docs.map((d) => `
        <li class="doc-item">
          <span>${d.fileName}</span>
          <span class="doc-status-pill doc-status-pill--${d.processingStatus}">${d.processingStatus}</span>
        </li>`).join("")}</ul>`
    : "<p class='muted-text'>No documents uploaded.</p>";

  elements.profileOverviewContent.innerHTML = `
    <div class="overview-field"><span class="overview-label">Name</span><span class="overview-value">${escHtml(overview.firstName || "")} ${escHtml(overview.lastName || "")}</span></div>
    <div class="overview-field"><span class="overview-label">Email</span><span class="overview-value">${escHtml(overview.email || "—")}</span></div>
    <div class="overview-field"><span class="overview-label">Phone</span><span class="overview-value">${escHtml(overview.phone || "—")}</span></div>
    <div class="overview-field"><span class="overview-label">Timezone</span><span class="overview-value">${escHtml(overview.preferredTimezone || "—")}</span></div>
    <div style="grid-column: 1 / -1"><p class="section-label" style="margin-top:.5rem">Uploaded Documents</p>${docsHtml}</div>
  `;
}

function renderProfileTab(tabName, items) {
  const list = elements[`${tabName}List`];
  const empty = elements[`${tabName}Empty`];
  if (!list) return;
  list.innerHTML = "";
  if (!items.length) {
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;
  items.forEach((item) => {
    const li = document.createElement("li");
    li.className = "profile-item";
    const badgeCls = item.sourceType === "intake" ? "source-badge--intake" : "source-badge--document";
    const badgeLabel = item.sourceType === "intake" ? "Intake" : "Document";
    li.innerHTML = `
      <span class="profile-item-value">${escHtml(item.value)}</span>
      <div style="display:flex;align-items:center;gap:.4rem;flex-shrink:0">
        <span class="source-badge ${badgeCls}" title="Source: ${escHtml(item.sourceType)}">${badgeLabel}</span>
        ${item.confidenceScore != null ? `<span class="muted-text" title="Confidence score">${Math.round(item.confidenceScore * 100)}%</span>` : ""}
        <button class="source-detail-btn" data-element-id="${item.id}" type="button" aria-label="View source details for ${escHtml(item.value)}">Source</button>
      </div>
    `;
    li.querySelector(".source-detail-btn").addEventListener("click", () => viewSourceDetail(item.id));
    list.appendChild(li);
  });
}

async function viewSourceDetail(elementId) {
  const patientId = state.clinical.patientId;
  try {
    const payload = await fetchJson(`/api/clinical/elements/${elementId}/source?patientId=${patientId}`);
    if (!payload.success) {
      elements.clinicalProfileStatus.textContent = "Could not load source details.";
      return;
    }
    const d = payload.data;
    const detail = [
      `Type: ${d.elementType}`,
      `Source: ${d.sourceType}${d.documentName ? ` — ${d.documentName} (${d.documentType})` : ""}`,
      d.confidenceScore != null ? `Confidence: ${Math.round(d.confidenceScore * 100)}%` : null,
      d.extractedAt ? `Extracted: ${new Date(d.extractedAt).toLocaleString()}` : null,
    ].filter(Boolean).join(" | ");
    elements.clinicalProfileStatus.textContent = detail;
  } catch {
    elements.clinicalProfileStatus.textContent = "Source detail unavailable.";
  }
}

async function runClinicalConflictCheck() {
  const patientId = state.clinical.patientId;
  elements.clinicalProfileStatus.textContent = "Running conflict check…";
  try {
    const payload = await fetchJson(`/api/clinical/patients/${patientId}/conflicts`);
    if (!payload.success) {
      elements.clinicalProfileStatus.textContent = payload.error?.message || "Conflict check failed.";
      return;
    }
    state.clinical.conflicts = payload.data.conflicts || [];
    renderConflictAlerts(payload.data);
    const count = payload.data.conflictCount || 0;
    elements.clinicalProfileStatus.textContent = payload.data.degraded
      ? "Conflict detection temporarily unavailable."
      : `${count} conflict${count !== 1 ? "s" : ""} detected.`;
  } catch {
    elements.clinicalProfileStatus.textContent = "Conflict check unavailable.";
  }
}

function renderConflictAlerts(data) {
  const conflicts = data.conflicts || [];
  elements.conflictAlertsList.innerHTML = "";

  if (!conflicts.length) {
    elements.conflictAlertsContainer.hidden = true;
    return;
  }

  conflicts.forEach((conflict) => {
    const li = document.createElement("li");
    li.className = "conflict-item";
    li.dataset.severity = conflict.severity;
    li.innerHTML = `
      <span class="conflict-severity">${escHtml(conflict.severity)} — ${escHtml(conflict.conflictType.replace(/_/g, " "))}</span>
      <span class="conflict-meds">${escHtml(conflict.medicationA)} + ${escHtml(conflict.medicationB)}</span>
      <span class="conflict-impact">${escHtml(conflict.clinicalImpact)}</span>
    `;
    elements.conflictAlertsList.appendChild(li);
  });

  elements.conflictAlertsContainer.hidden = false;
}

async function uploadClinicalDocument() {
  const file = elements.clinicalFileInput.files[0];
  if (!file) {
    elements.uploadStatusMessage.textContent = "Please select a PDF or DOCX file.";
    return;
  }
  elements.uploadStatusMessage.textContent = "Uploading…";
  elements.uploadDocumentButton.disabled = true;

  try {
    const patientId = state.clinical.patientId;
    const params = new URLSearchParams({ fileName: file.name, patientId });
    const response = await fetch(`/api/clinical/documents/upload?${params}`, {
      method: "POST",
      headers: { "Content-Type": file.type || "application/octet-stream" },
      body: file,
    });
    const payload = await response.json();
    if (payload.success) {
      elements.uploadStatusMessage.textContent = `Uploaded. Document ID: ${payload.data.documentId}. Status: ${payload.data.status}.`;
      elements.clinicalFileInput.value = "";
      await loadClinicalProfile();
    } else {
      elements.uploadStatusMessage.textContent = payload.error?.message || "Upload failed.";
    }
  } catch {
    elements.uploadStatusMessage.textContent = "Upload request failed.";
  } finally {
    elements.uploadDocumentButton.disabled = false;
  }
}

function switchClinicalTab(tabName) {
  state.clinical.activeTab = tabName;
  document.querySelectorAll(".tab-btn[data-tab]").forEach((btn) => {
    const active = btn.dataset.tab === tabName;
    btn.classList.toggle("tab-btn--active", active);
    btn.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".tab-panel").forEach((panel) => {
    const show = panel.id === `tab${tabName.charAt(0).toUpperCase()}${tabName.slice(1)}`;
    panel.classList.toggle("tab-panel--active", show);
    panel.hidden = !show;
  });
}

function escHtml(str) {
  return String(str ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// ================================================================
// EP-003: Coding Review + Conflict Resolution (TASK-025 to TASK-030)
// ================================================================

function switchCodingTab(tabName) {
  state.coding.activeTab = tabName;
  document.querySelectorAll(".tab-btn[data-coding-tab]").forEach((btn) => {
    const active = btn.dataset.codingTab === tabName;
    btn.classList.toggle("tab-btn--active", active);
    btn.setAttribute("aria-selected", String(active));
  });
  const panels = {
    suggestions: "codingTabSuggestions",
    allergy: "codingTabAllergy",
    conflicts: "codingTabConflicts",
    thresholds: "codingTabThresholds",
  };
  Object.entries(panels).forEach(([key, id]) => {
    const panel = document.getElementById(id);
    if (!panel) return;
    if (key === tabName) {
      panel.classList.add("tab-panel--active");
      panel.hidden = false;
    } else {
      panel.classList.remove("tab-panel--active");
      panel.hidden = true;
    }
  });
}

async function loadCodingData() {
  await Promise.all([
    loadAllergyConflicts(),
    loadThresholds(),
  ]);
}

// TASK-026/027: Generate ICD-10 and CPT suggestions
async function generateClinicalCodes() {
  const btn = elements.generateSuggestionsButton;
  btn.disabled = true;
  btn.textContent = "Generating…";
  setCodingStatus("");
  try {
    const pid = state.coding.patientId;
    // Generate both ICD-10 and CPT
    await Promise.all([
      fetch(`/api/clinical/patients/${pid}/suggestions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code_type: "icd10", clinical_text: "" }),
      }),
      fetch(`/api/clinical/patients/${pid}/suggestions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code_type: "cpt", clinical_text: "" }),
      }),
    ]);
    await loadSuggestions();
    setCodingStatus("Codes generated successfully.");
  } catch (err) {
    setCodingStatus("Failed to generate codes: " + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Generate Codes";
  }
}

async function loadSuggestions() {
  try {
    const pid = state.coding.patientId;
    const res = await fetch(`/api/clinical/patients/${pid}/suggestions`);
    if (!res.ok) throw new Error(res.status);
    const envelope = await res.json();
    const data = envelope.data || envelope;
    state.coding.suggestions = data.suggestions || [];
    renderSuggestions();
  } catch (_) {
    state.coding.suggestions = [];
    renderSuggestions();
  }
}

function renderSuggestions() {
  const all = state.coding.suggestions;
  const reviewOnly = elements.reviewOnlyFilter.checked;
  const codeType = elements.codeTypeFilter.value;
  const filtered = all.filter((s) => {
    if (reviewOnly && !s.reviewRequired) return false;
    if (codeType && s.codeType !== codeType) return false;
    return true;
  });
  const pending = filtered.filter((s) => s.status === "pending" || !s.status).length;
  if (pending > 0) {
    elements.reviewQueueBadge.textContent = String(pending);
    elements.reviewQueueBadge.hidden = false;
  } else {
    elements.reviewQueueBadge.hidden = true;
  }
  if (filtered.length === 0) {
    elements.suggestionsList.innerHTML = "";
    elements.suggestionsEmpty.hidden = false;
    return;
  }
  elements.suggestionsEmpty.hidden = true;
  elements.suggestionsList.innerHTML = filtered.map((s) => {
    const pct = Math.round((s.confidenceScore ?? 0) * 100);
    let fillClass = "confidence-fill--high";
    if (pct < 60) fillClass = "confidence-fill--low";
    else if (pct < 80) fillClass = "confidence-fill--medium";
    const statusPill = s.status && s.status !== "pending"
      ? `<span class="status-pill status-pill--${escHtml(s.status)}">${escHtml(s.status)}</span>`
      : "";
    const typeBadge = `<span class="source-badge source-badge--${escHtml(s.codeType || "")}">${escHtml((s.codeType || "").toUpperCase())}</span>`;
    const isResolved = s.status && s.status !== "pending";
    return `<li class="suggestion-item" data-review="${s.reviewRequired ? "true" : "false"}">
      <div class="suggestion-header">
        <span class="suggestion-code">${escHtml(s.code)}</span>
        ${typeBadge}
        ${statusPill}
        ${s.reviewRequired ? '<span class="source-badge" style="background:rgba(180,83,9,0.1);color:var(--warning)">Review Required</span>' : ""}
      </div>
      <div class="suggestion-desc">${escHtml(s.description)}</div>
      <div class="suggestion-meta">
        <span class="confidence-bar-wrap">
          <span class="confidence-bar"><span class="confidence-fill ${fillClass}" style="width:${pct}%"></span></span>
          ${pct}% confidence
        </span>
        <span>Source: ${escHtml(s.sourceElementType || "N/A")}</span>
      </div>
      <div class="suggestion-actions">
        <button class="action-btn action-btn--accept" onclick="reviewSuggestion(${s.id},'accept')" ${isResolved ? "disabled" : ""}>Accept</button>
        <button class="action-btn action-btn--reject" onclick="reviewSuggestion(${s.id},'reject')" ${isResolved ? "disabled" : ""}>Reject</button>
        <button class="action-btn action-btn--override" onclick="reviewSuggestion(${s.id},'override')" ${isResolved ? "disabled" : ""}>Override</button>
      </div>
    </li>`;
  }).join("");
}

// TASK-028: Code review action
async function reviewSuggestion(suggestionId, action) {
  setCodingStatus("");
  try {
    const res = await fetch(`/api/coding/suggestions/${suggestionId}/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, reviewerId: "frontend_user" }),
    });
    if (!res.ok) throw new Error(res.status);
    await loadSuggestions();
    setCodingStatus(`Suggestion ${action}d.`);
  } catch (err) {
    setCodingStatus("Review failed: " + err.message);
  }
}

// TASK-025: Allergy-drug conflict check
async function loadAllergyConflicts() {
  try {
    const pid = state.coding.patientId;
    const res = await fetch(`/api/clinical/patients/${pid}/allergy-conflicts`);
    if (!res.ok) throw new Error(res.status);
    const envelope = await res.json();
    const data = envelope.data || envelope;
    state.coding.allergyConflicts = data.conflicts || [];
    renderAllergyConflicts();
  } catch (_) {
    state.coding.allergyConflicts = [];
    renderAllergyConflicts();
  }
}

function renderAllergyConflicts() {
  const conflicts = state.coding.allergyConflicts;
  if (conflicts.length > 0) {
    elements.allergyConflictBadge.textContent = String(conflicts.length);
    elements.allergyConflictBadge.hidden = false;
  } else {
    elements.allergyConflictBadge.hidden = true;
  }
  if (conflicts.length === 0) {
    elements.allergyConflictList.innerHTML = "";
    elements.allergyConflictEmpty.hidden = false;
    return;
  }
  elements.allergyConflictEmpty.hidden = true;
  elements.allergyConflictList.innerHTML = conflicts.map((c) => {
    const sev = (c.severity || "unknown").toLowerCase();
    const sevColor = sev === "high" ? "var(--accent)" : sev === "medium" ? "var(--warning)" : "var(--muted)";
    return `<div class="conflict-item" style="border-left:4px solid ${sevColor}">
      <div class="conflict-header">
        <strong>${escHtml(c.allergen)}</strong> ↔ <strong>${escHtml(c.drug_name)}</strong>
        <span class="status-pill status-pill--pending" style="background:rgba(0,0,0,0.05);color:${sevColor}">${escHtml(c.severity || "")}</span>
      </div>
      <div class="muted-text">${escHtml(c.interaction_type || c.impact || "")}</div>
    </div>`;
  }).join("");
}

// TASK-030: Conflict resolution queue
async function loadConflictQueue() {
  const btn = elements.loadConflictQueueButton;
  btn.disabled = true;
  setCodingStatus("");
  try {
    const pid = state.coding.patientId;
    const res = await fetch(`/api/clinical/conflicts/queue?patientId=${pid}`);
    if (!res.ok) throw new Error(res.status);
    const envelope = await res.json();
    const data = envelope.data || envelope;
    state.coding.conflictQueue = data.conflicts || [];
    renderConflictQueue();
    setCodingStatus("Conflict queue loaded.");
  } catch (err) {
    setCodingStatus("Failed to load conflict queue: " + err.message);
  } finally {
    btn.disabled = false;
  }
}

function renderConflictQueue() {
  const conflicts = state.coding.conflictQueue;
  if (conflicts.length > 0) {
    elements.conflictQueueBadge.textContent = String(conflicts.length);
    elements.conflictQueueBadge.hidden = false;
  } else {
    elements.conflictQueueBadge.hidden = true;
  }
  if (conflicts.length === 0) {
    elements.conflictQueueList.innerHTML = "";
    elements.conflictQueueEmpty.hidden = false;
    return;
  }
  elements.conflictQueueEmpty.hidden = true;
  elements.conflictQueueList.innerHTML = conflicts.map((c) => {
    const conflictTable = c.conflict_table || "clinical_medication_conflicts";
    return `<div class="conflict-resolution-item">
      <div class="conflict-resolution-header">
        <strong>${escHtml(c.conflict_type || "Conflict")}</strong>
        <span class="muted-text">#${c.id}</span>
      </div>
      <div class="conflict-side-by-side">
        <div class="conflict-side">
          <span class="conflict-side-label">Value A</span>
          <span class="conflict-side-value">${escHtml(c.value_a || c.medication_a || c.allergen || "—")}</span>
        </div>
        <div class="conflict-side">
          <span class="conflict-side-label">Value B</span>
          <span class="conflict-side-value">${escHtml(c.value_b || c.medication_b || c.drug_name || "—")}</span>
        </div>
      </div>
      <div class="conflict-resolution-actions">
        <button class="action-btn action-btn--resolve" onclick="resolveConflict(${c.id},'${escHtml(conflictTable)}','resolve')">Resolve</button>
        <button class="action-btn action-btn--merge" onclick="resolveConflict(${c.id},'${escHtml(conflictTable)}','merge')">Merge</button>
        <button class="action-btn action-btn--discard" onclick="resolveConflict(${c.id},'${escHtml(conflictTable)}','discard')">Discard</button>
      </div>
    </div>`;
  }).join("");
}

async function resolveConflict(conflictId, conflictTable, action) {
  setCodingStatus("");
  try {
    const res = await fetch(`/api/clinical/conflicts/${conflictId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ conflictTable: conflictTable, action, reviewerId: "frontend_user" }),
    });
    if (!res.ok) throw new Error(res.status);
    await loadConflictQueue();
    setCodingStatus(`Conflict ${action}d.`);
  } catch (err) {
    setCodingStatus("Resolve failed: " + err.message);
  }
}

// TASK-029: Threshold configuration
async function loadThresholds() {
  try {
    const res = await fetch("/api/clinical/thresholds");
    if (!res.ok) throw new Error(res.status);
    const envelope = await res.json();
    const data = envelope.data || envelope;
    // data.thresholds is {icd10: {value, updatedBy, ...}, cpt: {...}}
    const raw = data.thresholds || {};
    state.coding.thresholds = {
      icd10: typeof raw.icd10 === "object" ? raw.icd10.value : (raw.icd10 ?? 0.70),
      cpt: typeof raw.cpt === "object" ? raw.cpt.value : (raw.cpt ?? 0.75),
    };
    populateThresholdSliders();
    await loadThresholdHistory();
  } catch (_) {}
}

function populateThresholdSliders() {
  const t = state.coding.thresholds;
  const icd10Pct = Math.round((t.icd10 ?? 0.70) * 100);
  const cptPct = Math.round((t.cpt ?? 0.75) * 100);
  elements.icd10ThresholdSlider.value = icd10Pct;
  elements.icd10ThresholdValue.textContent = icd10Pct + "%";
  elements.cptThresholdSlider.value = cptPct;
  elements.cptThresholdValue.textContent = cptPct + "%";
}

async function saveThreshold(codeType) {
  const role = elements.thresholdRoleInput.value.trim();
  if (!role) {
    setCodingStatus("Enter your role before saving a threshold.");
    return;
  }
  const sliderEl = codeType === "icd10" ? elements.icd10ThresholdSlider : elements.cptThresholdSlider;
  const newValue = Number(sliderEl.value) / 100;
  setCodingStatus("");
  try {
    const res = await fetch("/api/clinical/thresholds", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ codeType, thresholdValue: newValue, updatedBy: "frontend_user", role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = (err.error || err.data?.message || err.message) ?? String(res.status);
      throw new Error(msg);
    }
    await loadThresholds();
    setCodingStatus(`${codeType.toUpperCase()} threshold saved to ${Math.round(newValue * 100)}%.`);
  } catch (err) {
    setCodingStatus("Save failed: " + err.message);
  }
}

async function loadThresholdHistory() {
  try {
    const res = await fetch("/api/clinical/thresholds/history");
    if (!res.ok) throw new Error(res.status);
    const envelope = await res.json();
    const data = envelope.data || envelope;
    const history = data.history || [];
    if (history.length === 0) {
      elements.thresholdHistoryList.innerHTML = '<li class="muted-text">No history yet.</li>';
      return;
    }
    elements.thresholdHistoryList.innerHTML = history.map((h) => {
      const pct = Math.round((h.newValue ?? 0) * 100);
      const prev = Math.round((h.oldValue ?? 0) * 100);
      const ts = h.changedAt ? new Date(h.changedAt).toLocaleString() : "";
      return `<li class="threshold-history-item">
        <span>${escHtml((h.codeType || "").toUpperCase())}: ${prev}% → ${pct}% by ${escHtml(h.changedBy || "")}</span>
        <span>${escHtml(ts)}</span>
      </li>`;
    }).join("");
  } catch (_) {
    elements.thresholdHistoryList.innerHTML = '<li class="muted-text">Unable to load history.</li>';
  }
}

function setCodingStatus(msg) {
  if (elements.codingReviewStatus) {
    elements.codingReviewStatus.textContent = msg;
  }
}

// =============================================================================
// EP-005 US-043: RBAC — Role-Aware UI Gating (task_043_004)
// =============================================================================

// Centralised fetch wrapper that injects X-Role header on every API call.
const _origFetch = window.fetch;
window.fetch = function (input, init = {}) {
  const headers = new Headers(init.headers || {});
  headers.set("X-Role", state.rbac.role);
  headers.set("X-Patient-Id", String(state.clinical.patientId));
  headers.set("X-Admin-Id", state.rbac.adminId || "admin-demo");
  headers.set("X-Staff-Id", state.rbac.staffId || "staff-demo");
  return _origFetch(input, { ...init, headers });
};

function initRbac() {
  // Wire role selector buttons
  document.querySelectorAll(".rbac-role-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const role = btn.dataset.role;
      if (role) setActiveRole(role);
    });
  });
  applyRbacGating();
}

function setActiveRole(role) {
  state.rbac.role = role;

  // Update button active state
  document.querySelectorAll(".rbac-role-btn").forEach((btn) => {
    btn.classList.toggle("rbac-role-btn--active", btn.dataset.role === role);
  });

  // Update status label
  const statusEl = document.getElementById("rbacRoleStatus");
  if (statusEl) statusEl.textContent = `Role: ${role}`;

  // Fetch updated permissions from server and re-gate
  fetch("/api/auth/me")
    .then((r) => r.json())
    .then((envelope) => {
      const data = envelope.data || {};
      state.rbac.permissions = data.permissions || [];
      applyRbacGating();
      if (role === "admin") {
        loadAdminUsers();
      }
    })
    .catch(() => {
      applyRbacGating();
      if (role === "admin") {
        loadAdminUsers();
      }
    });
}

/**
 * Hides sections tagged with data-rbac-require when the active role
 * lacks the required permission, and shows them when it is granted.
 * Also disables/hides individual action buttons via data-rbac-action.
 * Elements with data-rbac-patient-only are shown only for the patient role.
 */
function applyRbacGating() {
  const role = state.rbac.role;

  // Section-level gating  ── data-rbac-require="action"
  document.querySelectorAll("[data-rbac-require]").forEach((el) => {
    const action = el.dataset.rbacRequire;
    const allowed = canPerform(role, action);
    el.hidden = !allowed;
    el.setAttribute("aria-hidden", String(!allowed));
  });

  // Patient-only elements  ── data-rbac-patient-only
  document.querySelectorAll("[data-rbac-patient-only]").forEach((el) => {
    const isPatient = role === "patient";
    el.hidden = !isPatient;
    el.setAttribute("aria-hidden", String(!isPatient));
  });

  // Staff/admin-only elements  ── data-rbac-staff-only
  document.querySelectorAll("[data-rbac-staff-only]").forEach((el) => {
    const isStaffOrAdmin = role === "staff" || role === "admin";
    el.hidden = !isStaffOrAdmin;
    el.setAttribute("aria-hidden", String(!isStaffOrAdmin));
  });

  // Button-level gating  ── data-rbac-action="action"
  document.querySelectorAll("[data-rbac-action]").forEach((btn) => {
    const action = btn.dataset.rbacAction;
    const allowed = canPerform(role, action);
    btn.disabled = !allowed;
    btn.title = allowed ? "" : `Requires permission: ${action}`;
  });
}

/**
 * Client-side permission check mirroring the server matrix.
 * The server is the authoritative source; this provides immediate UI feedback.
 */
const CLIENT_PERMISSION_MATRIX = {
  "appointments:search":    ["patient", "staff", "admin"],
  "appointments:view":      ["patient", "staff", "admin"],
  "appointments:book":      ["patient", "staff", "admin"],
  "appointments:checkout":  ["patient", "staff", "admin"],
  "appointments:resend":    ["staff", "admin"],
  "calendar:read":          ["patient", "staff", "admin"],
  "integrations:connect":   ["patient", "admin"],
  "integrations:disconnect": ["patient", "admin"],
  "clinical:view_profile":       ["staff", "admin"],
  "clinical:upload_document":    ["staff", "admin"],
  "clinical:process_document":   ["staff", "admin"],
  "clinical:view_conflicts":     ["staff", "admin"],
  "clinical:code_review":        ["staff", "admin"],
  "clinical:manage_thresholds":  ["admin"],
  "clinical:view_allergy_conflicts": ["staff", "admin"],
  "clinical:view_suggestions":   ["staff", "admin"],
  "clinical:generate_suggestions": ["staff", "admin"],
  "clinical:resolve_conflict":   ["staff", "admin"],
  "admin:dashboard":  ["admin"],
  "admin:ops_jobs":   ["admin"],
  "admin:audit_logs": ["staff", "admin"],
  "admin:user_management": ["admin"],
  "admin:change_log": ["admin"],
  "staff:queue_view": ["staff", "admin"],
  "staff:checkin":    ["staff", "admin"],
};

function canPerform(role, action) {
  const allowed = CLIENT_PERMISSION_MATRIX[action];
  return Array.isArray(allowed) && allowed.includes(role);
}

// =============================================================================
// EP-005 US-047: Admin User Management (task_047_001 – task_047_003)
// =============================================================================

async function loadAdminUsers() {
  if (!elements.userListContainer) return;
  elements.userListContainer.innerHTML = '<p class="muted-text">Loading…</p>';
  setUserMgmtStatus("");
  try {
    const payload = await fetchJson("/api/admin/users");
    if (!payload.success) {
      setUserMgmtStatus(payload.error?.message || "Failed to load users.");
      elements.userListContainer.innerHTML = '<p class="muted-text">Could not load user list.</p>';
      return;
    }
    state.adminUsers.users = payload.data || [];
    renderUserList();
  } catch {
    setUserMgmtStatus("User list unavailable.");
    elements.userListContainer.innerHTML = '<p class="muted-text">Could not load user list.</p>';
  }
}

function renderUserList() {
  const { query, role, status } = state.adminUsers.filter;
  const filtered = state.adminUsers.users.filter((u) => {
    if (query && !u.id.toLowerCase().includes(query) && !(u.email || "").toLowerCase().includes(query)) return false;
    if (role && u.role !== role) return false;
    if (status && u.status !== status) return false;
    return true;
  });

  if (!elements.userListContainer) return;

  if (!filtered.length) {
    elements.userListContainer.innerHTML = '<p class="muted-text">No users match the current filters.</p>';
    return;
  }

  elements.userListContainer.innerHTML = filtered.map((u) => {
    const isDeactivated = u.status === "inactive";
    const rowCls = isDeactivated ? "user-row user-row--deactivated" : "user-row";
    return `
      <div class="${rowCls}" data-user-id="${escHtml(u.id)}">
        <div class="user-row__info">
          <div class="user-row__id">${escHtml(u.id)}</div>
          <div class="user-row__email">${escHtml(u.email || "—")}</div>
        </div>
        <span class="role-badge">${escHtml(u.role)}</span>
        <span class="status-badge status-badge--${escHtml(u.status || "active")}">${escHtml(u.status || "active")}</span>
        <div class="user-row-actions">
          <button class="ghost-btn" type="button" data-action="edit-role" data-uid="${escHtml(u.id)}" data-current-role="${escHtml(u.role)}">Edit Role</button>
          <button class="ghost-btn" type="button" data-action="edit-status" data-uid="${escHtml(u.id)}" data-current-status="${escHtml(u.status || "active")}">Edit Status</button>
        </div>
      </div>
    `;
  }).join("");

  elements.userListContainer.querySelectorAll("button[data-action]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const uid = btn.dataset.uid;
      if (btn.dataset.action === "edit-role") {
        openEditRoleDialog(uid, btn.dataset.currentRole);
      } else {
        openEditStatusDialog(uid, btn.dataset.currentStatus);
      }
    });
  });
}

function openEditRoleDialog(userId, currentRole) {
  elements.editRoleUserId.textContent = userId;
  elements.editRoleSelect.value = currentRole;
  elements.editRoleReason.value = "";
  elements.editRoleStatus.textContent = "";
  elements.editRoleDialog._targetUserId = userId;
  elements.editRoleDialog.showModal();
}

async function onConfirmEditRole() {
  const userId = elements.editRoleDialog._targetUserId;
  const newRole = elements.editRoleSelect.value;
  const reason = elements.editRoleReason.value.trim();
  elements.editRoleStatus.textContent = "Saving…";
  try {
    const payload = await patchJson(`/api/admin/users/${encodeURIComponent(userId)}/role`, { role: newRole, reason });
    if (!payload.success) {
      elements.editRoleStatus.textContent = payload.error?.message || "Failed to update role.";
      return;
    }
    elements.editRoleDialog.close();
    setUserMgmtStatus(`Role updated for ${userId}.`);
    await loadAdminUsers();
  } catch {
    elements.editRoleStatus.textContent = "Request failed.";
  }
}

function openEditStatusDialog(userId, currentStatus) {
  elements.editStatusUserId.textContent = userId;
  elements.editStatusSelect.value = currentStatus;
  elements.editStatusReason.value = "";
  elements.editStatusStatus.textContent = "";
  elements.deactivateConfirmArea.hidden = currentStatus !== "inactive";
  elements.deactivateConfirmCheck.checked = false;
  elements.editStatusDialog._targetUserId = userId;
  elements.editStatusDialog.showModal();
}

async function onConfirmEditStatus() {
  const userId = elements.editStatusDialog._targetUserId;
  const newStatus = elements.editStatusSelect.value;
  const reason = elements.editStatusReason.value.trim();

  if (newStatus === "inactive" && !elements.deactivateConfirmCheck.checked) {
    elements.editStatusStatus.textContent = "Please check the confirmation box before deactivating.";
    return;
  }

  elements.editStatusStatus.textContent = "Saving…";
  try {
    const payload = await patchJson(`/api/admin/users/${encodeURIComponent(userId)}/status`, { status: newStatus, reason });
    if (!payload.success) {
      elements.editStatusStatus.textContent = payload.error?.message || "Failed to update status.";
      return;
    }
    elements.editStatusDialog.close();
    setUserMgmtStatus(`Status updated for ${userId}.`);
    await loadAdminUsers();
  } catch {
    elements.editStatusStatus.textContent = "Request failed.";
  }
}

async function onCreateUserSubmit() {
  const userId = document.getElementById("newUserId").value.trim();
  const email = document.getElementById("newUserEmail").value.trim();
  const role = document.getElementById("newUserRole").value;
  const status = document.getElementById("newUserStatus").value;

  let valid = true;
  [["newUserId", userId, "User ID is required."],
   ["newUserEmail", email, "Email is required."],
   ["newUserRole", role, "Role is required."]].forEach(([fieldId, val, msg]) => {
    const errEl = document.getElementById(`${fieldId}Error`);
    if (!val) {
      errEl.textContent = msg;
      document.getElementById(fieldId).setAttribute("aria-invalid", "true");
      valid = false;
    } else {
      errEl.textContent = "";
      document.getElementById(fieldId).removeAttribute("aria-invalid");
    }
  });
  if (!valid) return;

  elements.createUserFormStatus.textContent = "Creating…";
  try {
    const response = await fetch("/api/admin/users", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ userId, email, role, status }),
    });
    const payload = await response.json();
    if (!payload.success) {
      elements.createUserFormStatus.textContent = payload.error?.message || "Failed to create user.";
      return;
    }
    elements.createUserDialog.close();
    setUserMgmtStatus(`User '${userId}' created.`);
    await loadAdminUsers();
  } catch {
    elements.createUserFormStatus.textContent = "Request failed.";
  }
}

async function patchJson(url, payload) {
  const response = await fetch(url, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return response.json();
}

function setUserMgmtStatus(msg) {
  if (elements.userMgmtStatus) {
    elements.userMgmtStatus.textContent = msg;
  }
}

// =============================================================================
// EP-006 US-053 through US-060: Patient Dashboard & Admin Operational Dashboard
// =============================================================================

// --- Element references for EP-006 -----------------------------------------
const dashElements = {
  refreshDashboardButton: document.getElementById("refreshDashboardButton"),
  upcomingAppointmentsList: document.getElementById("upcomingAppointmentsList"),
  upcomingEmptyState: document.getElementById("upcomingEmptyState"),
  upcomingCountBadge: document.getElementById("upcomingCountBadge"),
  appointmentHistoryList: document.getElementById("appointmentHistoryList"),
  historyEmptyState: document.getElementById("historyEmptyState"),
  healthProfileSummary: document.getElementById("healthProfileSummary"),
  refreshHealthProfileButton: document.getElementById("refreshHealthProfileButton"),
  reportProfileDiscrepancyButton: document.getElementById("reportProfileDiscrepancyButton"),
  dashFileInput: document.getElementById("dashFileInput"),
  dashFileLabel: document.getElementById("dashFileLabel"),
  dashUploadButton: document.getElementById("dashUploadButton"),
  dashUploadProgress: document.getElementById("dashUploadProgress"),
  dashUploadProgressFill: document.getElementById("dashUploadProgressFill"),
  dashUploadStatus: document.getElementById("dashUploadStatus"),
  documentsList: document.getElementById("documentsList"),
  documentsCountBadge: document.getElementById("documentsCountBadge"),
  notifEmailToggle: document.getElementById("notifEmailToggle"),
  notifSmsToggle: document.getElementById("notifSmsToggle"),
  notifDndToggle: document.getElementById("notifDndToggle"),
  saveNotifPrefsButton: document.getElementById("saveNotifPrefsButton"),
  notifPrefsStatus: document.getElementById("notifPrefsStatus"),
  dashboardStatus: document.getElementById("dashboardStatus"),
  // US-060 admin operational dashboard
  refreshAdminMetricsButton: document.getElementById("refreshAdminMetricsButton"),
  metricsDateFrom: document.getElementById("metricsDateFrom"),
  metricsDateTo: document.getElementById("metricsDateTo"),
  metricsLocation: document.getElementById("metricsLocation"),
  applyMetricsFiltersButton: document.getElementById("applyMetricsFiltersButton"),
  clearMetricsFiltersButton: document.getElementById("clearMetricsFiltersButton"),
  kpiUtilization: document.getElementById("kpiUtilization"),
  kpiNoShow: document.getElementById("kpiNoShow"),
  kpiAvgWait: document.getElementById("kpiAvgWait"),
  kpiTotal: document.getElementById("kpiTotal"),
  adminProviderTableWrap: document.getElementById("adminProviderTableWrap"),
  adminProviderTableBody: document.getElementById("adminProviderTableBody"),
  adminMetricsLastUpdated: document.getElementById("adminMetricsLastUpdated"),
  adminOpsMetricsStatus: document.getElementById("adminOpsMetricsStatus"),
  // US-067 auto-refresh
  adminAutoRefreshToggle: document.getElementById("adminAutoRefreshToggle"),
  adminAutoRefreshStatus: document.getElementById("adminAutoRefreshStatus"),
  // US-068 provider filter
  metricsProvider: document.getElementById("metricsProvider"),
  // US-069 CSV export
  exportCsvButton: document.getElementById("exportCsvButton"),
  // US-061 no-show detail
  kpiNoShowDetail: document.getElementById("kpiNoShowDetail"),
  kpiNoShowDelta: document.getElementById("kpiNoShowDelta"),
  // US-062 wait-time warning
  kpiWaitWarning: document.getElementById("kpiWaitWarning"),
  kpiP95Wait: document.getElementById("kpiP95Wait"),
  // US-064 intake
  kpiIntakeRate: document.getElementById("kpiIntakeRate"),
  kpiIntakeLowFlag: document.getElementById("kpiIntakeLowFlag"),
  // US-065 insurance verification
  kpiInsVerified: document.getElementById("kpiInsVerified"),
  kpiInsPending: document.getElementById("kpiInsPending"),
  kpiInsFailed: document.getElementById("kpiInsFailed"),
  kpiInsIssueFlag: document.getElementById("kpiInsIssueFlag"),
  // US-066 AI-human agreement
  kpiAgreementRate: document.getElementById("kpiAgreementRate"),
  agreementByCategory: document.getElementById("agreementByCategory"),
  // US-063 utilization breakdown
  adminUtilBreakdownWrap: document.getElementById("adminUtilBreakdownWrap"),
  adminUtilBreakdownBody: document.getElementById("adminUtilBreakdownBody"),
  adminUtilEmptyState: document.getElementById("adminUtilEmptyState"),
};

// --- EP-006 initialisation (called from bootstrap()) -----------------------
async function initDashboard() {
  bindDashboardEvents();
  await Promise.all([
    loadUpcomingAppointments(),
    loadAppointmentHistory(),
    loadHealthProfile(),
    loadPatientDocuments(),
    loadNotificationPrefs(),
  ]);
}

function bindDashboardEvents() {
  dashElements.refreshDashboardButton?.addEventListener("click", () => {
    Promise.all([
      loadUpcomingAppointments(),
      loadAppointmentHistory(),
      loadHealthProfile(),
      loadPatientDocuments(),
      loadNotificationPrefs(),
    ]);
  });

  dashElements.refreshHealthProfileButton?.addEventListener("click", loadHealthProfile);

  dashElements.reportProfileDiscrepancyButton?.addEventListener("click", () => {
    alert("Thank you. A support request has been flagged for a clinical data review.\n\nPlease contact your care team if you need urgent assistance.");
  });

  dashElements.dashFileInput?.addEventListener("change", () => {
    const file = dashElements.dashFileInput.files[0];
    if (file) {
      dashElements.dashFileLabel.textContent = file.name;
    }
  });

  dashElements.dashUploadButton?.addEventListener("click", handleDashDocumentUpload);

  dashElements.saveNotifPrefsButton?.addEventListener("click", saveNotificationPrefs);

  // US-060 admin metrics
  dashElements.applyMetricsFiltersButton?.addEventListener("click", loadAllAdminMetrics);
  dashElements.clearMetricsFiltersButton?.addEventListener("click", () => {
    if (dashElements.metricsDateFrom) dashElements.metricsDateFrom.value = "";
    if (dashElements.metricsDateTo) dashElements.metricsDateTo.value = "";
    if (dashElements.metricsLocation) dashElements.metricsLocation.value = "";
    if (dashElements.metricsProvider) dashElements.metricsProvider.value = "";
    loadAllAdminMetrics();
  });
  dashElements.refreshAdminMetricsButton?.addEventListener("click", loadAllAdminMetrics);
  // US-067 auto-refresh toggle
  dashElements.adminAutoRefreshToggle?.addEventListener("change", () => {
    if (dashElements.adminAutoRefreshToggle.checked) _startAdminAutoRefresh();
    else _stopAdminAutoRefresh();
  });
  // US-069 CSV export
  dashElements.exportCsvButton?.addEventListener("click", handleCsvExport);
}

// Extend the top-level bootstrap to include EP-006 dashboard init.
const _origBootstrap = bootstrap;
// Override bootstrap (already called, so we attach to page load):
document.addEventListener("DOMContentLoaded", () => {
  initDashboard().catch(console.error);
  loadFilterOptions().catch(console.error);
  loadAllAdminMetrics();
  _startAdminAutoRefresh();
});

// --- US-054: Upcoming Appointments ------------------------------------------

async function loadUpcomingAppointments() {
  try {
    const res = await fetch("/api/patient/appointments/upcoming", {
      headers: rbacHeaders(),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed to load");
    renderUpcomingAppointments(json.data);
  } catch (err) {
    if (dashElements.upcomingAppointmentsList) {
      dashElements.upcomingAppointmentsList.innerHTML = `<p class="error-text">Could not load upcoming appointments.</p>`;
    }
  }
}

function renderUpcomingAppointments(data) {
  const list = dashElements.upcomingAppointmentsList;
  const empty = dashElements.upcomingEmptyState;
  const badge = dashElements.upcomingCountBadge;
  if (!list) return;

  const rawItems = data.items || data.appointments || [];
  const items = Array.isArray(rawItems) ? rawItems : Object.values(rawItems || {});
  if (badge) badge.textContent = data.total || items.length || 0;

  if (!items.length) {
    list.innerHTML = "";
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;

  list.innerHTML = items.map((appt) => {
    const apptDate = appt.appointment_date || appt.appointmentDate || appt.date || "";
    const start = appt.start_time || appt.startTime || appt.time || "";
    const end = appt.end_time || appt.endTime || "";
    const provider = appt.provider_name || appt.providerName || appt.provider || "";
    const specialty = appt.specialty || appt.specialty_name || "";
    const status = appt.status || appt.appointment_status || "booked";
    const actions = [];
    if (appt.can_reschedule) {
      actions.push(`<button class="ghost-btn dash-action-btn" type="button" aria-label="Reschedule appointment ${appt.id}" data-appt-id="${appt.id}" data-action="reschedule">Reschedule</button>`);
    }
    if (appt.can_cancel) {
      actions.push(`<button class="ghost-btn dash-action-btn dash-action-btn--danger" type="button" aria-label="Cancel appointment ${appt.id}" data-appt-id="${appt.id}" data-action="cancel">Cancel</button>`);
    }
    actions.push(`<button class="ghost-btn dash-action-btn" type="button" aria-label="View appointment ${appt.id} details" data-appt-id="${appt.id}" data-action="view">View details</button>`);
    return `
      <article class="appt-item" aria-label="Appointment on ${escHtml(apptDate)}">
        <div class="appt-item__meta">
          <span class="appt-item__date">${escHtml(apptDate)}</span>
          <span class="appt-item__time">${escHtml(start)}${end ? ` – ${escHtml(end)}` : ""}</span>
          <span class="appt-item__provider">${escHtml(provider)}</span>
          <span class="appt-item__specialty">${escHtml(specialty)}</span>
          <span class="appt-item__location">${escHtml(appt.location || "")}</span>
          <span class="badge badge--${status === 'booked' ? 'success' : 'default'}">${escHtml(status)}</span>
        </div>
        <div class="appt-item__actions" role="group" aria-label="Actions for appointment ${appt.id}">${actions.join("")}</div>
      </article>`;
  }).join("");

  list.querySelectorAll(".dash-action-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const action = btn.dataset.action;
      const id = btn.dataset.apptId;
      if (action === "reschedule") {
        alert(`Reschedule workflow for appointment #${id} — in progress.`);
      } else if (action === "cancel") {
        if (confirm(`Cancel appointment #${id}? This cannot be undone.`)) {
          alert(`Cancel request sent for appointment #${id}.`);
        }
      } else {
        alert(`Appointment #${id} detail view — select the slot in the calendar above to see full details.`);
      }
    });
  });
}

// --- US-055: Appointment History --------------------------------------------

async function loadAppointmentHistory() {
  try {
    const res = await fetch("/api/patient/appointments/history", {
      headers: rbacHeaders(),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed to load");
    renderAppointmentHistory(json.data);
  } catch (err) {
    if (dashElements.appointmentHistoryList) {
      dashElements.appointmentHistoryList.innerHTML = `<p class="error-text">Could not load appointment history.</p>`;
    }
  }
}

function renderAppointmentHistory(data) {
  const list = dashElements.appointmentHistoryList;
  const empty = dashElements.historyEmptyState;
  if (!list) return;

  const rawItems = data.items || data.appointments || [];
  const items = Array.isArray(rawItems) ? rawItems : Object.values(rawItems || {});
  if (!items.length) {
    list.innerHTML = "";
    if (empty) empty.hidden = false;
    return;
  }
  if (empty) empty.hidden = true;

  list.innerHTML = items.slice(0, 10).map((appt) => {
    const apptDate = appt.appointment_date || appt.appointmentDate || appt.date || "";
    const provider = appt.provider_name || appt.providerName || appt.provider || "";
    const specialty = appt.specialty || appt.specialty_name || "";
    const status = appt.status || appt.appointment_status || "completed";
    const notesHtml = appt.notes_available
      ? `<a href="${escHtml(appt.notes_url || "#")}" class="ghost-btn" target="_blank" rel="noopener noreferrer">View notes</a>`
      : `<span class="muted-text" title="${escHtml(appt.notes_unavailable_reason || "Notes not yet released")}">Notes not released</span>`;
    return `
      <article class="appt-item appt-item--history" aria-label="Past appointment on ${escHtml(apptDate)}">
        <div class="appt-item__meta">
          <span class="appt-item__date">${escHtml(apptDate)}</span>
          <span class="appt-item__provider">${escHtml(provider)}</span>
          <span class="appt-item__specialty">${escHtml(specialty)}</span>
          <span class="badge badge--default">${escHtml(status)}</span>
        </div>
        <div class="appt-item__notes">${notesHtml}</div>
      </article>`;
  }).join("");
}

// --- US-056: Health Profile -------------------------------------------------

async function loadHealthProfile() {
  try {
    const res = await fetch("/api/patient/health-profile", {
      headers: rbacHeaders(),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed to load");
    renderHealthProfile(json.data);
  } catch (err) {
    if (dashElements.healthProfileSummary) {
      dashElements.healthProfileSummary.innerHTML = `<p class="muted-text">Health profile unavailable.</p>`;
    }
  }
}

function renderHealthProfile(data) {
  const container = dashElements.healthProfileSummary;
  if (!container) return;

  const section = (title, items, tooltip) => {
    if (!items || !items.length) {
      return `<div class="health-section"><h4 class="health-section__title" title="${escHtml(tooltip || "")}">${escHtml(title)}</h4><p class="muted-text">None on record.</p></div>`;
    }
    const listItems = items.map((item) =>
      `<li class="health-item"><span class="health-item__label">${escHtml(item.label || item.display_value || "")}</span>
       ${item.status ? `<span class="health-item__status">${escHtml(item.status)}</span>` : ""}</li>`
    ).join("");
    return `<div class="health-section"><h4 class="health-section__title" title="${escHtml(tooltip || "")}">${escHtml(title)}</h4><ul class="health-list">${listItems}</ul></div>`;
  };

  container.innerHTML = `
    <div class="health-profile-grid">
      ${section("Medications", data.medications, "Current active medications on record")}
      ${section("Allergies", data.allergies, "Known patient allergies")}
      ${section("Diagnoses", data.diagnoses, "Active diagnoses")}
      ${section("Chronic Conditions", data.chronic_conditions, "Long-term conditions")}
      ${data.alerts?.length ? `<div class="health-alerts">${data.alerts.map(a => `<div class="health-alert-chip" role="alert">⚠ ${escHtml(a.label || "")}</div>`).join("")}</div>` : ""}
    </div>
    <p class="muted-text health-version">Version ${escHtml(String(data.version || 0))} · Updated ${escHtml(data.last_updated || "")}</p>`;
}

// --- US-057: Document Upload ------------------------------------------------

async function loadPatientDocuments() {
  try {
    const res = await fetch("/api/patient/documents", {
      headers: rbacHeaders(),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed to load");
    renderPatientDocuments(json.data);
  } catch (err) {
    if (dashElements.documentsList) {
      dashElements.documentsList.innerHTML = `<p class="muted-text">Documents unavailable.</p>`;
    }
  }
}

function renderPatientDocuments(data) {
  const list = dashElements.documentsList;
  const badge = dashElements.documentsCountBadge;
  if (!list) return;

  const items = data.items || [];
  if (badge) badge.textContent = data.total || 0;

  if (!items.length) {
    list.innerHTML = `<p class="muted-text">No documents uploaded yet.</p>`;
    return;
  }
  list.innerHTML = `<ul class="documents-list">${items.map((doc) => `
    <li class="doc-item" aria-label="Document ${escHtml(doc.file_name || "")}">
      <span class="doc-item__name">${escHtml(doc.file_name || "")}</span>
      <span class="doc-item__type">${escHtml(doc.file_type || "")}</span>
      <span class="doc-item__status badge badge--${doc.processing_status === 'complete' ? 'success' : 'default'}">${escHtml(doc.processing_status || "")}</span>
      <span class="doc-item__date muted-text">${escHtml(doc.uploaded_at || "")}</span>
    </li>`).join("")}</ul>`;
}

const _ALLOWED_DOC_TYPES = new Set(["application/pdf", "image/jpeg", "image/png",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]);
const _MAX_DOC_SIZE = 20 * 1024 * 1024;

async function handleDashDocumentUpload() {
  const file = dashElements.dashFileInput?.files?.[0];
  if (!file) {
    setDashUploadStatus("Please select a file first.");
    return;
  }
  if (!_ALLOWED_DOC_TYPES.has(file.type)) {
    setDashUploadStatus("Unsupported file type. Please upload a PDF, JPG, PNG, or DOCX file.");
    return;
  }
  if (file.size > _MAX_DOC_SIZE) {
    setDashUploadStatus("File is too large. Maximum size is 20 MB.");
    return;
  }

  if (dashElements.dashUploadProgress) dashElements.dashUploadProgress.hidden = false;
  if (dashElements.dashUploadProgressFill) dashElements.dashUploadProgressFill.style.width = "0%";
  setDashUploadStatus("Uploading…");

  try {
    // Simulate progress since fetch does not expose upload progress without XHR
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress = Math.min(progress + 20, 90);
      if (dashElements.dashUploadProgressFill) {
        dashElements.dashUploadProgressFill.style.width = `${progress}%`;
        dashElements.dashUploadProgressFill.closest("[role='progressbar']")?.setAttribute("aria-valuenow", progress);
      }
    }, 150);

    const arrayBuffer = await file.arrayBuffer();
    const res = await fetch(`/api/clinical/documents/upload?fileName=${encodeURIComponent(file.name)}&patientId=1`, {
      method: "POST",
      headers: { "Content-Type": file.type, ...rbacHeaders() },
      body: arrayBuffer,
    });
    clearInterval(progressInterval);
    if (dashElements.dashUploadProgressFill) dashElements.dashUploadProgressFill.style.width = "100%";

    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Upload failed");

    setDashUploadStatus(`✓ ${file.name} uploaded successfully.`);
    if (dashElements.dashFileInput) dashElements.dashFileInput.value = "";
    if (dashElements.dashFileLabel) dashElements.dashFileLabel.textContent = "Choose file (PDF, JPG, PNG, DOCX · max 20 MB)";
    await loadPatientDocuments();
  } catch (err) {
    setDashUploadStatus(`Upload failed: ${err.message}`);
  } finally {
    setTimeout(() => {
      if (dashElements.dashUploadProgress) dashElements.dashUploadProgress.hidden = true;
    }, 1500);
  }
}

function setDashUploadStatus(msg) {
  if (dashElements.dashUploadStatus) dashElements.dashUploadStatus.textContent = msg;
}

// --- US-058: Notification Preferences ----------------------------------------

async function loadNotificationPrefs() {
  try {
    const res = await fetch("/api/patient/notifications/preferences", {
      headers: rbacHeaders(),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed to load");
    applyNotificationPrefs(json.data);
  } catch (err) {
    if (dashElements.notifPrefsStatus) {
      dashElements.notifPrefsStatus.textContent = "Could not load notification preferences.";
    }
  }
}

function applyNotificationPrefs(prefs) {
  if (dashElements.notifEmailToggle) dashElements.notifEmailToggle.checked = !!prefs.email;
  if (dashElements.notifSmsToggle) dashElements.notifSmsToggle.checked = !!prefs.sms;
  if (dashElements.notifDndToggle) dashElements.notifDndToggle.checked = !!prefs.do_not_disturb;
}

async function saveNotificationPrefs() {
  const prefs = {
    email: dashElements.notifEmailToggle?.checked ?? true,
    sms: dashElements.notifSmsToggle?.checked ?? true,
    do_not_disturb: dashElements.notifDndToggle?.checked ?? false,
  };
  try {
    const res = await fetch("/api/patient/notifications/preferences", {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...rbacHeaders() },
      body: JSON.stringify(prefs),
    });
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Save failed");
    if (dashElements.notifPrefsStatus) dashElements.notifPrefsStatus.textContent = "✓ Preferences saved.";
    applyNotificationPrefs(json.data);
  } catch (err) {
    if (dashElements.notifPrefsStatus) dashElements.notifPrefsStatus.textContent = `Save failed: ${err.message}`;
  }
}

// --- US-060: Admin Operational Dashboard ------------------------------------

function _adminFilterParams() {
  const dateFrom = dashElements.metricsDateFrom?.value || "";
  const dateTo = dashElements.metricsDateTo?.value || "";
  const location = dashElements.metricsLocation?.value || "";
  const providerId = dashElements.metricsProvider?.value || "";
  const params = new URLSearchParams();
  if (dateFrom) params.set("date_from", dateFrom);
  if (dateTo) params.set("date_to", dateTo);
  if (location) params.set("location", location);
  if (providerId) params.set("provider_id", providerId);
  return params;
}

async function loadAdminOperationalMetrics() {
  if (!dashElements.kpiUtilization) return;  // Not admin view
  const params = _adminFilterParams();

  try {
    const res = await fetch(`/api/admin/operational-metrics?${params.toString()}`, {
      headers: rbacHeaders(),
    });
    if (res.status === 403) return;  // Not an admin session — silently skip
    const json = await res.json();
    if (!json.success) throw new Error(json.error?.message || "Failed");
    renderAdminMetrics(json.data);
  } catch (err) {
    if (dashElements.adminOpsMetricsStatus) {
      dashElements.adminOpsMetricsStatus.textContent = `Could not load metrics: ${err.message}`;
    }
  }
}

function renderAdminMetrics(data) {
  if (dashElements.kpiUtilization) dashElements.kpiUtilization.textContent = `${data.utilization_rate ?? "—"}%`;
  if (dashElements.kpiNoShow) dashElements.kpiNoShow.textContent = `${data.no_show_rate ?? "—"}%`;
  if (dashElements.kpiAvgWait) dashElements.kpiAvgWait.textContent = data.avg_wait_minutes ?? "—";
  if (dashElements.kpiTotal) dashElements.kpiTotal.textContent = data.total_appointments ?? "—";

  if (dashElements.adminMetricsLastUpdated) {
    dashElements.adminMetricsLastUpdated.textContent = `Last updated: ${data.last_updated || "—"}`;
  }

  const tbody = dashElements.adminProviderTableBody;
  const wrap = dashElements.adminProviderTableWrap;
  if (tbody && data.by_provider?.length) {
    tbody.innerHTML = data.by_provider.map((row) =>
      `<tr><td>${escHtml(row.provider)}</td><td>${escHtml(String(row.count))}</td></tr>`
    ).join("");
    if (wrap) wrap.hidden = false;
  } else if (wrap) {
    wrap.hidden = true;
  }
}

// --- RBAC helper (reuse existing state) -------------------------------------
function rbacHeaders() {
  const role = state?.rbac?.role || "patient";
  const h = { "X-Role": role };
  if (role === "admin" && state?.rbac?.adminId) h["X-Admin-Id"] = state.rbac.adminId;
  return h;
}

// ===========================================================================
// EP-006 US-061–069: Admin Analytics Extension
// ===========================================================================

// --- US-067: Auto-refresh (5-min cadence, Page Visibility API throttling) ---
const _AUTO_REFRESH_MS = 5 * 60 * 1000;
let _adminAutoRefreshTimer = null;

function _startAdminAutoRefresh() {
  _stopAdminAutoRefresh();
  if (!dashElements.adminAutoRefreshToggle?.checked) return;
  _adminAutoRefreshTimer = setInterval(() => {
    if (document.visibilityState === "visible") {
      loadAllAdminMetrics();
    }
  }, _AUTO_REFRESH_MS);
  if (dashElements.adminAutoRefreshStatus) {
    dashElements.adminAutoRefreshStatus.textContent = "Auto-refresh: on (every 5 min)";
  }
}

function _stopAdminAutoRefresh() {
  if (_adminAutoRefreshTimer) {
    clearInterval(_adminAutoRefreshTimer);
    _adminAutoRefreshTimer = null;
  }
  if (dashElements.adminAutoRefreshStatus) {
    dashElements.adminAutoRefreshStatus.textContent = "Auto-refresh: off";
  }
}

// Pause refresh when tab is hidden (US-067 FE-4)
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "hidden") {
    if (_adminAutoRefreshTimer) {
      clearInterval(_adminAutoRefreshTimer);
      _adminAutoRefreshTimer = null;
    }
  } else if (dashElements.adminAutoRefreshToggle?.checked) {
    _startAdminAutoRefresh();
  }
});

// --- US-068: Load filter options (populate provider dropdown) ---
async function loadFilterOptions() {
  if (!dashElements.metricsProvider) return;
  try {
    const res = await fetch("/api/admin/filter-options", { headers: rbacHeaders() });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const select = dashElements.metricsProvider;
    json.data.providers.forEach((p) => {
      const opt = document.createElement("option");
      opt.value = p.id;
      opt.textContent = `${escHtml(p.name)}${p.credentials ? " (" + escHtml(p.credentials) + ")" : ""}`;
      select.appendChild(opt);
    });
  } catch (_) { /* non-critical */ }
}

// --- Aggregate loader: runs all admin metric endpoints in parallel ---
async function loadAllAdminMetrics() {
  await Promise.allSettled([
    loadAdminOperationalMetrics(),
    loadNoShowMetrics(),
    loadWaitTimeMetrics(),
    loadUtilizationMetrics(),
    loadIntakeMetrics(),
    loadInsuranceMetrics(),
    loadAgreementMetrics(),
  ]);
}

// --- US-061: No-show rate with trend and prior-period comparison ---
async function loadNoShowMetrics() {
  if (!dashElements.kpiNoShowDetail) return;
  try {
    const res = await fetch(`/api/admin/metrics/no-show?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    dashElements.kpiNoShowDetail.textContent = `${d.rate ?? "—"}%`;
    if (dashElements.kpiNoShowDelta) {
      const delta = d.delta ?? 0;
      const sign = delta > 0 ? "▲" : delta < 0 ? "▼" : "=";
      dashElements.kpiNoShowDelta.textContent = ` ${sign}${Math.abs(delta)}%`;
      dashElements.kpiNoShowDelta.className = `kpi-delta kpi-delta--${delta > 0 ? "up" : delta < 0 ? "down" : "flat"}`;
    }
  } catch (_) { /* non-critical */ }
}

// --- US-062: Wait time with P95 and threshold warning ---
async function loadWaitTimeMetrics() {
  if (!dashElements.kpiP95Wait) return;
  try {
    const res = await fetch(`/api/admin/metrics/wait-time?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    dashElements.kpiP95Wait.textContent = d.p95_wait_minutes ?? "—";
    if (dashElements.kpiWaitWarning) {
      dashElements.kpiWaitWarning.hidden = !d.threshold_exceeded;
    }
  } catch (_) { /* non-critical */ }
}

// --- US-063: Utilization breakdown by specialty ---
async function loadUtilizationMetrics() {
  if (!dashElements.adminUtilBreakdownBody) return;
  try {
    const res = await fetch(`/api/admin/metrics/utilization?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    const tbody = dashElements.adminUtilBreakdownBody;
    const wrap = dashElements.adminUtilBreakdownWrap;
    const empty = dashElements.adminUtilEmptyState;
    if (d.by_specialty?.length) {
      tbody.innerHTML = d.by_specialty.map((r) =>
        `<tr>
          <td>${escHtml(r.specialty)}</td>
          <td>${escHtml(String(r.booked))}</td>
          <td>${escHtml(String(r.total))}</td>
          <td>${escHtml(String(r.utilization_rate))}%</td>
        </tr>`
      ).join("");
      if (wrap) wrap.hidden = false;
      if (empty) empty.hidden = true;
    } else {
      if (wrap) wrap.hidden = true;
      if (empty) empty.hidden = false;
    }
  } catch (_) { /* non-critical */ }
}

// --- US-064: Intake completion rate with low-completion warning ---
async function loadIntakeMetrics() {
  if (!dashElements.kpiIntakeRate) return;
  try {
    const res = await fetch(`/api/admin/metrics/intake?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    dashElements.kpiIntakeRate.textContent = `${d.completion_rate ?? "—"}`;
    if (dashElements.kpiIntakeLowFlag) {
      dashElements.kpiIntakeLowFlag.hidden = !d.low_completion_flag;
    }
  } catch (_) { /* non-critical */ }
}

// --- US-065: Insurance verification status ---
async function loadInsuranceMetrics() {
  if (!dashElements.kpiInsVerified) return;
  try {
    const res = await fetch(`/api/admin/metrics/insurance?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    if (dashElements.kpiInsVerified) dashElements.kpiInsVerified.textContent = d.verified ?? "—";
    if (dashElements.kpiInsPending) dashElements.kpiInsPending.textContent = d.pending ?? "—";
    if (dashElements.kpiInsFailed) dashElements.kpiInsFailed.textContent = d.failed ?? "—";
    if (dashElements.kpiInsIssueFlag) dashElements.kpiInsIssueFlag.hidden = !d.issue_flag;
  } catch (_) { /* non-critical */ }
}

// --- US-066: AI-human agreement rate with category breakdown ---
async function loadAgreementMetrics() {
  if (!dashElements.kpiAgreementRate) return;
  try {
    const res = await fetch(`/api/admin/metrics/agreement?${_adminFilterParams()}`, {
      headers: rbacHeaders(),
    });
    if (!res.ok) return;
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    dashElements.kpiAgreementRate.textContent = `${d.agreement_rate ?? "—"}`;
    const ul = dashElements.agreementByCategory;
    if (ul && d.by_category?.length) {
      ul.innerHTML = d.by_category.map((c) =>
        `<li class="analytics-category-item">
          <span class="analytics-category-name">${escHtml(c.category.toUpperCase())}</span>
          <span class="analytics-category-rate">${escHtml(String(c.agreement_rate))}%</span>
        </li>`
      ).join("");
    }
  } catch (_) { /* non-critical */ }
}

// --- US-069: CSV export download ---
async function handleCsvExport() {
  try {
    const btn = dashElements.exportCsvButton;
    if (btn) { btn.disabled = true; btn.textContent = "Exporting…"; }
    const url = `/api/admin/metrics/export?${_adminFilterParams()}`;
    const res = await fetch(url, { headers: rbacHeaders() });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `appointments_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (err) {
    if (dashElements.adminOpsMetricsStatus) {
      dashElements.adminOpsMetricsStatus.textContent = `Export failed: ${err.message}`;
    }
  } finally {
    const btn = dashElements.exportCsvButton;
    if (btn) { btn.disabled = false; btn.textContent = "Export CSV"; }
  }
}
