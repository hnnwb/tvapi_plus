const CATALOGS = [
  { file: 'catalog/vod-single.json', category: 'vod-single' },
  { file: 'catalog/vod-multi.json', category: 'vod-multi' },
  { file: 'catalog/live.json', category: 'live' },
  { file: 'catalog/epg.json', category: 'epg' },
  { file: 'catalog/tools.json', category: 'tools' },
];

const CLIENT_NAMES = { yingxia: 'Yingxia', yingshicang: '影视仓' };
const CATEGORY_NAMES = { 'vod-single': '单仓配置', 'vod-multi': '多仓配置', live: '直播', epg: '节目单与台标', tools: '工具与文档' };
const APP_NAMES = { yingxia: 'Yingxia', yingshicang: '影视仓' };
const TEXT = {
  zh: {
    noProbe: '尚无公开探测记录', eyebrow: 'TVBOX · 开源资源目录', title: '好源有据，逐条验证。', subtitle: '集中查找配置、直播与节目单资源。每条目标明来源、可用性检查和 Yingxia / 影视仓的实际测试状态。', total: '目录条目', verified: '播放实测', checked: '最近探测', browse: 'BROWSE', catalogTitle: '资源目录', searchLabel: '搜索资源', searchPlaceholder: '搜索名称、格式或来源', categoryLabel: '资源类别', allCategories: '所有类别', single: '单仓配置', multi: '多仓配置', live: '直播', epg: '节目单与台标', tools: '工具与文档', clientLabel: '客户端测试状态', allClients: '所有客户端状态', playbackTested: '播放实测', importTested: '导入实测', formatClaimed: '格式声称兼容', unknown: '未验证', incompatible: '不兼容', emptyTitle: '目录仍在建设中', emptyText: '目前没有已审核的资源条目。我们不会用未测试的链接填充数量；提交资源前请先阅读收录标准。', contribute: '查看收录说明 ↗', noResults: '没有符合条件的条目。试试其他关键词或筛选条件。', trustEyebrow: 'QUALITY CONTROL', qualityTitle: '数量不替代验证。', qualityText: '可访问不代表能播放；格式声明也不代表客户端兼容。状态按证据分级，测试记录包含客户端版本与日期。', quality1Title: '来源可追溯', quality1Text: '记录上游出处与许可信息，不镜像或重发第三方配置。', quality2Title: '可用性有时效', quality2Text: '定时有限探测只代表当时网络结果，不保证持续可用。', quality3Title: '兼容性靠实测', quality3Text: '分别标注格式声明、导入成功和实际播放，不把它们混为一谈。', footerNote: '由社区维护 · 条目链接指向上游 · 请遵守当地法律及上游条款', result: (shown, total) => `显示 ${shown} / ${total} 条`, noProbe: '暂无探测记录', lastProbe: (d) => `探测 ${d}`, status: { 'playback-tested': '播放实测', 'import-tested': '导入实测', 'format-claimed': '格式声称兼容', unknown: '未验证', incompatible: '不兼容' }, tested: (version, date) => `${version || '版本未记录'} · ${date || '日期未记录'}`, source: '来源', openResource: '打开资源链接', genericCategory: '资源', emptyProbe: '尚无公开探测记录', probeOk: '可访问性检查通过', probeFailed: '本次探测失败', probeStale: '探测失败 · 上次曾通过', fallbackUsed: '使用已审核备用地址', lastSuccess: (d) => `上次成功 ${d}`, loadError: '目录文件读取失败，请稍后刷新重试。'
  },
  en: {
    noProbe: 'No published probe data', eyebrow: 'TVBOX · OPEN RESOURCE CATALOG', title: 'Sources with evidence.', subtitle: 'Browse configuration, live TV, and EPG resources. Each entry separates provenance, availability checks, and hands-on Yingxia / Yingshicang results.', total: 'Catalog entries', verified: 'Playback tested', checked: 'Latest probe', browse: 'BROWSE', catalogTitle: 'Resource catalog', searchLabel: 'Search resources', searchPlaceholder: 'Search name, format, or source', categoryLabel: 'Resource category', allCategories: 'All categories', single: 'Single-source config', multi: 'Multi-source config', live: 'Live TV', epg: 'EPG and logos', tools: 'Tools and docs', clientLabel: 'Client test status', allClients: 'All client statuses', playbackTested: 'Playback tested', importTested: 'Import tested', formatClaimed: 'Format claimed', unknown: 'Unverified', incompatible: 'Incompatible', emptyTitle: 'Catalog is being built', emptyText: 'There are no reviewed entries yet. We will not inflate counts with untested links; review the inclusion criteria before submitting a resource.', contribute: 'Read contribution guide ↗', noResults: 'No entries match. Try another keyword or filter.', trustEyebrow: 'QUALITY CONTROL', qualityTitle: 'Volume is not verification.', qualityText: 'Reachability does not mean playable, and a format claim does not prove client compatibility. Statuses follow evidence, with client versions and dates recorded for tests.', quality1Title: 'Traceable provenance', quality1Text: 'Record upstream origin and license; do not mirror or republish third-party configs.', quality2Title: 'Time-bounded availability', quality2Text: 'Scheduled probes reflect one network observation, not a guarantee of continued availability.', quality3Title: 'Compatibility requires testing', quality3Text: 'Format claims, successful imports, and actual playback are reported separately.', footerNote: 'Community maintained · Links point upstream · Follow local law and upstream terms', result: (shown, total) => `Showing ${shown} / ${total}`, noProbe: 'No probe recorded', lastProbe: (d) => `Checked ${d}`, status: { 'playback-tested': 'Playback tested', 'import-tested': 'Import tested', 'format-claimed': 'Format claimed', unknown: 'Unverified', incompatible: 'Incompatible' }, tested: (version, date) => `${version || 'Version not recorded'} · ${date || 'Date not recorded'}`, source: 'Source', openResource: 'Open resource link', genericCategory: 'Resource', emptyProbe: 'No published probe data', probeOk: 'Availability check passed', probeFailed: 'Latest check failed', probeStale: 'Check failed · previously passed', fallbackUsed: 'Reviewed fallback used', lastSuccess: (d) => `Last success ${d}`, loadError: 'Catalog files failed to load. Please refresh and try again.'
  }
};

