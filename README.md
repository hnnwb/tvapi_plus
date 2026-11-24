# TVBox 资源目录

**简体中文** | [English](README.en.md)

一个面向 TVBox 生态的资源目录与格式检查项目。仓库记录资源链接和来源信息，不镜像第三方配置内容，也不运行源插件。

## 项目范围

- 使用一个主目录，按资源类型分类。
- 分开说明自动链接探测与客户端导入/播放能力；后两者需要运行真实客户端。
- 自动检查条目元数据；可选执行有限的 HTTP 探测与基础格式检查。
- 不自动解密、改写、代理或重新发布第三方配置，不在 CI 中执行 JS、Python 或 JAR 插件。

目录已收录少量经来源记录、可访问性或结构检查的直播列表、VOD 配置索引、EPG 与工具参考；这不代表已完成全面审核。请勿将 Awesome TVBox 等目录中的所有链接直接复制进来。只添加你有权公开引用的链接；公开可访问不等于获得版权授权，也不代表资源安全、兼容或可播放。格式错误、来源不明或权利无法说明的配置（例如当前无效的 XYQ JSON）不会作为可用接口收录。不要提交凭据、私人链接、令牌或账号信息。

## 目录结构

```text
catalog/
  vod-single.json    # 单仓配置链接
  vod-multi.json     # 多仓（urls）配置链接
  live.json          # M3U/TXT/JSON 直播列表
  epg.json           # EPG 与台标资源
  tools.json         # 开源项目仓库（只记地址与上游星级）
  online.json        # 在线影视站与下载落地页（适配浏览器，不导入客户端）
  search.json        # 网盘搜索与字幕站
  magnet.json        # 磁力与 BT 搜索站
  apps.json          # 应用：客户端仓库、产品页与下载页，条目写明支持的系统
schemas/
  catalog.schema.json       # 目录条目结构参考
  probe-report.schema.json   # 探测报告结构
scripts/
  check_catalog.py           # 元数据检查，可选 URL 探测
  refresh_status.py          # 定时重试/备用地址探测
  import_upstream.py         # 合并上游目录条目（按 URL 去重，可选）
  import_apps.py             # 合并上游客户软件清单（按 URL 去重，可选）
  check_upstream.py          # 定时比对两个上游清单：跟地址变更、报新加与消失（可选）
  build_subscriptions.py     # 生成配置索引与多仓订阅
.github/workflows/
  catalog-check.yml
```

## 添加条目

每个分类文件都是 JSON 数组。按相应类别填写允许的 `format`，每个 `id` 在所有分类中必须唯一：

```json
{
  "id": "reviewed-multi-source",
  "name": "已审核的多仓目录",
  "url": "https://example.org/catalog.json",
  "format": "tvbox-multi",
  "source": "https://github.com/owner/project",
  "license": "以上游条款为准",
  "notes": "已于 2026-11-20 审核公开引用",
  "rating": {
    "average": 4.4,
    "scores": { "more": 5, "speed": 4, "clean": 4, "stable": 4, "ease": 5 },
    "status": "recommended",
    "checked_at": "2026-06-06"
  }
}
```

`rating` 可选，只能转载上游自评：`scores` 必须包含 `more`、`speed`、`clean`、`stable`、`ease` 五个 1–5 的值，`average` 必须等于五项均值，`checked_at` 为 `YYYY-MM-DD`。检查脚本会拒绝均值不符、越界或字段缺失的评分。它是上游的判断，本仓库没有实测，也不构成推荐。

各分类允许格式：

| 文件 | `format` 值 |
| --- | --- |
| `vod-single.json` | `tvbox-json` |
| `vod-multi.json` | `tvbox-multi` |
| `live.json` | `m3u`、`txt`、`tvbox-live-json` |
| `epg.json` | `epg-xml`、`logo-library` |
| `tools.json` | `documentation`、`utility`、`project` |
| `online.json` | `web` |
| `search.json` | `web` |
| `magnet.json` | `web` |
| `apps.json` | `web`、`link-page`、`project`（三者都是该应用的入口） |

条目结构参考见 [`schemas/catalog.schema.json`](schemas/catalog.schema.json)。目录仅显示自动链接探测结果；客户端导入或实际播放需要运行客户端，不在页面显示占位状态。当前检查脚本直接执行自己的字段检查逻辑；JSON Schema 文件作为结构文档，尚未由脚本加载验证。

## 本地检查

需要 Python 3.10 或更高版本，不需要第三方 Python 包：

