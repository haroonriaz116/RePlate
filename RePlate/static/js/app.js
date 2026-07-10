/* RePlate frontend
 *
 * A small client side router drives every screen in this file. Each route
 * is a function that receives the matched params, fetches whatever JSON it
 * needs from the Flask API, and returns an HTML string for #app to render.
 * Nothing here is server rendered; the Flask backend only ever hands back
 * JSON or the index.html shell, and this file is the layer that turns that
 * JSON into the interface a person actually sees.
 */

const CATEGORY_EMOJI = {
  produce: "🥦", bakery: "🥐", dairy: "🥛", prepared: "🍱",
  pantry: "🥫", frozen: "🧊", other: "📦",
};

const state = { user: null };

/* ---------------- API helper ---------------- */

async function api(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = {};
  try { body = await res.json(); } catch (e) { /* no body */ }
  if (!res.ok) {
    const err = new Error((body.errors && body.errors[0]) || "Something went wrong.");
    err.errors = body.errors || [err.message];
    err.status = res.status;
    throw err;
  }
  return body;
}

/* ---------------- toast ---------------- */

function toast(message, kind = "success") {
  const stack = document.getElementById("toast-stack");
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => el.remove(), 3200);
}

/* ---------------- router ---------------- */

const routes = [
  { pattern: /^\/$/, view: viewHome },
  { pattern: /^\/login$/, view: viewLogin },
  { pattern: /^\/register$/, view: viewRegister },
  { pattern: /^\/listings$/, view: viewBrowse },
  { pattern: /^\/listings\/new$/, view: viewCreate },
  { pattern: /^\/listings\/(\d+)$/, view: viewDetail },
  { pattern: /^\/dashboard$/, view: viewDashboard },
];

async function router() {
  const path = location.pathname;
  const match = routes.find((r) => r.pattern.test(path));
  const app = document.getElementById("app");
  app.innerHTML = renderShell("<p>Loading&hellip;</p>");
  attachNavHandlers();

  if (!match) {
    app.innerHTML = renderShell(`<div class="empty-state"><h2>Page not found</h2><p>That page does not exist.</p></div>`);
    attachNavHandlers();
    return;
  }

  const params = path.match(match.pattern).slice(1);
  try {
    const html = await match.view(...params);
    app.innerHTML = renderShell(html);
  } catch (err) {
    app.innerHTML = renderShell(`<div class="empty-state"><h2>Something went wrong</h2><p>${escapeHtml(err.message)}</p></div>`);
  }
  attachNavHandlers();
  bindPageHandlers(path, params);
}

function navigate(path) {
  history.pushState({}, "", path);
  router();
}

window.addEventListener("popstate", router);

function attachNavHandlers() {
  document.querySelectorAll("a[data-link]").forEach((a) => {
    a.addEventListener("click", (e) => {
      e.preventDefault();
      navigate(a.getAttribute("href"));
    });
  });
  const logoutBtn = document.getElementById("logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
      await api("/auth/logout", { method: "POST" });
      state.user = null;
      toast("You have been logged out.", "info");
      navigate("/");
    });
  }
}

/* ---------------- shell / nav ---------------- */

function renderShell(inner) {
  const path = location.pathname;
  const navItem = (href, label) =>
    `<a data-link href="${href}" class="${path === href ? "active" : ""}">${label}</a>`;

  const rightLinks = state.user
    ? `${navItem("/dashboard", "Dashboard")}<button class="linklike" id="logout-btn">Log out</button>`
    : `${navItem("/login", "Log in")}<a data-link href="/register" class="btn btn-primary" style="padding:9px 18px;">Sign up</a>`;

  return `
    <nav class="nav">
      <a data-link href="/" class="brand">
        <span class="brand-mark">🍽️</span>
        <span class="brand-word">RePlate</span>
      </a>
      <div class="nav-links">
        ${navItem("/listings", "Browse listings")}
        ${rightLinks}
      </div>
    </nav>
    <main>${inner}</main>
    <footer>RePlate connects donors, recipients, and volunteers to redistribute surplus food before it goes to waste.</footer>
  `;
}

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function errorList(errors) {
  if (!errors || !errors.length) return "";
  return `<div class="error-list"><ul>${errors.map((e) => `<li>${escapeHtml(e)}</li>`).join("")}</ul></div>`;
}

