# TVBox single-source safe audit

Generated: 2026-11-21T05:05:08.472294+00:00
Source snapshot SHA-256: `9d19b1315996f5a2a7f1c5f261c4fff2e57b0b9cbaf55b1b45430e6e267a8be3`
Candidates: 48 unique URLs from 50 rows

Only credential-free HTTP(S) requests to public IPs are made; max four redirects, checked at each hop. Config cap 2 MiB, CMS cap 256 KiB, 8 s HTTP timeout, four configs concurrently, three unique CMS APIs/config. No Spider/JAR/JS/Python execution.

CMS searches use 4K, 2160p, UHD as broad filters, one result per term. Search hits are not necessarily 4K titles: for example, `我的24k氪金神眼` was returned for the 4K query but is not an explicit 4K label. Detail play URLs are extracted only; no media is fetched or decoded because the host denied sandbox-exec and unrestricted ffprobe may follow nested playlist URLs.

| Candidate | Config | CMS APIs | Search hits | Explicit 4K titles | Titles with play URLs | Detail lookups passed |
|---|---:|---:|---:|---:|---:|---:|
| 宝盒 | tvbox-json-structural | 3 | 0 | 0 | 0 | 0 |
| 小马 | tvbox-json-structural | 3 | 0 | 0 | 0 | 0 |
| 神秘大佬 | tvbox-json-structural | 3 | 0 | 0 | 0 | 0 |
| 金鹰 | tvbox-json-structural | 3 | 2 | 0 | 1 | 2 |
| 真心 | tvbox-json-structural | 3 | 1 | 0 | 1 | 1 |
| 荐片 | tvbox-json-structural | 3 | 1 | 0 | 1 | 1 |
| 二月红接口 | tvbox-json-structural | 1 | 0 | 0 | 0 | 0 |
| 1号VIP源 | tvbox-json-structural | 1 | 0 | 0 | 0 | 0 |
| 潇洒 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 潇洒Github备用 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 摸鱼儿 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 王二小 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 牛二 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 牛儿 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 软件内置源 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 嗷呜 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 饭太硬 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 俊哥 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| my interface | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| ok线路2 | tvbox-json-structural | 0 | 0 | 0 | 0 | 0 |
| 无意云 | failed | 0 | 0 | 0 | 0 | 0 |
| 饭太硬 | failed | 0 | 0 | 0 | 0 | 0 |
| 少儿频道 | failed | 0 | 0 | 0 | 0 | 0 |
| 摸鱼儿 | failed | 0 | 0 | 0 | 0 | 0 |
| 4k云盘接口 | failed | 0 | 0 | 0 | 0 | 0 |
| 欧歌接口 | failed | 0 | 0 | 0 | 0 | 0 |
| 菜妮丝 | failed | 0 | 0 | 0 | 0 | 0 |
| 肥猫 | failed | 0 | 0 | 0 | 0 | 0 |
| 欧歌免费 | failed | 0 | 0 | 0 | 0 | 0 |
| 小盒子4K | failed | 0 | 0 | 0 | 0 | 0 |
| 小盒子 | failed | 0 | 0 | 0 | 0 | 0 |
| 王二小接口 | failed | 0 | 0 | 0 | 0 | 0 |
| 饭太硬cc | failed | 0 | 0 | 0 | 0 | 0 |
| 王二小新站 | failed | 0 | 0 | 0 | 0 | 0 |
| 王二小放牛娃 | failed | 0 | 0 | 0 | 0 | 0 |
| 肥猫备用 | failed | 0 | 0 | 0 | 0 | 0 |
| 香雅情 | failed | 0 | 0 | 0 | 0 | 0 |
| 南风 | failed | 0 | 0 | 0 | 0 | 0 |
| uuccc | failed | 0 | 0 | 0 | 0 | 0 |
| fmys | failed | 0 | 0 | 0 | 0 | 0 |
| 饭太硬备用 | failed | 0 | 0 | 0 | 0 | 0 |
| 新接口 | failed | 0 | 0 | 0 | 0 | 0 |
| ok线路1 | failed | 0 | 0 | 0 | 0 | 0 |
| 11号托管源 | failed | 0 | 0 | 0 | 0 | 0 |
| sss公用源 | failed | 0 | 0 | 0 | 0 | 0 |
| 拾光 | failed | 0 | 0 | 0 | 0 | 0 |
| 小苹果线路 | failed | 0 | 0 | 0 | 0 | 0 |
| 66号GitCode源 | failed | 0 | 0 | 0 | 0 | 0 |

## 4K evidence

Title labels and CMS responses are not media measurements. No media is fetched or decoded, so no result confirms resolution, bitrate, Mac playback, sustained quality, or rights. Spider/JAR/JS/Python rules remain untested.

Totals: 20 parsed configs; 20 CMS APIs sampled; 4 broad search results; 0 explicit 4K/UHD/2160p titles; 3 titles with play URLs; 0 explicit-label titles with URLs; 4 detail responses passed; 0 streams verified as 4K.
