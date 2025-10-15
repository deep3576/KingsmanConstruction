// App scripts: contact form + admin employees + attendance UI
document.querySelectorAll('.collapsible-button').forEach(button => {
  button.addEventListener('click', function() {
    this.classList.toggle('active');
    const content = this.nextElementSibling;
    const icon = this.querySelector('.icon');

    if (content.style.display === "block") {
      content.style.display = "none";
      icon.textContent = "+";
    } else {
      content.style.display = "block";
      icon.textContent = "-";
    }
  });
});
// Get elements











document.addEventListener('DOMContentLoaded', () => {
  const y = new Date().getFullYear();
  const yearEl = document.getElementById('year');
  if (yearEl) yearEl.textContent = y;

  // Contact form
  const form = document.getElementById('contactForm');
  const msg = document.getElementById('formMsg');
  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      msg.textContent = 'Sending…';
      const data = new FormData(form);
      try {
        const res = await fetch('/contact', { method: 'POST', body: data });
        const json = await res.json();
        if (json.ok) { msg.textContent = "Thanks! We'll get back to you shortly."; form.reset(); }
        else { msg.textContent = json.error || 'Something went wrong.'; }
      } catch { msg.textContent = 'Network error. Please try again.'; }
    });
  }

  initAdminEmployeesUI();
  initAttendanceApp();
});

function initAdminEmployeesUI(){
  // Toggle Add Employee form
  const addBtn = document.getElementById('btnAddEmp');
  const formCard = document.getElementById('empFormCard');
  const cancelBtn = document.getElementById('empFormCancel');
  const empForm = document.getElementById('empForm');
  const empFormMsg = document.getElementById('empFormMsg');

  if (addBtn && formCard) addBtn.addEventListener('click', () => formCard.classList.toggle('hidden'));
  if (cancelBtn && empForm && empFormMsg) {
    cancelBtn.addEventListener('click', () => {
      formCard.classList.add('hidden'); empForm.reset();
      empFormMsg.textContent = ''; empFormMsg.className = 'inline-msg';
    });
  }

  // Create employee via JSON
  if (empForm && empFormMsg) {
    empForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      empFormMsg.textContent = 'Saving…'; empFormMsg.className = 'inline-msg';
      const payload = Object.fromEntries(new FormData(empForm).entries());
      try {
        const res = await fetch('/admin-portal/employees/create', {
          method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)
        });
        const json = await res.json();
        if (json.ok) {
          empFormMsg.textContent = 'Employee added!'; empFormMsg.className = 'inline-msg success';
          // Prepend to table
          const tbody = document.querySelector('#employeesTable tbody');
          if (tbody) {
            const e = json.employee;
            const tr = document.createElement('tr');
            tr.innerHTML = `
              <td>${e.full_name}</td>
              <td>${e.job_title || '-'}</td>
              <td>${e.email || '-'}</td>
              <td>${e.phone || '-'}</td>
              <td>$${Number(e.daily_rate).toFixed(2)}</td>
              <td>
                <select class="emp-status" data-id="${e.id}">
                  <option value="active" ${e.status==='active'?'selected':''}>Active</option>
                  <option value="inactive" ${e.status==='inactive'?'selected':''}>Inactive</option>
                </select>
                <small class="row-msg" id="empRowMsg-${e.id}"></small>
              </td>
              <td>${e.start_date || '-'}</td>
              <td>${e.updated_at || ''}</td>`;
            tbody.prepend(tr);
            wireStatusSelect(tr.querySelector('.emp-status'));
          }
          empForm.reset();
        } else {
          empFormMsg.textContent = json.error || 'Save failed'; empFormMsg.className = 'inline-msg error';
        }
      } catch {
        empFormMsg.textContent = 'Network error'; empFormMsg.className = 'inline-msg error';
      }
    });
  }

  // Inline status change
  document.querySelectorAll('.emp-status').forEach(wireStatusSelect);
  function wireStatusSelect(sel){
    sel?.addEventListener('change', async () => {
      const id = sel.dataset.id;
      const rowMsg = document.getElementById(`empRowMsg-${id}`);
      if (rowMsg){ rowMsg.textContent = 'Saving…'; rowMsg.className = 'row-msg'; }
      try{
        const res = await fetch(`/admin-portal/employees/${id}/status`, {
          method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ status: sel.value })
        });
        const json = await res.json();
        if (json.ok){ if (rowMsg){ rowMsg.textContent = 'Updated'; rowMsg.className = 'row-msg success'; setTimeout(()=> rowMsg.textContent='', 1500);} }
        else { if (rowMsg){ rowMsg.textContent = json.error || 'Error'; rowMsg.className = 'row-msg error'; } }
      }catch{
        if (rowMsg){ rowMsg.textContent = 'Network error'; rowMsg.className = 'row-msg error'; }
      }
    });
  }

  // Toggle timesheet panel
  const attBtn = document.getElementById('btnToggleAttendance');
  const attPanel = document.getElementById('attendancePanel');
  if (attBtn && attPanel){ attBtn.addEventListener('click', () => attPanel.classList.toggle('hidden')); }
}

