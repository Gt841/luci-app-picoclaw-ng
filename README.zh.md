# luci-app-picoclaw-ng

OpenWrt / iStoreOS 上的 PicoClaw 管理插件（改版）。

在浏览器里安装、启动和配置 [PicoClaw](https://github.com/sipeed/picoclaw)，不需要先 SSH 手动下载二进制、也不需要手写 JSON。

> 本仓库基于 [GennKann/luci-app-picoclaw](https://github.com/GennKann/luci-app-picoclaw) 修改。3.0.0 起生命周期页面按 OpenClash 风格重建，操作逻辑参考 [UFI-TOOLS](https://github.com/kanoqwq/UFI-TOOLS) 中的 PicoClaw 插件；模型、通道等高级配置仍由上游 Launcher 页面完成。上游插件作者与 PicoClaw 作者见文末鸣谢。

## 与上游插件的区别

| | 上游插件 | 本改版 |
|---|---|---|
| 页面形态 | 配置中心式多标签 | **状态总览 + 操作台**（OpenClash 风格） |
| 安装 PicoClaw | 需手动下载并上传 | 页面按 CPU 架构选择正确的官方资产，一键后台安装 |
| 架构适配 | — | 自动识别 `arm64/armv7/armv6/x86_64/mipsle/riscv64/loong64/s390x`，可手动覆盖 |
| 安装内容 | 只有 `picoclaw` | `picoclaw` + `picoclaw-launcher` 同时安装 |
| 版本策略 | 跟随上游 latest | 固定为插件适配的版本（当前 `0.3.1`），校验 SHA256，不自动跨版本 |
| 运行模式 | 只有 Gateway | **Gateway（默认）+ 按需临时网页面板** |
| Launcher 监听 | — | 临时打开面板时默认 `public`，端口可配；备用面板走另一个端口 |
| 数据管理 | — | 一键导出配置 / 技能 / 记忆数据，一键安装 OpenWrt 技能包 |

## 功能

- **状态总览**：运行状态灯、PID、运行模式、监听端口、内存占用、开机自启、当前版本 / 上游最新版、核心与 Launcher 路径、配置目录，一次看全。
- **生命周期操作**：安装 / 更新、启动、停止、重启、打开网页面板、备用端口面板、关闭面板、开关自启、清空运行日志。
- **架构自动选择**：优先用 `uname -m`，其次 `/etc/openwrt_release` 的 `DISTRIB_ARCH`，再退回 `/proc/cpuinfo`；映射到官方 `Linux_*` 资产。识别不出或需要覆盖时，在安装卡片的下拉框中手动选择。
- **后台安装**：procd oneshot 执行下载、校验、解压、替换，页面轮询步骤和进度，不会卡在「安装中」。安装失败会展示最近日志。
- **完整性校验**：下载后校验 SHA256，解压后在目录树中查找 `picoclaw` / `picoclaw-launcher`，执行版本自检，失败自动回滚旧二进制。
- **固定版本**：插件内写死支持的 PicoClaw 版本，避免上游配置结构变化后整个页面不可用。
- **数据导出**：一键导出配置、技能、记忆数据（可打包全部），下载到本机。
- **OpenWrt 技能包**：把内置的诊断 / 备份 / 应用安装技能装进 PicoClaw 工作区。
- **操作日志（溯源）**：开关默认关闭；开启后记录页面操作、安装/更新每一步以及服务启停，写入 `/etc/picoclaw-luci.log`，256 KB 自动轮转。

## 环境要求

- OpenWrt 21.02+ 或 iStoreOS，带 LuCI
- 可访问 GitHub（安装/更新时需要）
- 磁盘空间：PicoClaw 核心 + Launcher 解压后约 63 MB（下载包约 23 MB），请预留 100 MB 以上
- 内存：本改版不针对小内存设备做裁剪，建议 256 MB 以上

## 安装插件

```bash
# 在仓库根目录构建 IPK
python3 scripts/build-ipk.py

# 复制到路由器后安装
opkg install luci-app-picoclaw-ng_3.0.2-1_all.ipk
rm -rf /tmp/luci-*
```

OpenWrt 25.x（apk 系统）可在路由器上执行 `sh scripts/build-apk-v3.sh` 构建 APK。Release 包使用项目密钥签名，先把仓库内的公钥导入路由器一次，之后安装无需 `--allow-untrusted`：

```bash
scp keys/luci-app-picoclaw-ng.rsa.pub root@<路由器IP>:/etc/apk/keys/
scp luci-app-picoclaw-ng-3.0.2-r1.apk root@<路由器IP>:/tmp/
ssh root@<路由器IP> 'apk add /tmp/luci-app-picoclaw-ng-3.0.2-r1.apk'
```

自行构建且未提供签名私钥的包仍未签名，需要 `--allow-untrusted`，见下方签名说明。

没有 25.x 路由器时，可在装有 Docker 的机器上用 Alpine 容器构建（APK v3 必须由 apk-tools 3 的 `apk mkpkg` 生成）：

```bash
docker run --rm -v "$PWD:/work" -w /work alpine:edge sh scripts/build-apk-v3.sh
```

仓库内的 `.github/workflows/build-packages.yml` 会在 CI 中同时构建 IPK 与 APK，并分别作为 artifact 上传。CI 产物未签名；正式 Release 使用项目密钥在本地签名。

### APK 签名（可选）

Release 包使用项目密钥签名，公钥位于 `keys/luci-app-picoclaw-ng.rsa.pub`。需要自行构建签名包时：

```bash
# 1. 生成 RSA 密钥对（私钥保存在仓库外）
sh scripts/gen-apk-key.sh

# 2. 用私钥构建；同目录必须有对应的 *.rsa.pub 公钥
PC_SIGN_KEY="$HOME/.config/luci-app-picoclaw-ng/apk-keys/luci-app-picoclaw-ng.rsa" \
  sh scripts/build-apk-v3.sh

# 3. 在路由器上信任公钥（只需一次）
scp "$HOME/.config/luci-app-picoclaw-ng/apk-keys/luci-app-picoclaw-ng.rsa.pub" \
  root@<路由器IP>:/etc/apk/keys/
ssh root@<路由器IP> 'apk add /tmp/luci-app-picoclaw-ng-3.0.2-r1.apk'
```

在 Alpine 容器中构建时，把密钥目录只读挂载进去：

```bash
docker run --rm -v "$PWD:/work" \
  -v "$HOME/.config/luci-app-picoclaw-ng/apk-keys:/keys:ro" \
  -w /work -e PC_SIGN_KEY=/keys/luci-app-picoclaw-ng.rsa \
  alpine:edge sh scripts/build-apk-v3.sh
```

签名成功时构建日志会输出 `apk verify ... OK`。签名必须在 `apk mkpkg` 阶段完成：apk-tools 3.0.x 的 `apk adbsign` 处理已有 v3 包时可能把文件截断，不要用它补签名。私钥不要提交到仓库（已在 `.gitignore` 排除）；更换密钥后需要给每台路由器重新导入新公钥。

安装完成后打开：

```
http://<路由器IP>/cgi-bin/luci/admin/services/picoclaw
```

首次进入会看到「PicoClaw 未安装」提示，点击「安装核心」即可。安装器会自动执行 `picoclaw onboard` 生成默认配置和工作区；安装完成后服务按当前模式自动启动（默认 Gateway，未配置模型时以受限模式保活）。

## 源码结构与软件中心收录

包源码按 OpenWrt / iStoreOS 约定放在 `apps/picoclaw/`：

- `apps/picoclaw/luci-app-picoclaw-ng/` — 插件本体，`luasrc/` 对应 `/usr/lib/lua/luci`，`root/` 对应 `/`，可用 SDK 直接编译
- `apps/picoclaw/app-meta-picoclaw/` — iStore 软件中心元数据（图标 + 依赖），不含程序文件

`scripts/build-ipk.py` 和 `scripts/build-apk-v3.sh` 都从上述目录取文件，产物内容与目录保持一致。收录到 iStore 的提交流程与 `syncapps.yaml` 片段见 [`apps/picoclaw/README.md`](apps/picoclaw/README.md)。

## 运行模式

### Gateway（默认）

- 启动 `picoclaw gateway`
- 不开放 Web 控制台，只为消息通道（飞书、Telegram、QQ 等）提供后台服务
- 日常运行推荐保持这个模式，占用更低、攻击面更小
- 未配置默认模型时以 `--allow-empty` 受限模式运行，先开面板配置模型即可正常对话
- 配置可直接编辑 `/root/.picoclaw/config.json`，或临时开面板改完再关

### Launcher 网页面板（按需临时启动）

- 首页点击「打开网页面板」，临时启动 `picoclaw-launcher -no-browser [-public] -port <端口>`
- 面板只用于可视化配置模型、通道和技能；点击「关闭面板」或重启路由器后自动恢复 Gateway
- 默认端口 `18800`，可在状态卡片下方的「面板端口」里修改
- 打开面板时默认 `public`，局域网内可直接访问 `http://<路由器IP>:18800`；取消 public 后只监听 `127.0.0.1`
- Launcher 0.3.1 使用自身的面板密码认证（旧的 token 登录已移除）；首次进入请立即设置强密码，未设置密码时 public 面板允许同网段完成首次设置
- 「备用端口面板」用主端口 + 1000 再起一个面板，方便主端口被占用或浏览器缓存异常时进入；登录仍使用 Launcher 面板密码
- 也可以把默认模式持久设为 Launcher，但不建议长期开启

默认模式与端口写入 UCI（`/etc/config/picoclaw`）；临时面板通过 `/tmp/picoclaw-panel` 标记，重启后自动失效。运行日志在 `/var/log/picoclaw.log`，超过 2 MB 启动时轮转。

## 版本策略

- 插件只安装和更新到 `PC_SUPPORTED_VERSION` 指定的版本（当前 `0.3.1`）。
- 每次下载都校验官方 SHA256，并对解压出的二进制执行版本自检。
- 已安装版本高于插件支持版本时，页面会提示并拒绝自动更新/降级。
- 上游出现新版本时，页面只做提示，不提供一键升级，等插件适配后再更新。

## 操作日志（溯源）

在运行日志卡片的标题栏有「诊断日志」开关，默认关闭。关闭时不会创建或写入任何日志文件。

开启后以下内容会带时间戳写入 `/etc/picoclaw-luci.log`：

- 页面上的每一次操作（启动/停止/重启、模式与端口、配置保存、自动启动、技能、定时任务、MCP、模型等），包含操作参数和结果；
- 一键安装、更新的每一步（架构选择、下载大小、SHA256、解压、备份、版本自检、回滚、重启）；
- init 脚本收到的启停请求、实际执行的后端命令和发送的信号。

日志中的 API Key、请求头、环境变量、配置全文和任务消息不会落盘；URL 里的 `user:password@` 会自动打码。文件超过 256 KB 时轮转为 `.1`（只保留一份），可在页面上直接查看和清空。

## 权限说明

本改版不改变原有的权限模型：服务和 PicoClaw 配置仍以 `root` 运行，配置目录仍是 `/root/.picoclaw`。

## 鸣谢

- [PicoClaw](https://github.com/sipeed/picoclaw) — Sipeed 及所有贡献者，本项目安装的二进制与 Launcher 均来自其官方 Release。
- [luci-app-picoclaw](https://github.com/GennKann/luci-app-picoclaw) — GennKann，本改版的管理页面与大部分实现来自该仓库。
- [UFI-TOOLS](https://github.com/kanoqwq/UFI-TOOLS) — kano，本改版的生命周期操作流程与交互参考了 UFI-TOOLS 中的 PicoClaw 插件。

## 许可证

[MIT](LICENSE)。本改版保留原项目版权声明，并新增改版部分版权声明。PicoClaw 本身同样以 MIT 发布，版权归其作者所有。
