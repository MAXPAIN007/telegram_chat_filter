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

  const noFilesSelected = body.dataset.noFilesSelected || "No files selected";
  const filesSelectedTemplate = body.dataset.filesSelectedTemplate || "Selected files: {count}";
  const resetDone = body.dataset.resetDone === "1";
  const resetSuccessMessage = body.dataset.resetSuccess || "Reset completed";
  const sendSuccessTemplate = body.dataset.sendSuccessTemplate || 'File "{filename}" sent successfully.';
  const sendErrorFallback = body.dataset.sendErrorFallback || "Send failed.";

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

  if (resetDone) {
    showToast(resetSuccessMessage, "success");
  }

  if (fileInput && fileSelectionText) {
    fileInput.addEventListener("change", () => {
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
    });
  }

  if (openResetModalBtn) {
    openResetModalBtn.addEventListener("click", () => {
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
      const runId = button.dataset.runId;
      const filename = button.dataset.filename;
      const lang = button.dataset.lang || "ru";

      button.disabled = true;
      const originalText = button.textContent;
      button.textContent = "Sending...";

      try {
        const response = await fetch(
          `/send-to-agent/${runId}/${encodeURIComponent(filename)}?lang=${encodeURIComponent(lang)}`,
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