```sh
python3 scripts/check_catalog.py
python3 scripts/check_catalog.py --check-urls --report probe-report.json
python3 scripts/refresh_status.py --report /tmp/probe-report.json --retries 0 --delay 0
# Optional: TVBox-like configuration-fetch request headers (not app/runtime playback)
python3 scripts/refresh_status.py --request-profile tvbox --report /tmp/probe-report.json --retries 0 --delay 0
```

默认只做离线元数据检查。`--check-urls` 仅联系解析到公网地址的第三方主机，使用有超时和响应体大小限制的 GET 请求；跳转目标也必须是公网 HTTP(S)，不执行响应内容。它会对 TVBox JSON、多仓 `urls`、M3U/TXT、直播 JSON 和 EPG XML 做基本结构检查。网络探测失败只记录在报告中，不会自动删除或改写目录条目。不同地区、网络、User-Agent 和上游策略可能导致结果不同。刷新脚本默认用项目标识 UA；可选 `--request-profile tvbox` 只模拟 TVBox 风格的配置拉取请求头（`okhttp/3.15` 和 `X-Requested-With: com.github.tvbox.osc`），用来观察服务端兼容性差异，不会运行客户端、Spider 或播放器，也不代表实际导入/播放测试。

## GitHub Actions

- push 和 Pull Request 对目录、Schema、脚本或工作流文件的变更触发离线元数据检查。
- 每日两次定时任务先跑 `scripts/check_upstream.py`：抓两个上游清单（`laoma528/awesome-zhuiju-free` 的 `resources.json` 与 `jiji262/awesome-tvbox` 的 README）按条目比对。上游改了地址的条目自动跟随并把旧地址写进 `fallback_urls`；上游新加的条目用同一个导入脚本自动收录进对应分类，删除的只写进 `reports/upstream-changes.json` 并在页面「上游变动」里列出，不自动删除。抓取失败时保留上次快照，不影响后面的探测。
- 每日两次定时任务及手动选择 URL 检查的工作流会运行有限 URL/格式探测，带短重试；可选 `fallback_urls` 必须先审核且不会自动发现或写入。成功仅表示该次链接/格式探测通过，不代表客户端可导入或实际播放。
- 探测会原子更新 `probe-report.json` 并提交状态文件，保留上次成功时间；当前失败会标记为 failed/stale，不删除目录条目，也不覆盖配置数据。仓库中的空状态报告是首跑基线，不代表探测通过。定时工作流在同一次运行中部署 Pages，确保自动提交后的报告也能发布。
- 不会下载/镜像第三方配置，不执行 Spider/JS/Python/JAR；探测仍不等于客户端播放测试。失败请求明细作为保留 14 天的 artifact 上传。

工作流定义见 [`.github/workflows/catalog-check.yml`](.github/workflows/catalog-check.yml)。GitHub Actions 定时任务使用 UTC 时间 `05:23` 和 `17:23`，可能受 GitHub 调度延迟影响。

## 发布方式

分类 JSON 文件是目录的原始数据，也驱动仓库内的双语静态目录页。目录合并了上游 awesome-zhuiju-free 的条目：同一 URL 只保留一条，新条目继承上游星级并由 `scripts/import_upstream.py` 按 URL 去重后再写入，重复执行不会重复追加。页面只有一个列表板块，分类用标签页切换（单仓、多仓、直播、EPG、磁力与 BT、网盘与字幕、在线站、应用、开源项目），标签页后带各自条数；列表按「检测通过优先、再按上游星级降序、最后按名称」排序。星级以半星显示并附数字，窄屏则缩成小号星形。页面支持按名称/格式/来源搜索，并按类别筛选；它展示自动链接探测结果，但不会替用户运行源插件。GitHub Pages 发布工作流在 push 到 `main` 时部署静态页面；首次发布前，仓库管理员需在 Settings → Pages 中将 Source 设为 GitHub Actions。这里记录的 URL 指向上游，不是本仓库托管的镜像。

“尽量完整”通过持续收集和审核实现，不等于无差别搬运。只有出处、引用权限和格式可说明的条目才能进入目录；任何实际播放测试声明都必须有客户端测试证据。

## 验证记录

发布页的“验证记录”面板读取 [`reports/verification-report.json`](reports/verification-report.json)。报告区分抓取/回退集成、媒体解码和客户端实播；通过临时本机服务得到的回退结果不等于客户端兼容。状态 `passed` 仅表示报告中列出的那一步通过，`failed` 表示该样本步骤失败，`not-tested` 表示没有执行。当前记录明确标注 TVBox 客户端实播与真实 4K 均未验证。刷新报告时须保留测试快照、方法和限制说明，并同步更新中英文页面数据。

## 自建订阅

