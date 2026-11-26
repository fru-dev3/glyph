// The Support button every fru.dev site shows (Fru, 2026-11-26: "very prominent almost everywhere ... you cannot miss it",
// not a link hiding in the footer). One file, loaded by glyph.fru.dev, fru.dev and every context source with
//   <script src="https://glyph.fru.dev/support.js" defer></script>
// It pins a "Buy me a coffee" button to the bottom right, above any pinned footer bar, and opens fru.dev/coffee
// (Buy Me a Coffee). Fru, same day: no heart, it must read as paying at a glance; a coffee cup is the pattern
// people already know.
(() => {
  if (window.__fruSupport) return;
  window.__fruSupport = true;
  const host = location.hostname;
  if (/^\/support\/?$/.test(location.pathname)) return;

  const css = `
#fru-support{position:fixed;right:max(16px,env(safe-area-inset-right));bottom:calc(16px + var(--fru-support-lift,0px) + env(safe-area-inset-bottom));z-index:2147483000;
  display:inline-flex;align-items:center;gap:8px;padding:10px 18px 10px 13px;border-radius:14px;background:#008000;color:#fff!important;text-decoration:none!important;
  font:700 16px/1 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;letter-spacing:.005em;
  box-shadow:0 10px 26px rgba(0,60,0,.32),0 0 0 2px rgba(255,255,255,.95);transition:transform .2s,box-shadow .2s,background .2s}
#fru-support:hover{transform:translateY(-2px);background:#006e00;box-shadow:0 14px 32px rgba(0,60,0,.42),0 0 0 2px #fff}
#fru-support:focus-visible{outline:3px solid #0B1A10;outline-offset:3px}
#fru-support svg{width:26px;height:26px;flex:none;margin-top:-2px}
#fru-support .steam{animation:fru-steam 2.4s ease-in-out infinite}
#fru-support .steam:nth-of-type(2){animation-delay:.4s}
@keyframes fru-steam{0%,100%{opacity:.6;transform:translateY(1px)}50%{opacity:1;transform:translateY(-1px)}}
@media (max-width:520px){#fru-support{padding:10px 14px 10px 12px;font-size:15px}#fru-support svg{width:24px;height:24px}}
@media (prefers-reduced-motion:reduce){#fru-support,#fru-support .steam{transition:none;animation:none!important}}
@media print{#fru-support{display:none}}`;

  const add = () => {
    if (document.getElementById("fru-support")) return;
    const st = document.createElement("style");
    st.textContent = css;
    document.head.appendChild(st);
    const a = document.createElement("a");
    a.id = "fru-support";
    a.href = "https://fru.dev/coffee";
    a.target = "_blank";
    a.rel = "noopener";
    a.setAttribute("aria-label", "Buy me a coffee: everything here is free, built by one person");
    a.title = "Everything here is free, built by one person. Buy me a coffee to keep it going.";
    a.innerHTML = '<svg viewBox="2 1.2 20 20" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
      + '<path class="steam" d="M8 2.5c-.6.8-.6 1.7 0 2.5"/><path class="steam" d="M12 2.5c-.6.8-.6 1.7 0 2.5"/>'
      + '<path d="M3.5 8.5h13v6a5 5 0 0 1-5 5h-3a5 5 0 0 1-5-5z" fill="currentColor"/>'
      + '<path d="M16.5 10h1.5a2.5 2.5 0 0 1 0 5h-1.6"/></svg>Buy me a coffee';
    a.addEventListener("click", () => { try { window.gtag && gtag("event", "support_click", { from: "coffee_button", site: host, link_url: a.href }); } catch {} });
    document.body.appendChild(a);

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
