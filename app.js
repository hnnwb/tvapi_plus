const CUSTOM_SINGLE_STATUS_URL = 'reports/custom-single-candidates.json';
const CATALOGS = [
  { file: 'catalog/vod-single.json', category: 'vod-single' },
  { file: 'catalog/vod-multi.json', category: 'vod-multi' },
  { file: 'catalog/live.json', category: 'live' },
  { file: 'catalog/epg.json', category: 'epg' },
  { file: 'catalog/tools.json', category: 'tools' },
];

const CATEGORY_NAMES = { 'vod-single': '单仓配置', 'vod-multi': '多仓配置', live: '直播', epg: '节目单与台标', tools: '工具与文档' };
const TEXT = {
  zh: {
 verificationEyebrow: '验证记录 / TEST EVIDENCE', verificationTitle: '可复现的验证记录', testsLabel: '自动化测试通过', clientPlaybackNotTested: 'TVBox 客户端实播：未验证', true4kNotTested: '真实 4K：未验证', checkPassed: '通过', checkFailed: '失败', checkNotTested: '未测试', checkDate: '测试记录',
 customSingleAvailable: '候选 API 单仓 · 未验证播放', customSingleUnavailable: '单仓候选暂不可用', navCatalog: '资源矩阵', navVerification: '验证记录', navQuality: '验证协议', heroEyebrow: '开放资源 · 资源索引', heroTitleFirst: '你的影视资源', heroTitleSecond: '导航中枢。', heroSubtitle: '配置、直播与节目单，一站检索。每条资源保留来源和自动探测结果，让选择有依据。', explore: '探索资源', submitSource: '提交资源', consoleTitle: '索引状态', consoleResources: '已收录资源', consoleReachable: '链接可达', consoleProbe: '最近探测', evidenceFirst: '以证据为先', single: '单仓配置', multi: '多仓配置', live: '直播', epg: '节目单与台标', tools: '工具与文档', quickSingle: '上游单仓索引；自建单仓有结果时列入其中', quickCustom: '候选 API · 未验证播放', quickMulti: '复制即可导入的多仓订阅', quickLive: '频道与直播列表', quickEpg: 'EPG 与图标资源', quickTools: '辅助工具与指南', catalogLive: '分类条目', catalogState: '目录', catalogHint: '选择分类可快速筛选', total: '目录条目', verified: '链接可达', checked: '最近探测', browse: 'BROWSE / 资源检索', catalogTitle: '资源矩阵', searchLabel: '搜索资源', searchPlaceholder: '搜索名称、格式或来源', categoryLabel: '资源类别', allCategories: '所有类别', single: '单仓配置', multi: '多仓配置', live: '直播', epg: '节目单与台标', tools: '工具与文档', copyUrl: '复制源链接', copied: '已复制', copyFailed: '复制失败', emptyTitle: '目录仍在建设中', emptyText: '目前没有已审核的资源条目。我们不会用未测试的链接填充数量；提交资源前请先阅读收录标准。', contribute: '查看收录说明 ↗', noResults: '没有符合条件的条目。试试其他关键词或筛选条件。', trustEyebrow: '验证协议 / VALIDATION PROTOCOL', qualityTitle: '数量不替代验证。', qualityText: '可访问不代表能播放；格式声明也不代表客户端兼容。自动链接探测与客户端播放验证是不同结论。', quality1Title: '来源可追溯', quality1Text: '记录上游出处与许可信息，不镜像或重发第三方配置。', quality2Title: '可用性有时效', quality2Text: '定时有限探测只代表当时网络结果，不保证持续可用。', quality3Title: '兼容性靠实测', quality3Text: '自动化检查链接与格式；实际导入和播放需在客户端验证。', footerNote: '由社区维护 · 条目链接指向上游 · 请遵守当地法律及上游条款', result: (shown, total) => `显示 ${shown} / ${total} 条`, noProbe: '暂无探测记录', lastProbe: (d) => `探测 ${d}`, status: { 'playback-tested': '播放实测', 'import-tested': '导入实测', 'format-claimed': '格式声称兼容', unknown: '未验证', incompatible: '不兼容' }, tested: (version, date) => `${version || '版本未记录'} · ${date || '日期未记录'}`, source: '来源', openResource: '打开资源链接', genericCategory: '资源', emptyProbe: '尚无公开探测记录', probePassing: (n) => `${n} 条可达`, probeOk: '链接探测通过', probeFailed: '本次探测失败', probeStale: '探测失败 · 上次曾通过', fallbackUsed: '使用已审核备用地址', lastSuccess: (d) => `上次成功 ${d}`, loadError: '目录文件读取失败，请稍后刷新重试。'
  },
  en: {
 verificationEyebrow: 'VERIFICATION LOG / TEST EVIDENCE', verificationTitle: 'Reproducible verification', testsLabel: 'Automated tests passed', clientPlaybackNotTested: 'TVBox client playback: not verified', true4kNotTested: 'True 4K: not verified', checkPassed: 'Passed', checkFailed: 'Failed', checkNotTested: 'Not tested', checkDate: 'Recorded',
 customSingleAvailable: 'Candidate API bundle · playback unverified', customSingleUnavailable: 'Custom bundle unavailable', navCatalog: 'Resource matrix', navVerification: 'Test evidence', navQuality: 'Validation', heroEyebrow: 'OPEN SOURCE · RESOURCE INDEX', heroTitleFirst: 'Your media source', heroTitleSecond: 'command center.', heroSubtitle: 'Find configurations, live TV, and EPG in one place. Provenance and automated probe results stay visible on every entry.', explore: 'Explore resources', submitSource: 'Submit a source', consoleTitle: 'INDEX STATUS', consoleResources: 'Catalog entries', consoleReachable: 'Links reachable', consoleProbe: 'Latest probe', evidenceFirst: 'EVIDENCE FIRST', quickSingle: 'Upstream single-source index', quickCustom: 'Candidate APIs · playback unverified', quickMulti: 'Multi-source subscription URL', quickLive: 'Channels and playlists', quickEpg: 'EPG and channel logos', quickTools: 'Utilities and guides', catalogLive: 'Category entries', catalogState: 'CATALOG', catalogHint: 'Choose a category to filter', total: 'Catalog entries', verified: 'Links reachable', checked: 'Latest probe', browse: 'BROWSE / DISCOVER', catalogTitle: 'Resource matrix', searchLabel: 'Search resources', searchPlaceholder: 'Search name, format, or source', categoryLabel: 'Resource category', allCategories: 'All categories', single: 'Single-source config', multi: 'Multi-source config', live: 'Live TV', epg: 'EPG and logos', tools: 'Tools and docs', copyUrl: 'Copy source URL', copied: 'Copied', copyFailed: 'Copy failed', emptyTitle: 'Catalog is being built', emptyText: 'There are no reviewed entries yet. We will not inflate counts with untested links; review the inclusion criteria before submitting a resource.', contribute: 'Read contribution guide ↗', noResults: 'No entries match. Try another keyword or filter.', trustEyebrow: 'VALIDATION PROTOCOL', qualityTitle: 'Volume is not verification.', qualityText: 'Reachability does not mean playable, and a format claim does not prove client compatibility. Automated link probes and client playback tests answer different questions.', quality1Title: 'Traceable provenance', quality1Text: 'Record upstream origin and license; do not mirror or republish third-party configs.', quality2Title: 'Time-bounded availability', quality2Text: 'Scheduled probes reflect one network observation, not a guarantee of continued availability.', quality3Title: 'Compatibility requires testing', quality3Text: 'Automated checks cover links and formats; import and playback need the actual client.', footerNote: 'Community maintained · Links point upstream · Follow local law and upstream terms', result: (shown, total) => `Showing ${shown} / ${total}`, noProbe: 'No probe recorded', lastProbe: (d) => `Checked ${d}`, status: { 'playback-tested': 'Playback tested', 'import-tested': 'Import tested', 'format-claimed': 'Format claimed', unknown: 'Unverified', incompatible: 'Incompatible' }, tested: (version, date) => `${version || 'Version not recorded'} · ${date || 'Date not recorded'}`, source: 'Source', openResource: 'Open resource link', genericCategory: 'Resource', emptyProbe: 'No published probe data', probePassing: (n) => `${n} reachable`, probeOk: 'Link probe passed', probeFailed: 'Latest check failed', probeStale: 'Check failed · previously passed', fallbackUsed: 'Reviewed fallback used', lastSuccess: (d) => `Last success ${d}`, loadError: 'Catalog files failed to load. Please refresh and try again.'
  }
};

