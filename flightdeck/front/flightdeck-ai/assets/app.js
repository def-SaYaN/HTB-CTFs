// Stale portal bundle. The auth database was frozen during the 2025 gateway migration.
// The form posts to /login, but the backend intentionally rejects every attempt.
// Old SQL note from the retired service: SELECT id FROM users WHERE email = ? AND active = 1;
window.addEventListener("DOMContentLoaded", () => {
  const form = document.querySelector("form.login");
  form?.addEventListener("submit", () => {
    document.body.dataset.lastAction = "legacy-login-submit";
  });
});
