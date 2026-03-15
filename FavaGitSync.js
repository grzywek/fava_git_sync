export default {
  guessURL() {
    // Module is loaded from {base}/extension_js_module/FavaGitSync.js
    return import.meta.url.replace(/\/extension_js_module\/FavaGitSync\.js.*$/, "");
  },

  guessedURL: "",
  statusInterval: null,

  init() {
    this.guessedURL = this.guessURL();
    const spacer = document.querySelector("header > span.spacer");
    const header = document.querySelector("header");

    const syncButton = document.createElement("button");
    syncButton.id = "git-sync-button";
    syncButton.textContent = "sync";
    syncButton.style.fontWeight = "bold";
    syncButton.style.cursor = "pointer";

    syncButton.onclick = async () => {
      syncButton.disabled = true;
      syncButton.textContent = "sync ⏳";
      try {
        const response = await fetch(
          this.guessedURL + "/extension/FavaGitSync/sync"
        );
        if (response.ok) {
          this.updateIndicator("🟢");
        } else {
          this.updateIndicator("❌");
        }
      } catch {
        this.updateIndicator("❌");
      }
      syncButton.disabled = false;
    };

    header.insertBefore(syncButton, spacer);

    // Initial status check + start polling every 30s
    this.checkStatus();
    this.statusInterval = setInterval(() => this.checkStatus(), 30000);
  },

  async checkStatus() {
    try {
      const response = await fetch(
        this.guessedURL + "/extension/FavaGitSync/status"
      );
      if (!response.ok) {
        this.updateIndicator("❌");
        return;
      }
      const data = await response.json();

      if (data.remote_ahead > 0) {
        this.updateIndicator("🔴");
      } else if (data.local_ahead > 0 || data.dirty) {
        this.updateIndicator("🟡");
      } else {
        this.updateIndicator("🟢");
      }
    } catch {
      this.updateIndicator("❌");
    }
  },

  updateIndicator(icon) {
    const syncButton = document.getElementById("git-sync-button");
    if (syncButton) {
      syncButton.textContent = `sync ${icon}`;
    }
  },

  onPageLoad() {
    this.checkStatus();
  },

  onExtensionPageLoad() {},
};
