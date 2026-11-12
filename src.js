/* 流入元の記録（集客の庭② 2026-11-12）
   最初に来た時の入口を30日だけ覚え、フォーム送信の本文末尾へ「流入：…」1行で添える。
   受け口（GAS）は変えない＝本文の1行で運ぶ。CRMへの登録は inbound_lead_ingest.py がこの行を読む。
   保存が使えない環境（プライベートウィンドウ等）では、その場の情報だけで1行を作る。 */
(function () {
  var KEY = 'afw_first_touch';
  var TTL = 30 * 24 * 3600 * 1000;
  var SELF = /(^|\.)ai-flow-works\.com$/;

  function hostOf(u) {
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; }
  }
  function kind(utmSource, refHost) {
    var s = (utmSource || refHost || '').toLowerCase();
    if (!s) return '直接';
    if (/google|yahoo|bing|duckduckgo|ecosia|baidu/.test(s)) return utmSource ? '広告・' + s : '検索';
    if (/facebook|fb|instagram|t\.co|twitter|x\.com|threads|tiktok|youtube|note\.com/.test(s)) return 'SNS';
    if (/line/.test(s)) return 'LINE';
    if (/mail|newsletter/.test(s)) return 'メール';
    if (/coconala|crowdworks|lancers/.test(s)) return 'PF';
    if (/ai-flow-architect\.github\.io/.test(s)) return '旧サイト';
    return '他サイト';
  }
  function now() {
    var q = new URLSearchParams(location.search);
    var ref = hostOf(document.referrer);
    if (SELF.test(ref)) ref = '';
    var utm = ['utm_source', 'utm_medium', 'utm_campaign'].map(function (k) { return q.get(k) || ''; });
    return { k: kind(utm[0], ref), ref: ref, lp: location.pathname, utm: utm.filter(Boolean).join('/'), t: Date.now() };
  }
  var first = null;
  try {
    var saved = JSON.parse(localStorage.getItem(KEY) || 'null');
    if (saved && Date.now() - saved.t < TTL) first = saved;
  } catch (e) {}
  var cur = now();
  // 30日以内の記録があれば上書きしない＝最初の入口を守る（2回目の訪問の「直接」で消さない）。
  if (!first) {
    first = cur;
    try { localStorage.setItem(KEY, JSON.stringify(first)); } catch (e) {}
  }

  window.AFW_SRC = function (form) {
    var parts = ['流入：' + first.k, '入口：' + first.lp];
    if (first.ref) parts.push('参照元：' + first.ref);
    if (first.utm) parts.push('utm：' + first.utm);
    parts.push('送信：' + (form || location.pathname));
    return parts.join(' | ');
  };
})();
