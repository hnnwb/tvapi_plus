'use strict';

const CUSTOM_SINGLE_STATUS_URL = 'reports/custom-single-candidates.json';
const CONFIG_INDEX_URL = 'configs.json';
const PROBE_REPORT_URL = 'probe-report.json';
const VERIFICATION_URL = 'reports/verification-report.json';

const CATALOGS = [
  { file: 'catalog/vod-single.json', category: 'vod-single' },
  { file: 'catalog/vod-multi.json', category: 'vod-multi' },
  { file: 'catalog/live.json', category: 'live' },
  { file: 'catalog/epg.json', category: 'epg' },
  { file: 'catalog/online.json', category: 'online' },
  { file: 'catalog/search.json', category: 'search' },
  { file: 'catalog/apps.json', category: 'apps' },
  { file: 'catalog/tools.json', category: 'tools' },
];

const IMPORTABLE = new Set(['vod-single', 'vod-multi', 'live', 'epg']);
const CONFIG_INDEX_IDS = new Set(['tvapi-plus-custom-single', 'xiaoma-tvbox-config']);

const TEXT = {
  zh: {
    navCatalog: '资源', navVerification: '检测', navRules: '收录规则',
    heroEyebrow: '配置 · 直播 · EPG · 在线站 · 项目',
    heroTitle: '资源索引',
    heroSub: '一个直接可用的索引：能复制、能打开、标着上游和最近一次检测结果。不送你猜。',
    explore: '浏览资源', openIndex: '配置索引 JSON',
    statTotal: '目录条目', statReachable: '最近一次可达', statChecked: '检测时间', statCandidate: '自建候选接口',
    allCategories: '全部', single: '单仓配置', multi: '多仓配置', live: '直播', epg: 'EPG',
    online: '在线影视站', searchSites: '网盘与字幕', apps: '播放器', tools: '工具与项目',
    searchLabel: '搜索资源', searchPlaceholder: '搜索名称、来源',
    result: (shown, total) => `显示 ${shown} / ${total} 条`,
    hintAll: '配置与直播可直接导入客户端；在线站、搜索与播放器是浏览器入口，导入客户端无效。',
    hintImportable: '这一类可以直接复制链接、在客户端里导入。检测只说明当时能取到，不代表能播放。',
    hintWeb: '这一类是在浏览器里用的站点，不是 TVBox 配置，复制到客户端不会生效。',
    emptyText: '当前分类没有条目。',
    noResults: '没有匹配的条目。',
    verifyTitle: '检测记录', verifyLead: '检测只回答“当时能不能取到、取到的是不是那个格式”。它不证明能导入，也不证明能播放。',
    testsLabel: '自动化测试通过', clientNotTested: '客户端实播：未验证', true4kNotTested: '真实 4K：未验证',
    checkPassed: '通过', checkFailed: '失败', checkNotTested: '未测试',
    rulesTitle: '收录规则',
    rule1Title: '来源可回溯', rule1Text: '每条都记上游出处与许可说明。不镜像、不重发第三方配置。',
    rule2Title: '结果有时效', rule2Text: '定时检测只代表一次网络观察，隔天的结果可能与今天不同。',
    rule3Title: '不冒充实测', rule3Text: '没有客户端实播证据的条目，不会被标成“已测试”或“优质”。',
    footNote: '条目链接指向上游，版权归原作者；检测结果不构成可用性保证。',
    copy: '复制', copied: '已复制', copyFailed: '复制失败', open: '打开',
    probeOk: '检测通过', probeFail: '检测失败', probeStale: '上次通过',
    noProbe: '未检测', lastSuccess: (d) => `上次通过 ${d}`, checkedAt: (d) => `检测于 ${d}`,
    category: { 'vod-single': '单仓配置', 'vod-multi': '多仓配置', live: '直播', epg: 'EPG', online: '在线影视站', search: '网盘与字幕', apps: '播放器', tools: '工具与项目' },
    loadError: '目录文件读取失败，请刷新重试。',
  },
  en: {
    navCatalog: 'Resources', navVerification: 'Checks', navRules: 'Rules',
    heroEyebrow: 'Configs · Live · EPG · Streaming sites · Projects',
    heroTitle: 'Resource index',
    heroSub: 'A plain, usable index: copy it, open it, with upstream credit and the latest check on every row. No guessing games.',
    explore: 'Browse resources', openIndex: 'Config index JSON',
    statTotal: 'Catalog entries', statReachable: 'Reachable last check', statChecked: 'Checked', statCandidate: 'Candidate APIs',
    allCategories: 'All', single: 'Single config', multi: 'Multi config', live: 'Live', epg: 'EPG',
    online: 'Streaming sites', searchSites: 'Cloud search & subs', apps: 'Players', tools: 'Tools & projects',
    searchLabel: 'Search resources', searchPlaceholder: 'Search name or source',
    result: (shown, total) => `Showing ${shown} of ${total}`,
    hintAll: 'Configs and playlists import straight into a client. Streaming sites, search pages and players are browser destinations; importing them does nothing.',
    hintImportable: 'Copy the link and import it in a client. A passing check only means it answered once, not that it plays.',
    hintWeb: 'This category is used in a browser. These are not TVBox configs and will not work when imported.',
    emptyText: 'No entries in this category.',
    noResults: 'No matching entries.',
    verifyTitle: 'Check log', verifyLead: 'A check answers one question: did it answer, and was the body the expected format. It does not prove import or playback.',
    testsLabel: 'Automated tests passed', clientNotTested: 'Client playback: not verified', true4kNotTested: 'True 4K: not verified',
    checkPassed: 'Passed', checkFailed: 'Failed', checkNotTested: 'Not tested',
    rulesTitle: 'Inclusion rules',
    rule1Title: 'Traceable source', rule1Text: 'Every row records its upstream and licence note. Nothing is mirrored or republished.',
    rule2Title: 'Results expire', rule2Text: 'A scheduled check is one network observation. Tomorrow it may differ.',
    rule3Title: 'No faked testing', rule3Text: 'Without client playback evidence, a row is never labelled tested or recommended.',
    footNote: 'Links point upstream; rights stay with their owners. A passing check is not a guarantee of availability.',
    copy: 'Copy', copied: 'Copied', copyFailed: 'Copy failed', open: 'Open',
    probeOk: 'Check passed', probeFail: 'Check failed', probeStale: 'Passed earlier',
    noProbe: 'Not checked', lastSuccess: (d) => `passed ${d}`, checkedAt: (d) => `checked ${d}`,
    category: { 'vod-single': 'Single config', 'vod-multi': 'Multi config', live: 'Live', epg: 'EPG', online: 'Streaming sites', search: 'Cloud search & subs', apps: 'Players', tools: 'Tools & projects' },
    loadError: 'Catalog files failed to load. Please refresh.',
  },
};