let entries = [];
let lang = localStorage.getItem('tvapi-language') || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
let probeReport = null;

function applyLanguage() {
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const value = TEXT[lang][node.dataset.i18n];
    if (typeof value === 'string') node.textContent = value;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => { node.placeholder = TEXT[lang][node.dataset.i18nPlaceholder]; });
  document.getElementById('language-toggle').textContent = lang === 'zh' ? 'EN' : '中文';
  document.getElementById('language-toggle').setAttribute('aria-label', lang === 'zh' ? 'Switch language' : '切换语言');
  render();
}

function entryStates(entry) { return Object.values(entry.clients || {}).map((result) => result.status); }
function hasClientState(entry, filter) { return filter === 'all' || entryStates(entry).includes(filter); }
function categoryLabel(category) {
  const keys = { 'vod-single': 'single', 'vod-multi': 'multi', live: 'live', epg: 'epg', tools: 'tools' };
  return TEXT[lang][keys[category]] || (lang === 'zh' ? CATEGORY_NAMES[category] : TEXT[lang].genericCategory);
}
function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
}
function safeExternalUrl(value) {
  try {
    const url = new URL(value);
    return ['http:', 'https:'].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}
function probeInfo(id) {
  const item = probeReport?.probes?.find((probe) => probe.id === id);
  if (!item) return null;
  const dateValue = item.status === 'ok' ? (item.last_success_at || item.checked_at) : (item.last_success_at || null);
  const date = dateValue ? new Date(dateValue) : null;
  const dateText = date && !Number.isNaN(date.valueOf())
    ? date.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en', { year: 'numeric', month: 'short', day: 'numeric' })
    : null;
  const label = item.status === 'ok'
    ? TEXT[lang].probeOk
    : item.stale ? TEXT[lang].probeStale : TEXT[lang].probeFailed;
  const previousSuccess = item.status === 'ok' ? item.previous_last_success_at : item.last_success_at;
  const previousDate = previousSuccess ? new Date(previousSuccess) : null;
  const previousDateText = previousDate && !Number.isNaN(previousDate.valueOf())
    ? previousDate.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en', { year: 'numeric', month: 'short', day: 'numeric' })
    : null;
  return { item, dateText, label, previousDateText };
}
function renderCard(entry) {
  const source = escapeHTML(entry.source);
  const safeHref = safeExternalUrl(entry.url);
  const clientMarkup = Object.entries(entry.clients || {}).map(([id, result]) => {
    const status = TEXT[lang].status[result.status] || result.status;
    const clientName = APP_NAMES[id] || CLIENT_NAMES[id] || id;
    const when = result.tested_at ? `<span class="test-date">${escapeHTML(TEXT[lang].tested(result.tested_version, result.tested_at))}</span>` : '';
    return `<span><span class="status status-${escapeHTML(result.status)}">${escapeHTML(clientName)} · ${escapeHTML(status)}</span>${when}</span>`;
  }).join('');
  const probe = probeInfo(entry.id);
  const probeMarkup = probe
    ? `<span class="test-date">${escapeHTML(probe.label)}${probe.dateText ? ` · ${escapeHTML(probe.dateText)}` : ''}${probe.item.used_fallback ? ` · ${escapeHTML(TEXT[lang].fallbackUsed)}` : ''}${probe.previousDateText ? ` · ${escapeHTML(TEXT[lang].lastSuccess(probe.previousDateText))}` : ''}</span>`
    : `<span class="test-date">${escapeHTML(TEXT[lang].emptyProbe)}</span>`;
  const licenseMarkup = entry.license ? `<span class="test-date">${escapeHTML(entry.license)}</span>` : '';
  return `<article class="catalog-item">
    <div class="item-primary"><div class="item-name">${escapeHTML(entry.name)}</div><div class="item-source" title="${source}">${escapeHTML(TEXT[lang].source)}: ${source}</div>${licenseMarkup}</div>
    <div class="item-meta"><span class="item-category">${escapeHTML(categoryLabel(entry._category))}</span><span class="item-format">${escapeHTML(entry.format)}</span></div>
    <div class="item-tests"><div class="client-results">${clientMarkup}</div>${probeMarkup}</div>
    ${safeHref ? `<a class="item-link" href="${escapeHTML(safeHref)}" target="_blank" rel="noreferrer" aria-label="${escapeHTML(TEXT[lang].openResource)}: ${escapeHTML(entry.name)}" title="${escapeHTML(TEXT[lang].openResource)}">↗</a>` : '<span class="item-link" aria-hidden="true">–</span>'}
  </article>`;
}
function render() {
  const query = document.getElementById('search').value.trim().toLowerCase();
  const category = document.getElementById('category-filter').value;
  const client = document.getElementById('client-filter').value;
  const filtered = entries.filter((entry) => {
    const haystack = `${entry.name} ${entry.format} ${entry.source} ${entry.notes} ${entry.url}`.toLowerCase();
    return (category === 'all' || entry._category === category) && hasClientState(entry, client) && haystack.includes(query);
  });
  document.getElementById('total-count').textContent = String(entries.length);
  document.getElementById('verified-count').textContent = String(entries.filter((entry) => entryStates(entry).includes('playback-tested')).length);
  const checked = probeReport?.generated_at ? new Date(probeReport.generated_at) : null;
  const failedCount = probeReport?.probes?.filter((probe) => probe.status === 'failed').length || 0;
  const checkedDate = checked && !Number.isNaN(checked.valueOf()) ? checked.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en', { month: 'short', day: 'numeric' }) : '—';
  document.getElementById('checked-at').textContent = failedCount ? `${checkedDate} · ${failedCount} ${lang === 'zh' ? '项失败' : 'failed'}` : checkedDate;
  document.getElementById('result-count').textContent = TEXT[lang].result(filtered.length, entries.length);
  document.getElementById('catalog-list').innerHTML = filtered.map(renderCard).join('');
  document.getElementById('empty-state').hidden = entries.length !== 0;
  document.getElementById('no-results').hidden = entries.length === 0 || filtered.length !== 0;
}

async function loadData() {
  try {
    const [catalogResults, reportResponse] = await Promise.all([
      Promise.all(CATALOGS.map(async ({ file, category }) => {
        const response = await fetch(file, { cache: 'no-store' });
        if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error(`${file}: expected array`);
        return data.map((entry) => ({ ...entry, _category: category }));
      })),
      fetch('probe-report.json', { cache: 'no-store' }).catch(() => null)
    ]);
    entries = catalogResults.flat();
    if (reportResponse?.ok) probeReport = await reportResponse.json();
    applyLanguage();
  } catch (error) {
    console.error('Unable to load catalog:', error);
    document.getElementById('empty-state').hidden = true;
    const state = document.getElementById('no-results');
    state.textContent = TEXT[lang].loadError;
    state.hidden = false;
  }
}

document.getElementById('search').addEventListener('input', render);
document.getElementById('category-filter').addEventListener('change', render);
document.getElementById('client-filter').addEventListener('change', render);
document.getElementById('language-toggle').addEventListener('click', () => {
  lang = lang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('tvapi-language', lang);
  applyLanguage();
});
applyLanguage();
loadData();
