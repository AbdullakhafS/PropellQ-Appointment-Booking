const state = {
  filters: {
    dateFrom: "",
    dateTo: "",
    timeOfDay: "",
    provider: "",
    specialty: "",
    sortBy: "date",
    sortDir: "asc",
    page: 1,
    pageSize: 10,
  },
  pagination: {
    page: 1,
    totalPages: 1,
    total: 0,
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
  resultsList: document.getElementById("resultsList"),
  statusMessage: document.getElementById("statusMessage"),
  emptyState: document.getElementById("emptyState"),
  filterSummary: document.getElementById("filterSummary"),
  clearFiltersButton: document.getElementById("clearFiltersButton"),
  emptyClearButton: document.getElementById("emptyClearButton"),
  expandRangeButton: document.getElementById("expandRangeButton"),
  prevPageButton: document.getElementById("prevPageButton"),
  nextPageButton: document.getElementById("nextPageButton"),
  pageLabel: document.getElementById("pageLabel"),
  providerDialog: document.getElementById("providerDialog"),
  providerDialogBody: document.getElementById("providerDialogBody"),
};

let providerDebounceHandle;
let searchDebounceHandle;

initialize().catch((error) => {
  console.error(error);
  elements.statusMessage.textContent = "Failed to initialize appointment search.";
});

async function initialize() {
  hydrateFromUrl();
  syncFormWithState();
  await populateSpecialties();
  bindEvents();
  await fetchAndRenderResults();
}

function bindEvents() {
  elements.form.addEventListener("input", (event) => {
    const target = event.target;
    if (!(target instanceof HTMLElement)) {
      return;
    }

    if (target.id === "provider") {
      state.filters.provider = elements.provider.value.trim();
      state.filters.page = 1;
      scheduleProviderSuggestions();
      scheduleSearch();
      return;
    }

    updateStateFromInputs();
    state.filters.page = 1;
    scheduleSearch();
  });

  elements.sortBy.addEventListener("change", () => {
    state.filters.sortBy = elements.sortBy.value;
    state.filters.page = 1;
    fetchAndRenderResults();
  });

  elements.clearFiltersButton.addEventListener("click", () => {
    resetFilters();
  });

  elements.emptyClearButton.addEventListener("click", () => {
    resetFilters();
  });

  elements.expandRangeButton.addEventListener("click", () => {
    if (!state.filters.dateTo) {
      return;
    }

    const currentTo = new Date(state.filters.dateTo);
    currentTo.setDate(currentTo.getDate() + 14);
    state.filters.dateTo = toIsoDate(currentTo);
    elements.dateTo.value = state.filters.dateTo;
    state.filters.page = 1;
    fetchAndRenderResults();
  });

  elements.prevPageButton.addEventListener("click", () => {
    if (state.filters.page <= 1) {
      return;
    }
    state.filters.page -= 1;
    fetchAndRenderResults();
  });

  elements.nextPageButton.addEventListener("click", () => {
    if (state.filters.page >= state.pagination.totalPages) {
      return;
    }
    state.filters.page += 1;
    fetchAndRenderResults();
  });

  elements.provider.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      clearSuggestions();
    }
  });
}

function hydrateFromUrl() {
  const params = new URLSearchParams(window.location.search);
  state.filters.dateFrom = params.get("dateFrom") || "";
  state.filters.dateTo = params.get("dateTo") || "";
  state.filters.timeOfDay = params.get("timeOfDay") || "";
  state.filters.provider = params.get("provider") || "";
  state.filters.specialty = params.get("specialty") || "";
  state.filters.sortBy = params.get("sortBy") || "date";
  state.filters.page = Number(params.get("page") || "1");
}

function syncFormWithState() {
  elements.dateFrom.value = state.filters.dateFrom;
  elements.dateTo.value = state.filters.dateTo;
  elements.timeOfDay.value = state.filters.timeOfDay;
  elements.provider.value = state.filters.provider;
  elements.sortBy.value = state.filters.sortBy;
}