let entries = [];
let probeReport = null;
let verificationReport = null;
let candidateCount = 0;
let lang = localStorage.getItem('tvapi-language') || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
let activeCategory = 'all';

function t() { return TEXT[lang]; }

function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function safeHref(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:' ? url.href : null;
  } catch {
    return null;
  }
}

function formatDate(value, withTime = false) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.valueOf())) return null;
  return date.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en-US',
    withTime ? { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' } : { month: 'short', day: 'numeric' });
}

function probeFor(id) {
  return probeReport?.probes?.find((item) => item.id === id) || null;
}

function probeChip(entry) {
  const probe = probeFor(entry.id);
  if (!probe) return `<span class="chip">${escapeHTML(t().noProbe)}</span>`;
  const date = formatDate(probe.status === 'ok' ? (probe.last_success_at || probe.checked_at) : probe.last_success_at);
  if (probe.status === 'ok') {
    return `<span class="chip chip--ok">${escapeHTML(t().probeOk)}${date ? ` · ${escapeHTML(date)}` : ''}</span>`;
  }
  if (probe.stale && date) {
    return `<span class="chip chip--stale">${escapeHTML(t().probeStale)} · ${escapeHTML(date)}</span>`;
  }
  if (date) {
    return `<span class="chip chip--fail">${escapeHTML(t().probeFail)}</span><span class="chip">${escapeHTML(t().lastSuccess(date))}</span>`;
  }
  return `<span class="chip chip--fail">${escapeHTML(t().probeFail)}</span>`;
}

