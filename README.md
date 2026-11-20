# TVBox 资源目录

**简体中文** | [English](README.en.md)

一个面向 TVBox 生态的资源目录与格式检查项目，涵盖 Yingxia（映霞）、影视仓及其他兼容客户端。仓库记录资源链接和来源信息，不镜像第三方配置内容，也不运行源插件。

## 项目范围

- 使用一个主目录，按资源类型分类，不按客户端拆分 Git 分支。
- 分别记录客户端兼容声明、链接可访问性和实际播放测试结果，避免把它们混为一谈。
- 自动检查条目元数据；可选执行有限的 HTTP 探测与基础格式检查。
- 不自动解密、改写、代理或重新发布第三方配置，不在 CI 中执行 JS、Python 或 JAR 插件。

目前各资源目录为空，等待审核后录入。请勿将 Awesome TVBox 等目录中的所有链接直接复制进来。只添加你有权公开引用的链接；公开可访问不等于获得版权授权，也不代表资源安全、兼容或可播放。不要提交凭据、私人链接、令牌或账号信息。

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
  catalog.schema.json  # 条目结构参考
scripts/
  check_catalog.py     # 元数据检查，可选 URL 探测
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
```

默认只做离线元数据检查。`--check-urls` 会联系目录中的第三方主机，使用有超时和响应体大小限制的 GET 请求；只接受 HTTP(S) 跳转，不执行响应内容。它会对 TVBox JSON、多仓 `urls`、M3U/TXT、直播 JSON 和 EPG XML 做基本结构检查。网络探测失败只记录在报告中，不会自动删除或改写目录条目。不同地区、网络、User-Agent 和上游策略可能导致结果不同。

## GitHub Actions

- push 和 Pull Request 对目录、Schema、脚本或工作流文件的变更触发离线元数据检查。
- 每日定时任务及手动选择 URL 检查的工作流会运行有限 URL/格式探测，并把 `probe-report.json` 作为保留 14 天的 artifact 上传。
- 工作流不会自动提交、删除或改写目录数据。

工作流定义见 [`.github/workflows/catalog-check.yml`](.github/workflows/catalog-check.yml)。GitHub Actions 定时任务使用 UTC 时间 `05:23`，可能受 GitHub 调度延迟影响。

## 发布方式

分类 JSON 文件是目录的原始数据，可通过 GitHub Raw 地址读取。仓库目前没有生成网页、Pages 发布工作流或客户端专用筛选输出；如需 Pages 导航页或按 Yingxia/影视仓生成视图，应在后续单独实现。这里记录的 URL 指向上游，不是本仓库托管的镜像。

## 法律与安全

本项目是技术目录，不构成对资源的背书。资源提供者负责其内容和服务条款。请只收录你有权公开引用的资源链接和元数据，尊重删除请求。自动化只检查元数据、语法和可访问性；外部配置和插件代码一律视为不可信，不在 CI 中执行。使用者须遵守所在地法律法规及上游服务条款。
