/**
 * 外链图片走本站代理，避免防盗链导致空白。
 */
(function (global) {
  function proxyImg(url) {
    if (!url) return "";
    var s = String(url).trim();
    if (!s) return "";
    if (s.indexOf("/api/img") === 0) return s;
    return "/api/img?url=" + encodeURIComponent(s);
  }

  function imgTag(url, alt, className) {
    var src = proxyImg(url);
    if (!src) return "";
    var cls = className ? ' class="' + className + '"' : "";
    var a = String(alt || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/"/g, "&quot;");
    return (
      "<img" +
      cls +
      ' src="' +
      src.replace(/"/g, "&quot;") +
      '" alt="' +
      a +
      '" loading="lazy" decoding="async" />'
    );
  }

  global.SkiImg = { proxy: proxyImg, tag: imgTag };
})(window);