/* ---------------- views ---------------- */

async function viewHome() {
  const data = await api("/home");
  const { stats, recent } = data;

  const statCard = (num, label) => `
    <div class="glass-stat">
      <div class="stat-num">${num}</div>
      <div class="stat-label">${label}</div>
    </div>`;

  const recentHtml = recent.length
    ? `<div class="listing-grid">${recent.map(listingCard).join("")}</div>`
    : `<div class="empty-state">No listings are open right now. Check back soon.</div>`;

  return `
    <section class="hero">
      <h1>Surplus food, redirected before it's wasted.</h1>
      <p>RePlate connects donors with extra food, recipients who need it, and volunteers who can close the gap between them.</p>
      <div class="hero-actions">
        <a data-link href="/listings" class="btn btn-primary">Browse open listings</a>
        <a data-link href="/register" class="btn btn-ghost">Create an account</a>
      </div>
    </section>
    <div class="stat-grid">
      ${statCard(stats.active_listings, "Active listings")}
      ${statCard(stats.total_listings, "Total listings posted")}
      ${statCard(stats.completed, "Donations delivered")}
      ${statCard(stats.volunteers, "Volunteers on the network")}
    </div>
    <div class="section-head"><h2>Closing soon</h2><a data-link href="/listings">See all listings &rarr;</a></div>
    ${recentHtml}
  `;
}

function listingCard(l) {
  const daysLabel = l.days_until_expiry === null
    ? ""
    : l.days_until_expiry <= 0
      ? "Best by today"
      : `Best by in ${l.days_until_expiry} day${l.days_until_expiry === 1 ? "" : "s"}`;
  return `
    <a data-link href="/listings/${l.id}" class="card listing-card">
      <div class="top-row">
        <span class="emoji">${CATEGORY_EMOJI[l.category] || "📦"}</span>
        <span class="badge badge-${l.status}">${l.status_label}</span>
      </div>
      <h3>${escapeHtml(l.title)}</h3>
      <div class="meta">${l.quantity} ${escapeHtml(l.unit)} &middot; ${escapeHtml(l.donor_organization || l.donor_name || "")}</div>
      <div class="pickup">${escapeHtml(l.pickup_location)}</div>
      <div class="meta">${daysLabel}</div>
    </a>`;
}

function viewLogin() {
  if (state.user) { navigate("/dashboard"); return ""; }
  return `
    <div class="card form-card">
      <h2 style="margin-bottom:18px;">Log in</h2>
      <div id="form-errors"></div>
      <form id="login-form">
        <div class="field"><label>Email</label><input type="email" name="email" required></div>
        <div class="field"><label>Password</label><input type="password" name="password" required></div>
        <button class="btn btn-primary btn-block" type="submit">Log in</button>
      </form>
      <p style="margin-top:16px; font-size:0.88rem;">New to RePlate? <a data-link href="/register">Create an account</a></p>
    </div>`;
}

function viewRegister() {
  if (state.user) { navigate("/dashboard"); return ""; }
  return `
    <div class="card form-card">
      <h2 style="margin-bottom:18px;">Create an account</h2>
      <div id="form-errors"></div>
      <form id="register-form">
        <div class="field"><label>Full name</label><input type="text" name="name" required></div>
        <div class="field"><label>Email</label><input type="email" name="email" required></div>
        <div class="field"><label>Password</label><input type="password" name="password" required minlength="8"></div>
        <div class="field">
          <label>I am signing up as a</label>
          <select name="role" required>
            <option value="">Choose a role&hellip;</option>
            <option value="donor">Donor</option>
            <option value="recipient">Recipient</option>
            <option value="volunteer">Volunteer</option>
          </select>
        </div>
        <div class="field"><label>Organization (optional)</label><input type="text" name="organization"></div>
        <div class="field"><label>Location (optional)</label><input type="text" name="location"></div>
        <button class="btn btn-primary btn-block" type="submit">Sign up</button>
      </form>
      <p style="margin-top:16px; font-size:0.88rem;">Already have an account? <a data-link href="/login">Log in</a></p>
    </div>`;
}

