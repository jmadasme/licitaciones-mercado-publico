// Telemetría del catálogo — widget de pulso (número + rejilla de densidad)
// Se autoejecuta al cargar la página: registra la señal y dibuja la rejilla.
(function () {
  "use strict";

  var WORKER = "https://telemetria.jmadasme.workers.dev";
  var SITE = "licitaciones-mercado-publico"; // identificador de este sitio en el backend (un contador por repo)
  var WEEKS = 26; // columnas (semanas) de la rejilla

  function pad(n) { return n < 10 ? "0" + n : "" + n; }

  function keyOf(d) {
    return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate());
  }

  function buildWidget() {
    var style = document.createElement("style");
    style.textContent = [
      ".tel{width:100%;margin-top:22px;padding-top:18px;border-top:1px solid var(--line)}",
      ".tel-head{display:flex;align-items:baseline;gap:20px;flex-wrap:wrap}",
      ".tel-label{font-family:var(--mono);font-size:10px;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);display:flex;align-items:center;gap:8px}",
      ".tel-label .dot{width:6px;height:6px;border-radius:50%;background:var(--accent);box-shadow:0 0 0 3px rgba(42,157,143,.14)}",
      ".tel-num{font-family:var(--mono);font-size:26px;font-weight:500;letter-spacing:-.03em;color:var(--text);line-height:1}",
      ".tel-grid{display:flex;justify-content:space-between;gap:2px;width:100%;margin-top:16px;overflow:hidden}",
      ".tel-col{display:flex;flex-direction:column;gap:2px;flex:0 0 auto}",
      ".tel-cell{width:10px;height:10px;border-radius:2px;background:rgba(148,190,200,.07)}",
      "@media(max-width:620px){.tel-cell{width:7px;height:7px}}"
    ].join("\n");
    document.head.appendChild(style);

    var box = document.createElement("div");
    box.className = "tel";
    box.innerHTML =
      '<div class="tel-head">' +
        '<span class="tel-label"><span class="dot"></span>telemetría</span>' +
        '<span class="tel-num" id="tel-num">&mdash;</span>' +
      "</div>" +
      '<div class="tel-grid" id="tel-grid"></div>';

    var foot = document.querySelector(".footer .wrap") || document.querySelector(".footer") || document.querySelector("footer") || document.body;
    foot.appendChild(box);
  }

  function setNumber(total) {
    var num = document.getElementById("tel-num");
    if (num) num.textContent = (typeof total === "number" ? total : 0).toLocaleString("es-CL");
  }

  function drawGrid(days) {
    var grid = document.getElementById("tel-grid");
    if (!grid) return;
    days = days || {};

    var now = new Date();
    var today = new Date(Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate()));
    var dow = today.getUTCDay(); // 0 = domingo
    var start = new Date(today.getTime() - (dow + (WEEKS - 1) * 7) * 86400000);

    var matrix = [];
    var max = 0;
    for (var w = 0; w < WEEKS; w++) {
      var col = [];
      for (var r = 0; r < 7; r++) {
        var d = new Date(start.getTime() + (w * 7 + r) * 86400000);
        var c = days[keyOf(d)] || 0;
        col.push(c);
        if (c > max) max = c;
      }
      matrix.push(col);
    }

    var levels = [
      "rgba(148,190,200,.07)",
      "rgba(42,157,143,.25)",
      "rgba(42,157,143,.45)",
      "rgba(42,157,143,.70)",
      "#2A9D8F"
    ];

    grid.innerHTML = "";
    for (w = 0; w < WEEKS; w++) {
      var colEl = document.createElement("div");
      colEl.className = "tel-col";
      for (r = 0; r < 7; r++) {
        var c2 = matrix[w][r];
        var lvl = 0;
        if (c2 > 0 && max > 0) lvl = Math.max(1, Math.ceil((c2 / max) * 4));
        var cell = document.createElement("span");
        cell.className = "tel-cell";
        cell.style.background = levels[lvl];
        colEl.appendChild(cell);
      }
      grid.appendChild(colEl);
    }
  }

  function init() {
    buildWidget();
    drawGrid({}); // rejilla neutra mientras carga
    fetch(WORKER + "/hit?site=" + encodeURIComponent(SITE), { method: "POST" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        setNumber(data.total);
        drawGrid(data.days);
      })
      .catch(function () { /* silencio: queda la rejilla neutra */ });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
