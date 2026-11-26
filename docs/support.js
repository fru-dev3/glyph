// The Support button every fru.dev site shows (Fru, 2026-11-26: "very prominent almost everywhere ... you cannot miss it",
// not a link hiding in the footer). One file, loaded by glyph.fru.dev, fru.dev and every context source with
//   <script src="https://glyph.fru.dev/support.js" defer></script>
// It pins a green Support pill to the bottom right, above any pinned footer bar, and opens glyph.fru.dev/support.
(() => {
  if (window.__fruSupport) return;
  window.__fruSupport = true;
  const host = location.hostname;
  if (/^\/support\/?$/.test(location.pathname)) return;

  const css = `
#fru-support{position:fixed;right:max(16px,env(safe-area-inset-right));bottom:calc(16px + var(--fru-support-lift,0px) + env(safe-area-inset-bottom));z-index:2147483000;
  display:inline-flex;align-items:center;gap:8px;padding:12px 20px 12px 16px;border-radius:999px;background:#008000;color:#fff!important;text-decoration:none!important;
  font:700 16px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;letter-spacing:.01em;
  box-shadow:0 10px 26px rgba(0,80,0,.35),0 0 0 3px rgba(255,255,255,.9);transition:transform .2s,box-shadow .2s,background .2s}
#fru-support:hover{transform:translateY(-2px);background:#006e00;box-shadow:0 14px 32px rgba(0,80,0,.45),0 0 0 3px #fff}
#fru-support:focus-visible{outline:3px solid #0B1A10;outline-offset:3px}
#fru-support svg{width:18px;height:18px;flex:none}
#fru-support.beat svg{animation:fru-beat 1.1s ease-in-out 2}
@keyframes fru-beat{0%,100%{transform:scale(1)}15%{transform:scale(1.3)}30%{transform:scale(1)}45%{transform:scale(1.2)}}
@media (max-width:520px){#fru-support{padding:11px 16px 11px 13px;font-size:15px}}
@media (prefers-reduced-motion:reduce){#fru-support,#fru-support svg{transition:none;animation:none!important}}
@media print{#fru-support{display:none}}`;

  const add = () => {
    if (document.getElementById("fru-support")) return;
    const st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);
    const a = document.createElement("a");
    a.id = "fru-support";
    a.href = "https://glyph.fru.dev/support" + (host === "glyph.fru.dev" ? "" : "?from=" + encodeURIComponent(host));
    a.setAttribute("aria-label", "Support fru.dev: keep it free");
    a.title = "Everything here is free, built by one person. Support it monthly or once.";
    a.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 21s-7.5-4.6-10-9.3C.4 8.4 2.3 4.5 6.2 4.5c2.4 0 4 1.4 5.8 3.5 1.8-2.1 3.4-3.5 5.8-3.5 3.9 0 5.8 3.9 4.2 7.2C19.5 16.4 12 21 12 21z"/></svg>Support';
    a.addEventListener("click", () => { try { window.gtag && gtag("event", "support_click", { from: "pill", site: host, link_url: a.href }); } catch {} });
    document.body.appendChild(a);
    setTimeout(() => a.classList.add("beat"), 1500);

    // Sit above a pinned footer bar (the context sources pin one to the viewport bottom), never on top of it.
    const lift = () => {
      let h = 0;
      for (const x of [innerWidth / 2, innerWidth - 40]) for (let el of document.elementsFromPoint(x, innerHeight - 2)) {
        for (; el && el !== document.body && el !== a; el = el.parentElement) {
          if (getComputedStyle(el).position !== "fixed" && getComputedStyle(el).position !== "sticky") continue;
          const r = el.getBoundingClientRect();
          if (r.height <= 140 && Math.abs(r.bottom - innerHeight) <= 2 && r.width >= innerWidth * 0.6) h = Math.max(h, r.height);
        }
      }
      a.style.setProperty("--fru-support-lift", h + "px");
    };
    lift();
    [500, 1500, 4000].forEach((ms) => setTimeout(lift, ms));
    addEventListener("resize", lift);
  };
  document.body ? add() : addEventListener("DOMContentLoaded", add);
})();