function displayHost(value) {
  try {
    return new URL(value).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function renderRow(entry) {
  const href = safeHref(entry.url);
  const notes = entry.notes
    ? `<p class="row-notes">${escapeHTML(entry.notes)}</p>`
    : (href ? `<p class="row-notes">${escapeHTML(entry.url)}</p>` : '');
  const escapedSource = escapeHTML(entry.source);
  const source = `<p class="row-source">${escapedSource.startsWith('https://github.com') ? `<a href="${escapedSource}" target="_blank" rel="noreferrer">${escapedSource}</a>` : escapedSource}</p>`;
  return `<article class="row">
    <div class="row-main">
      <div class="row-meta">
        <span class="chip">${escapeHTML(t().category[entry._category] || entry._category)}</span>
        <span class="chip">${escapeHTML(entry.format)}</span>
        ${probeChip(entry)}
      </div>
      <h3 class="row-name">${escapeHTML(entry.name)}</h3>
      <p class="row-host">${escapeHTML(displayHost(entry.url))}</p>
      ${source}
      ${notes}
    </div>
    <div class="row-actions">
      ${href ? `<button class="act" type="button" data-copy-url="${escapeHTML(entry.url)}" data-copy-name="${escapeHTML(entry.name)}">${escapeHTML(t().copy)}</button>` : ''}
      ${href ? `<a class="act act--fill" href="${escapeHTML(href)}" target="_blank" rel="noreferrer" title="${escapeHTML(t().open)}: ${escapeHTML(entry.name)}">${escapeHTML(t().open)}</a>` : ''}
    </div>
  </article>`;
}

function applyLanguage() {
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const value = t()[node.dataset.i18n];
    if (typeof value === 'string') node.textContent = value;
  });
  document.getElementById('search').placeholder = t().searchPlaceholder;
  document.getElementById('language-toggle').textContent = lang === 'zh' ? 'EN' : '中文';
  document.getElementById('language-toggle').setAttribute('aria-label', lang === 'zh' ? 'Switch language' : '切换语言');
  document.title = lang === 'zh' ? 'TVBox 资源索引' : 'TVBox resource index';
  if (verificationReport) renderVerification(verificationReport);
  render();
}

function currentVisible() {
  const query = document.getElementById('search').value.trim().toLowerCase();
  return entries.filter((entry) => {
    if (activeCategory !== 'all' && entry._category !== activeCategory) return false;
    if (!query) return true;
    return `${entry.name} ${entry.format} ${entry.source} ${entry.notes || ''} ${entry.url}`.toLowerCase().includes(query);
  });
}

function render() {
  const visible = currentVisible();
  document.getElementById('total-count').textContent = String(entries.length);
  const ids = new Set(entries.map((entry) => entry.id));
  const reachable = new Set((probeReport?.probes || [])
    .filter((probe) => probe.status === 'ok' && ids.has(probe.id)).map((probe) => probe.id));
  document.getElementById('verified-count').textContent = String(reachable.size);
  document.getElementById('checked-at').textContent = formatDate(probeReport?.generated_at, true) || '—';
  document.getElementById('custom-single-count').textContent = candidateCount ? String(candidateCount) : '—';
  document.getElementById('custom-single-count').title = candidateCount
    ? 'subscriptions/tvbox-custom-single.json'
    : '';
  document.getElementById('result-count').textContent = t().result(visible.length, entries.length);
  document.getElementById('tab-hint').textContent = activeCategory === 'all'
    ? t().hintAll
    : IMPORTABLE.has(activeCategory) ? t().hintImportable : t().hintWeb;
  document.getElementById('catalog-list').innerHTML = visible.map(renderRow).join('');
  document.getElementById('empty-state').hidden = entries.length !== 0;
  document.getElementById('empty-state').querySelector('p').textContent = t().emptyText;
  document.getElementById('no-results').textContent = t().noResults;
  document.getElementById('no-results').hidden = entries.length === 0 || visible.length !== 0;
  document.querySelectorAll('.tab').forEach((tab) => {
    const active = tab.dataset.category === activeCategory;
    tab.classList.toggle('is-active', active);
    tab.setAttribute('aria-selected', active ? 'true' : 'false');
  });
  document.querySelectorAll('[data-count-for]').forEach((counter) => {
    const key = counter.dataset.countFor;
    counter.textContent = String(key === 'all' ? entries.length : entries.filter((entry) => entry._category === key).length);
  });
}

function renderVerification(report) {
  const date = new Date(report.generated_at);
  document.getElementById('verification-date').textContent = Number.isNaN(date.valueOf())
    ? '—'
    : date.toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US', { dateStyle: 'medium', timeStyle: 'short' });
  const summary = report.summary || {};
  document.getElementById('verification-summary').innerHTML = [
    `<span>${escapeHTML(t().testsLabel)}: ${Number(summary.local_unit_tests_passed) || 0}</span>`,
    `<span>${escapeHTML(t().clientNotTested)}</span>`,
    `<span>${escapeHTML(t().true4kNotTested)}</span>`,
  ].join('');
  const labels = { passed: t().checkPassed, failed: t().checkFailed, 'not-tested': t().checkNotTested };
  document.getElementById('verification-list').innerHTML = (report.checks || []).map((check) => {
    const title = lang === 'zh' ? check.subject_zh : check.subject;
    const method = lang === 'zh' ? check.method_zh : check.method;
    return `<article class="verification-item">
      <div class="verification-item-head">
        <h3>${escapeHTML(title)}</h3>
        <span class="status status-${escapeHTML(check.status)}">${escapeHTML(labels[check.status] || labels['not-tested'])}</span>
      </div>
      <p>${escapeHTML(method)}</p>
      <small>${escapeHTML(check.snapshot)} · ${escapeHTML(check.kind)}</small>
      <p class="limit">${escapeHTML(check.limitations)}</p>
    </article>`;
  }).join('');
}