let entries = [];
let lang = localStorage.getItem('tvapi-language') || (navigator.language.toLowerCase().startsWith('zh') ? 'zh' : 'en');
let probeReport = null;
let verificationReport = null;
let customSingleState = 'loading';
let customSingleMode = 'unavailable';

function applyLanguage() {
  document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
  document.querySelectorAll('[data-i18n]').forEach((node) => {
    const value = TEXT[lang][node.dataset.i18n];
    if (typeof value === 'string') node.textContent = value;
  });
  document.querySelectorAll('[data-i18n-placeholder]').forEach((node) => { node.placeholder = TEXT[lang][node.dataset.i18nPlaceholder]; });
  document.getElementById('page-title').replaceChildren(
    document.createTextNode(`${TEXT[lang].heroTitleFirst} `),
    document.createElement('br'),
    Object.assign(document.createElement('em'), { textContent: TEXT[lang].heroTitleSecond })
  );
  document.querySelectorAll('[data-count-for]').forEach((counter) => {
    const count = entries.filter((entry) => entry._category === counter.dataset.countFor).length;
    counter.textContent = String(count).padStart(2, '0');
  });
  document.getElementById('visible-categories').textContent = String(new Set(entries.map((entry) => entry._category)).size).padStart(2, '0');
  document.getElementById('language-toggle').textContent = lang === 'zh' ? 'EN' : '中文';
  renderCustomSingleState();
  document.getElementById('language-toggle').setAttribute('aria-label', lang === 'zh' ? 'Switch language' : '切换语言');
  if (verificationReport) renderVerification(verificationReport);
  render();
}

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
  const copyUrl = safeHref ? String(entry.url) : null;
  const probe = probeReport?.probes?.some((item) => item.id === entry.id) ? probeInfo(entry.id) : null;
  const probeMarkup = probe
    ? `<span class="test-date">${escapeHTML(probe.label)}${probe.dateText ? ` · ${escapeHTML(probe.dateText)}` : ''}${probe.item.used_fallback ? ` · ${escapeHTML(TEXT[lang].fallbackUsed)}` : ''}${probe.previousDateText ? ` · ${escapeHTML(TEXT[lang].lastSuccess(probe.previousDateText))}` : ''}</span>`
    : `<span class="test-date">${escapeHTML(TEXT[lang].emptyProbe)}</span>`;
  const licenseMarkup = entry.license ? `<span class="test-date">${escapeHTML(entry.license)}</span>` : '';
  return `<article class="catalog-item">
    <div class="item-primary"><div class="item-name">${escapeHTML(entry.name)}</div><div class="item-source" title="${source}">${escapeHTML(TEXT[lang].source)}: ${source}</div>${licenseMarkup}</div>
    <div class="item-meta"><span class="item-category">${escapeHTML(categoryLabel(entry._category))}</span><span class="item-format">${escapeHTML(entry.format)}</span></div>
    <div class="item-tests">${probeMarkup}</div>
    <div class="item-actions">
      ${copyUrl ? `<button class="item-copy" type="button" data-copy-url="${escapeHTML(copyUrl)}" aria-label="${escapeHTML(TEXT[lang].copyUrl)}: ${escapeHTML(entry.name)}" title="${escapeHTML(TEXT[lang].copyUrl)}"><svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="12" rx="1"/><path d="M16 8V4H4v12h4"/></svg><span data-copy-label>${escapeHTML(TEXT[lang].copyUrl)}</span></button>` : ''}
      ${safeHref ? `<a class="item-link" href="${escapeHTML(safeHref)}" target="_blank" rel="noreferrer" aria-label="${escapeHTML(TEXT[lang].openResource)}: ${escapeHTML(entry.name)}" title="${escapeHTML(TEXT[lang].openResource)}">↗</a>` : ''}
    </div>
  </article>`;
}
function renderCustomSingleState() {
  const link = document.getElementById('custom-single-link');
  if (!link) return;
  const available = customSingleState === 'available' || customSingleState === 'candidate';
  link.hidden = customSingleState === 'unavailable' || customSingleState === 'loading';
  link.href = available ? 'subscriptions/tvbox-custom-single.json' : '#custom-single-link';
  link.classList.toggle('is-disabled', !available);
  link.setAttribute('aria-disabled', String(!available));
  link.title = customSingleMode === 'historical-unverified'
    ? (lang === 'zh' ? '历史结构化配置中的去重 type-1 接口；仅作候选，未实播' : 'Deduplicated type-1 APIs from structural config parses; candidates only, not playback tested')
    : customSingleMode === 'screened'
      ? (lang === 'zh' ? 'CMS 接口检查通过；媒体和客户端播放未验证' : 'CMS checks passed; media and client playback unverified')
      : '';
  link.tabIndex = available ? 0 : -1;
  link.querySelector('[data-i18n="quickCustom"]').textContent = customSingleMode === 'historical-unverified'
    ? (lang === 'zh' ? `历史候选 API · 未验证播放 · ${window.customSingleStatus?.unique_candidate_apis || 0} 个` : `Historical API candidates · playback unverified · ${window.customSingleStatus?.unique_candidate_apis || 0}`)
    : available ? TEXT[lang].customSingleAvailable : TEXT[lang].customSingleUnavailable;
  link.querySelector('.quick-amount').textContent = available
    ? (customSingleMode === 'historical-unverified' ? `${window.customSingleStatus?.unique_candidate_apis || 0} API` : 'JSON')
    : '—';
}
function render() {
  renderCustomSingleState();
  const query = document.getElementById('search').value.trim().toLowerCase();
  const category = document.getElementById('category-filter').value;
  const filtered = entries.filter((entry) => {
    const haystack = `${entry.name} ${entry.format} ${entry.source} ${entry.notes} ${entry.url}`.toLowerCase();
    return (category === 'all' || entry._category === category) && haystack.includes(query);
  });
  document.getElementById('total-count').textContent = String(entries.length);
  const currentIds = new Set(entries.map((entry) => entry.id));
  const successfulProbes = new Set((probeReport?.probes || []).filter((probe) => probe.status === 'ok' && currentIds.has(probe.id)).map((probe) => probe.id));
  document.getElementById('verified-count').textContent = String(successfulProbes.size);
  const checked = probeReport?.generated_at ? new Date(probeReport.generated_at) : null;
  const failedCount = new Set((probeReport?.probes || []).filter((probe) => probe.status === 'failed').map((probe) => probe.id)).size;
  const checkedDate = checked && !Number.isNaN(checked.valueOf()) ? checked.toLocaleDateString(lang === 'zh' ? 'zh-CN' : 'en', { month: 'short', day: 'numeric' }) : '—';
  document.getElementById('checked-at').textContent = failedCount ? `${checkedDate} · ${failedCount} ${lang === 'zh' ? '项失败' : 'failed'}` : checkedDate;
  document.getElementById('result-count').textContent = TEXT[lang].result(filtered.length, entries.length);
  document.getElementById('catalog-list').innerHTML = filtered.map(renderCard).join('');
  document.getElementById('empty-state').hidden = entries.length !== 0;
  document.getElementById('no-results').hidden = entries.length === 0 || filtered.length !== 0;
}