async function viewBrowse() {
  const params = new URLSearchParams(location.search);
  const status = params.get("status") || "available";
  const category = params.get("category") || "";
  const q = params.get("q") || "";
  const page = params.get("page") || "1";

  const data = await api(`/listings/?status=${status}&category=${category}&q=${encodeURIComponent(q)}&page=${page}`);

  const categoryOptions = data.categories
    .map((c) => `<option value="${c}" ${c === category ? "selected" : ""}>${CATEGORY_EMOJI[c]} ${c[0].toUpperCase() + c.slice(1)}</option>`)
    .join("");

  const grid = data.listings.length
    ? `<div class="listing-grid">${data.listings.map(listingCard).join("")}</div>`
    : `<div class="empty-state">No listings match those filters.</div>`;

  const pager = data.pages > 1
    ? `<div class="pagination">
        ${data.has_prev ? `<button class="btn btn-ghost" data-page="${data.page - 1}">Previous</button>` : ""}
        <span style="align-self:center; color:var(--ink-soft); font-size:0.88rem;">Page ${data.page} of ${data.pages}</span>
        ${data.has_next ? `<button class="btn btn-ghost" data-page="${data.page + 1}">Next</button>` : ""}
      </div>`
    : "";

  return `
    <h2>Browse listings</h2>
    <form id="filter-form" class="filter-bar" style="margin-top:18px;">
      <select name="status">
        <option value="available" ${status === "available" ? "selected" : ""}>Available</option>
        <option value="all" ${status === "all" ? "selected" : ""}>All statuses</option>
        <option value="claimed" ${status === "claimed" ? "selected" : ""}>Claimed</option>
        <option value="delivered" ${status === "delivered" ? "selected" : ""}>Delivered</option>
      </select>
      <select name="category"><option value="">Every category</option>${categoryOptions}</select>
      <input type="text" name="q" placeholder="Search by title" value="${escapeHtml(q)}">
      <button class="btn btn-primary" type="submit">Filter</button>
    </form>
    ${grid}
    ${pager}
  `;
}

async function viewDetail(id) {
  const { listing } = await api(`/listings/${id}`);

  const logsHtml = listing.logs.length
    ? listing.logs.map((log) => `
        <div class="log-item">
          <strong>${log.status_label}</strong><br>
          ${escapeHtml(log.note || "")}<br>
          <time>${escapeHtml(log.changed_by || "")} &middot; ${new Date(log.timestamp).toLocaleString()}</time>
        </div>`).join("")
    : `<p style="color:var(--ink-soft); font-size:0.88rem;">No history yet.</p>`;

  let actions = "";
  const u = state.user;
  if (u) {
    if (u.role === "recipient" && listing.status === "available") {
      actions = `<button class="btn btn-primary" data-action="claim">Claim this listing</button>`;
    } else if (u.role === "recipient" && listing.recipient_id === u.id && listing.status === "claimed") {
      actions = `
        <button class="btn btn-primary" data-action="deliver">Mark as delivered</button>
        <button class="btn btn-ghost" data-action="release">Release claim</button>`;
    } else if (u.role === "volunteer" && listing.status === "claimed" && !listing.volunteer_id) {
      actions = `<button class="btn btn-primary" data-action="accept">Accept delivery run</button>`;
    } else if (u.role === "volunteer" && listing.volunteer_id === u.id && listing.status === "in_transit") {
      actions = `<button class="btn btn-primary" data-action="deliver">Mark as delivered</button>`;
    } else if (u.role === "donor" && listing.donor_id === u.id && ["available", "claimed", "in_transit"].includes(listing.status)) {
      actions = `<button class="btn btn-danger" data-action="cancel">Cancel listing</button>`;
    }
  }

  return `
    <div class="detail-grid">
      <div class="card detail-card">
        <div class="top-row" style="margin-bottom:10px;">
          <span class="emoji" style="font-size:2.2rem;">${CATEGORY_EMOJI[listing.category] || "📦"}</span>
          <span class="badge badge-${listing.status}">${listing.status_label}</span>
        </div>
        <h2>${escapeHtml(listing.title)}</h2>
        <p>${escapeHtml(listing.description)}</p>
        <p><strong>${listing.quantity} ${escapeHtml(listing.unit)}</strong> &middot; posted by ${escapeHtml(listing.donor_organization || listing.donor_name || "a donor")}</p>
        <p>Pickup at ${escapeHtml(listing.pickup_location)}${listing.pickup_window_start ? ` between ${escapeHtml(listing.pickup_window_start)} and ${escapeHtml(listing.pickup_window_end)}` : ""}</p>
        <div id="detail-errors"></div>
        <div style="display:flex; gap:10px; margin-top:18px; flex-wrap:wrap;">${actions}</div>
      </div>
      <div class="card log-card">
        <h3 style="margin-bottom:12px;">Status history</h3>
        ${logsHtml}
      </div>
    </div>`;
}