async function loadData() {
  try {
    const [catalogs, probeResponse, verificationResponse, candidateResponse, indexResponse] = await Promise.all([
      Promise.all(CATALOGS.map(async ({ file, category }) => {
        const response = await fetch(file, { cache: 'no-store' });
        if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error(`${file}: expected array`);
        return data.map((entry) => ({ ...entry, _category: category }));
      })),
      fetch(PROBE_REPORT_URL, { cache: 'no-store' }).catch(() => null),
      fetch(VERIFICATION_URL, { cache: 'no-store' }).catch(() => null),
      fetch(CUSTOM_SINGLE_STATUS_URL, { cache: 'no-store' }).catch(() => null),
      fetch(CONFIG_INDEX_URL, { cache: 'no-store' }).catch(() => null),
    ]);
    entries = catalogs.flat();
    if (indexResponse?.ok) {
      const configIndex = await indexResponse.json();
      const indexed = (configIndex.configs || [])
        .filter((item) => CONFIG_INDEX_IDS.has(item.id))
        .map((item) => ({
          id: item.id,
          name: item.name,
          url: item.url,
          format: 'tvbox-json',
          source: item.source || 'configs.json',
          notes: item.id === 'tvapi-plus-custom-single'
            ? (lang === 'zh' ? '自建单仓候选，由历史结构解析去重生成；未实播。' : 'Self-built single candidate deduplicated from structural parses; not playback tested.')
            : (lang === 'zh' ? '上游单仓入口，未实播。' : 'Upstream single config entry; not playback tested.'),
          _category: 'vod-single',
          _displayOrder: Number(item.display_order) || 10,
        }));
      const indexedIds = new Set(indexed.map((item) => item.id));
      entries = entries.filter((item) => !indexedIds.has(item.id)).concat(indexed);
    }
    const order = { 'vod-single': 0, 'vod-multi': 1, live: 2, epg: 3, online: 4, search: 5, apps: 6, tools: 7 };
    entries.sort((a, b) => (order[a._category] ?? 9) - (order[b._category] ?? 9)
      || (a._displayOrder ?? 0) - (b._displayOrder ?? 0)
      || String(a.name).localeCompare(String(b.name), 'zh-Hans-CN'));
    if (probeResponse?.ok) probeReport = await probeResponse.json();
    if (verificationResponse?.ok) {
      verificationReport = await verificationResponse.json();
      renderVerification(verificationReport);
    }
    if (candidateResponse?.ok) {
      const candidate = await candidateResponse.json();
      if (candidate.verification_status === 'unverified-candidate') {
        candidateCount = Number(candidate.unique_candidate_apis) || 0;
      }
    }
    applyLanguage();
  } catch (error) {
    console.error('Unable to load catalog:', error);
    const state = document.getElementById('no-results');
    state.textContent = t().loadError;
    state.hidden = false;
    document.getElementById('empty-state').hidden = true;
  }
}

async function copyText(value) {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    const field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.append(field);
    field.select();
    const ok = document.execCommand('copy');
    field.remove();
    return ok;
  }
}

document.getElementById('catalog-list').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-copy-url]');
  if (!button) return;
  const ok = await copyText(button.dataset.copyUrl);
  const original = t().copy;
  button.textContent = ok ? t().copied : t().copyFailed;
  window.setTimeout(() => {
    if (button.isConnected) button.textContent = original;
  }, 1600);
});

document.getElementById('tabs').addEventListener('click', (event) => {
  const tab = event.target.closest('.tab');
  if (!tab) return;
  activeCategory = tab.dataset.category;
  render();
});

document.getElementById('search').addEventListener('input', render);
document.getElementById('language-toggle').addEventListener('click', () => {
  lang = lang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('tvapi-language', lang);
  applyLanguage();
});
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    document.getElementById('search').focus();
  }
});

applyLanguage();
loadData();
