# luci-app-picoclaw-ng

A reworked LuCI app for [PicoClaw](https://github.com/sipeed/picoclaw) on OpenWrt / iStoreOS.

Install, start and configure PicoClaw from the browser — no SSH, no manual binary download, no hand-edited JSON.

> Based on [GennKann/luci-app-picoclaw](https://github.com/GennKann/luci-app-picoclaw). Since 3.0.0 the lifecycle page is rebuilt in an OpenClash-like style, with operation flow modelled on the PicoClaw plugin in [UFI-TOOLS](https://github.com/kanoqwq/UFI-TOOLS); model/channel configuration still happens in the upstream Launcher. Credits are at the end of this file.

## What changed

| | Upstream plugin | This fork |
|---|---|---|
| UI | Tabbed config centre | **Status dashboard + control desk** (OpenClash style) |
| Installing PicoClaw | Manual download + upload | Picks the right official asset for the CPU, installs in the background |
| Architecture | — | Auto-detects `arm64/armv7/armv6/x86_64/mipsle/riscv64/loong64/s390x`, manual override available |
| What gets installed | `picoclaw` only | `picoclaw` + `picoclaw-launcher` |
| Version policy | Follows upstream `latest` | Pinned to the version supported by the plugin (currently `0.3.1`), SHA256 verified |
| Run modes | Gateway only | **Gateway (default) + on-demand web panel** |
| Launcher binding | — | `public` by default when opened; port configurable; backup panel on an alternate port |
| Data | — | Export config / skills / memory, install the bundled OpenWrt skill pack |

## Features

- **Status dashboard**: state light, PID, run mode, listen port, memory use, autostart, installed vs upstream version, core and launcher paths, config dir.
- **Lifecycle controls**: install / update, start, stop, restart, open web panel, backup panel, close panel, toggle autostart, clear runtime log.
- **Architecture-aware install**: `uname -m` first, then `DISTRIB_ARCH` from `/etc/openwrt_release`, then `/proc/cpuinfo`; maps to official `Linux_*` assets, with a manual dropdown in the install card as fallback.
- **Background installer**: a procd oneshot performs download, verification, extraction and replacement; the page polls step and progress, so it never gets stuck.
- **Integrity checks**: SHA256 verification, binaries located anywhere in the extracted tree, version self-check, automatic rollback on failure.
- **Pinned upstream version**: a future upstream release cannot silently break the plugin.
- **Data export**: download config, skills, memory or everything as a tarball.
- **OpenWrt skill pack**: installs bundled diagnostics / backup / app-installer skills into the PicoClaw workspace.
- **Operation log (audit trail)**: off by default. When enabled, page actions, install/update steps and service start/stop are written to `/etc/picoclaw-luci.log` with 256 KB rotation.

## Requirements

- OpenWrt 21.02+ or iStoreOS with LuCI
- Access to GitHub (during install/update)
- Disk: about 63 MB extracted for PicoClaw + Launcher (23 MB download); reserve 100 MB or more
- Memory: this fork does not target very small devices; 256 MB+ recommended

## Install the plugin

```bash
# Build the IPK from the repository root
python3 scripts/build-ipk.py

# Copy to the router and install
opkg install luci-app-picoclaw-ng_3.0.2-1_all.ipk
rm -rf /tmp/luci-*
```

On OpenWrt 25.x (apk-based), run `sh scripts/build-apk-v3.sh` on the router. Release packages are signed with the project key; import the bundled public key once, then install without `--allow-untrusted`:

```bash
scp keys/luci-app-picoclaw-ng.rsa.pub root@<router-ip>:/etc/apk/keys/
scp luci-app-picoclaw-ng-3.0.2-r1.apk root@<router-ip>:/tmp/
ssh root@<router-ip> 'apk add /tmp/luci-app-picoclaw-ng-3.0.2-r1.apk'
```

Packages built without a signing key are unsigned and still need `--allow-untrusted`; see the signing section below.

Without a 25.x router, build it in an Alpine container (APK v3 must be produced by `apk mkpkg` from apk-tools 3):

```bash
docker run --rm -v "$PWD:/work" -w /work alpine:edge sh scripts/build-apk-v3.sh
```

The included `.github/workflows/build-packages.yml` builds both the IPK and the APK in CI and uploads them as separate artifacts. CI artifacts are unsigned; official releases are signed locally with the project key.

### Signing the APK (optional)

Release packages are signed with the project key; its public key is `keys/luci-app-picoclaw-ng.rsa.pub`. To build signed packages yourself:

```bash
# 1. Generate an RSA key pair (the private key is stored outside the repository)
sh scripts/gen-apk-key.sh

# 2. Build with the private key; the public key must sit next to it as *.rsa.pub
PC_SIGN_KEY="$HOME/.config/luci-app-picoclaw-ng/apk-keys/luci-app-picoclaw-ng.rsa" \
  sh scripts/build-apk-v3.sh

# 3. Trust the public key on the router once
scp "$HOME/.config/luci-app-picoclaw-ng/apk-keys/luci-app-picoclaw-ng.rsa.pub" \
  root@<router-ip>:/etc/apk/keys/
ssh root@<router-ip> 'apk add /tmp/luci-app-picoclaw-ng-3.0.2-r1.apk'
```

When building in the Alpine container, mount the key directory read-only:

```bash
docker run --rm -v "$PWD:/work" \
  -v "$HOME/.config/luci-app-picoclaw-ng/apk-keys:/keys:ro" \
  -w /work -e PC_SIGN_KEY=/keys/luci-app-picoclaw-ng.rsa \
  alpine:edge sh scripts/build-apk-v3.sh
```

The build prints `apk verify ... OK` when signing succeeds. Sign during `apk mkpkg`; do not use `apk adbsign` from apk-tools 3.0.x on an existing v3 package, it can truncate the file. Keep the private key out of git (it is covered by `.gitignore`); replacing the key means importing the new public key on every router again.

Open:

```
http://<router-ip>/cgi-bin/luci/admin/services/picoclaw
```

The first visit shows a "PicoClaw is not installed" banner. Click **Install core**; the installer runs `picoclaw onboard` to create the default config and workspace, then starts the service in the selected mode (Gateway by default, kept alive in limited mode until a model is configured).

## Source layout and store listing

Package sources follow the OpenWrt / iStoreOS convention under `apps/picoclaw/`:

- `apps/picoclaw/luci-app-picoclaw-ng/` — the plugin, where `luasrc/` maps to `/usr/lib/lua/luci` and `root/` maps to `/`; buildable with an SDK
- `apps/picoclaw/app-meta-picoclaw/` — iStore store metadata (icon + dependencies) with no program files

Both `scripts/build-ipk.py` and `scripts/build-apk-v3.sh` read from those directories, so package contents stay in sync with the tree. See [`apps/picoclaw/README.md`](apps/picoclaw/README.md) for the iStore submission steps and the `syncapps.yaml` snippet.

## Run modes

### Gateway (default)

- Runs `picoclaw gateway`
- No web console; only the background messaging gateway (Feishu, Telegram, QQ, etc.)
- Recommended for daily operation: lower overhead and a smaller attack surface
- Without a default model it runs in `--allow-empty` limited mode; open the panel once to configure a model
- Configure by editing `/root/.picoclaw/config.json`, or open the panel briefly and close it again

### Launcher web panel (on demand)

- Click **Open web panel** to start `picoclaw-launcher -no-browser [-public] -port <port>` temporarily
- Use it only for visual configuration; click **Close panel** or reboot to return to Gateway
- Default port `18800`, editable in the **panel port** field below the status grid
- `public` is enabled by default (`http://<router-ip>:18800`); disable it to bind `127.0.0.1`
- Launcher v0.3.1 authenticates with its own dashboard password (the old token login was removed). Set a strong password on first visit; while no password exists, a public panel lets anyone on the LAN complete the initial setup
- **Backup panel** starts the panel on an alternate port (primary port + 1000), useful when the port is occupied or a browser cache misbehaves; it uses the same Launcher dashboard password
- You can persist Launcher as the default mode, but it is not recommended long-term

The default mode and port are stored in UCI (`/etc/config/picoclaw`) and read by the init script. The temporary panel flag lives in `/tmp/picoclaw-panel` and disappears after reboot. Runtime output goes to `/var/log/picoclaw.log` and rotates at 2 MB on service start.

## Version policy

- Installs and updates only to `PC_SUPPORTED_VERSION` (currently `0.3.1`).
- Every download is checked against the official SHA256 and the extracted binary reports its version.
- If the installed version is newer than the supported one, the page warns and refuses update/downgrade.
- When upstream ships a newer release, the page only shows a notice; upgrade happens after the plugin adds support.

## Operation log (audit trail)

The **Diagnostics** switch in the runtime-log card header controls the plugin operation log; it is off by default. While it is off, no log file is created or written.

When enabled, the following is appended with timestamps to `/etc/picoclaw-luci.log`:

- Every page action (start/stop/restart, mode and port, config save, autostart, skills, scheduled jobs, MCP, models, etc.), including parameters and the result;
- Each step of install/update (architecture choice, download size, SHA256, extraction, backup, version self-check, rollback, restart);
- Init-script start/stop requests, the actual backend command executed, and signals sent.

API keys, request headers, environment variables, the full config and task messages are never written. `user:password@` in URLs is masked automatically. The file rotates to `.1` above 256 KB (one file kept) and can be viewed or cleared directly in the UI.

## Permissions

This fork keeps the original permission model: the service and PicoClaw configuration still run as `root`, with config under `/root/.picoclaw`.

## Credits

- [PicoClaw](https://github.com/sipeed/picoclaw) — Sipeed and all contributors. The binaries and Launcher installed by this plugin come from their official releases.
- [luci-app-picoclaw](https://github.com/GennKann/luci-app-picoclaw) — GennKann, the origin of this fork and its earlier management pages.
- [UFI-TOOLS](https://github.com/kanoqwq/UFI-TOOLS) — kano. The lifecycle workflow and interaction in this fork are modelled on the PicoClaw plugin in UFI-TOOLS.

## License

[MIT](LICENSE). Original copyright notices are preserved; copyright for the fork changes is added. PicoClaw itself is also MIT-licensed, copyright its authors.