本项目会生成自己的多仓订阅入口与独立自建单仓。自建单仓优先采用当前筛查通过 list/search/detail 且详情返回直链的 CMS；若当前严格筛查为空，则回退汇总历史结构审计里可读配置的 type-1 API 候选，生成明确标注“候选未实播”的配置供用户导入试用。回退候选并不表示 API 当前可达、搜索成功或能播放。不会下载/镜像整个第三方配置，也不执行 Spider、JS、JAR、Python。

`scripts/build_subscriptions.py` 将经过目录校验的数据生成到指定输出根目录：`configs.json` 是配置索引，`subscriptions/tvbox-multi.json` 是本站多仓 JSON，`subscriptions/tvbox-custom-single.json` 是单独的自建候选 JSON。生成器先用当前严格筛查结果；若为空，则从 `reports/single-source-audit.json` 中结构可读配置提取 type-1 API 并去重回退。候选回退不表示 API 当前可达、普通搜索成功、详情有直链或客户端实播；它不含远程 Spider/脚本。报告记录有限历史测试范围，不能把未测试解释为上游全失效。多仓订阅清单仅包含 `catalog/playback-evidence.json` 中有合格实播证据的 VOD 配置；证据需记录客户端、版本、日期、测试范围及至少 30 秒成功播放。当前证据表为空，因此多仓订阅清单为空。输出不含直播、EPG、工具文档或未经审核的备用地址。Pages 发布后地址为 `https://hnnwb.github.io/tvapi_plus/configs.json`、`https://hnnwb.github.io/tvapi_plus/subscriptions/tvbox-multi.json` 和（仅非空时）`https://hnnwb.github.io/tvapi_plus/subscriptions/tvbox-custom-single.json`。不同客户端对多仓格式要求可能不同，构建测试只验证文件结构，不证明实际导入或播放。定时探测不保证播放质量或长期可用。不要将未授权、失效、重复或未验证的源标成优质。

## 点播检验方案

当前自动检查只验证配置文件格式和有限网络可访问性，不执行 Spider / JS / Python / JAR，也不会把“HTTP 200”标记为可播放。单仓候选应按以下阶段逐级检验；前一阶段失败时不要把条目标成 `playback-tested`：

1. **配置可读**：记录配置 URL、最终跳转 URL、时间、网络环境和客户端版本；完整解析 JSON，确认 `sites` 结构及站点 `type`。图片封装/加密配置只能在可信客户端或官方工具中解析，不用来历不明的在线解密站。
2. **站点可搜**：优先选明确的 `type: 1` CMS 站点。客户端内搜索一个公开、非敏感的常见节目，记录站点名、结果是否返回、响应时间和错误信息。可选的只读 API 冒烟仅检查 CMS 列表 JSON 的 `code`、`total`、`list`；它不能验证客户端搜索逻辑或播放链路。
3. **播放地址可取**：从搜索结果进入详情并选择线路，确认客户端能取到非空播放地址。记录是否卡在详情、选集或解析阶段；不要把第三方播放地址复制进公开日志。
4. **实际播放**：使用有权观看的内容，等待画面和声音连续播放至少 30 秒；记录视频/音频是否出流、清晰度切换和缓冲/错误。只有这一步成功才可标为 `playback-tested`。
5. **重复验证**：至少换一个站点或另一条内容，并在不同日期复测；区分“单站失败”和“整个配置不可用”。保留失败项和证据，不因一个成功样例推断全源质量。

| 现象 | 优先检查 | 需要记录 |
| --- | --- | --- |
| 配置导入失败 | JSON、图片封装/加密、客户端版本与格式支持 | 客户端提示、配置响应类型 |
| 搜索无结果/加载中 | 站点 CMS API、网络/DNS、站点是否可搜索 | 站点名、搜索耗时、错误文本 |
| 有结果但详情/选集卡住 | Spider/JAR/JS 兼容、站点详情 API | 失败发生在哪一步、客户端日志 |
| 点播放后一直转圈 | 返回的播放地址、解析器、TLS/UA/重定向、客户端解码器 | 是否拿到地址、错误日志、网络环境 |
| 只有个别线路失败 | 对照另一站点/线路；可能是上游资源下线或地域限制 | 失败与成功的线路类型，不公开令牌化 URL |

不要为验证而在本仓库或 CI 执行未知 Spider/脚本；自动化结构检查与真实客户端播放测试应分别记录。没有客户端日志和具体站点/线路信息时，无法单靠配置 JSON 定位“转圈”的根因。

## 法律与安全

本项目是技术目录，不构成对资源的背书。资源提供者负责其内容和服务条款。请只收录你有权公开引用的资源链接和元数据，尊重删除请求。自动化只检查元数据、语法和可访问性；外部配置和插件代码一律视为不可信，不在 CI 中执行。使用者须遵守所在地法律法规及上游服务条款。
