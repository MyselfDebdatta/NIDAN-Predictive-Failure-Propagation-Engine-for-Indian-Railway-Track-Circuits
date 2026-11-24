/* ==========================================================================
   NIDAN · Mockup shell + micro-interactions
   No framework. Renders shared chrome so every screen tells one story.
   ========================================================================== */
(function () {
  "use strict";

  const page = document.body.dataset.page || "command";
  const scope = document.body.dataset.scope || "SER / ADRA / ADRA YARD";
  const role = document.body.dataset.role || "SSE / Sig · Adra";

  const I = {
    grid: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2.5" y="2.5" width="6" height="6" rx="1.2"/><rect x="11.5" y="2.5" width="6" height="6" rx="1.2"/><rect x="2.5" y="11.5" width="6" height="6" rx="1.2"/><rect x="11.5" y="11.5" width="6" height="6" rx="1.2"/></svg>',
    bell: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M5 8a5 5 0 0 1 10 0c0 3 1 4 1.5 5H3.5C4 12 5 11 5 8Z"/><path d="M8 16a2 2 0 0 0 4 0"/></svg>',
    track: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M6 2v16M14 2v16"/><path d="M3.5 5h13M3.5 10h13M3.5 15h13"/></svg>',
    nodes: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="5" cy="5" r="2.2"/><circle cx="15" cy="7" r="2.2"/><circle cx="8" cy="15" r="2.2"/><path d="M7 5.6 12.8 6.6M6.2 7.1 7.2 12.8M13.6 8.9 9.4 13.4"/></svg>',
    wave: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 11h3l2-6 3 12 3-9 1.5 3H18"/></svg>',
    tablet: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3.5" y="2.5" width="13" height="15" rx="2"/><path d="M8.5 15h3"/></svg>',
    swatch: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="3" y="3" width="6" height="6" rx="1.4"/><rect x="11" y="3" width="6" height="6" rx="1.4"/><rect x="3" y="11" width="6" height="6" rx="1.4"/><circle cx="14" cy="14" r="3"/></svg>',
    search: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><circle cx="9" cy="9" r="5.2"/><path d="m13 13 4 4"/></svg>',
    shield: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 2.5 4 5v5c0 4 2.6 6.6 6 7.5 3.4-.9 6-3.5 6-7.5V5l-6-2.5Z"/><path d="m7.4 10 1.9 2 3.3-3.6"/></svg>',
    plus: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7"><path d="M10 4v12M4 10h12"/></svg>',
    filter: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 5h14M6 10h8M8 15h4"/></svg>',
    download: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M10 3v9m0 0 3.2-3.2M10 12 6.8 8.8M4 15.5h12"/></svg>',
    chevron: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.7"><path d="m7 5 5 5-5 5"/></svg>',
    clock: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="10" cy="10" r="7"/><path d="M10 6v4.4l2.8 1.6"/></svg>',
    book: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 4.5c2.6-1 4.8-1 7 0v11c-2.2-1-4.4-1-7 0v-11ZM17 4.5c-2.6-1-4.8-1-7 0v11c2.2-1 4.4-1 7 0v-11Z"/></svg>',
    camera: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2.5" y="6" width="15" height="10" rx="2"/><path d="M7 6l1.2-2h3.6L13 6"/><circle cx="10" cy="11" r="2.8"/></svg>',
    check: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m4 10.5 4 4 8-9"/></svg>',
    offline: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M2 3l16 14"/><path d="M6.5 12.5a5 5 0 0 1 5.6-1.4M4 9a9 9 0 0 1 3-1.9M12 9.4c1.4.3 2.6 1 3.5 1.9M10 16h.01"/></svg>',
    alert: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M10 3 2 16.5h16L10 3Z"/><path d="M10 8v4M10 14.5h.01"/></svg>',
    spark: '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="m10 2 1.8 5.4L17 9l-5.2 1.6L10 16l-1.8-5.4L3 9l5.2-1.6L10 2Z"/></svg>'
  };

  const NAV = [
    { group: "Operate" },
    { id: "command", label: "Command centre", href: "command-center.html", icon: "grid" },
    { id: "queue", label: "Alert queue", href: "alert-queue.html", icon: "bell", count: "24" },
    { id: "asset", label: "Circuit detail", href: "circuit-detail.html", icon: "track" },
    { id: "clusters", label: "Common cause", href: "command-center.html#graph", icon: "nodes", count: "3" },
    { group: "Assure" },
    { id: "model", label: "Model health", href: "model-health.html", icon: "wave" },
    { id: "field", label: "Field app", href: "field-tablet.html", icon: "tablet" },
    { group: "Reference" },
    { id: "ds", label: "Design system", href: "design-system.html", icon: "swatch" },
    { id: "cover", label: "Cover & gallery", href: "index.html", icon: "book" }
  ];

  function brandLogo() {
    return '<span class="brand__stack">' +
      '<img class="brand__logo" src="../assets/brand/nidan-logo-ui-dark.svg" alt="NIDAN">' +
      '<span class="brand__deva">निदान</span>' +
      '</span>';
  }

  function topbar() {
    const el = document.createElement("header");
    el.className = "topbar";
    el.innerHTML =
      '<a class="brand" href="index.html" aria-label="NIDAN home">' +
        brandLogo() +
      '</a>' +
      '<div class="scope">' +
        '<span class="scope__path">' + scope.split("/").map(function (s, i) {
          return i === 0 ? '<b>' + s.trim() + '</b>' : '<span class="sep">/</span>' + s.trim();
        }).join(" ") + '</span>' +
        '<span class="chip chip--teal chip--advisory" title="Advisory system. No write path to interlocking, signals, routes or track circuits.">Advisory · non-vital</span>' +
      '</div>' +
      '<div class="topbar__right">' +
        '<button class="search" type="button">' + I.search + '<span>Search assets or alerts</span><kbd>⌘K</kbd></button>' +
        '<span class="live"><i></i>Live · 12s</span>' +
        '<div class="lang" role="group" aria-label="Language"><button class="is-on" type="button">EN</button><button class="deva" type="button">हिं</button></div>' +
        '<div class="user"><span class="avatar">SP</span><span class="user__meta"><b>S. Panda</b><small>' + role + '</small></span></div>' +
      '</div>';
    return el;
  }

  function rail() {
    const el = document.createElement("aside");
    el.className = "rail";
    el.setAttribute("aria-label", "Primary");
    let html = "";
    let open = false;
    NAV.forEach(function (n) {
      if (n.group) {
        if (open) html += "</div>";
        html += '<div class="rail__group"><div class="rail__label">' + n.group + "</div>";
        open = true;
        return;
      }
      html += '<a class="nav-item' + (n.id === page ? " is-active" : "") + '" href="' + n.href + '"' +
        (n.id === page ? ' aria-current="page"' : "") + ">" +
        I[n.icon] + "<span>" + n.label + "</span>" +
        (n.count ? '<span class="nav-item__count">' + n.count + "</span>" : "") +
        "</a>";
    });
    if (open) html += "</div>";
    html +=
      '<div class="rail__foot">' +
        '<div class="rail__role"><span class="dot"></span><div><b>S. Panda</b><span>' + role + "</span></div></div>" +
        '<div class="rail__ver">NIDAN front-end 2.4.1<br>RDSO/SPN/257 v2.0 aligned<br>Read-only · audit trail on</div>' +
      "</div>";
    el.innerHTML = html;
    return el;
  }

  function statusbar() {
    const el = document.createElement("footer");
    el.className = "statusbar";
    el.innerHTML =
      '<span class="status-flag">' + I.shield + "Advisory only</span>" +
      '<span class="statusbar__seg">No write path to interlocking, signals, routes or track circuits</span>' +
      '<span class="u-spacer"></span>' +
      '<span class="statusbar__seg">SMMS <b>linked</b></span>' +
      '<span class="statusbar__seg">Twin <b>0.3.1</b> · GNN <b>0.2.0</b> · Survival <b>0.2.4</b></span>' +
      '<span class="statusbar__seg" data-clock>14:32:08 IST</span>';
    return el;
  }

  function mountShell() {
    const app = document.querySelector(".app");
    if (!app) return;
    const main = app.querySelector(".main");
    app.insertBefore(topbar(), app.firstChild);
    app.insertBefore(rail(), main);
    app.appendChild(statusbar());
  }

  /* ---- Sparklines ------------------------------------------------------ */
  function drawSparks() {
    document.querySelectorAll("svg[data-points]").forEach(function (svg, idx) {
      const pts = svg.dataset.points.split(",").map(Number).filter(function (n) { return !isNaN(n); });
      if (pts.length < 2) return;
      const W = 100, H = 34, pad = 3;
      const min = Math.min.apply(null, pts), max = Math.max.apply(null, pts);
      const span = (max - min) || 1;
      const xy = pts.map(function (v, i) {
        return [ (i / (pts.length - 1)) * W, H - pad - ((v - min) / span) * (H - pad * 2) ];
      });
      const line = xy.map(function (p, i) { return (i ? "L" : "M") + p[0].toFixed(1) + " " + p[1].toFixed(1); }).join(" ");
      const area = line + " L100 " + H + " L0 " + H + " Z";
      svg.setAttribute("viewBox", "0 0 100 34");
      svg.setAttribute("preserveAspectRatio", "none");
      svg.setAttribute("aria-hidden", "true");
      const kind = svg.dataset.kind || "teal";
      const stroke = kind === "amber" ? "var(--amber-400)" : kind === "red" ? "var(--red-400)" : kind === "muted" ? "var(--ink-300)" : "var(--teal-400)";
      const fill = kind === "amber" ? "rgba(249,190,92,.14)" : kind === "red" ? "rgba(255,107,112,.14)" : kind === "muted" ? "rgba(125,154,173,.10)" : "rgba(56,224,206,.13)";
      let inner = '<path d="' + area + '" fill="' + fill + '"/>';
      if (svg.dataset.base) {
        inner += '<line x1="0" y1="' + H + '" x2="' + W + '" y2="' + H + '" stroke="var(--ink-500)" stroke-width=".8" stroke-dasharray="2 3"/>';
      }
      inner += '<path d="' + line + '" fill="none" stroke="' + stroke + '" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round" vector-effect="non-scaling-stroke"/>';
      const last = xy[xy.length - 1];
      inner += '<circle cx="' + last[0].toFixed(1) + '" cy="' + last[1].toFixed(1) + '" r="1.6" fill="' + stroke + '" vector-effect="non-scaling-stroke"/>';
      svg.innerHTML = inner;
    });
  }

  /* ---- Tabs ------------------------------------------------------------ */
  function wireTabs() {
    document.querySelectorAll("[data-tabs]").forEach(function (group) {
      const tabs = group.querySelectorAll("[data-tab]");
      const name = group.getAttribute("data-tabs");
      tabs.forEach(function (tab) {
        tab.addEventListener("click", function () {
          tabs.forEach(function (t) {
            t.classList.toggle("is-on", t === tab);
            t.setAttribute("aria-selected", t === tab ? "true" : "false");
          });
          document.querySelectorAll('[data-tabpanel][data-group="' + name + '"]').forEach(function (p) {
            p.classList.toggle("is-on", p.dataset.tabpanel === tab.dataset.tab);
          });
        });
        tab.addEventListener("keydown", function (e) {
          if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
          e.preventDefault();
          const arr = Array.prototype.slice.call(tabs);
          const i = arr.indexOf(tab);
          const next = arr[(i + (e.key === "ArrowRight" ? 1 : arr.length - 1)) % arr.length];
          next.focus(); next.click();
        });
      });
    });
  }

  /* ---- Rows selectable ------------------------------------------------- */
  function wireRows() {
    document.querySelectorAll("tr[data-selectable]").forEach(function (row) {
      row.addEventListener("click", function (e) {
        if (e.target.closest("button, a")) return;
        const box = row.querySelector(".checkbox");
        if (box) box.classList.toggle("is-on");
        row.classList.toggle("is-selected");
      });
    });
  }

  /* ---- Clock ----------------------------------------------------------- */
  function clock() {
    const el = document.querySelector("[data-clock]");
    if (!el) return;
    const tick = function () {
      const d = new Date();
      const ist = new Date(d.getTime() + (d.getTimezoneOffset() + 330) * 60000);
      el.textContent = ist.toTimeString().slice(0, 8) + " IST";
    };
    tick();
    setInterval(tick, 1000);
  }

  /* ---- Field mode toggle ----------------------------------------------- */
  function wireFieldToggle() {
    document.querySelectorAll("[data-theme-toggle]").forEach(function (btn) {
      btn.addEventListener("click", function () {
        document.body.classList.toggle("theme-field");
      });
    });
    document.querySelectorAll('[data-act="lang"]').forEach(function (btn) {
      btn.addEventListener("click", function () {
        const on = document.body.classList.toggle("is-hindi");
        btn.classList.toggle("is-on", on);
        document.querySelectorAll("[data-hi]").forEach(function (node) {
          node.classList.toggle("hide", !on);
        });
        document.querySelectorAll("[data-en]").forEach(function (node) {
          node.classList.toggle("hide", on);
        });
      });
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    mountShell();
    drawSparks();
    wireTabs();
    wireRows();
    clock();
    wireFieldToggle();
  });
})();
