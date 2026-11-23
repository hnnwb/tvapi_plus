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
  { file: 'catalog/magnet.json', category: 'magnet' },
  { file: 'catalog/search.json', category: 'search' },
  { file: 'catalog/apps.json', category: 'apps' },
  { file: 'catalog/tools.json', category: 'tools' },
  { file: 'catalog/online.json', category: 'online' },
];

const IMPORTABLE = new Set(['vod-single', 'vod-multi', 'live', 'epg']);
const WEB_ONLY = new Set(['online', 'magnet', 'search', 'apps', 'tools']);
const CONFIG_INDEX_IDS = new Set(['tvapi-plus-custom-single', 'xiaoma-tvbox-config']);
const CATEGORY_ORDER = {
  'vod-single': 0, 'vod-multi': 1, live: 2, epg: 3, magnet: 4, search: 5,
  apps: 6, tools: 9, online: 10,
};

const STAR_PATH = 'M8 .9l2.1 4.4 4.8.7-3.5 3.4.8 4.8L8 11.9l-4.2 2.3.8-4.8L1.1 6l4.8-.7z';
const STAR_DEFS = `<svg class="star-defs" aria-hidden="true" width="0" height="0" focusable="false"><defs><linearGradient id="star-half"><stop offset="50%" stop-color="#f5a623"/><stop offset="50%" stop-color="#e3e3e8"/></linearGradient></defs></svg>`;

