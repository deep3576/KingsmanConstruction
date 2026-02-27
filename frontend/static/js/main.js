const API_BASE = (window.CONSTRUCTION_API_BASE || "http://localhost:8000/api/kingsman/v1").replace(/\/$/, "");

document.addEventListener("DOMContentLoaded", () => {
  const yearEl = document.getElementById("year");
  if (yearEl) yearEl.textContent = String(new Date().getFullYear());

  loadHealth();
  loadServices();
  bindContactForm();
});

async function loadHealth() {
  const statusEl = document.getElementById("apiStatus");
  if (!statusEl) return;

  try {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error("unhealthy");
    statusEl.textContent = `API connected: ${API_BASE}`;
  } catch {
    statusEl.textContent = "API unavailable right now. Update window.CONSTRUCTION_API_BASE for your backend host.";
  }
}

async function loadServices() {
  const listEl = document.getElementById("serviceList");
  if (!listEl) return;

  try {
    const response = await fetch(`${API_BASE}/services`);
    if (!response.ok) return;
    const data = await response.json();
    const services = data.items || [];
    if (!services.length) return;

    listEl.innerHTML = services.map((service) => `
      <article class="card">
        <h3>${service.title}</h3>
        <p>${service.description}</p>
      </article>
    `).join("");
  } catch {
    // keep static fallback cards rendered in HTML
  }
}

function bindContactForm() {
  const form = document.getElementById("contactForm");
  const msg = document.getElementById("formMsg");
  if (!form || !msg) return;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    msg.textContent = "Sending…";

    const payload = Object.fromEntries(new FormData(form).entries());

    try {
      const response = await fetch(`${API_BASE}/contact`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (response.ok && data.ok) {
        msg.textContent = data.message || "Thanks! We'll get back to you shortly.";
        form.reset();
        return;
      }

      msg.textContent = data.errors?.join(" ") || data.error || "Something went wrong.";
    } catch {
      msg.textContent = "Network error. Please try again.";
    }
  });
}