function updateStateFromInputs() {
  state.filters.dateFrom = elements.dateFrom.value;
  state.filters.dateTo = elements.dateTo.value;
  state.filters.timeOfDay = elements.timeOfDay.value;
  state.filters.provider = elements.provider.value.trim();
  state.filters.specialty = elements.specialty.value;
}

function resetFilters() {
  state.filters = {
    ...state.filters,
    dateFrom: "",
    dateTo: "",
    timeOfDay: "",
    provider: "",
    specialty: "",
    page: 1,
    sortBy: "date",
  };

  syncFormWithState();
  elements.specialty.value = "";
  clearSuggestions();
  fetchAndRenderResults();
}

function scheduleProviderSuggestions() {
  window.clearTimeout(providerDebounceHandle);
  providerDebounceHandle = window.setTimeout(() => {
    fetchProviderSuggestions();
  }, 250);
}

function scheduleSearch() {
  window.clearTimeout(searchDebounceHandle);
  searchDebounceHandle = window.setTimeout(() => {
    fetchAndRenderResults();
  }, 250);
}

async function populateSpecialties() {
  const response = await fetch("/api/appointments/specialties");
  const payload = await response.json();
  if (!payload.success) {
    return;
  }

  const fragment = document.createDocumentFragment();
  payload.data.forEach((specialty) => {
    const option = document.createElement("option");
    option.value = specialty.name;
    option.textContent = specialty.name;
    fragment.appendChild(option);
  });
  elements.specialty.appendChild(fragment);

  if (state.filters.specialty) {
    elements.specialty.value = state.filters.specialty;
  }
}

async function fetchProviderSuggestions() {
  const query = state.filters.provider;
  if (query.length < 2) {
    clearSuggestions();
    return;
  }

  const response = await fetch(`/api/providers/suggest?query=${encodeURIComponent(query)}`);
  const payload = await response.json();

  clearSuggestions();
  if (!payload.success || payload.data.length === 0) {
    elements.provider.setAttribute("aria-expanded", "false");
    return;
  }

  const fragment = document.createDocumentFragment();
  payload.data.forEach((provider) => {
    const item = document.createElement("li");
    item.className = "suggestion-item";
    item.setAttribute("role", "option");

    const button = document.createElement("button");
    button.type = "button";
    button.textContent = `${provider.name} (${provider.specialty})`;
    button.addEventListener("click", () => {
      elements.provider.value = provider.name;
      state.filters.provider = provider.name;
      state.filters.page = 1;
      clearSuggestions();
      fetchAndRenderResults();
    });

    item.appendChild(button);
    fragment.appendChild(item);
  });

  elements.providerSuggestions.appendChild(fragment);
  elements.provider.setAttribute("aria-expanded", "true");
}

function clearSuggestions() {
  elements.providerSuggestions.innerHTML = "";
  elements.provider.setAttribute("aria-expanded", "false");
}

async function fetchAndRenderResults() {
  updateStateFromInputs();
  writeUrlState();
  renderSummary();

  elements.statusMessage.textContent = "Loading available appointments...";

  const params = new URLSearchParams();
  Object.entries(state.filters).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      params.set(key, String(value));
    }
  });

  const response = await fetch(`/api/appointments/search?${params.toString()}`);
  const payload = await response.json();

  if (!payload.success) {
    elements.resultsList.innerHTML = "";
    elements.emptyState.hidden = true;
    elements.statusMessage.textContent = payload.error.message;
    return;
  }

  const { items, pagination } = payload.data;
  state.pagination = pagination;
  state.filters.page = pagination.page;

  renderCards(items);
  updatePaginationControls();

  const latency = payload.meta?.latencyMs ?? 0;
  elements.statusMessage.textContent = `${pagination.total} slots found in ${latency}ms.`;

  if (items.length === 0) {
    elements.emptyState.hidden = false;
  } else {
    elements.emptyState.hidden = true;
  }
}

