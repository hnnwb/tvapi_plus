# TVBox 资源目录

**简体中文** | [English](README.en.md)

一个面向 TVBox 生态的资源目录与格式检查项目，涵盖 Yingxia（映霞）、影视仓及其他兼容客户端。仓库记录资源链接和来源信息，不镜像第三方配置内容，也不运行源插件。

## 项目范围

- 使用一个主目录，按资源类型分类，不按客户端拆分 Git 分支。
- 分别记录客户端兼容声明、链接可访问性和实际播放测试结果，避免把它们混为一谈。
- 自动检查条目元数据；可选执行有限的 HTTP 探测与基础格式检查。
- 不自动解密、改写、代理或重新发布第三方配置，不在 CI 中执行 JS、Python 或 JAR 插件。

目录已收录少量经来源记录、可访问性或结构检查的直播列表、VOD 配置索引、EPG 与工具参考；这不代表已完成全面审核。请勿将 Awesome TVBox 等目录中的所有链接直接复制进来。只添加你有权公开引用的链接；公开可访问不等于获得版权授权，也不代表资源安全、兼容或可播放。格式错误、来源不明或权利无法说明的配置（例如当前无效的 XYQ JSON）不会作为可用接口收录。不要提交凭据、私人链接、令牌或账号信息。

## 目录结构

```text
catalog/
  clients.json       # 客户端能力参考表
  vod-single.json    # 单仓配置链接
  vod-multi.json     # 多仓（urls）配置链接
  live.json          # M3U/TXT/JSON 直播列表
  epg.json           # EPG 与台标资源
  tools.json         # 开发文档与工具
schemas/
  catalog.schema.json       # 目录条目结构参考
  probe-report.schema.json   # 探测报告结构
scripts/
  check_catalog.py           # 元数据检查，可选 URL 探测
  refresh_status.py          # 定时重试/备用地址探测
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
  "clients": {
    "yingxia": { "status": "format-claimed", "tested_version": null, "tested_at": null },
    "yingshicang": { "status": "format-claimed", "tested_version": null, "tested_at": null }
  }
}
```

客户端状态可填：`unknown`、`format-claimed`、`import-tested`、`playback-tested`、`incompatible`。只有真实测试后才使用 `import-tested` 或 `playback-tested`，并填写客户端版本和 `YYYY-MM-DD` 日期。`format-claimed` 仅表示格式或上游说明声称兼容，不代表 Yingxia 或影视仓实际验证通过。影视仓不同版本、运行环境和源类型可能表现不同。

各分类允许格式：

| 文件 | `format` 值 |
| --- | --- |
| `vod-single.json` | `tvbox-json` |
| `vod-multi.json` | `tvbox-multi` |
| `live.json` | `m3u`、`txt`、`tvbox-live-json` |
| `epg.json` | `epg-xml`、`logo-library` |
| `tools.json` | `documentation`、`utility` |

客户端参考定义见 [`catalog/clients.json`](catalog/clients.json)，条目结构参考见 [`schemas/catalog.schema.json`](schemas/catalog.schema.json)。当前检查脚本直接执行自己的字段检查逻辑；JSON Schema 文件作为结构文档，尚未由脚本加载验证。

## 本地检查

需要 Python 3.10 或更高版本，不需要第三方 Python 包：

```sh
python3 scripts/check_catalog.py
python3 scripts/check_catalog.py --check-urls --report probe-report.json
python3 scripts/refresh_status.py --report /tmp/probe-report.json --retries 0 --delay 0
```

默认只做离线元数据检查。`--check-urls` 仅联系解析到公网地址的第三方主机，使用有超时和响应体大小限制的 GET 请求；跳转目标也必须是公网 HTTP(S)，不执行响应内容。它会对 TVBox JSON、多仓 `urls`、M3U/TXT、直播 JSON 和 EPG XML 做基本结构检查。网络探测失败只记录在报告中，不会自动删除或改写目录条目。不同地区、网络、User-Agent 和上游策略可能导致结果不同。

## GitHub Actions

- push 和 Pull Request 对目录、Schema、脚本或工作流文件的变更触发离线元数据检查。
- 每日两次定时任务及手动选择 URL 检查的工作流会运行有限 URL/格式探测，带短重试；可选 `fallback_urls` 必须先审核且不会自动发现或写入。
- 探测会原子更新 `probe-report.json` 并提交状态文件，保留上次成功时间；当前失败会标记为 failed/stale，不删除目录条目，也不覆盖配置数据。仓库中的空状态报告是首跑基线，不代表探测通过。定时工作流在同一次运行中部署 Pages，确保自动提交后的报告也能发布。
- 不会下载/镜像第三方配置，不执行 Spider/JS/Python/JAR；探测仍不等于客户端播放测试。失败请求明细作为保留 14 天的 artifact 上传。

工作流定义见 [`.github/workflows/catalog-check.yml`](.github/workflows/catalog-check.yml)。GitHub Actions 定时任务使用 UTC 时间 `05:23` 和 `17:23`，可能受 GitHub 调度延迟影响。

## 发布方式

分类 JSON 文件是目录的原始数据，也驱动仓库内的双语静态目录页。页面支持按名称/格式/来源搜索，并按类别和客户端测试状态筛选；它展示探测与实测状态，但不会替用户运行源插件。GitHub Pages 发布工作流在 push 到 `main` 时部署静态页面；首次发布前，仓库管理员需在 Settings → Pages 中将 Source 设为 GitHub Actions。这里记录的 URL 指向上游，不是本仓库托管的镜像。

“尽量完整”通过持续收集和审核实现，不等于无差别搬运。只有出处、引用权限和格式可说明的条目才能进入目录；播放测试状态必须有版本及日期。定时网络探测只是有限时点的可访问性结果，不保证频道播放质量或长期可用。不要为了填满列表而把未授权、失效、重复或未经验证的源标成优质。

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
