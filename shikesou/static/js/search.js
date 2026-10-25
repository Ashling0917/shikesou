/**
 * 首页搜索 & 热搜榜单
 */
(function () {
  const keywordInput = document.getElementById("keyword");
  const btnSearch = document.getElementById("btnSearch");
  const hintEl = document.getElementById("hint");
  const resultsSection = document.getElementById("resultsSection");
  const resultsEl = document.getElementById("results");
  const resultHint = document.getElementById("resultHint");
  const hotList = document.getElementById("hotList");

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function cardHtml(r, extraPic) {
    const img = r["图片"] || "";
    const name = escapeHtml(r["菜名"] || "");
    const photo = img
      ? window.SkiImg.tag(img, r["菜名"] || "")
      : '<div class="pic-ph"></div>';
    return (
      '<a class="card" href="/static/detail.html?id=' +
      escapeHtml(r.id) +
      '">' +
      '<div class="pic">' +
      (extraPic || "") +
      photo +
      "</div>" +
      '<div class="body">' +
      '<div class="nm">' +
      name +
      "</div>" +
      '<div class="meta">' +
      (r["分类"]
        ? '<span class="tag">' + escapeHtml(r["分类"]) + "</span>"
        : "") +
      "<span>" +
      escapeHtml(r["耗时"] || "—") +
      "</span>" +
      "<span>" +
      escapeHtml(r["热量"] || "—") +
      "</span>" +
      "</div></div></a>"
    );
  }

  function renderResults(list, keyword) {
    resultsSection.style.display = "block";
    if (resultHint) {
      resultHint.textContent = list.length
        ? "共 " + list.length + " 条"
        : "";
    }
    if (!list.length) {
      resultsEl.innerHTML =
        '<div class="empty">没有找到「' +
        escapeHtml(keyword) +
        "」相关食谱，换个关键词试试～</div>";
      return;
    }
    resultsEl.innerHTML = list.map(function (r) {
      return cardHtml(r);
    }).join("");
  }

  async function doSearch(kw) {
    const keyword = (kw != null ? kw : keywordInput.value).trim();
    keywordInput.value = keyword;
    if (hintEl) hintEl.textContent = "搜索中…";
    try {
      const res = await fetch(
        "/api/search?keyword=" + encodeURIComponent(keyword)
      );
      const json = await res.json();
      const list = json.data || [];
      if (hintEl) {
        hintEl.textContent = list.length
          ? list.length + " 条结果"
          : "无匹配";
      }
      renderResults(list, keyword);
      resultsSection.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      if (hintEl) hintEl.textContent = "搜索失败";
      resultsSection.style.display = "block";
      resultsEl.innerHTML =
        '<div class="empty">搜索失败，请确认服务已启动</div>';
    }
  }

  async function loadHotRank() {
    try {
      const res = await fetch("/api/hotrank?limit=12");
      const json = await res.json();
      const list = json.data || [];
      if (!list.length) {
        hotList.innerHTML = '<div class="empty">暂无热搜数据</div>';
        return;
      }
      hotList.innerHTML = list
        .map(function (item, idx) {
          return cardHtml(
            item,
            '<span class="rank-badge">' + (idx + 1) + "</span>"
          );
        })
        .join("");
    } catch (e) {
      hotList.innerHTML =
        '<div class="empty">热搜加载失败，请确认后端已启动</div>';
    }
  }

  btnSearch.addEventListener("click", function () {
    doSearch();
  });

  keywordInput.addEventListener("keydown", function (e) {
    if (e.key === "Enter") doSearch();
  });

  document.querySelectorAll(".quick-tags .tag").forEach(function (btn) {
    btn.addEventListener("click", function () {
      doSearch(btn.dataset.kw);
    });
  });

  var params = new URLSearchParams(location.search);
  if (params.get("q")) {
    doSearch(params.get("q"));
  }

  loadHotRank();
})();