function viewCreate() {
  if (!state.user) { navigate("/login"); return ""; }
  if (state.user.role !== "donor") {
    return `<div class="empty-state"><h2>Donor accounts only</h2><p>Only donor accounts can post a listing.</p></div>`;
  }
  return `
    <div class="card form-card wide">
      <h2 style="margin-bottom:18px;">Post a listing</h2>
      <div id="form-errors"></div>
      <form id="create-form">
        <div class="field"><label>Title</label><input type="text" name="title" required></div>
        <div class="field"><label>Description</label><textarea name="description" required></textarea></div>
        <div class="field-row">
          <div class="field">
            <label>Category</label>
            <select name="category">
              ${Object.keys(CATEGORY_EMOJI).map((c) => `<option value="${c}">${CATEGORY_EMOJI[c]} ${c[0].toUpperCase() + c.slice(1)}</option>`).join("")}
            </select>
          </div>
          <div class="field"><label>Quantity</label><input type="number" step="0.1" name="quantity" required></div>
          <div class="field"><label>Unit</label><input type="text" name="unit" value="servings"></div>
        </div>
        <div class="field"><label>Best-by date</label><input type="date" name="expiry_date" required></div>
        <div class="field"><label>Pickup location</label><input type="text" name="pickup_location" required></div>
        <div class="field-row">
          <div class="field"><label>Pickup window start</label><input type="text" name="pickup_window_start" placeholder="e.g. 4:00 PM"></div>
          <div class="field"><label>Pickup window end</label><input type="text" name="pickup_window_end" placeholder="e.g. 6:00 PM"></div>
        </div>
        <button class="btn btn-primary btn-block" type="submit">Post listing</button>
      </form>
    </div>`;
}