function renderVerification(report) {
  const date = new Date(report.generated_at);
  document.getElementById('verification-date').textContent = Number.isNaN(date.valueOf()) ? '—' : date.toLocaleString(lang === 'zh' ? 'zh-CN' : 'en', { dateStyle: 'medium', timeStyle: 'short' });
  const summary = report.summary || {};
  document.getElementById('verification-summary').innerHTML = [
    `<span>${escapeHTML(TEXT[lang].testsLabel)}: <strong>${Number(summary.local_unit_tests_passed) || 0}</strong></span>`,
    `<span>${escapeHTML(TEXT[lang].clientPlaybackNotTested)}</span>`,
    `<span>${escapeHTML(TEXT[lang].true4kNotTested)}</span>`
  ].join('');
  const labels = { passed: TEXT[lang].checkPassed, failed: TEXT[lang].checkFailed, 'not-tested': TEXT[lang].checkNotTested };
  document.getElementById('verification-list').innerHTML = (report.checks || []).map((check) => {
    const title = lang === 'zh' ? check.subject_zh : check.subject;
    const description = lang === 'zh' ? check.method_zh : check.method;
    return `<article class="verification-item"><div class="verification-item-head"><h3>${escapeHTML(title)}</h3><span class="verification-status status-${escapeHTML(check.status)}">${escapeHTML(labels[check.status] || labels['not-tested'])}</span></div><p>${escapeHTML(description)}</p><small>${escapeHTML(check.snapshot)} · ${escapeHTML(check.kind)}</small><p class="verification-limit">${escapeHTML(check.limitations)}</p></article>`;
  }).join('');
}

