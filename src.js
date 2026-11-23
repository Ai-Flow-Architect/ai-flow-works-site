/* 流入元の記録（集客の庭② 2026-11-12／広告の判定を追加 2026-11-12）
   最初に来た時の入口を30日だけ覚え、フォーム送信の本文末尾へ「流入：…」1行で添える。
   受け口（GAS）は変えない＝本文の1行で運ぶ。CRMへの登録は inbound_lead_ingest.py がこの行を読む
   （「流入：」の後の最初の「|」までが種類＝この並びは変えない。足す項目は「送信：」の前に置く）。
   広告の判定：Googleのクリック番号（gclid/gbraid/wbraid）がある、または utm_medium が有料の印
   → 「広告・<媒体>」。fbclid だけでは広告にしない（無料の投稿のリンクにも付くため）。
   最初の入口とは別に「直近の広告」を1つ（30日）覚える。
   保存が使えない環境（プライベートウィンドウ等）では、その場の情報だけで1行を作る。 */
(function () {
  var KEY = 'afw_first_touch';
  var KEY_AD = 'afw_last_ad';
  var TTL = 30 * 24 * 3600 * 1000;
  var SELF = /(^|\.)ai-flow-works\.com$/;
  var PAID = /^(cpc|ppc|paid|paid_social)$/;
  var ID_KEYS = ['gclid', 'gbraid', 'wbraid', 'fbclid'];

  function hostOf(u) {
    try { return new URL(u).hostname.replace(/^www\./, ''); } catch (e) { return ''; }
  }
  // 1行を「|」で区切って運ぶので、値から区切りと改行を落とし、長さを切る。
  function clean(v, n) {
    return String(v || '').replace(/[|｜\s]+/g, ' ').trim().slice(0, n);
  }
  function isAd(medium, idKey) {
    return (!!idKey && idKey !== 'fbclid') || PAID.test((medium || '').toLowerCase());
  }
  // 広告の媒体＝utm_source。無ければクリック番号の種類から決める（fbclid＋有料の印は Meta）。
  // どちらも無ければ「不明」＝Google の件数に混ぜない。
  function adMedia(utmSource, idKey) {
    if (utmSource) return utmSource.toLowerCase();
    if (idKey === 'fbclid') return 'facebook';
    return idKey ? 'google' : '不明';
  }
  function kind(utmSource, refHost, ad, idKey) {
    if (ad) return '広告・' + adMedia(utmSource, idKey);
    var s = (utmSource || refHost || '').toLowerCase();
    if (!s) return '直接';
    if (/google|yahoo|bing|duckduckgo|ecosia|baidu/.test(s)) return '検索';
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
    var utm = ['utm_source', 'utm_medium', 'utm_campaign'].map(function (k) { return clean(q.get(k), 60); });
    var idKey = '', id = '';
    for (var i = 0; i < ID_KEYS.length && !id; i++) {
      id = (q.get(ID_KEYS[i]) || '').replace(/[^A-Za-z0-9_.-]/g, '').slice(0, 200);
      if (id) idKey = ID_KEYS[i];
    }
    var ad = isAd(utm[1], idKey);
    return {
      k: kind(utm[0], ref, ad, idKey), ad: ad, ref: ref, lp: location.pathname,
      utm: utm.filter(Boolean).join('/'), camp: utm[2], term: clean(q.get('utm_term'), 60),
      id: id, idk: idKey, t: Date.now()
    };
  }
  function load(key) {
    try {
      var v = JSON.parse(localStorage.getItem(key) || 'null');
      if (v && Date.now() - v.t < TTL) return v;
    } catch (e) {}
    return null;
  }
  function save(key, v) {
    try { localStorage.setItem(key, JSON.stringify(v)); } catch (e) {}
  }

  var cur = now();
  var first = load(KEY);
  // 30日以内の記録があれば上書きしない＝最初の入口を守る（2回目の訪問の「直接」で消さない）。
  if (!first) {
    first = cur;
    save(KEY, first);
  }
  // 直近の広告＝広告で来た訪問のたびに上書き（広告でない訪問では消さない）。
  var lastAd = load(KEY_AD);
  if (cur.ad) {
    lastAd = cur;
    save(KEY_AD, lastAd);
  }

  function day(t) {
    var d = new Date(t);
    return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2);
  }

  window.AFW_SRC = function (form) {
    var parts = ['流入：' + first.k, '入口：' + first.lp];
    if (first.ref) parts.push('参照元：' + first.ref);
    if (first.utm) parts.push('utm：' + first.utm);
    if (first.camp) parts.push('キャンペーン：' + first.camp);
    if (first.term) parts.push('語：' + first.term);
    if (first.id) parts.push('id：' + first.id, 'id種類：' + first.idk);
    // 最初の入口そのものが直近の広告なら、同じ事を2度書かない。
    if (lastAd && lastAd.t !== first.t) {
      var a = [lastAd.k];
      if (lastAd.id) a.push(lastAd.idk + '=' + lastAd.id);
      if (lastAd.utm) a.push('utm=' + lastAd.utm);
      if (lastAd.camp) a.push('キャンペーン=' + lastAd.camp);
      if (lastAd.term) a.push('語=' + lastAd.term);
      a.push('日=' + day(lastAd.t));
      parts.push('直近広告：' + a.join(' '));
    }
    parts.push('送信：' + (form || location.pathname));
    return parts.join(' | ');
  };
})();
