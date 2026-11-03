(function () {
  "use strict";

  const data = window.SITE_CONTENT;
  const $ = (sel) => document.querySelector(sel);

  // HTML 이스케이프
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  const tags = (list) => `<ul class="tag-list">${list.map((t) => `<li class="tag">${esc(t)}</li>`).join("")}</ul>`;

  const ICONS = {
    reactor: '<path d="M9 3h6M10 3v6L5 19a2 2 0 0 0 1.8 2.8h10.4A2 2 0 0 0 19 19l-5-10V3"/><path d="M7.5 15h9"/>',
    plug: '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0z"/><path d="M12 18v4"/>',
    chart: '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 6-7"/>',
    record: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6M8 13h8M8 17h5"/>',
    flask: '<circle cx="7" cy="17" r="3"/><circle cx="17" cy="7" r="3"/><path d="M9.5 14.5l5-5M17 13v5a2 2 0 0 1-2 2h-3M7 11V6a2 2 0 0 1 2-2h3"/>'
  };

  // ---------- 단순 바인딩 ----------
  document.querySelectorAll("[data-bind]").forEach((el) => {
    const value = el.dataset.bind.split(".").reduce((o, k) => (o ? o[k] : ""), data);
    el.textContent = value || "";
  });
  $("#year").textContent = new Date().getFullYear();

  const { profile } = data;
  if (profile.resumeUrl) {
    const btn = $("#resume-btn");
    btn.href = profile.resumeUrl;
    btn.hidden = false;
  }

  // ---------- About ----------
  $("#about-text").innerHTML = data.about.paragraphs.map((p) => `<p>${esc(p)}</p>`).join("");
  $("#principles").innerHTML = data.about.principles
    .map((p) => `<li><strong>${esc(p.title)}</strong><span>${esc(p.text)}</span></li>`)
    .join("");

  // ---------- Expertise ----------
  $("#expertise-list").innerHTML = data.expertise
    .map(
      (e) => `<article class="card">
        <div class="card-icon"><svg viewBox="0 0 24 24" aria-hidden="true">${ICONS[e.icon] || ICONS.reactor}</svg></div>
        <h3>${esc(e.title)}</h3>
        <p>${esc(e.text)}</p>
      </article>`
    )
    .join("");

  // ---------- Skills ----------
  $("#skills-list").innerHTML = data.skills
    .map((g) => `<div class="skill-group"><h3>${esc(g.category)}</h3>${tags(g.items)}</div>`)
    .join("");

  // ---------- Projects + 필터 (FR-2) ----------
  const allTags = [...new Set(data.projects.flatMap((p) => p.tags))];
  let activeTag = null;

  const filterBar = $("#project-filters");
  filterBar.innerHTML = ["전체", ...allTags]
    .map((t, i) => `<button class="filter-btn" data-tag="${i ? esc(t) : ""}" aria-pressed="${i === 0}">${esc(t)}</button>`)
    .join("");

  filterBar.addEventListener("click", (e) => {
    const btn = e.target.closest(".filter-btn");
    if (!btn) return;
    activeTag = btn.dataset.tag || null;
    filterBar.querySelectorAll(".filter-btn").forEach((b) => b.setAttribute("aria-pressed", String(b === btn)));
    renderProjects();
  });

  function renderProjects() {
    const list = $("#project-list");
    const items = data.projects
      .map((p, i) => ({ p, i }))
      .filter(({ p }) => !activeTag || p.tags.includes(activeTag));
    list.innerHTML = items.length
      ? items
          .map(
            ({ p, i }) => `<button class="project-card" data-index="${i}" aria-haspopup="dialog">
              <span class="period">${esc(p.period)}</span>
              <h3>${esc(p.title)}</h3>
              <p>${esc(p.summary)}</p>
              ${tags(p.tags)}
              <span class="more">자세히 보기 →</span>
            </button>`
          )
          .join("")
      : `<p class="empty-msg">해당 기술의 프로젝트가 없습니다.</p>`;
  }
  renderProjects();

  // ---------- 프로젝트 상세 (FR-3) ----------
  const dialog = $("#project-dialog");
  let lastFocus = null;

  $("#project-list").addEventListener("click", (e) => {
    const card = e.target.closest(".project-card");
    if (!card) return;
    const p = data.projects[Number(card.dataset.index)];
    $("#dialog-body").innerHTML = `
      <span class="period">${esc(p.period)}</span>
      <h2 id="dialog-title">${esc(p.title)}</h2>
      ${tags(p.tags)}
      <h3>Problem</h3><p>${esc(p.problem)}</p>
      <h3>Role</h3><p>${esc(p.role)}</p>
      <h3>Solution</h3><p>${esc(p.solution)}</p>
      <h3>Results</h3><ul>${p.results.map((r) => `<li>${esc(r)}</li>`).join("")}</ul>
      ${p.image ? `<img src="${esc(p.image)}" alt="${esc(p.title)} 화면" loading="lazy" />` : ""}`;
    lastFocus = card;
    dialog.showModal();
  });

  $("#dialog-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close(); // 배경 클릭 시 닫기
  });
  dialog.addEventListener("close", () => lastFocus && lastFocus.focus());

  // ---------- Experience ----------
  $("#experience-list").innerHTML = data.experience
    .map(
      (x) => `<li>
        <span class="period">${esc(x.period)}</span>
        <h3>${esc(x.org)}</h3>
        <span class="role">${esc(x.role)}</span>
        <p>${esc(x.text)}</p>
      </li>`
    )
    .join("");

  // ---------- Contact (FR-4) ----------
  const emailLink = $("#email-link");
  emailLink.href = `mailto:${profile.email}`;
  emailLink.textContent = profile.email;

  const status = $("#copy-status");
  $("#copy-email").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(profile.email);
      status.textContent = "이메일 주소가 복사되었습니다.";
    } catch (err) {
      status.textContent = "복사에 실패했습니다. 직접 선택해 복사해 주세요.";
    }
    clearTimeout(status._t);
    status._t = setTimeout(() => (status.textContent = ""), 2500);
  });

  $("#ext-links").innerHTML = profile.links
    .filter((l) => l.url)
    .map((l) => `<li><a class="btn btn-ghost btn-sm" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)}</a></li>`)
    .join("");

  // ---------- 모바일 메뉴 ----------
  const navToggle = $(".nav-toggle");
  const navMenu = $("#nav-menu");
  const setMenu = (open) => {
    navMenu.classList.toggle("open", open);
    navToggle.setAttribute("aria-expanded", String(open));
    navToggle.setAttribute("aria-label", open ? "메뉴 닫기" : "메뉴 열기");
  };
  navToggle.addEventListener("click", () => setMenu(!navMenu.classList.contains("open")));
  navMenu.addEventListener("click", (e) => {
    if (e.target.closest("a")) setMenu(false);
  });

  // ---------- 현재 섹션 하이라이트 ----------
  const navLinks = [...navMenu.querySelectorAll("a[href^='#']")];
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        navLinks.forEach((a) => a.classList.toggle("active", a.getAttribute("href") === `#${entry.target.id}`));
      });
    },
    { rootMargin: "-45% 0px -50% 0px" }
  );
  navLinks.forEach((a) => {
    const target = document.querySelector(a.getAttribute("href"));
    if (target) observer.observe(target);
  });

  // ---------- 테마 전환 (FR-6) ----------
  const root = document.documentElement;
  $(".theme-toggle").addEventListener("click", () => {
    const current = root.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = current === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    try {
      localStorage.setItem("theme", next);
    } catch (e) {}
  });
})();
