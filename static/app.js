document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const toastContainer = document.getElementById("toast-container");
  const fileInput = document.getElementById("files");
  const fileSelectionText = document.getElementById("file-selection-text");

  const modalBackdrop = document.getElementById("modal-backdrop");
  const modalCancel = document.getElementById("modal-cancel");
  const modalConfirm = document.getElementById("modal-confirm");
  const openResetModalBtn = document.getElementById("open-reset-modal");
  const resetForm = document.querySelector(".reset-form");

  const processingModeSelect = document.getElementById("processing_mode");
  const basicModeBlock = document.getElementById("basic-mode-block");
  const advancedModeBlock = document.getElementById("advanced-mode-block");

  const addFilterRowBtn = document.getElementById("add-filter-row");
  const filtersContainer = document.getElementById("advanced-filters-container");
  const filterRowTemplate = document.getElementById("advanced-filter-row-template");

  const noFilesSelected = body.dataset.noFilesSelected || "No files selected";
  const filesSelectedTemplate = body.dataset.filesSelectedTemplate || "Selected files: {count}";
  const resetDone = body.dataset.resetDone === "1";
  const resetSuccessMessage = body.dataset.resetSuccess || "Reset completed";
  const sendSuccessTemplate = body.dataset.sendSuccessTemplate || 'File "{filename}" sent successfully.';
  const sendErrorFallback = body.dataset.sendErrorFallback || "Send failed.";

  const FIELD_OPTIONS = {
    chat: [
      { value: "id", label: "id", type: "numeric" },
      { value: "name", label: "name", type: "text" },
      { value: "type", label: "type", type: "text" },
    ],
    message: [
      { value: "id", label: "id", type: "numeric" },
      { value: "reply_to_message_id", label: "reply_to_message_id", type: "numeric" },
      { value: "date", label: "date", type: "date" },
      { value: "from", label: "from", type: "text" },
      { value: "text", label: "text", type: "text" },
    ],
  };

  const OPERATOR_OPTIONS = {
    text: [
      ["contains", "contains"],
      ["not_contains", "not contains"],
      ["equals", "equals"],
      ["not_equals", "not equals"],
      ["starts_with", "starts with"],
      ["ends_with", "ends with"],
    ],
    numeric: [
      ["equals", "equals"],
      ["not_equals", "not equals"],
      ["greater_than", "greater than"],
      ["less_than", "less than"],
    ],
    date: [
      ["equals", "equals"],
      ["not_equals", "not equals"],
      ["on_or_after", "on or after"],
      ["on_or_before", "on or before"],
    ],
  };

  const showToast = (message, type = "success", timeout = 4000) => {
    if (!toastContainer) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(-6px)";
      setTimeout(() => toast.remove(), 180);
    }, timeout);
  };

  const openModal = () => {
    if (modalBackdrop) modalBackdrop.classList.remove("hidden");
  };

  const closeModal = () => {
    if (modalBackdrop) modalBackdrop.classList.add("hidden");
  };

  const updateFileSelectionText = () => {
    if (!fileInput || !fileSelectionText) return;
    const files = Array.from(fileInput.files || []);

    if (!files.length) {
      fileSelectionText.textContent = noFilesSelected;
      return;
    }

    if (files.length === 1) {
      fileSelectionText.textContent = files[0].name;
      return;
    }

    fileSelectionText.textContent = filesSelectedTemplate.replace("{count}", String(files.length));
  };

  const updateModeVisibility = () => {
    if (!processingModeSelect) return;

    const mode = processingModeSelect.value;

    if (basicModeBlock) {
      basicModeBlock.classList.toggle("hidden", mode !== "basic");
    }

    if (advancedModeBlock) {
      advancedModeBlock.classList.toggle("hidden", mode !== "advanced");
    }
  };

  const getFieldMeta = (scope, fieldValue) => {
    const fields = FIELD_OPTIONS[scope] || [];
    return fields.find((f) => f.value === fieldValue) || fields[0] || null;
  };

  const populateFieldOptions = (scopeSelect, fieldSelect, preferredField = null) => {
    const scope = scopeSelect.value;
    const options = FIELD_OPTIONS[scope] || [];

    fieldSelect.innerHTML = "";
    options.forEach((opt) => {
      const option = document.createElement("option");
      option.value = opt.value;
      option.textContent = opt.label;
      if (preferredField && preferredField === opt.value) {
        option.selected = true;
      }
      fieldSelect.appendChild(option);
    });

    if (!preferredField && options.length) {
      fieldSelect.value = options[0].value;
    }
  };

  const populateOperatorOptions = (scopeSelect, fieldSelect, operatorSelect, preferredOperator = null) => {
    const scope = scopeSelect.value;
    const fieldMeta = getFieldMeta(scope, fieldSelect.value);
    const fieldType = fieldMeta?.type || "text";
    const options = OPERATOR_OPTIONS[fieldType] || [];

    operatorSelect.innerHTML = "";
    options.forEach(([value, label]) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      if (preferredOperator && preferredOperator === value) {
        option.selected = true;
      }
      operatorSelect.appendChild(option);
    });

    if (!preferredOperator && options.length) {
      operatorSelect.value = options[0][0];
    }
  };

  const hydrateAdvancedRow = (row, values = {}) => {
    const scopeSelect = row.querySelector(".adv-scope");
    const fieldSelect = row.querySelector(".adv-field");
    const operatorSelect = row.querySelector(".adv-operator");
    const valueInput = row.querySelector(".adv-value");
    const modeSelect = row.querySelector(".adv-mode");
    const removeBtn = row.querySelector(".adv-remove-row");

    scopeSelect.value = values.scope || "chat";
    populateFieldOptions(scopeSelect, fieldSelect, values.field || null);
    populateOperatorOptions(scopeSelect, fieldSelect, operatorSelect, values.operator || null);

    if (values.value) valueInput.value = values.value;
    if (values.mode) modeSelect.value = values.mode;

    scopeSelect.addEventListener("change", () => {
      populateFieldOptions(scopeSelect, fieldSelect);
      populateOperatorOptions(scopeSelect, fieldSelect, operatorSelect);
    });

    fieldSelect.addEventListener("change", () => {
      populateOperatorOptions(scopeSelect, fieldSelect, operatorSelect);
    });

    removeBtn.addEventListener("click", () => {
      row.remove();
      ensureAtLeastOneAdvancedRow();
    });
  };

  const addAdvancedRow = (values = {}) => {
    if (!filterRowTemplate || !filtersContainer) return;
    const fragment = filterRowTemplate.content.cloneNode(true);
    const row = fragment.querySelector(".advanced-filter-row");
    hydrateAdvancedRow(row, values);
    filtersContainer.appendChild(fragment);
  };

  const ensureAtLeastOneAdvancedRow = () => {
    if (!filtersContainer) return;
    const rows = filtersContainer.querySelectorAll(".advanced-filter-row");
    if (!rows.length) {
      addAdvancedRow({
        scope: "chat",
        field: "name",
        operator: "contains",
        value: "",
        mode: "include",
      });
    }
  };

  const syncResetFormAdvancedFields = () => {
    if (!resetForm) return;

    const modeInput = resetForm.querySelector('input[name="processing_mode"]');
    if (modeInput && processingModeSelect) {
      modeInput.value = processingModeSelect.value;
    }

    const matchModeTarget = document.getElementById("reset_adv_match_mode");
    const outputModeTarget = document.getElementById("reset_adv_output_mode");
    const dateFromTarget = document.getElementById("reset_adv_date_from");
    const dateToTarget = document.getElementById("reset_adv_date_to");
    const hiddenFiltersContainer = document.getElementById("reset-advanced-hidden-filters");

    const advMatchMode = document.getElementById("adv_match_mode");
    const advOutputMode = document.getElementById("adv_output_mode");
    const advDateFrom = document.getElementById("adv_date_from");
    const advDateTo = document.getElementById("adv_date_to");

    if (matchModeTarget && advMatchMode) matchModeTarget.value = advMatchMode.value;
    if (outputModeTarget && advOutputMode) outputModeTarget.value = advOutputMode.value;
    if (dateFromTarget && advDateFrom) dateFromTarget.value = advDateFrom.value;
    if (dateToTarget && advDateTo) dateToTarget.value = advDateTo.value;

    if (hiddenFiltersContainer) {
      hiddenFiltersContainer.innerHTML = "";

      const rows = document.querySelectorAll(".advanced-filter-row");
      rows.forEach((row) => {
        const scope = row.querySelector(".adv-scope")?.value ?? "";
        const field = row.querySelector(".adv-field")?.value ?? "";
        const operator = row.querySelector(".adv-operator")?.value ?? "";
        const value = row.querySelector(".adv-value")?.value ?? "";
        const mode = row.querySelector(".adv-mode")?.value ?? "include";

        [
          ["adv_scope[]", scope],
          ["adv_field[]", field],
          ["adv_operator[]", operator],
          ["adv_value[]", value],
          ["adv_mode[]", mode],
        ].forEach(([name, val]) => {
          const input = document.createElement("input");
          input.type = "hidden";
          input.name = name;
          input.value = val;
          hiddenFiltersContainer.appendChild(input);
        });
      });
    }
  };

  if (resetDone) {
    showToast(resetSuccessMessage, "success");
  }

  if (fileInput) {
    fileInput.addEventListener("change", updateFileSelectionText);
    updateFileSelectionText();
  }

  if (processingModeSelect) {
    processingModeSelect.addEventListener("change", updateModeVisibility);
    updateModeVisibility();
  }

  if (filtersContainer) {
    ensureAtLeastOneAdvancedRow();
  }

  if (addFilterRowBtn) {
    addFilterRowBtn.addEventListener("click", () => addAdvancedRow());
  }

  if (openResetModalBtn) {
    openResetModalBtn.addEventListener("click", () => {
      syncResetFormAdvancedFields();
      openModal();
    });
  }

  if (modalCancel) {
    modalCancel.addEventListener("click", closeModal);
  }

  if (modalBackdrop) {
    modalBackdrop.addEventListener("click", (event) => {
      if (event.target === modalBackdrop) {
        closeModal();
      }
    });
  }

  if (modalConfirm && resetForm) {
    modalConfirm.addEventListener("click", () => {
      closeModal();
      resetForm.submit();
    });
  }

  const buttons = document.querySelectorAll(".send-agent-btn");

  buttons.forEach((button) => {
    button.addEventListener("click", async () => {
      const processingMode = button.dataset.processingMode;
      const profileId = button.dataset.profileId;
      const runId = button.dataset.runId;
      const filename = button.dataset.filename;
      const lang = button.dataset.lang || "ru";

      button.disabled = true;
      const originalText = button.textContent;
      button.textContent = "Sending...";

      try {
        const response = await fetch(
          `/send-to-agent/${encodeURIComponent(processingMode)}/${encodeURIComponent(profileId)}/${encodeURIComponent(runId)}/${encodeURIComponent(filename)}?lang=${encodeURIComponent(lang)}`,
          { method: "POST" }
        );

        const payload = await response.json();

        if (!response.ok || !payload.ok) {
          throw new Error(payload.message || sendErrorFallback);
        }

        const details = payload.details || {};
        const successText = sendSuccessTemplate
          .replace("{filename}", filename)
          .replace("{status}", details.status_code ?? "")
          .replace("{size}", details.size_mb ?? "");

        showToast(successText, "success");
      } catch (error) {
        showToast(error.message || sendErrorFallback, "error", 5000);
      } finally {
        button.disabled = false;
        button.textContent = originalText;
      }
    });
  });
});