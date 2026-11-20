# Changelog

All notable changes to `luci-app-picoclaw-ng` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **iStore 元数据包** — 新增 `apps/picoclaw/app-meta-picoclaw/`，包含软件中心图标与依赖，仅用于商店展示
- **收录说明** — 新增 `apps/picoclaw/README.md`，记录聚合仓提交流程、`syncapps.yaml` 片段与三处版本同步要求

### Changed
- **源码目录改为 OpenWrt 标准布局** — 插件移动到 `apps/picoclaw/luci-app-picoclaw-ng/`（`luasrc/` 对应 `/usr/lib/lua/luci`，`root/` 对应 `/`），并提供 `luci.mk` 版 Makefile，可直接在 SDK/buildroot 编译
- `scripts/build-ipk.py` 与 `scripts/build-apk-v3.sh` 改为从新目录取文件；重建后的包内容与 3.0.2 逐文件一致

---

## [3.0.2] - 2026-11-20

### Added
- **APK 正式签名** — 3.0.2 的 APK 使用项目 RSA 4096 密钥签名，公钥随仓库发布在 `keys/luci-app-picoclaw-ng.rsa.pub`；路由器导入公钥后可直接 `apk add`，无需 `--allow-untrusted`
- **鸣谢 UFI-TOOLS** — README 增加 kano 与 [UFI-TOOLS](https://github.com/kanoqwq/UFI-TOOLS) 的署名，注明生命周期操作流程参考来源

### Changed
- 版本号更新为 3.0.2（IPK `3.0.2-1`，APK `3.0.2-r1`）

---

## [3.0.1] - 2026-11-20

### Added
- **APK 签名支持** — 设置 `PC_SIGN_KEY` 后由 `apk mkpkg --sign-key` 在打包阶段签名，构建结束自动执行 `apk verify`；新增 `scripts/gen-apk-key.sh` 生成 RSA 密钥对，私钥默认保存在仓库外并被 `.gitignore` 排除
- 文档补充签名构建、在路由器 `/etc/apk/keys` 安装公钥以及容器内挂载密钥的方式

### Changed
- **移除「默认运行设置」卡片** — 默认模式固定为 Gateway，不再提供模式切换
- **面板端口与 public 收进状态卡下方的小行** — 保存后重启服务并关闭临时面板
- **上游二进制资产选择移到安装进度卡片** — 只影响本次安装/更新，识别失败时仍可手动指定
- **诊断日志开关移到运行日志卡片标题栏** — 默认关闭，切换后立即生效
- 包版本更新为 3.0.1

### Notes
- apk-tools 3.0.x 的 `apk adbsign` 会给已有 v3 包补签名时截断文件，签名统一在 `mkpkg` 阶段完成

---

## [3.0.0] - 2026-11-20

### Changed — 模块重建
- **控制层与页面按生命周期重写** — 不再沿用原先的配置中心式页面，改为 OpenClash 风格的「状态总览 + 操作台」：启动状态、PID、模式、监听端口、内存占用、开机自启、当前/上游版本、核心与面板路径、数据/日志目录集中展示
- **生命周期操作对齐 UFI 插件逻辑** — 安装/更新、启动、停止、重启、打开网页面板、备用端口面板、关闭面板、开关自启、一键安装 OpenWrt 技能包、清空日志、导出配置/技能/数据（config/skills/memory/all）
- **上游资产按 CPU 架构选择** — 根据 `uname -m`、`/etc/openwrt_release` 的 `DISTRIB_ARCH` 与 `/proc/cpuinfo` 自动映射到 0.3.1 的 `Linux_arm64 / armv7 / armv6 / x86_64 / mipsle / riscv64 / loong64 / s390x`；识别不出或想覆盖时可在页面下拉手动指定
- **安装器兼容归档目录层级** — 解压后在整棵目录树中查找 `picoclaw` / `picoclaw-launcher`，避免不同打包层级导致「找不到二进制」
- **首次安装自动初始化配置** — 安装器在缺少 `/root/.picoclaw/config.json` 时执行 `picoclaw onboard`；init 启动 Gateway 前也会补做一次，避免「装完就退出」
- **Gateway 以受限模式保活** — 尚未配置默认模型时使用 `picoclaw gateway --allow-empty` 启动，进程不会立即退出，用户可先开面板配置模型
- **高级配置仍交给 Launcher** — 页面只做生命周期与少量运行参数（模式、端口、public、资产、调试日志）；模型/渠道等配置在临时面板里完成，用完即可关闭，重启后回到 Gateway
- 包版本更新为 3.0.0

### Removed
- Launcher 面板不再伪造随机 token：0.3.1 已移除 token 登录；备用面板改为另一个端口，页面提示首次进入立即设置面板密码
- 页面内置的本地压缩包上传入口（安装统一走按架构自动下载，失败时看安装日志与手动资产选择）

---

## [2.0.1] - 2026-11-20

### Fixed
- **本地上传安装崩溃** — LuCI 的 ucode runtime 把上传文件表示为 table 而不是临时路径，旧代码直接调用 `path:match()` 报 `attempt to call method 'match' (a nil value)`；现在统一由 `materialize_upload()` 落盘为 `/tmp` 文件后再处理，兼容传统 Lua runtime 与 ucode runtime
- **一键安装/更新卡在「安装中...」** — 下载改由 procd oneshot（`/etc/init.d/picoclaw-installer` + `/usr/lib/picoclaw-install.sh`）在后台执行，不再占用 uhttpd CGI 请求，避免超时后页面无反馈
- **安装进度可见** — 安装器每一步写入 `/tmp/picoclaw-install.status` 与 `/tmp/picoclaw-install.log`；页面显示当前步骤、自动刷新，并在失败时展开最近 60 行日志，便于定位下载/校验/替换失败原因

### Changed
- 一键安装和「立即更新」共用同一套后台安装器；进行中会禁用重复触发按钮
- **默认运行模式改为 Gateway** — 开机只跑 `picoclaw gateway` 消息网关；init 脚本缺省值、UCI 默认配置、页面单选项同步调整
- **网页面板改为按需临时启动** — 首页状态卡片提供「打开网页面板 / 返回 Gateway 模式」，通过 `/tmp/picoclaw-panel` 标记切换为 `picoclaw-launcher`，重启路由器后自动回到 Gateway
- **首页改为 OpenClash 风格状态总览** — 顶部状态灯 + 启停/重启主按钮，信息栅格展示运行模式、开机自启、核心路径、面板程序、配置目录、监听端口、当前/支持/上游版本
- **安装进度条** — 下载阶段按远端 Content-Length 计算真实百分比，替换原先的不确定进度动画
- 包版本更新为 2.0.1

### Notes
- 权限模型未调整：服务与配置仍在 `root` / `/root/.picoclaw`

---

## [2.0.0] - 2026-11-20

分叉自 [GennKann/luci-app-picoclaw](https://github.com/GennKann/luci-app-picoclaw) v1.2.0，包名改为 `luci-app-picoclaw-ng`。

### Added
- **Launcher / Gateway 双运行模式** — 默认 Launcher；模式、Launcher 端口、是否 public 可在页面配置，保存在 UCI `/etc/config/picoclaw`
- **自动安装 Launcher** — 一键安装同时部署 `picoclaw` 与 `picoclaw-launcher`
- **架构自动识别** — 结合 `uname -m` 与 `DISTRIB_ARCH`，覆盖 x86_64、arm64、armv6、armv7、mipsle、riscv64、loong64、s390x；不支持架构给出明确原因
- **安装包完整性校验** — 内置 0.3.1 各架构 SHA256，下载后校验；解压后执行 `picoclaw version` 自检，失败回滚并清理
- **固定上游版本** — 安装/更新目标锁定 `PC_SUPPORTED_VERSION`；页面显示插件支持版本与上游最新版本，上游领先时提示「尚未适配」
- **可开关的操作日志（溯源）** — UCI `debug_log` 默认 `0`；开启后页面每个操作、安装/更新/上传的每一步、init 启停信号都带时间戳写入 `/etc/picoclaw-luci.log`，超过 256 KB 轮转为 `.1`；日志中不记录 API Key、请求头、环境变量、配置全文和任务消息，URL 凭据自动打码；页面可直接查看和清空
- **IPK + APK 双格式** — `scripts/build-ipk.py` 产出 opkg 用的 IPK；`scripts/build-apk-v3.sh` 在 OpenWrt 25.x（apk-tools 3）上用官方 `apk mkpkg` 产出 v3 APK，两份产物内容一致；新增 `.github/workflows/build-packages.yml`，CI 在 Alpine 容器中同时构建两种格式
- 页面新增「运行模式」卡片，显示 Launcher 访问地址；状态卡按模式显示 Launcher / Gateway 端口

### Changed
- 更新行为由「跟随 latest」改为「只更新到插件支持版本」；已安装更高版本时拒绝降级
- Launcher 默认 `-public` 监听所有网卡，端口默认 18800，可在界面修改
- init 脚本按 UCI 模式启动 Launcher 或 Gateway，停止时同时结束两个进程
- 本地上传安装也会顺带替换包内存在的 `picoclaw-launcher`
- IPK/APK 构建脚本包名更新为 `luci-app-picoclaw-ng`，版本 2.0.0
- README 重写，补充模式说明、版本策略、权限说明与上游鸣谢

### Notes
- 权限模型未调整：服务与配置仍在 `root` / `/root/.picoclaw`
- 不针对小内存、小磁盘设备做裁剪

---

## [1.2.0] - 2026-11-15

### Added
- **定时任务页** — 列出 / 新建 / 启用 / 禁用 / 删除 `workspace/cron/jobs.json` 里的任务，支持固定间隔与 cron 表达式，可指定投递通道与收件人
- **MCP 服务页** — 增删 MCP 服务器，stdio 支持启动参数与环境变量，http / sse 支持请求头，可标记延迟加载
- **技能页** — 技能卡片（名称 / 版本 / 描述）、内置技能标记、从注册表安装、粘贴导入、删除；原硬件页的技能入口迁移至此
- **模型与认证页** — `model_list` 列表、切换默认模型、启用停用、新增模型、API Key 配置状态（只显示有无与条数）、`picoclaw auth status` 只读展示
- **推理强度设置** — 模型条目支持 `thinking_level`（low / medium / high / max / adaptive），每行一个下拉，写入后自动重启
- **APK (v3/ADB) 构建脚本** `scripts/build-apk-v3.sh` — 在 OpenWrt 25.x 路由器上直接用系统 `apk mkpkg` 产出 v3 包，内置隐私扫描与 CRLF 检查；旧的 `build-apk-25xx.sh`（v2 格式，25.x 装不上）已标注废弃
- 标签栏支持换行，面板切换增加淡入位移动画

### Fixed
- **CLI 读错配置目录** — LuCI 进程 CWD 为 `/www` 且未设置 `HOME`，直接调用 `picoclaw` 会让 CLI 在错误位置读写配置，导致新建定时任务 / 改模型全部无效；现在所有调用统一前缀 `HOME=/root /usr/bin/picoclaw`
- **硬件页定时任务列表恒为空** — 同上原因，`picoclaw cron list` 读到了不存在的配置目录
- **配置编辑表单会写坏配置** — `steering_mode` / `media_cleanup.enabled` 少了 `agents.defaults.` / `tools.` 前缀，`listen`、`providers.*` 在 0.3.1 里已不存在；表单保存会往顶层写未知字段，严格校验下 PicoClaw 直接拒绝加载
- **保存配置加校验与回滚** — 写盘前备份，写后跑 `picoclaw model` 试解析，遇到 unknown field 自动回滚并提示具体字段
- **模型指南与示例适配 0.3.1** — provider 列改为真实取值（zhipu / moonshot / openrouter…），新增 23 项 provider 矩阵，示例改成 0.3.1 实际字段，补上「max_tokens 只能写在 agents.defaults」警告，删掉已移除的 `picoclaw config security`
- **模型清单更新到 2026-11** — DeepSeek V4.1 Flash / Claude Fable 5.2 / Sonnet 5.5 / GPT-5.5 / Gemini 4 Carbon / GLM-5.3 / Kimi K3 / Qwen3.8 Max 等 16 条，上下文按厂商口径显示；默认模型改为按当前配置动态高亮
- **内置预设技能目录是空的** — 三个 `openwrt-*` 目录只建了目录没装 `SKILL.md`，点「预设技能」或安装都没反应
- **预设技能 frontmatter 缺开头的 `---`** — 即使装上也没有 name/description，PicoClaw 无法识别
- **删除技能不消失** — 原实现只 `rmtree` 目录，不走 CLI，`skills store` 里的记录残留；现在先 `picoclaw skills remove`，再兜底删目录，并自动清理指向已消失目录的 store 条目
- 删除确认弹窗删的是列表最后一项（按钮 selectors 取错了目标），已按卡片定位
- BusyBox 下 `cp -r src/. dst/` 不生效，改成 `cp -r src skills_dir/`
- `gateway_port` 指标缺少中英文文案

### Changed
- 硬件页的「已安装技能」「定时任务」卡片改为一行入口，指向新的独立标签页
- 定时任务与配置类修改保存后重启服务（网关不监听 jobs.json / config 变化，实测进程内不重载）
- 配置编辑的 providers 区块改为指向「模型与认证」的提示（0.3.1 用 model_list 管模型）
- 技能页拆成「已安装」与「可安装的内置技能」两组，内置技能卡片新增单个「安装」按钮（`install_preset_one`）
- README 五种语言补充 APK 安装方式（`apk add --allow-untrusted`）并把 IPK 版本号更新到 1.2.0

### Packaging
- IPK：`luci-app-picoclaw_1.2.0-1_all.ipk`（tar.gz 三层嵌套，非 AR 格式）
- APK：`luci-app-picoclaw-1.2.0-r1.apk`（v3/ADB 格式，未签名，需 `--allow-untrusted`）
- 两者均包含 3 个内置技能的 `SKILL.md`（此前 IPK 里只有空目录）
- 打包脚本内置隐私扫描：命中 `sk-` 密钥、硬编码凭据或本机路径即中止，不写盘

## [1.1.6] - 2026-04-28

### Added
- **PicoClaw v0.2.7 兼容** — 适配 `channel_list` + `settings` 新配置格式（旧版 `channels` 自动兼容）
- **新增通道支持** — IRC、Matrix、OneBot、Pico、Pico Client、VK（i18n 5语言翻译）
- **微信绑定增强** — 新增"已授权但未启用"中间状态检测（通过 security.yml 判断）

### Fixed
- **通道列表空白** — v0.2.7 配置格式破坏性变更：`channels` → `channel_list`，子字段移入 `settings`，LuCI 模板未适配导致页面空白
- **通道开关写入错误路径** — `buildChannelsForm()` 中 toggle 的 `data-path` 硬编码 `channels.xxx.enabled`，v0.2.7 下应写 `channel_list.xxx.enabled`
- **服务启动绕过 procd** — 上传安装/在线更新后用 `os.execute("picoclaw gateway &")` 直接启动，改为 `/etc/init.d/picoclaw start`（procd 管理）
- **BusyBox pkill 不存在** — `pkill -f` 替换为 `killall`（OpenWrt BusyBox 无 pkill）
- **i18n 残留** — 删除废弃的 `wechat_work` / `tl_wechat_work` 翻译

### Changed
- PicoClaw 推荐版本更新至 v0.2.7
- README 5语言版本号徽章和下载链接更新至 v1.1.6

---

## [1.1.5] - 2026-04-24

### Fixed
- **Shell 注入修复** — 上传安装路径 `upload_path` 添加白名单校验 (`is_safe_tmp_path`) 和 `shell_quote` 转义，防止路径遍历注入
- **find 结果注入修复** — `do_upload_install` 和 `do_update` 中 `find` 返回路径添加前缀校验，防止恶意文件名注入
- **rm -rf 替换** — 技能删除改用 Lua 原生 `rmtree()` 递归删除，避免 shell `rm -rf` 静默风险
- **ANSI 剥离修复** — 聊天回复去 ANSI 码改用纯 Lua `gsub`，消除 `echo | sed` shell 注入风险
- **XSS 修复** — 技能删除确认框 `confirm()` 中的 `sk.name` 改用 `data-confirm` 属性，防止单引号注入

---

## [1.1.3] - 2026-04-10

### Added
- **搜索引擎配置区域** — 在配置编辑标签页中可直接配置搜索引擎（GLM Search、百度搜索、DuckDuckGo、Brave、Tavily、Perplexity、SearXNG）
- **GFW 提示** — 为国内用户标注哪些搜索引擎被 GFW 屏蔽
- **5语言 i18n 翻译** — 搜索引擎相关标签的完整多语言支持（中文、英文、日文、葡萄牙文、德文）

### Changed
- README 5语言版本新增「模型配置方法」和「搜索引擎配置」章节
- 版本号徽章更新至 v1.1.3
- IPK 下载链接更新至 v1.1.3

---

## [1.1.2] - 2026-04-10

### Fixed
- **IPK 打包格式规范化** — control 文件严格对齐 istore-repo 参考格式
- **control.tar.gz** 添加 `.` 目录条目、postinst（OpenWrt 标准 160 bytes）、prerm（117 bytes）
- **data.tar.gz** 添加 `.` 目录条目和中间目录（./usr/, ./usr/lib/ 等）
- **Description 双空格** — 冒号后双空格（OpenWrt 规范）
- **Installed-Size** — 改为 data.tar.gz 实际字节数（非硬编码）
- **Source/Depends 字段** — Source 改为 `feeds/packages/luci/applications/luci-app-picoclaw`，Depends 添加 `libc`

### Added
- 新打包脚本 `build_v112_targz.py`，含完整验证（MD5 对比、格式校验）

---

## [1.1.0] - 2026-04-10

### Fixed
- **标签切换 Bug** — i18n 字典键名含 `-`（如 `mg_prov_glm-4.5-air`）导致 JS 语法错误，所有标签无法切换。修复：给含特殊字符的键名加引号
- **默认模型选择器** — 页面加载后默认模型不匹配配置文件值。修复：批量添加行时抑制 refreshDefaultModelSelect 调用
- **SecureString 字符数组** — `glm-4.5-air` 的 api_keys 是字符数组 `["[","N","O","T","_","H","E","R","E","]"]`，原代码只取 `key[0]`。修复：检测并 join 拼接

### Changed
- i18n 键名引号包裹（5语言版本）
- 模型列表渲染逻辑优化

---

## [1.0.9] - 2026-04-07

### Fixed
- **Gateway 端口显示异常** — 端口检测不再硬编码 4966/4967（18790/18791 十六进制），改为从 `config.json` 动态读取 `gateway.port`，支持任意端口配置。状态栏现在显示实际端口号
- **模型配置表单优化** — Provider 保留下拉选择（新增 Qwen / 通义百炼选项）；Model 名称从固定下拉改为手动输入框，支持任意自定义模型（如 qwen3.5-27b）；新增 API Key 密码输入字段；模型上下文提示自动匹配已知模型，未知模型显示通用建议
- **微信状态判断逻辑修复** — 修正检查路径为 `config.channels.weixin`（原错误地检查顶层 `config.weixin`）；`enabled=true` 时直接显示"已连接"状态；兼容顶层 config.weixin 向后兼容；「前往启用」按钮跳转修正为正确 Tab 索引 + 自动滚动到通道管理区域

---

## [1.0.8] - 2026-04-06

### Added
- 五语言完整 README 文档（English, 中文, 日本語, Deutsch, Português）
- iStore 商店安装状态说明（已合入官方源）
- FAQ 章节（常见问题解答）：停止按钮无效、CSRF token 错误、postinst 报错等已知问题及解决方案
- 新功能特性：kill-9 三步停止策略、CSRF 安全修复、微信个人号接入状态检测

### Changed
- README 版本号更新至 v1.0.8，PicoClaw 版本标注 v0.2.5
- Tech Stack 和项目结构章节完善

### Fixed
- IPK 打包数据截断问题（v1.0.5 遗留，v1.0.6 已修复基础上的二次验证）
- init.d 脚本停止策略升级：优雅停止 → pidof 检查 → kill-9 强杀 → 等待清理

---

## [1.0.7] - 2026-04-05

### Fixed
- **IPK 安装 Malformed 错误** — 修复打包脚本数据截断问题，所有文件大小与源文件完全一致
- **main.htm 安装后缺失** — 确保 HTML 模板正确打包进 IPK
- **API Key 读取失败** — 修复 PicoClaw 0.2.5 版本 `.security.yml` 路径和格式的兼容性
- **LuCI 页面服务异常** — 修复控制器 JSON 解析错误导致的页面渲染失败

### Added
- 完整的安装验证流程（打包前自动检查文件大小）
- GitHub Issue #1 用户反馈回复和处理记录

---

## [1.0.6] - 2026-04-05

### Fixed
- **IPK 格式问题**（重大修复）— 确认 opkg/iStoreOS 接受 tar.gz 格式（非 AR 格式）
- **IPK 数据截断** — picoclaw.lua 少 ~4.8KB，main.htm 少 ~623B；根因为打包脚本写入不完整
- 新打包脚本 `build_v106_targz.py` 带完整性校验，每个文件打包前后大小比对
- 路由器实测安装成功，opkg 不再报 Malformed

### Changed
- 打包脚本重构，增加数据完整性验证步骤
- 所有源文件（controller/view/init.d）大小验证通过后才生成 IPK

---

## [1.0.5] - 2026-04-05

### Added
- 初始 IPK 打包支持（含 init.d 服务管理脚本）
- LuCI 更新按钮：通过 GitHub API 动态查询 Release 资产列表，自动匹配 CPU 架构
- istore 目录结构初始化（用于后续提交 PR）

### Known Issues
- ⚠️ IPK 存在数据截断 BUG（此版本已废弃，请使用 v1.0.6+）

---

## [1.0.4] - 2026-04-04

### Added
- 飞书（Feishu/Lark）channel 配置支持
- WebSocket 长连接模式（无需公网 webhook）
- App ID / App Secret 直接在 config.json 中配置

### Changed
- 配置编辑器适配 PicoClaw 0.2.5 版本的新配置结构

---

## [1.0.3] - 2026-04-03

### Added
- 模型自定义配置功能：支持在 config.json 的 model_list 中添加自定义模型
- .security.yml 双文件配置体系支持
- openrouter-auto 虚拟模型内置支持

### Fixed
- 配置保存时 JSON 格式校验增强

---

## [1.0.2] - 2026-04-02

### Added
- 🎉 **初始正式发布**
- LuCI 控制器 (`picoclaw.lua`)：服务管理、配置读写、日志查看、状态检测
- LuCI 模板 (`main.htm`)：
  - 仪表盘：实时服务状态、PID、内存、端口监听
  - 配置编辑：表单化 AI 模型/供应商设置 + JSON 直接编辑
  - 通道管理：飞书、Telegram、Discord、微信等通道状态
  - 硬件控制：系统信息、USB 设备、GPIO 引脚操作
  - 技能管理：查看/删除/导入 PicoClaw 技能
  - 定时任务：Cron 任务一览
- Init.d 服务脚本 (`picoclaw.init`)：开机自启、procd 管理
- 3 个内置预设技能：
  - 系统诊断（网络/DNS/网关检测、日志分析）
  - 配置备份（交互式备份流程）
  - 智能安装（opkg/is-opkg 模糊搜索）
- 多语言界面框架（i18n）
- CSRF token 安全保护

---

## [Unreleased]

### Planned
- 更多 AI 提供商预设模板（Groq、Mistral、Cohere 等）
- 主题切换（暗色模式）
- 配置导入/导出功能
- 多用户会话管理
- 实时日志流（WebSocket）

---

[1.1.6]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.1.6
[1.1.5]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.1.5
[1.1.3]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.1.3
[1.1.2]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.1.2
[1.1.0]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.1.0
[1.0.9]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.9
[1.0.8]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.8
[1.0.7]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.7
[1.0.6]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.6
[1.0.5]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.5
[1.0.4]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.4
[1.0.3]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.3
[1.0.2]: https://github.com/GennKann/luci-app-picoclaw/releases/tag/v1.0.2
