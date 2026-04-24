(function () {
  "use strict";

  const PENDING_KEY = "expense-tracker:pending-submission";
  const state = {
    expenses: [],
    allCategories: [],
    selectedCategory: "",
    isSubmitting: false,
  };

  const form = document.querySelector("#expense-form");
  const amountInput = document.querySelector("#amount");
  const categoryInput = document.querySelector("#category");
  const descriptionInput = document.querySelector("#description");
  const dateInput = document.querySelector("#date");
  const submitButton = document.querySelector("#submit-button");
  const submitStatus = document.querySelector("#submit-status");
  const listStatus = document.querySelector("#list-status");
  const refreshButton = document.querySelector("#refresh-button");
  const categoryFilter = document.querySelector("#category-filter");
  const visibleTotal = document.querySelector("#visible-total");
  const expenseRows = document.querySelector("#expense-rows");

  function todayIsoDate() {
    return new Date().toISOString().slice(0, 10);
  }

  function setStatus(element, message, kind) {
    element.textContent = message || "";
    element.dataset.kind = kind || "";
  }

  function normalizePayloadFromForm() {
    return {
      amount: amountInput.value.trim(),
      category: categoryInput.value.trim(),
      description: descriptionInput.value.trim(),
      date: dateInput.value.trim(),
    };
  }

  function fingerprint(payload) {
    return JSON.stringify(payload);
  }

  function validatePayload(payload) {
    if (!payload.amount || !payload.category || !payload.description || !payload.date) {
      return "All fields are required.";
    }
    if (!/^\d+(\.\d{1,2})?$/.test(payload.amount)) {
      return "Amount must be positive with at most two decimal places.";
    }
    if (Number(payload.amount) <= 0) {
      return "Amount must be greater than zero.";
    }
    if (!/^\d{4}-\d{2}-\d{2}$/.test(payload.date)) {
      return "Date must use YYYY-MM-DD format.";
    }
    return "";
  }

  function createIdempotencyKey() {
    if (window.crypto && window.crypto.randomUUID) {
      return window.crypto.randomUUID();
    }
    return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function readPendingSubmission() {
    try {
      const stored = localStorage.getItem(PENDING_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch (_error) {
      localStorage.removeItem(PENDING_KEY);
      return null;
    }
  }

  function writePendingSubmission(pending) {
    localStorage.setItem(PENDING_KEY, JSON.stringify(pending));
  }

  function clearPendingSubmission() {
    localStorage.removeItem(PENDING_KEY);
  }

  function getOrCreatePendingSubmission(payload) {
    const payloadFingerprint = fingerprint(payload);
    const pending = readPendingSubmission();
    if (pending && pending.fingerprint === payloadFingerprint && pending.key) {
      return pending;
    }

    const nextPending = {
      key: createIdempotencyKey(),
      fingerprint: payloadFingerprint,
      payload,
      createdAt: new Date().toISOString(),
    };
    writePendingSubmission(nextPending);
    return nextPending;
  }

  function restorePendingSubmission() {
    const pending = readPendingSubmission();
    if (!pending || !pending.payload) {
      return;
    }

    amountInput.value = pending.payload.amount || "";
    categoryInput.value = pending.payload.category || "";
    descriptionInput.value = pending.payload.description || "";
    dateInput.value = pending.payload.date || todayIsoDate();
    setStatus(submitStatus, "Pending submission restored. Retry will reuse the same request key.", "info");
  }

  async function fetchJson(url, options) {
    const response = await fetch(url, options);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) {
      const message = body.message || "Request failed.";
      const error = new Error(message);
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return body;
  }

  function listUrl() {
    const params = new URLSearchParams();
    if (state.selectedCategory) {
      params.set("category", state.selectedCategory);
    }
    params.set("sort", "date_desc");
    const query = params.toString();
    return query ? `/expenses?${query}` : "/expenses";
  }

  function renderRows() {
    expenseRows.innerHTML = "";
    if (state.expenses.length === 0) {
      const row = document.createElement("tr");
      const cell = document.createElement("td");
      cell.className = "empty-cell";
      cell.colSpan = 4;
      cell.textContent = "No expenses match the current filters.";
      row.appendChild(cell);
      expenseRows.appendChild(row);
      return;
    }

    for (const expense of state.expenses) {
      const row = document.createElement("tr");
      const dateCell = document.createElement("td");
      const categoryCell = document.createElement("td");
      const descriptionCell = document.createElement("td");
      const amountCell = document.createElement("td");

      dateCell.textContent = expense.date;
      categoryCell.textContent = expense.category;
      descriptionCell.textContent = expense.description;
      amountCell.textContent = expense.amount;
      amountCell.className = "amount-cell";

      row.append(dateCell, categoryCell, descriptionCell, amountCell);
      expenseRows.appendChild(row);
    }
  }

  function renderCategories() {
    const current = categoryFilter.value;
    categoryFilter.innerHTML = "";

    const allOption = document.createElement("option");
    allOption.value = "";
    allOption.textContent = "All categories";
    categoryFilter.appendChild(allOption);

    for (const category of state.allCategories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = category;
      categoryFilter.appendChild(option);
    }

    categoryFilter.value = state.allCategories.includes(current) ? current : "";
    state.selectedCategory = categoryFilter.value;
  }

  async function loadCategories() {
    const data = await fetchJson("/expenses");
    const seen = new Set();
    state.allCategories = [];
    for (const expense of data.expenses || []) {
      const key = expense.category.toLowerCase();
      if (!seen.has(key)) {
        seen.add(key);
        state.allCategories.push(expense.category);
      }
    }
    renderCategories();
  }

  async function loadExpenses() {
    setStatus(listStatus, "Loading expenses...", "info");
    try {
      const data = await fetchJson(listUrl());
      state.expenses = data.expenses || [];
      visibleTotal.textContent = data.total || "0.00";
      renderRows();
      setStatus(listStatus, "", "");
    } catch (error) {
      setStatus(listStatus, error.message, "error");
    }
  }

  async function refreshData() {
    refreshButton.disabled = true;
    try {
      await loadCategories();
      await loadExpenses();
    } finally {
      refreshButton.disabled = false;
    }
  }

  async function submitExpense(event) {
    event.preventDefault();
    if (state.isSubmitting) {
      return;
    }

    const payload = normalizePayloadFromForm();
    const validationMessage = validatePayload(payload);
    if (validationMessage) {
      setStatus(submitStatus, validationMessage, "error");
      return;
    }

    const pending = getOrCreatePendingSubmission(payload);
    state.isSubmitting = true;
    submitButton.disabled = true;
    setStatus(submitStatus, "Submitting...", "info");

    try {
      await fetchJson("/expenses", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Idempotency-Key": pending.key,
        },
        body: JSON.stringify(payload),
      });

      clearPendingSubmission();
      form.reset();
      dateInput.value = todayIsoDate();
      setStatus(submitStatus, "Expense saved.", "success");
      await refreshData();
    } catch (error) {
      if (error.status >= 400 && error.status < 500) {
        clearPendingSubmission();
        setStatus(submitStatus, error.message, "error");
      } else {
        writePendingSubmission(pending);
        setStatus(submitStatus, "Network/server issue. Retry will reuse the same request key.", "error");
      }
    } finally {
      state.isSubmitting = false;
      submitButton.disabled = false;
    }
  }

  form.addEventListener("submit", submitExpense);
  refreshButton.addEventListener("click", refreshData);
  categoryFilter.addEventListener("change", function () {
    state.selectedCategory = categoryFilter.value;
    loadExpenses();
  });

  dateInput.value = todayIsoDate();
  restorePendingSubmission();
  refreshData();
})();
