const state = {
  token: localStorage.getItem('eve_token') || '',
  user: null,
  centres: [],
  tests: [],
  centreTests: new Map(),
  bookings: [],
  paymentBookingId: null,
};

const $ = (id) => document.getElementById(id);
const $$ = (selector) => Array.from(document.querySelectorAll(selector));

function toast(message, kind = '') {
  const el = document.createElement('div');
  el.className = `toast ${kind}`;
  el.textContent = message;
  $('toast-region').appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

function openModal(id) {
  $(id).classList.remove('hidden');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  $(id).classList.add('hidden');
  document.body.style.overflow = '';
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json');
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`);

  const response = await fetch(path, { ...options, headers });
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }

  if (!response.ok) {
    const detail = data?.detail || (Array.isArray(data) ? data.map((x) => x.msg).join(', ') : null) || `Request failed (${response.status})`;
    const error = new Error(detail);
    error.status = response.status;
    throw error;
  }
  return data;
}

function setView(view) {
  if (view === 'admin' && state.user?.role !== 'ADMIN') {
    showAuth('login');
    return;
  }
  $$('.view').forEach((el) => el.classList.remove('active-view'));
  $(`view-${view}`).classList.add('active-view');
  $$('.nav-link').forEach((el) => el.classList.toggle('active', el.dataset.view === view));
  window.location.hash = view;
  $('mobile-nav').classList.remove('open');
  if (view === 'discover') loadCatalog();
  if (view === 'bookings') loadBookings();
  if (view === 'admin') loadAdminLists();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function showAuth(mode = 'login') {
  setAuthMode(mode);
  openModal('auth-modal');
}

function setAuthMode(mode) {
  const login = mode === 'login';
  $('login-form').classList.toggle('hidden', !login);
  $('register-form').classList.toggle('hidden', login);
  $('auth-title').textContent = login ? 'Welcome back' : 'Create your account';
  $('auth-subtitle').textContent = login ? 'Sign in to manage appointments and payments.' : 'Create a patient account in a few seconds.';
  $$('.auth-tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.authTab === mode));
}

function updateAuthUI() {
  const admin = state.user?.role === 'ADMIN';
  $$('.admin-only').forEach((el) => el.classList.toggle('hidden', !admin));
  $('auth-btn').textContent = state.user ? `${state.user.name} · Sign out` : 'Sign in';
  $('hero-demo').textContent = state.user ? 'Open my workspace' : 'Try demo access';
}

async function hydrateUser() {
  if (!state.token) {
    state.user = null;
    updateAuthUI();
    return;
  }
  try {
    state.user = await api('/auth/me');
  } catch {
    state.token = '';
    state.user = null;
    localStorage.removeItem('eve_token');
  }
  updateAuthUI();
}

async function login(email, password) {
  const data = await api('/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) });
  state.token = data.access_token;
  localStorage.setItem('eve_token', state.token);
  await hydrateUser();
  closeModal('auth-modal');
  toast(`Signed in as ${state.user?.name || email}`, 'success');
  setView('bookings');
}

async function register(name, email, password) {
  await api('/auth/signup', { method: 'POST', body: JSON.stringify({ name, email, password }) });
  toast('Account created. Sign in to continue.', 'success');
  $('login-email').value = email;
  $('login-password').value = password;
  setAuthMode('login');
}

function requireAuth(action) {
  if (!state.user) {
    showAuth('login');
    toast('Please sign in to continue.');
    return;
  }
  action();
}

async function loadHealth() {
  const started = performance.now();
  try {
    await api('/health');
    const ms = Math.round(performance.now() - started);
    $('health-pill').classList.remove('down');
    $('health-pill').innerHTML = '<i></i><span>Operational</span>';
    $('stat-latency').textContent = `${ms}ms`;
  } catch {
    $('health-pill').classList.add('down');
    $('health-pill').innerHTML = '<i></i><span>Unavailable</span>';
    $('stat-latency').textContent = '—';
  }
}

async function loadCatalog() {
  try {
    const [centres, tests] = await Promise.all([
      api('/centres?page=1&page_size=100'),
      api('/tests'),
    ]);
    state.centres = centres;
    state.tests = tests;
    state.centreTests = new Map();
    await Promise.all(state.centres.map(async (centre) => {
      state.centreTests.set(centre.id, await api(`/centres/${centre.id}/tests`));
    }));

    $('stat-centres').textContent = state.centres.length;
    $('stat-tests').textContent = state.tests.length;
    populateTestFilter();
    renderCatalog();
    populateBookingForm();
    loadAdminLists();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function populateTestFilter() {
  const select = $('test-filter');
  const current = select.value;
  select.innerHTML = `<option value="all">All tests</option>${state.tests.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('')}`;
  if ([...select.options].some((o) => o.value === current)) select.value = current;
}

function renderCatalog() {
  const query = $('catalog-search').value.trim().toLowerCase();
  const testId = $('test-filter').value;
  const rows = [];

  state.centres.forEach((centre) => {
    (state.centreTests.get(centre.id) || []).forEach((mapping) => {
      const test = state.tests.find((t) => t.id === mapping.test_id);
      if (!test) return;
      const haystack = `${test.name} ${test.description || ''} ${centre.name} ${centre.location}`.toLowerCase();
      if (query && !haystack.includes(query)) return;
      if (testId !== 'all' && String(test.id) !== testId) return;
      rows.push({ centre, test, mapping });
    });
  });

  $('catalog-grid').innerHTML = rows.map(({ centre, test, mapping }) => `
    <article class="catalog-card">
      <div class="catalog-top"><div class="catalog-icon">✚</div><div class="catalog-price">₹${Number(mapping.price).toFixed(2)}</div></div>
      <div><h3>${escapeHtml(test.name)}</h3><p>${escapeHtml(test.description || 'Diagnostic laboratory test available at this centre.')}</p></div>
      <div class="catalog-meta">
        <div class="catalog-centre"><span>Centre</span><strong>${escapeHtml(centre.name)}</strong></div>
        <div class="catalog-centre"><span>Location</span><strong>${escapeHtml(centre.location)}</strong></div>
      </div>
      <button class="primary-btn book-from-card" data-centre="${centre.id}" data-test="${test.id}">Book this test</button>
    </article>`).join('');

  $('catalog-empty').classList.toggle('hidden', rows.length > 0);
  $$('.book-from-card').forEach((button) => {
    button.addEventListener('click', () => requireAuth(() => openBooking(button.dataset.centre, button.dataset.test)));
  });
}

function openBooking(centreId = '', testId = '') {
  populateBookingForm();
  if (centreId) $('booking-centre').value = centreId;
  populateBookingTests();
  if (testId) $('booking-test').value = testId;
  updateBookingAmount();

  const dt = new Date(Date.now() + 48 * 60 * 60 * 1000);
  dt.setMinutes(0, 0, 0);
  $('booking-time').value = toLocalInputValue(dt);
  openModal('booking-modal');
}

function populateBookingForm() {
  const centreSelect = $('booking-centre');
  const current = centreSelect.value;
  centreSelect.innerHTML = `<option value="">Select a diagnostic centre</option>${state.centres.map((c) => `<option value="${c.id}">${escapeHtml(c.name)} · ${escapeHtml(c.location)}</option>`).join('')}`;
  if (current) centreSelect.value = current;
  populateBookingTests();
}

function populateBookingTests() {
  const centreId = Number($('booking-centre').value);
  const offered = centreId ? (state.centreTests.get(centreId) || []) : [];
  const current = $('booking-test').value;
  $('booking-test').innerHTML = `<option value="">Select a test</option>${offered.map((m) => {
    const t = state.tests.find((x) => x.id === m.test_id);
    return t ? `<option value="${t.id}" data-price="${m.price}">${escapeHtml(t.name)} · ₹${Number(m.price).toFixed(2)}</option>` : '';
  }).join('')}`;
  if ([...$('booking-test').options].some((o) => o.value === current)) $('booking-test').value = current;
}

function updateBookingAmount() {
  const option = $('booking-test').selectedOptions[0];
  $('booking-amount').textContent = option?.dataset?.price ? `₹${Number(option.dataset.price).toFixed(2)}` : 'Select a centre and test';
}

async function createBooking(event) {
  event.preventDefault();
  try {
    const payload = {
      centre_id: Number($('booking-centre').value),
      test_id: Number($('booking-test').value),
      appointment_at: new Date($('booking-time').value).toISOString(),
    };
    const booking = await api('/bookings', { method: 'POST', body: JSON.stringify(payload) });
    closeModal('booking-modal');
    toast(`Booking #${booking.id} created and is pending payment.`, 'success');
    await loadBookings();
    openPayment(booking.id, booking.amount);
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function loadBookings() {
  if (!state.user) {
    $('login-required-bookings').classList.remove('hidden');
    $('bookings-summary').classList.add('hidden');
    $('booking-list').innerHTML = '';
    $('booking-empty').classList.add('hidden');
    return;
  }

  $('login-required-bookings').classList.add('hidden');
  try {
    state.bookings = await api('/bookings/me');
    renderBookings();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function renderBookings() {
  $('bookings-summary').classList.remove('hidden');
  const counts = { confirmed: 0, pending: 0 };
  let total = 0;
  state.bookings.forEach((b) => {
    if (b.status === 'CONFIRMED') counts.confirmed += 1;
    if (b.status === 'PENDING') counts.pending += 1;
    total += Number(b.amount);
  });
  $('summary-all').textContent = state.bookings.length;
  $('summary-confirmed').textContent = counts.confirmed;
  $('summary-pending').textContent = counts.pending;
  $('summary-total').textContent = `₹${total.toFixed(2)}`;

  if (!state.bookings.length) {
    $('booking-list').innerHTML = '';
    $('booking-empty').classList.remove('hidden');
    return;
  }

  $('booking-empty').classList.add('hidden');
  $('booking-list').innerHTML = state.bookings.map((b) => {
    const test = state.tests.find((t) => t.id === b.test_id);
    const centre = state.centres.find((c) => c.id === b.centre_id);
    const actions = b.status === 'PENDING'
      ? `<button class="primary-btn pay-booking" data-id="${b.id}" data-amount="${b.amount}">Pay ₹${Number(b.amount).toFixed(2)}</button><button class="outline-btn cancel-booking" data-id="${b.id}">Cancel</button>`
      : b.status === 'CONFIRMED'
        ? `<button class="outline-btn copy-booking" data-id="${b.id}">Copy booking ID</button>`
        : '';
    return `<article class="booking-card">
      <div class="booking-main">
        <span class="booking-id">Booking #${b.id}</span>
        <div style="display:flex;align-items:center;gap:9px;flex-wrap:wrap"><h3>${escapeHtml(test?.name || `Diagnostic test #${b.test_id}`)}</h3><span class="status ${b.status.toLowerCase()}">${b.status}</span></div>
        <p>${escapeHtml(centre?.name || `Centre #${b.centre_id}`)} · ${escapeHtml(centre?.location || '')}</p>
        <div class="booking-meta"><span>Appointment <strong>${formatDateTime(b.appointment_at)}</strong></span><span>Amount <strong>₹${Number(b.amount).toFixed(2)}</strong></span></div>
      </div>
      <div class="booking-actions">${actions}</div>
    </article>`;
  }).join('');

  $$('.pay-booking').forEach((btn) => btn.addEventListener('click', () => openPayment(btn.dataset.id, btn.dataset.amount)));
  $$('.cancel-booking').forEach((btn) => btn.addEventListener('click', () => cancelBooking(btn.dataset.id)));
  $$('.copy-booking').forEach((btn) => btn.addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(`EVE booking #${btn.dataset.id}`); } catch {}
    toast('Booking reference copied.', 'success');
  }));
}

async function cancelBooking(id) {
  try {
    await api(`/bookings/${id}/cancel`, { method: 'POST' });
    toast(`Booking #${id} cancelled.`, 'success');
    await loadBookings();
  } catch (error) {
    toast(error.message, 'error');
  }
}

function openPayment(bookingId, amount) {
  state.paymentBookingId = Number(bookingId);
  $('payment-amount').textContent = `₹${Number(amount).toFixed(2)}`;
  openModal('payment-modal');
}

async function simulatePayment(status) {
  if (!state.paymentBookingId) return;
  const key = `eve-booking-${state.paymentBookingId}-${crypto.randomUUID ? crypto.randomUUID() : Date.now()}`;
  try {
    const payment = await api('/payments/', {
      method: 'POST',
      headers: { 'Idempotency-Key': key },
      body: JSON.stringify({ booking_id: state.paymentBookingId, simulate_status: status }),
    });
    closeModal('payment-modal');
    toast(`Payment ${payment.status.toLowerCase()}. Booking status updated.`, payment.status === 'SUCCESS' ? 'success' : 'error');
    await loadBookings();
  } catch (error) {
    toast(error.message, 'error');
  }
}

async function loadAdminLists() {
  if (state.user?.role !== 'ADMIN') return;
  if (!state.centres.length || !state.tests.length) await loadCatalog();
  $('attach-centre').innerHTML = state.centres.map((c) => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
  $('attach-test').innerHTML = state.tests.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join('');
}

async function createCentre(event) {
  event.preventDefault();
  try {
    await api('/centres', { method: 'POST', body: JSON.stringify({ name: $('centre-name').value, location: $('centre-location').value }) });
    $('centre-form').reset();
    toast('Diagnostic centre created.', 'success');
    await loadCatalog();
  } catch (error) { toast(error.message, 'error'); }
}

async function createTest(event) {
  event.preventDefault();
  try {
    await api('/tests', { method: 'POST', body: JSON.stringify({ name: $('test-name').value, description: $('test-description').value || null, base_price: $('test-price').value }) });
    $('test-form').reset();
    toast('Diagnostic test created.', 'success');
    await loadCatalog();
  } catch (error) { toast(error.message, 'error'); }
}

async function attachTest(event) {
  event.preventDefault();
  try {
    await api(`/centres/${$('attach-centre').value}/tests`, { method: 'POST', body: JSON.stringify({ test_id: Number($('attach-test').value), price: $('attach-price').value }) });
    $('attach-price').value = '';
    toast('Test attached to centre with the configured price.', 'success');
    await loadCatalog();
  } catch (error) { toast(error.message, 'error'); }
}

async function sendWebhook(event) {
  event.preventDefault();
  try {
    const payload = {
      event_id: $('webhook-event').value,
      payment_id: Number($('webhook-payment').value),
      event_type: 'payment.updated',
      status: $('webhook-status').value,
    };
    const result = await api('/payments/webhook/demo/', { method: 'POST', body: JSON.stringify(payload) });
    toast(result.processed ? `Webhook processed for booking #${result.booking_id}.` : 'Duplicate webhook detected and ignored safely.', 'success');
    await loadBookings();
  } catch (error) { toast(error.message, 'error'); }
}

function formatDateTime(value) {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value));
}

function toLocalInputValue(date) {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>\'"]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#039;', '"': '&quot;' }[char]));
}