function renderCards(items) {
  elements.resultsList.innerHTML = "";
  if (!items.length) {
    return;
  }

  const fragment = document.createDocumentFragment();
  items.forEach((slot) => {
    const article = document.createElement("article");
    article.className = "card";

    const title = document.createElement("h3");
    title.textContent = `${slot.provider_name} • ${slot.specialty}`;

    const meta = document.createElement("div");
    meta.className = "meta";
    meta.innerHTML = `
      <span>${slot.appointment_date} at ${slot.start_time}</span>
      <span>${slot.location}</span>
      <span>Credentials: ${slot.credentials}</span>
    `;

    const actions = document.createElement("div");
    actions.className = "card-actions";

    const detailsButton = document.createElement("button");
    detailsButton.type = "button";
    detailsButton.className = "ghost-btn";
    detailsButton.textContent = "Provider details";
    detailsButton.addEventListener("click", () => showProviderDetails(slot.provider_id));

    const bookButton = document.createElement("button");
    bookButton.type = "button";
    bookButton.textContent = "Book Now";
    bookButton.addEventListener("click", () => bookAppointment(slot.id));

    actions.append(detailsButton, bookButton);
    article.append(title, meta, actions);
    fragment.appendChild(article);
  });

  elements.resultsList.appendChild(fragment);
}

async function showProviderDetails(providerId) {
  const response = await fetch(`/api/providers/${providerId}`);
  const payload = await response.json();

  if (!payload.success) {
    elements.statusMessage.textContent = "Unable to load provider details.";
    return;
  }

  elements.providerDialogBody.innerHTML = `
    <p><strong>Name:</strong> ${payload.data.name}</p>
    <p><strong>Specialty:</strong> ${payload.data.specialty}</p>
    <p><strong>Credentials:</strong> ${payload.data.credentials}</p>
  `;
  elements.providerDialog.showModal();
}

async function bookAppointment(appointmentId) {
  const response = await fetch(`/api/appointments/${appointmentId}/book`, {
    method: "POST",
  });
  const payload = await response.json();

  if (!payload.success) {
    elements.statusMessage.textContent = payload.error.message;
    return;
  }

  elements.statusMessage.textContent = `Appointment ${appointmentId} booked successfully.`;
  fetchAndRenderResults();
}

function updatePaginationControls() {
  const current = state.pagination.page;
  const totalPages = state.pagination.totalPages;

  elements.pageLabel.textContent = `Page ${current} of ${totalPages}`;
  elements.prevPageButton.disabled = current <= 1;
  elements.nextPageButton.disabled = current >= totalPages;
}

function renderSummary() {
  const parts = [];
  if (state.filters.dateFrom || state.filters.dateTo) {
    parts.push(`Date: ${state.filters.dateFrom || "Any"} to ${state.filters.dateTo || "Any"}`);
  }
  if (state.filters.timeOfDay) {
    parts.push(`Time: ${state.filters.timeOfDay}`);
  }
  if (state.filters.provider) {
    parts.push(`Provider: ${state.filters.provider}`);
  }
  if (state.filters.specialty) {
    parts.push(`Specialty: ${state.filters.specialty}`);
  }

  elements.filterSummary.textContent = parts.length > 0 ? parts.join(" | ") : "No active filters.";
}

function writeUrlState() {
  const params = new URLSearchParams();
  Object.entries(state.filters).forEach(([key, value]) => {
    if (["pageSize", "sortDir"].includes(key)) {
      return;
    }

    if (value !== "" && value !== null && value !== undefined) {
      params.set(key, String(value));
    }
  });

  const newUrl = `${window.location.pathname}?${params.toString()}`;
  window.history.replaceState({}, "", newUrl);
}

function toIsoDate(value) {
  return value.toISOString().slice(0, 10);
}