function initAttendanceApp(){
  const root = document.getElementById('attendanceApp') || document.getElementById('attendancePanel');
  if (!root) return;

  const sel = root.querySelector('#attEmployee');
  const monthLabel = root.querySelector('#attMonthLabel');
  const grid = root.querySelector('#calGrid');
  const btnPrev = root.querySelector('[data-att="prev"]');
  const btnNext = root.querySelector('[data-att="next"]');

  const selDate = root.querySelector('#attSelectedDate');
  const selStatus = root.querySelector('#attStatus');
  const selIn = root.querySelector('#attIn');
  const selOut = root.querySelector('#attOut');
  const selNotes = root.querySelector('#attNotes');
  const btnSave = root.querySelector('#attSave');
  const attMsg = document.getElementById('attMsg');

  const state = { year: new Date().getFullYear(), month: new Date().getMonth()+1, data: {}, selected: null };

  function ymLabel(y, m){ return new Date(y, m-1, 1).toLocaleDateString(undefined, { month:'long', year:'numeric' }); }
  function todayStr(){
    const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }

  async function load(){
    grid.innerHTML = '';
    monthLabel.textContent = ymLabel(state.year, state.month);
    if (!sel?.value) return;
    const q = new URLSearchParams({ employee_id: sel.value, year: String(state.year), month: String(state.month) });
    const res = await fetch('/admin-portal/attendance-data?'+q.toString());
    const json = await res.json();
    if (!json.ok) return;
    state.data = json.days || {};
    drawCalendar();
  }

  function drawCalendar(){
    grid.innerHTML = '';
    const y = state.year, m = state.month, t= todayStr();
    const first = new Date(y, m-1, 1);
    const startDow = first.getDay();
    const daysInMonth = new Date(y, m, 0).getDate();

    for(let i=0;i<startDow;i++) grid.appendChild(dayCell(null, true));
    for(let d=1; d<=daysInMonth; d++){
      const dt = `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
      const info = state.data[dt] || null;
      const cell = dayCell({dt, d, info});
      if (dt===t) cell.classList.add('today');
      grid.appendChild(cell);
    }
  }

  function dayCell(payload, disabled=false){
    const el = document.createElement('div');
    el.className = 'cal-day'+(disabled?' disabled':'');
    if (!disabled && payload){
      const {dt, d, info} = payload;
      el.dataset.date = dt;
      const tag = document.createElement('div'); tag.className = 'tag';
      const dv = document.createElement('div'); dv.className = 'd'; dv.textContent = d;
      el.appendChild(dv); el.appendChild(tag);
      if (info && info.status){ el.classList.add(info.status); tag.textContent = labelFor(info.status); }
      el.addEventListener('click', () => onPick(dt));
    }
    return el;
  }

  function labelFor(s){ switch(s){case 'present': return 'Present'; case 'absent': return 'Absent'; case 'half-day': return 'Half-day'; case 'leave': return 'Leave'; default: return '';} }

  function onPick(dt){
    state.selected = dt;
    selDate.textContent = dt;
    root.querySelectorAll('.cal-day.selected').forEach(n => n.classList.remove('selected'));
    const el = grid.querySelector(`.cal-day[data-date="${dt}"]`); if (el) el.classList.add('selected');
    const info = state.data[dt] || {};
    selStatus.value = info.status || 'present';
    selIn.value = info.sign_in || '';
    selOut.value = info.sign_out || '';
    selNotes.value = info.notes || '';
  }

  async function save(){
    if (!state.selected || !sel?.value) return;
    attMsg && (attMsg.textContent = 'Saving…', attMsg.className = 'inline-msg');
    const payload = {
      employee_id: Number(sel.value),
      date: state.selected,
      status: selStatus.value,
      sign_in_time: selIn.value,
      sign_out_time: selOut.value,
      notes: selNotes.value.trim()
    };
    try {
      const res = await fetch('/admin-portal/attendance-save', { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload) });
      const json = await res.json();
      if (json.ok){
        state.data[state.selected] = { status: payload.status, sign_in: payload.sign_in_time || null, sign_out: payload.sign_out_time || null, notes: payload.notes || null };
        drawCalendar();
        attMsg && (attMsg.textContent = 'Saved', attMsg.className = 'inline-msg success');
        setTimeout(()=> { if(attMsg) attMsg.textContent=''; }, 1500);
      } else {
        attMsg && (attMsg.textContent = json.error || 'Save failed', attMsg.className = 'inline-msg error');
      }
    } catch {
      attMsg && (attMsg.textContent = 'Network error', attMsg.className = 'inline-msg error');
    }
  }

  btnPrev?.addEventListener('click', () => { if (--state.month < 1){ state.month = 12; state.year--; } load(); });
  btnNext?.addEventListener('click', () => { if (++state.month > 12){ state.month = 1; state.year++; } load(); });
  sel?.addEventListener('change', load);
  btnSave?.addEventListener('click', save);
  load();
}