const TEXT = {
  zh: {
    navCatalog: '全部资源', navVerification: '检测',
    heroEyebrow: '配置 · 苹果 · 安卓 · 开源 · 网盘与磁力',
    heroTitle: '资源索引',
    heroSub: '列表按检测结果与上游星级排序：能取到的、星多的排前面。星级来自上游自评，检测结果只说明当时能不能取到。',
    explore: '开始浏览', openIndex: '配置索引 JSON',
    statTotal: '目录条目', statReachable: '最近一次可达', statRated: '带上游星级', statChecked: '检测时间',
    listEyebrow: '检测 · 排序',
    listTitle: '全部资源',
    allCategories: '全部', single: '单仓配置', multi: '多仓配置', live: '直播', epg: 'EPG',
    magnet: '磁力与 BT', searchSites: '网盘与字幕', onlineSites: '在线站', apps: '应用', tools: '开源项目', via: '来源',
    searchLabel: '搜索资源', searchPlaceholder: '搜索名称、来源',
    result: (shown, total) => `显示 ${shown} / ${total} 条`,
    hintAll: '同一分类内先按检测结果、再按上游星级排序；星级相同的按名称排。',
    hintImportable: '这一类可以直接复制链接、在客户端里导入。检测只说明当时能取到，不代表能播放。',
    hintWeb: '这一类是在浏览器里用的站点，不是 TVBox 配置，复制到客户端不会生效。',
    hintApps: '应用清单：条目指向项目仓库、发布页或下载页，平台写在条目说明里；星标数折算的星级只表示热度。',
    ratedAs: '上游自评',
    ratedNone: '无星级',
    removed: '上游已移除',
    emptyText: '当前分类没有条目。',
    noResults: '没有匹配的条目。',
    verifyTitle: '检测记录', verifyLead: '检测只回答“当时能不能取到、取到的是不是那个格式”。它不证明能导入，也不证明能播放。',
    testsLabel: '自动化测试通过', ratingsLabel: '星级：上游自评转载', clientNotTested: '客户端实播：未验证', true4kNotTested: '真实 4K：未验证',
    checkPassed: '通过', checkFailed: '失败', checkNotTested: '未测试',
    rulesTitle: '收录规则',
    rule1Title: '来源可回溯', rule1Text: '每条都记上游出处与许可说明。不镜像、不重发第三方配置。',
    rule2Title: '星级是上游自评', rule2Text: '星级原样转载自上游，附检查日期；本仓库没有实测，也不替上游背书。',
    rule3Title: '不冒充实测', rule3Text: '没有客户端实播证据的条目，不会被标成“已测试”或“优质”。',
    footNote: '条目链接指向上游，版权归原作者；星级与检测结果都不构成可用性保证。',
    copy: '复制', copied: '已复制', copyFailed: '复制失败', open: '打开', details: '详情',
    probeOk: '检测通过', probeFail: '检测失败', probeStale: '上次通过', noProbe: '未检测',
    lastSuccess: (d) => `上次通过 ${d}`,
    category: {
      'vod-single': '单仓配置', 'vod-multi': '多仓配置', live: '直播', epg: 'EPG', magnet: '磁力与 BT',
      search: '网盘与字幕', apps: '应用',
      tools: '开源项目', online: '在线影视站',
    },
    loadError: '目录文件读取失败，请刷新重试。',
  },
  en: {
    navCatalog: 'All resources', navVerification: 'Checks',
    heroEyebrow: 'Configs · Apple · Android · Open source · Cloud & magnet',
    heroTitle: 'Resource index',
    heroSub: 'The list is ordered by check result, then by upstream stars: reachable and well-rated first. Stars are the upstream self-assessment; a check only says the URL answered.',
    explore: 'Start browsing', openIndex: 'Config index JSON',
    statTotal: 'Catalog entries', statReachable: 'Reachable last check', statRated: 'With upstream stars', statChecked: 'Checked',
    listEyebrow: 'Checks · order',
    listTitle: 'All resources',
    allCategories: 'All', single: 'Single config', multi: 'Multi config', live: 'Live', epg: 'EPG',
    magnet: 'Magnet & BT', searchSites: 'Cloud search & subs', onlineSites: 'Streaming sites', apps: 'Apps', tools: 'Open source', via: 'via',
    searchLabel: 'Search resources', searchPlaceholder: 'Search name or source',
    result: (shown, total) => `Showing ${shown} of ${total}`,
    hintAll: 'Within a category: passing checks first, then the higher upstream rating, then name.',
    hintImportable: 'Copy the link and import it in a client. A passing check only means it answered once, not that it plays.',
    hintWeb: 'This category is used in a browser. These are not TVBox configs and will not work when imported.',
    hintApps: 'An app list: rows point at a repository, release page or download page and name their platform. Stars converted to a rating only mean popularity.',
    ratedAs: 'upstream', ratedNone: 'No rating', removed: 'Removed upstream',
    emptyText: 'No entries in this category.',
    noResults: 'No matching entries.',
    verifyTitle: 'Check log', verifyLead: 'A check answers one question: did it answer, and was the body the expected format. It does not prove import or playback.',
    testsLabel: 'Automated tests passed', ratingsLabel: 'Stars: upstream self-assessment', clientNotTested: 'Client playback: not verified', true4kNotTested: 'True 4K: not verified',
    checkPassed: 'Passed', checkFailed: 'Failed', checkNotTested: 'Not tested',
    rulesTitle: 'Inclusion rules',
    rule1Title: 'Traceable source', rule1Text: 'Every row records its upstream and licence note. Nothing is mirrored or republished.',
    rule2Title: 'Stars are upstream', rule2Text: 'Ratings are republished untouched with their check date. This project measured none of them and does not vouch for them.',
    rule3Title: 'No faked testing', rule3Text: 'Without client playback evidence, a row is never labelled tested or recommended.',
    footNote: 'Links point upstream; rights stay with their owners. Neither stars nor checks guarantee availability.',
    copy: 'Copy', copied: 'Copied', copyFailed: 'Copy failed', open: 'Open', details: 'Details',
    probeOk: 'Check passed', probeFail: 'Check failed', probeStale: 'Passed earlier', noProbe: 'Not checked',
    lastSuccess: (d) => `passed ${d}`,
    category: {
      'vod-single': 'Single config', 'vod-multi': 'Multi config', live: 'Live', epg: 'EPG', magnet: 'Magnet & BT',
      search: 'Cloud search & subs', apps: 'Apps',
      tools: 'Open source', online: 'Streaming sites',
    },
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

function starRow(average) {
  if (typeof average !== 'number' || !Number.isFinite(average)) return '';
  const rounded = Math.round(Math.max(0, Math.min(5, average)) * 2) / 2;
  let stars = '';
  for (let index = 1; index <= 5; index += 1) {
    const fill = rounded >= index ? 'star' : rounded >= index - 0.5 ? 'star star--half' : 'star star--empty';
    const paint = fill === 'star star--half' ? 'url(#star-half)' : undefined;
    stars += `<svg class="${fill}" viewBox="0 0 16 16" aria-hidden="true" focusable="false"><path d="${STAR_PATH}"${paint ? ` fill="${paint}"` : ''}/></svg>`;
  }
  const label = `${average.toFixed(2)} / 5`;
  return `<span class="stars" title="${escapeHTML(`${t().ratedAs} ${label}`)}" aria-label="${escapeHTML(`${t().ratedAs} ${label}`)}">${stars}</span><span class="rating-num">${escapeHTML(average.toFixed(1))}</span>`;
}

// Removed entries keep their record but must never rank as if still recommended.
function isRemoved(entry) {
  return entry.rating?.status === 'removed';
}

function ratingOf(entry) {
  if (isRemoved(entry)) return null;
  return entry.rating && typeof entry.rating.average === 'number' ? entry.rating.average : null;
}

// An upstream entry reused across devices is the same source, not a second one.
function dedupe(list) {
  const seen = new Set();
  return list.filter((entry) => {
    const key = String(entry.url).replace(/^https?:\/\//, '').replace(/\/+$/, '').toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

function sortEntries(list, probeIds) {
  return list.slice().sort((a, b) => {
    const passed = Number(probeIds.has(b.id)) - Number(probeIds.has(a.id));
    if (passed) return passed;
    const rated = (ratingOf(b) ?? -1) - (ratingOf(a) ?? -1);
    if (rated) return rated;
    return String(a.name).localeCompare(String(b.name), 'zh-Hans-CN');
  });
}

function actionsFor(entry) {
  const href = safeHref(entry.url);
  if (!href) return '';
  const copy = `<button class="act" type="button" data-copy-url="${escapeHTML(entry.url)}">${escapeHTML(t().copy)}</button>`;
  const open = `<a class="act act--fill" href="${escapeHTML(href)}" target="_blank" rel="noreferrer" title="${escapeHTML(`${t().open}: ${entry.name}`)}">${escapeHTML(t().open)}</a>`;
  return copy + open;
}

function renderRow(entry) {
  const href = safeHref(entry.url);
  const average = ratingOf(entry);
  const rating = isRemoved(entry)
    ? `<span class="chip chip--removed">${escapeHTML(t().removed)}</span>`
    : average === null ? `<span class="rating-num">${escapeHTML(t().ratedNone)}</span>` : starRow(average);
  const escapedSource = escapeHTML(entry.source);
  const sourceHost = displayHost(entry.source);
  // Repeating the aggregator URL on every imported row is noise; name it once, short.
  const source = sourceHost && sourceHost !== displayHost(entry.url)
    ? `<span class="chip chip--source">${escapeHTML(t().via)} <a href="${escapedSource}" target="_blank" rel="noreferrer">${escapeHTML(sourceHost)}</a></span>`
    : '';
  return `<article class="row">
    <div class="row-main">
      <div class="row-line">
        ${href ? `<a class="row-name" href="${escapeHTML(href)}" target="_blank" rel="noreferrer">${escapeHTML(entry.name)}</a>` : `<span class="row-name">${escapeHTML(entry.name)}</span>`}
        <span class="row-host">${escapeHTML(displayHost(entry.url))}</span>
      </div>
      <div class="row-meta">
        <span class="chip">${escapeHTML(t().category[entry._category] || entry._category)}</span>
        <span class="chip">${escapeHTML(entry.format)}</span>
        ${rating}
        ${probeChip(entry)}
        ${source}
      </div>
    </div>
    <div class="row-actions">${actionsFor(entry)}</div>
  </article>`;
}

function reachableIds() {
  const ids = new Set(entries.map((entry) => entry.id));
  return new Set((probeReport?.probes || [])
    .filter((probe) => probe.status === 'ok' && ids.has(probe.id)).map((probe) => probe.id));
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
  return sortEntries(dedupe(entries.filter((entry) => {
    if (activeCategory !== 'all' && entry._category !== activeCategory) return false;
    if (!query) return true;
    return `${entry.name} ${entry.format} ${entry.source} ${entry.notes || ''} ${entry.url}`.toLowerCase().includes(query);
  })), reachableIds());
}

function render() {
  const visible = currentVisible();
  const passed = reachableIds();
  document.getElementById('total-count').textContent = String(new Set(entries.map((entry) => entry.url)).size);
  document.getElementById('verified-count').textContent = String(passed.size);
  document.getElementById('rated-count').textContent = String(dedupe(entries.filter((entry) => ratingOf(entry) !== null)).length);
  document.getElementById('checked-at').textContent = formatDate(probeReport?.generated_at, true) || '—';
  document.getElementById('result-count').textContent = t().result(visible.length, new Set(entries.map((entry) => entry.url)).size);
  document.getElementById('tab-hint').textContent = activeCategory === 'all'
    ? t().hintAll
    : activeCategory === 'apps' ? t().hintApps
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
    counter.textContent = String(new Set(entries.filter((entry) => key === 'all' || entry._category === key).map((entry) => entry.url)).size);
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
    `<span>${escapeHTML(t().ratingsLabel)}</span>`,
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
    entries.sort((a, b) => (CATEGORY_ORDER[a._category] ?? 99) - (CATEGORY_ORDER[b._category] ?? 99)
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

document.body.addEventListener('click', async (event) => {
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

document.body.insertAdjacentHTML('afterbegin', STAR_DEFS);
applyLanguage();
loadData();
