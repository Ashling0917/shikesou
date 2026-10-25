/**
 * 统一导航四项；若检测到旧版结构（首页 / 缺灶边好物 / ul）则立刻重绘。
 */
(function () {
  var LINKS = [
    { key: "index", href: "/static/index.html", label: "搜索" },
    { key: "zone", href: "/static/topics.html", label: "特色专区" },
    { key: "kitchen", href: "/static/kitchen.html", label: "灶边好物" },
    { key: "assistant", href: "/static/assistant.html", label: "小灶灵" },
  ];

  function pageKey() {
    var p = (location.pathname || "").toLowerCase();
    if (p.indexOf("topics") !== -1 || p.indexOf("zone") !== -1) return "zone";
    if (p.indexOf("kitchen") !== -1) return "kitchen";
    if (p.indexOf("assistant") !== -1) return "assistant";
    if (p.indexOf("detail") !== -1 || p.indexOf("calorie") !== -1) return "";
    return "index";
  }

  function buildHtml(active, showBack) {
    var html = '<a class="nav-brand" href="/static/index.html">食刻搜</a><div class="nav-tabs">';
    for (var i = 0; i < LINKS.length; i++) {
      var item = LINKS[i];
      html +=
        "<a" +
        (item.key === active ? ' class="active"' : "") +
        ' href="' +
        item.href +
        '">' +
        item.label +
        "</a>";
    }
    html += "</div>";
    if (showBack) {
      html +=
        '<a class="nav-back btn btn-ghost" href="/static/index.html">← 返回搜索</a>';
    }
    return html;
  }

  function broken(nav) {
    var t = (nav.textContent || "").replace(/\s+/g, "");
    return (
      t.indexOf("灶边好物") === -1 ||
      t.indexOf("首页") !== -1 ||
      t.indexOf("食食刻搜") !== -1 ||
      nav.querySelector("ul") != null ||
      nav.querySelector(".mark, .nav-logo") != null
    );
  }

  function mountFab(active) {
    if (active === "assistant") return;
    if (document.getElementById("xiaozhaolingFab")) return;
    var a = document.createElement("a");
    a.id = "xiaozhaolingFab";
    a.className = "xiaozhaoling-fab";
    a.href = "/static/assistant.html";
    a.title = "有任何问题都可以问我哦！";
    a.setAttribute("aria-label", "打开小灶灵 AI 厨房助手");
    a.innerHTML =
      '<span class="xiaozhaoling-bubble" aria-hidden="true">有任何问题都可以问我哦！</span>' +
      '<img class="xiaozhaoling-char" src="/static/img/xiaozhaoling-char.png?v=8" alt="小灶灵" width="995" height="929" />';
    a.addEventListener("click", function (e) {
      e.preventDefault();
      location.href = "/static/assistant.html";
    });
    document.body.appendChild(a);
  }

  function boot() {
    var nav = document.getElementById("siteNav") || document.querySelector("nav.nav");
    var active = pageKey();
    if (nav) {
      var showBack = nav.getAttribute("data-back") === "1";
      if (broken(nav) || !nav.querySelector(".nav-tabs")) {
        nav.innerHTML = buildHtml(active, showBack);
      }
    }
    mountFab(active);
  }

  boot();
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  }
})();