async function viewDashboard() {
  if (!state.user) { navigate("/login"); return ""; }
  const data = await api("/dashboard/");

  if (data.role === "donor") {
    const counts = data.counts;
    const grid = data.listings.length
      ? `<div class="listing-grid">${data.listings.map(listingCard).join("")}</div>`
      : `<div class="empty-state">You have not posted a listing yet.</div>`;
    return `
      <div class="section-head"><h2>Your donor dashboard</h2><a data-link href="/listings/new" class="btn btn-primary">Post a listing</a></div>
      <div class="stat-grid" style="grid-template-columns:repeat(3,1fr);">
        <div class="glass-stat"><div class="stat-num">${counts.available}</div><div class="stat-label">Available</div></div>
        <div class="glass-stat"><div class="stat-num">${counts.in_progress}</div><div class="stat-label">In progress</div></div>
        <div class="glass-stat"><div class="stat-num">${counts.delivered}</div><div class="stat-label">Delivered</div></div>
      </div>
      ${grid}`;
  }

  if (data.role === "recipient") {
    const grid = data.listings.length
      ? `<div class="listing-grid">${data.listings.map(listingCard).join("")}</div>`
      : `<div class="empty-state">You have not claimed a listing yet.</div>`;
    return `
      <div class="section-head"><h2>Your claimed listings</h2><a data-link href="/listings" class="btn btn-primary">Browse listings</a></div>
      ${grid}`;
  }

  // volunteer
  const availableGrid = data.available_runs.length
    ? `<div class="listing-grid">${data.available_runs.map(listingCard).join("")}</div>`
    : `<div class="empty-state">No delivery runs are waiting for a volunteer right now.</div>`;
  const myGrid = data.my_runs.length
    ? `<div class="listing-grid">${data.my_runs.map(listingCard).join("")}</div>`
    : `<div class="empty-state">You have not picked up a delivery run yet.</div>`;
  return `
    <h2>Your volunteer dashboard</h2>
    <p style="color:var(--ink-soft);">${data.open_runs_total} delivery run${data.open_runs_total === 1 ? "" : "s"} currently need a volunteer.</p>
    <div class="section-head"><h3>Open runs</h3></div>
    ${availableGrid}
    <div class="section-head"><h3>Your runs</h3></div>
    ${myGrid}`;
}

/* ---------------- form & action bindings ---------------- */

function bindPageHandlers(path) {
  const loginForm = document.getElementById("login-form");
  if (loginForm) {
    loginForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(loginForm);
      try {
        const { user, message } = await api("/auth/login", { method: "POST", body: JSON.stringify(Object.fromEntries(fd)) });
        state.user = user;
        toast(message, "success");
        navigate("/dashboard");
      } catch (err) {
        document.getElementById("form-errors").innerHTML = errorList(err.errors);
      }
    });
  }

  const registerForm = document.getElementById("register-form");
  if (registerForm) {
    registerForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(registerForm);
      try {
        const { user, message } = await api("/auth/register", { method: "POST", body: JSON.stringify(Object.fromEntries(fd)) });
        state.user = user;
        toast(message, "success");
        navigate("/dashboard");
      } catch (err) {
        document.getElementById("form-errors").innerHTML = errorList(err.errors);
      }
    });
  }

  const filterForm = document.getElementById("filter-form");
  if (filterForm) {
    filterForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const fd = new FormData(filterForm);
      const params = new URLSearchParams(Object.fromEntries(fd));
      navigate(`/listings?${params.toString()}`);
    });
    document.querySelectorAll("[data-page]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const params = new URLSearchParams(location.search);
        params.set("page", btn.getAttribute("data-page"));
        navigate(`/listings?${params.toString()}`);
      });
    });
  }

  const createForm = document.getElementById("create-form");
  if (createForm) {
    createForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(createForm);
      try {
        const { listing, message } = await api("/listings/", { method: "POST", body: JSON.stringify(Object.fromEntries(fd)) });
        toast(message, "success");
        navigate(`/listings/${listing.id}`);
      } catch (err) {
        document.getElementById("form-errors").innerHTML = errorList(err.errors);
      }
    });
  }

  document.querySelectorAll("[data-action]").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const action = btn.getAttribute("data-action");
      const id = path.match(/\/listings\/(\d+)/)[1];
      try {
        const { message } = await api(`/listings/${id}/${action}`, { method: "POST" });
        toast(message, "success");
        router();
      } catch (err) {
        const box = document.getElementById("detail-errors");
        if (box) box.innerHTML = errorList(err.errors);
        toast(err.message, "error");
      }
    });
  });
}

/* ---------------- boot ---------------- */

(async function init() {
  try {
    const { user } = await api("/auth/me");
    state.user = user;
  } catch (e) { /* not logged in */ }
  router();
})();
