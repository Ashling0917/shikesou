/**
 * 热量计算：可在独立页或食谱详情页使用
 * 详情页：window.CalorieCalc.init({ seed: [{name, grams}, ...] })
 */
(function () {
  function addRow(rowsEl, name, grams) {
    const row = document.createElement("div");
    row.className = "ingredient-row";
    row.innerHTML =
      '<input type="text" class="name" placeholder="食材名称，如：鸡蛋" value="' +
      escapeAttr(name || "") +
      '" />' +
      '<input type="number" class="grams" placeholder="克重" min="1" step="1" value="' +
      (grams || "") +
      '" />' +
      '<button type="button" class="btn-remove" title="删除">×</button>';
    row.querySelector(".btn-remove").addEventListener("click", function () {
      row.remove();
    });
    rowsEl.appendChild(row);
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/"/g, "&quot;")
      .replace(/</g, "&lt;");
  }

  function collectItems(rowsEl) {
    const items = [];
    rowsEl.querySelectorAll(".ingredient-row").forEach(function (row) {
      const name = row.querySelector(".name").value.trim();
      const grams = parseFloat(row.querySelector(".grams").value);
      if (name && grams > 0) {
        items.push({ name: name, grams: grams });
      }
    });
    return items;
  }

  async function calc(ctx) {
    const items = collectItems(ctx.rowsEl);
    if (!items.length) {
      alert("请至少添加一条有效食材（名称 + 克重）");
      return;
    }
    try {
      const res = await fetch("/api/calorie/calc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ items: items }),
      });
      const json = await res.json();
      const data = json.data;
      if (!data) {
        alert(json.message || "计算失败");
        return;
      }
      ctx.resultBody.innerHTML = (data.items || [])
        .map(function (it) {
          return (
            "<tr><td>" +
            it.name +
            (it.known ? "" : " <small style='color:#8a7b6b'>(估算)</small>") +
            "</td><td>" +
            it.grams +
            "</td><td>" +
            it.calories +
            "</td></tr>"
          );
        })
        .join("");
      ctx.totalCal.textContent = data.total_calories;
      ctx.percentEl.textContent = data.percent_of_daily + "%";
      if (ctx.calNote) {
        ctx.calNote.textContent = data.note || "计算值仅供参考。";
      }
      ctx.resultEl.classList.add("show");
      ctx.resultEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } catch (e) {
      alert("请求失败，请确认后端已启动");
    }
  }

  /**
   * 从「五花肉500g」「西红柿2个」「葱花适量」解析名称与克重
   */
  function parseIngredientText(text) {
    const raw = String(text || "").trim();
    if (!raw) return null;

    let m = raw.match(/^(.+?)(\d+(?:\.\d+)?)\s*(g|克|G)$/i);
    if (m) {
      return { name: m[1].trim(), grams: parseFloat(m[2]) };
    }

    m = raw.match(/^(.+?)(\d+(?:\.\d+)?)\s*(个|只|条|根|片|瓣|勺)$/);
    if (m) {
      const unit = m[3];
      const n = parseFloat(m[2]);
      const approx = { 个: 50, 只: 50, 条: 400, 根: 30, 片: 5, 瓣: 5, 勺: 15 };
      return { name: m[1].trim(), grams: Math.round(n * (approx[unit] || 50)) };
    }

    m = raw.match(/^(.+?)(半个|适量|少许|少量|若干)$/);
    if (m) {
      return { name: m[1].trim(), grams: "" };
    }

    return { name: raw, grams: "" };
  }

  function init(options) {
    options = options || {};
    const rowsEl = document.getElementById(options.rowsId || "rows");
    const btnAdd = document.getElementById(options.addId || "btnAdd");
    const btnCalc = document.getElementById(options.calcId || "btnCalc");
    const resultEl = document.getElementById(options.resultId || "result");
    const resultBody = document.getElementById(options.resultBodyId || "resultBody");
    const totalCal = document.getElementById(options.totalId || "totalCal");
    const percentEl = document.getElementById(options.percentId || "percent");
    const calNote = document.getElementById(options.noteId || "calNote");

    if (!rowsEl || !btnAdd || !btnCalc || !resultEl || !resultBody || !totalCal || !percentEl) {
      return;
    }

    const ctx = {
      rowsEl: rowsEl,
      resultEl: resultEl,
      resultBody: resultBody,
      totalCal: totalCal,
      percentEl: percentEl,
      calNote: calNote,
    };

    rowsEl.innerHTML = "";
    resultEl.classList.remove("show");

    const seed =
      options.seed && options.seed.length
        ? options.seed
        : [
            { name: "鸡蛋", grams: 150 },
            { name: "西红柿", grams: 200 },
          ];

    seed.forEach(function (d) {
      addRow(rowsEl, d.name, d.grams);
    });

    btnAdd.onclick = function () {
      addRow(rowsEl, "", "");
    };
    btnCalc.onclick = function () {
      calc(ctx);
    };
  }

  window.CalorieCalc = {
    init: init,
    parseIngredientText: parseIngredientText,
  };

  // 独立热量页：DOM 已就绪时自动初始化
  if (document.getElementById("rows") && document.getElementById("btnCalc")) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", function () {
        init();
      });
    } else {
      init();
    }
  }
})();