function routeFromHash() {
  const hash = window.location.hash.replace('#', '');
  const allowed = ['home', 'discover', 'bookings', 'admin'];
  setView(allowed.includes(hash) ? hash : 'home');
}

$('auth-btn').addEventListener('click', () => {
  if (state.user) {
    state.token = '';
    state.user = null;
    localStorage.removeItem('eve_token');
    updateAuthUI();
    toast('You have been signed out.');
    setView('home');
  } else showAuth('login');
});

$('docs-link').addEventListener('click', () => window.open('/docs', '_blank', 'noopener'));
$('swagger-link').addEventListener('click', () => window.open('/docs', '_blank', 'noopener'));
$('redoc-link').addEventListener('click', () => window.open('/redoc', '_blank', 'noopener'));
$('hero-book').addEventListener('click', () => requireAuth(() => { setView('discover'); openBooking(); }));
$('hero-demo').addEventListener('click', () => state.user ? setView('bookings') : login('demo@evehealthcare.local', 'Demo@12345').catch((e) => toast(e.message, 'error')));
$('open-booking-top').addEventListener('click', () => requireAuth(() => openBooking()));
$('booking-view-action').addEventListener('click', () => requireAuth(() => openBooking()));
$('booking-login').addEventListener('click', () => showAuth('login'));
$('empty-booking-btn').addEventListener('click', () => setView('discover'));
$('refresh-catalog').addEventListener('click', loadCatalog);
$('catalog-search').addEventListener('input', renderCatalog);
$('test-filter').addEventListener('change', renderCatalog);
$('booking-centre').addEventListener('change', () => { populateBookingTests(); updateBookingAmount(); });
$('booking-test').addEventListener('change', updateBookingAmount);
$('booking-form').addEventListener('submit', createBooking);
$('pay-success').addEventListener('click', () => simulatePayment('SUCCESS'));
$('pay-failed').addEventListener('click', () => simulatePayment('FAILED'));
$('centre-form').addEventListener('submit', createCentre);
$('test-form').addEventListener('submit', createTest);
$('attach-form').addEventListener('submit', attachTest);
$('webhook-form').addEventListener('submit', sendWebhook);
$('use-admin-demo').addEventListener('click', () => {
  $('login-email').value = 'admin@evehealthcare.local';
  $('login-password').value = 'Admin@12345';
  toast('Admin demo credentials loaded.');
});

$$('[data-auth-tab]').forEach((tab) => tab.addEventListener('click', () => setAuthMode(tab.dataset.authTab)));
$$('[data-close-modal]').forEach((el) => el.addEventListener('click', () => closeModal(el.dataset.closeModal)));
$$('.nav-link, .mobile-nav button').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));
$('mobile-menu').addEventListener('click', () => $('mobile-nav').classList.toggle('open'));
$('login-form').addEventListener('submit', (e) => { e.preventDefault(); login($('login-email').value, $('login-password').value).catch((error) => toast(error.message, 'error')); });
$('register-form').addEventListener('submit', (e) => { e.preventDefault(); register($('register-name').value, $('register-email').value, $('register-password').value).catch((error) => toast(error.message, 'error')); });

window.addEventListener('hashchange', routeFromHash);

(async function init() {
  await hydrateUser();
  await Promise.all([loadHealth(), loadCatalog()]);
  routeFromHash();
  updateAuthUI();
})();
