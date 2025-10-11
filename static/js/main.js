document.addEventListener('DOMContentLoaded', () => {
  const y = new Date().getFullYear();
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = y;

  const form = document.getElementById('contactForm');
  const msg = document.getElementById('formMsg');
  if (!form) return;
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    msg.textContent = 'Sending…';
    const data = new FormData(form);
    try {
      const res = await fetch('/contact', { method: 'POST', body: data });
      const json = await res.json();
      if (json.ok) { msg.textContent = 'Thanks! We\'ll get back to you shortly.'; form.reset(); }
      else { msg.textContent = json.error || 'Something went wrong.'; }
    } catch (err) {
      msg.textContent = 'Network error. Please try again.';
    }
  });
});