async function loadData() {
  try {
    const [catalogResults, reportResponse, verificationResponse, screeningResponse, customStatusResponse] = await Promise.all([
      Promise.all(CATALOGS.map(async ({ file, category }) => {
        const response = await fetch(file, { cache: 'no-store' });
        if (!response.ok) throw new Error(`${file}: HTTP ${response.status}`);
        const data = await response.json();
        if (!Array.isArray(data)) throw new Error(`${file}: expected array`);
        return data.map((entry) => ({ ...entry, _category: category }));
      })),
      fetch('probe-report.json', { cache: 'no-store' }).catch(() => null),
      fetch('reports/verification-report.json', { cache: 'no-store' }).catch(() => null),
      fetch('reports/interface-screening.json', { cache: 'no-store' }).catch(() => null),
      fetch(CUSTOM_SINGLE_STATUS_URL, { cache: 'no-store' }).catch(() => null)
    ]);
    entries = catalogResults.flat();
    if (reportResponse?.ok) probeReport = await reportResponse.json();
    if (verificationResponse?.ok) {
      verificationReport = await verificationResponse.json();
      renderVerification(verificationReport);
    }
    if (screeningResponse?.ok) {
      const screening = await screeningResponse.json();
      if (customStatusResponse?.ok) window.customSingleStatus = await customStatusResponse.json();
      const screenedReady = Number(screening.summary?.included) > 0 && Number(screening.summary?.cms_api_tested) > 0;
      customSingleState = screenedReady ? 'available' : Number(screening.limits?.historical_candidate_apis) > 0 ? 'candidate' : 'unavailable';
      const candidateReady = window.customSingleStatus?.verification_status === 'unverified-candidate'
        && Number(window.customSingleStatus.unique_candidate_apis) > 0;
      customSingleState = screenedReady ? 'available' : candidateReady ? 'candidate' : 'unavailable';
      customSingleMode = screenedReady ? 'screened' : candidateReady ? 'historical-unverified' : 'unavailable';
    } else {
      customSingleState = 'unavailable';
    }
    applyLanguage();
  } catch (error) {
    console.error('Unable to load catalog:', error);
    customSingleState = 'unavailable';
    customSingleMode = 'unavailable';
    renderCustomSingleState();
    document.getElementById('empty-state').hidden = true;
    const state = document.getElementById('no-results');
    state.textContent = TEXT[lang].loadError;
    state.hidden = false;
  }
}

