/**
 * 小灶灵：展示回答，并把推荐菜谱做成可点链接
 */
(function () {
  const messages = document.getElementById("messages");
  const input = document.getElementById("chatInput");
  const btnSend = document.getElementById("btnSend");

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function linkifyDetail(text) {
    return escapeHtml(text).replace(
      /\/static\/detail\.html\?id=(\d+)/g,
      '<a href="/static/detail.html?id=$1">查看详情</a>'
    );
  }

  function appendBubble(text, role, recipes) {
    const div = document.createElement("div");
    div.className = "bubble " + role;
    if (role === "bot") {
      div.innerHTML = linkifyDetail(text).replace(/\n/g, "<br>");
      if (recipes && recipes.length) {
        const wrap = document.createElement("div");
        wrap.className = "chat-recipes";
        recipes.forEach(function (r) {
          if (!r.id) return;
          const a = document.createElement("a");
          a.className = "chat-recipe-chip";
          a.href = "/static/detail.html?id=" + encodeURIComponent(r.id);
          a.textContent = r["菜名"] || r.id;
          wrap.appendChild(a);
        });
        div.appendChild(wrap);
      }
    } else {
      div.textContent = text;
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  async function send(question) {
    const q = (question != null ? question : input.value).trim();
    if (!q) return;
    input.value = "";
    appendBubble(q, "user");

    const loading = document.createElement("div");
    loading.className = "bubble bot";
    loading.textContent = "小灶灵翻菜谱中…";
    messages.appendChild(loading);
    messages.scrollTop = messages.scrollHeight;

    try {
      const res = await fetch("/api/assistant/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      const json = await res.json();
      loading.remove();
      const data = json.data || {};
      appendBubble(
        data.answer || "暂时没有想好怎么回答～",
        "bot",
        data.recipes || []
      );
    } catch (e) {
      loading.remove();
      appendBubble("网络出错了，请确认后端服务已启动。", "bot");
    }
  }

  btnSend.addEventListener("click", function () {
    send();
  });

  input.addEventListener("keydown", function (e) {
    if (e.key === "Enter") send();
  });

  document.querySelectorAll(".chat-quick .tag").forEach(function (btn) {
    btn.addEventListener("click", function () {
      send(btn.dataset.q);
    });
  });
})();
