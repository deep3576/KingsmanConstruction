const API_BASE = (window.CONSTRUCTION_API_BASE || "http://localhost:8000/api/kingsman/v1").replace(/\/$/, "");

document.addEventListener("DOMContentLoaded", () => {
  bindLoginForm();
  bindSignupForm();
});

function bindLoginForm() {
  const form = document.getElementById("loginForm");
  const msg = document.getElementById("loginMsg");
  if (!form || !msg) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.textContent = "Signing in…";

    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        msg.textContent = data.error || data.errors?.join(" ") || "Login failed.";
        return;
      }

      localStorage.setItem("kingsman_user", JSON.stringify(data.user));
      msg.textContent = `Welcome ${data.user.full_name || data.user.email}`;
      setTimeout(() => {
        window.location.href = "index.html";
      }, 700);
    } catch {
      msg.textContent = "Network error. Please try again.";
    }
  });
}

function bindSignupForm() {
  const form = document.getElementById("signupForm");
  const msg = document.getElementById("signupMsg");
  if (!form || !msg) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.textContent = "Creating account…";

    const payload = Object.fromEntries(new FormData(form).entries());
    try {
      const response = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();
      if (!response.ok || !data.ok) {
        msg.textContent = data.error || data.errors?.join(" ") || "Signup failed.";
        return;
      }

      msg.textContent = "Account created. Redirecting to login…";
      setTimeout(() => {
        window.location.href = "login.html";
      }, 700);
    } catch {
      msg.textContent = "Network error. Please try again.";
    }
  });
}