document.getElementById('search').addEventListener('input', render);
document.getElementById('category-filter').addEventListener('change', render);
document.getElementById('catalog-list').addEventListener('click', async (event) => {
  const button = event.target.closest('[data-copy-url]');
  if (!button) return;
  const url = button.dataset.copyUrl;
  const fallbackCopy = () => {
    const field = document.createElement('textarea');
    field.value = url;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.append(field);
    field.select();
    const copied = document.execCommand('copy');
    field.remove();
    if (!copied) window.prompt(TEXT[lang].copyFailed, url);
    return copied;
  };
  try {
    if (!navigator.clipboard?.writeText) throw new Error('Clipboard API unavailable');
    await navigator.clipboard.writeText(url);
    const label = button.querySelector('[data-copy-label]');
    label.textContent = TEXT[lang].copied;
    button.classList.add('is-copied');
    window.setTimeout(() => {
      if (!button.isConnected) return;
      label.textContent = TEXT[lang].copyUrl;
      button.classList.remove('is-copied');
    }, 1800);
  } catch {
    if (fallbackCopy()) {
      button.querySelector('[data-copy-label]').textContent = TEXT[lang].copied;
      button.classList.add('is-copied');
      window.setTimeout(() => {
        if (!button.isConnected) return;
        button.querySelector('[data-copy-label]').textContent = TEXT[lang].copyUrl;
        button.classList.remove('is-copied');
      }, 1800);
    }
  }
});
document.querySelectorAll('.quick-link[data-category]').forEach((link) => {
  link.addEventListener('click', () => {
    document.getElementById('category-filter').value = link.dataset.category;
    render();
  });
});
document.addEventListener('keydown', (event) => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault();
    document.getElementById('search').focus();
  }
});
document.getElementById('language-toggle').addEventListener('click', () => {
  lang = lang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('tvapi-language', lang);
  applyLanguage();
});
applyLanguage();
loadData();
