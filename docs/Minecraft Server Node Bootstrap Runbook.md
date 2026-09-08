# Minecraft Server Node Bootstrap Runbook

## 1. 文档职责

本手册用于把一台接近裸机状态的 Ubuntu 云主机搭建成可运行以下组件的
Minecraft Production Node：

- Fabric Minecraft Server；
- GDMC HTTP Interface；
- WorldEdit；
- GDPC / 自定义 Python 生成器；
- HeadlessMC Render Worker；
- HMC-Specifics；
- Visual Probe；
- Xvfb + Mesa 真实软件 OpenGL 渲染。

本手册独立于 `Minecraft Server Agent Operations Runbook.md`。两者的状态边界是：

| 状态 | 含义 | 应读文档 |
|---|---|---|
| `BARE_NODE` | Java、系统依赖、服务端、客户端或关键 mods 尚未安装 | 本手册 |
| `PROVISIONED_COLD` | 全部制品已安装且校验通过，但两个服务都没启动 | 日常 Operations Runbook 的冷启动章节 |
| `HOT_READY` | Server 和 Render Worker 已运行，Probe 为 `READY` | 日常 Operations Runbook 的热启动章节 |

缺少关键依赖的机器不是“冷启动”，而是“未完成安装”。不要用日常启动命令反复
尝试修补一台裸机。

本手册只授权新节点的软件安装和服务初始化，不授权迁移或修改既有 Minecraft
世界。若目标路径中已经存在世界、服务进程或未知制品，停止覆盖安装，先转入日常
运维手册进行审计。

## 2. 当前锁定的部署版本

本环境复刻 2026-09-08 在腾讯云 Ubuntu 节点通过 S0 验收的组合：

| Component | Pinned version |
|---|---|
| OS | Ubuntu Server 24.04 LTS, x86_64 |
| Java | OpenJDK 21 |
| Minecraft | 1.21.11 |
| Fabric Loader | 0.19.5 |
| Fabric server launcher | 1.1.2 |
| Fabric API | 0.141.6+1.21.11 |
| GDMC HTTP Interface | 1.8.4-1.21.11 |
| WorldEdit | 7.4.2 for Fabric/Minecraft 1.21.11 |
| HeadlessMC | 2.10.0 |
| HMC-Specifics | 2.4.0, Fabric/Minecraft 1.21.11 |
| Visual Probe | 0.1.0 |
| GDPC | 8.1.0 |

不要在初装过程中顺手升级其中一个组件。Minecraft、Fabric Loader、Fabric API、
GDMC、HMC-Specifics 与 Visual Probe 是一个经过验收的兼容集合；升级必须作为新的
兼容性任务单独测试。

## 3. 目标主机最低条件

推荐基线：

- Ubuntu 24.04 x86_64；
- 普通运行用户 `ubuntu`，具备 `sudo`；
- 至少 4 GiB RAM；
- 建议至少 2 GiB swap；
- 至少 10 GiB 可用磁盘；
- SSH 或云厂商控制台提供的带外恢复通道；
- 出站网络能力已经分类，见第 5 节。

腾讯云验收节点实际为约 3.6 GiB RAM、2 GiB swap、40 GiB 系统盘。两个 Java
进程运行时内存余量不宽裕，因此 4 GiB 是可运行基线，不是高负载推荐值。

## 4. 裸机与覆盖安装安全门

登录后先执行只读审计：

```bash
whoami
hostname
. /etc/os-release && printf '%s %s\n' "$ID" "$VERSION_ID"
uname -m
free -h
df -h / /home/ubuntu

command -v java || true
command -v screen || true
screen -ls 2>&1 || true
ss -ltnp | awk 'NR == 1 || /:59916|:9000|:8766/'

find /home/ubuntu -maxdepth 2 \
  \( -name 'level.dat' -o -name 'server.properties' -o -name 'headlessmc-launcher.jar' \) \
  -print 2>/dev/null
```

只有同时满足以下条件时，才把主机归类为 `BARE_NODE`：

- 没有 Minecraft/HeadlessMC Java 进程；
- `59916`、`9000`、`8766` 没有被占用；
- 没有需要保留的 `/home/ubuntu/world`；
- 没有未知来源的 HeadlessMC 或 mods 安装；
- OS 与 CPU 架构符合计划。

发现已有世界时，不得删除、覆盖或用空世界替换。发现部分安装时，应记录现状并按
组件恢复，而不是假装它是裸机。

## 5. 出站网络分级

初装依赖三类不同网络：

1. Ubuntu APT 镜像：Java、Xvfb、Mesa、Python 等系统包；
2. Mojang/Fabric CDN：Minecraft 服务端、客户端、libraries、assets 和 Fabric；
3. GitHub/Modrinth：HeadlessMC、HMC-Specifics、GDMC、WorldEdit 等制品。

在目标主机上探测连通性：

裸机如果没有 `curl`，先尝试通过 APT 安装最小探测工具；这一步失败本身就说明不能
走普通在线安装，应转向 `FULL_OFFLINE`/预制镜像：

```bash
if ! command -v curl >/dev/null 2>&1; then
  sudo apt-get update && sudo apt-get install -y curl ca-certificates
fi

command -v curl
```

```bash
for url in \
  https://archive.ubuntu.com/ubuntu/ \
  https://meta.fabricmc.net/v2/versions/game \
  https://maven.fabricmc.net/ \
  https://piston-meta.mojang.com/mc/game/version_manifest_v2.json \
  https://libraries.minecraft.net/ \
  https://resources.download.minecraft.net/ \
  https://api.modrinth.com/v2/version/oY3E2pzA \
  https://github.com/headlesshq/hmc-specifics/releases/download/1.21.11-latest/hmc-specifics-1.21.11-fabric-latest.jar
do
  code="$(curl -L -sS -o /dev/null -w '%{http_code}' \
    --connect-timeout 5 --max-time 15 --range 0-0 "$url" 2>/dev/null || true)"
  printf '%-4s %s\n' "${code:-ERR}" "$url"
done
```

对站点根路径来说，`401`、`403`、`404` 仍可能表示网络可达；重点是 DNS、TLS 和
连接没有超时。不要因为一次成功就认为后续几百 MiB 的下载一定稳定。

按结果选择安装模式：

| Mode | 网络状态 | 安装策略 |
|---|---|---|
| `ONLINE` | APT、Mojang/Fabric、GitHub/Modrinth 都稳定 | 可直接下载，但仍必须校验固定哈希 |
| `GITHUB_BLOCKED` | APT 与 Mojang/Fabric 可达，GitHub 不稳定或不可达 | 推荐：在可信工作站组装开源/自研制品包，经 SCP 或私有 COS 转运 |
| `GAME_CDN_BLOCKED` | GitHub可达或不可达，但 Mojang/Fabric 不可达 | 转运制品包，并使用在授权联网环境中预热、清理过的私有客户端/服务端缓存 |
| `FULL_OFFLINE` | APT 也不可用 | 优先使用预制云镜像；离线 `.deb` 必须来自同一 Ubuntu 发行版和架构 |

2026-09-08 对既有腾讯云节点的复核中，上述测试站点均可建立连接，包括 GitHub。
这只是当时节点的观测结果，不是下一台腾讯云机器的部署前提。

## 6. 制品获取原则

推荐默认采用 `GITHUB_BLOCKED` 模式的思路，即使目标机器当前能够访问 GitHub：

```text
可信联网工作站
  ↓ 下载固定版本
  ↓ 核对上游哈希/本项目接受哈希
  ↓ 生成 SHA256SUMS
  ↓ 打包
SCP 或私有 COS 临时签名 URL
  ↓
目标 Ubuntu 节点
  ↓ 先校验外层包哈希
  ↓ 再校验内部 SHA256SUMS
  ↓ 安装
```

这样 HMC-Specifics 等 GitHub 制品不需要由目标服务器直接访问 GitHub。

禁止：

- 使用不明 GitHub 加速站、网盘转载或第三方“整合包”；
- 使用 `latest` 而不校验内容哈希；
- 只验证文件名或大小；
- 把 COS SecretId/SecretKey、Probe token 或 SSH 私钥写进包；
- 用 `rsync --delete` 覆盖未知服务器目录；
- 把 Mojang 客户端缓存公开发布。

HeadlessMC 的 `-offline` 是本部署中连接离线模式服务器的固定身份配置，不是绕过
Minecraft 所有权或许可要求的手段。

## 7. 已验收制品清单与哈希

下列 SHA-256 来自本地工作区和既有腾讯云节点的双向核对。安装时应将实际文件与
这些值比较。

| Installed artifact | Bytes | SHA-256 |
|---|---:|---|
| `fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar` | 181841 | `2b63d293be54c8f5484a242859cab841dcee38511e11b2f82e92211f19872d08` |
| `fabric-api-0.141.6+1.21.11.jar` | 2426039 | `bdff7fd7e220085cfad2ff9b1f40dde6534ae0b96cf378f97a374bc54cb9ed0f` |
| `gdmc_http_interface-1.8.4-1.21.11.jar` | 266474 | `602be3e318bfe7ee6d12eb9deddf8a3acf0f121d3c01272637fbd9f067b900dd` |
| `worldedit-mod-7.4.2.jar` | 6970159 | `f964976b47d6b2766753738815bdeef54a25e1861343f3038df389b9dddcea60` |
| `headlessmc-launcher.jar` (HeadlessMC 2.10.0) | 13010386 | `52bd5006f478377b3893011d458562977d38c65ead6d2b31089beb4d614f13cd` |
| `hmc-specifics-1.21.11-2.4.0-fabric-release.jar` | 5588929 | `931979a82c567021b064442700f8066d7e8acf25da0d30738341ad17686e2808` |
| `mc-visual-probe-0.1.0.jar` | 47630 | `b40ba0889337e2ce1cfcc0ed9d8e1d56c06448ad95023180a232a469e133562c` |
| `connect.bash` | 10712 | `dace9a661312400ce10e163db3bfc747aec8caae38593f4d3f21468e634f9ed1` |

HMC-Specifics 上游文件名是
`hmc-specifics-1.21.11-fabric-latest.jar`。本部署在核对上述固定哈希后，将其改名为
带版本的 `hmc-specifics-1.21.11-2.4.0-fabric-release.jar`，避免“latest”名称掩盖
内容漂移。

Visual Probe 与 `connect.bash` 是本项目制品，不从公共下载站获取；应从受控工作区
的已验收构建输出进入部署包。

## 8. 上游直连来源

仅在 `ONLINE` 模式中直接从目标机下载。所有下载都先进入 `incoming`，哈希匹配后
才能安装。

| Artifact | Pinned upstream source |
|---|---|
| Fabric server launcher | `https://meta.fabricmc.net/v2/versions/loader/1.21.11/0.19.5/1.1.2/server/jar` |
| Fabric API | `https://maven.fabricmc.net/net/fabricmc/fabric-api/fabric-api/0.141.6%2B1.21.11/fabric-api-0.141.6%2B1.21.11.jar` |
| HeadlessMC 2.10.0 | `https://github.com/headlesshq/headlessmc/releases/download/2.10.0/headlessmc-launcher-2.10.0.jar` |
| HMC-Specifics | `https://github.com/headlesshq/hmc-specifics/releases/download/1.21.11-latest/hmc-specifics-1.21.11-fabric-latest.jar` |
| GDMC HTTP 1.8.4 | `https://github.com/Niels-NTG/gdmc_http_interface/releases/download/v1.8.4/gdmc_http_interface-1.8.4-1.21.11.jar` |
| WorldEdit 7.4.2 | `https://cdn.modrinth.com/data/1u6JkXh5/versions/oY3E2pzA/worldedit-mod-7.4.2.jar` |

示例模式：

```bash
install_root=/home/ubuntu/incoming/mc-node-bootstrap
install -d -m 0750 "$install_root/artifacts"

curl -fL --retry 3 --retry-delay 2 \
  -o "$install_root/artifacts/headlessmc-launcher.jar" \
  'https://github.com/headlesshq/headlessmc/releases/download/2.10.0/headlessmc-launcher-2.10.0.jar'

printf '%s  %s\n' \
  '52bd5006f478377b3893011d458562977d38c65ead6d2b31089beb4d614f13cd' \
  "$install_root/artifacts/headlessmc-launcher.jar" \
  | sha256sum -c -
```

任一哈希不匹配都必须停止安装。不要把新哈希自动写回手册。

## 9. 推荐离线转运包

工作站组装包时使用以下逻辑结构：

```text
mc-node-bootstrap-1.21.11/
├── SHA256SUMS
├── artifacts/
│   ├── server/
│   │   ├── fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar
│   │   └── mods/
│   │       ├── fabric-api-0.141.6+1.21.11.jar
│   │       ├── gdmc_http_interface-1.8.4-1.21.11.jar
│   │       └── worldedit-mod-7.4.2.jar
│   ├── hmc/
│   │   ├── headlessmc-launcher.jar
│   │   ├── connect.bash
│   │   └── hmc-specifics-1.21.11-2.4.0-fabric-release.jar
│   └── client-mods/
│       ├── fabric-api-0.141.6+1.21.11.jar
│       ├── gdmc_http_interface-1.8.4-1.21.11.jar
│       ├── hmc-specifics-1.21.11-2.4.0-fabric-release.jar
│       └── mc-visual-probe-0.1.0.jar
├── python-wheels/                 # FULL_OFFLINE 时使用
└── private-cache/                 # GAME_CDN_BLOCKED 时使用；不得公开
    ├── server-runtime.tar.gz
    └── hmc-client-cache-x86_64.tar.gz
```

`SHA256SUMS` 应使用包内相对路径，并覆盖所有制品。压缩包本身再生成一个独立 SHA-256，
通过与下载 URL 不同的通道传给目标 Agent。

当前工作区中已验收制品的来源映射：

| Workspace source | Bundle destination |
|---|---|
| `fabric 1.21.11/fabric-server.jar` | `artifacts/server/fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar` |
| `fabric 1.21.11/mods/fabric-api-0.141.6+1.21.11.jar` | Server mods，并复制一份到 Client mods |
| `fabric 1.21.11/mods/gdmc_http_interface-1.8.4-1.21.11.jar` | Server mods，并复制一份到 Client mods |
| `fabric 1.21.11/mods/worldedit-mod-7.4.2.jar` | 仅 Server mods |
| `headless mc/headlessmc-launcher.jar` | `artifacts/hmc/headlessmc-launcher.jar` |
| `headless mc/HeadlessMC/specifics/hmc-specifics/hmc-specifics-1.21.11-2.4.0-fabric-release.jar` | HMC specifics，并复制一份到 Client mods |
| `headless mc/connect.bash` | `artifacts/hmc/connect.bash` |
| `mc-visual-probe/build/libs/mc-visual-probe-0.1.0.jar` | 仅 Client mods |

不要把工作区中的 `headlessmc.log*`、Windows `config.properties`、本地 world、
`*-sources.jar` 或测试输出混入部署包。

从当前授权 Windows 工作站传输的示例：

```powershell
ssh -i <SSH_KEY_PATH> ubuntu@<SERVER_PUBLIC_IP> `
  "install -d -m 0750 /home/ubuntu/incoming"

scp -i <SSH_KEY_PATH> `
  .\mc-node-bootstrap-1.21.11.tar.gz `
  ubuntu@<SERVER_PUBLIC_IP>:/home/ubuntu/incoming/
```

如果使用腾讯云 COS：

- Bucket 必须为私有；
- 使用短时有效的预签名 HTTPS URL；
- URL 和凭据不得写入仓库或共享日志；
- 下载后立即验证外层与内层哈希；
- 部署完成后撤销 URL 或删除临时对象。

不要因为目标机访问 GitHub 失败就转向未知代理。SCP 或私有 COS 是可审计的替代路径。

## 10. 安装 Ubuntu 运行依赖

腾讯云 Ubuntu 24.04 x86_64 上已验证的包集合：

```bash
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  openjdk-21-jre-headless \
  screen xvfb xauth \
  curl jq ca-certificates unzip tar rsync \
  python3 python3-venv python3-pip \
  libgl1-mesa-dri libglx-mesa0 mesa-utils \
  libasound2t64 \
  libx11-6 libxext6 libxi6 libxrender1 libxtst6 \
  libxrandr2 libxcursor1 libxinerama1 libxxf86vm1 \
  libfreetype6 libfontconfig1 libnss3
```

验证：

```bash
java -version
python3 --version
screen --version
dpkg-query -W -f='${binary:Package}\t${Version}\n' xvfb
xvfb-run -a -s '-screen 0 854x480x24 -nolisten tcp' glxinfo -B
```

要求 Java major version 至少为 21，`glxinfo -B` 必须返回可用 OpenGL renderer。
无 GPU 云主机通常显示 Mesa llvmpipe；这仍是真实 framebuffer 渲染，不是
HeadlessMC LWJGL stub。

如果没有 swap，在确认磁盘空间和云盘策略后可创建独立 swapfile；不要覆盖现有 swap：

```bash
swapon --show
free -h
```

创建 swap 属于主机级变更，应在云平台磁盘和运维策略确认后执行，不应由安装脚本
无条件完成。

## 11. 校验并展开转运包

假设外层文件已经上传到 `/home/ubuntu/incoming`：

```bash
cd /home/ubuntu/incoming
sha256sum mc-node-bootstrap-1.21.11.tar.gz
```

先与带外收到的外层哈希比较。再检查归档路径，拒绝绝对路径和 `..` 路径：

```bash
tar -tzf mc-node-bootstrap-1.21.11.tar.gz \
  | awk '$0 ~ /^\// || $0 ~ /(^|\/)\.\.($|\/)/ { bad=1; print "UNSAFE", $0 } END { exit bad }'

tar -xzf mc-node-bootstrap-1.21.11.tar.gz -C /home/ubuntu/incoming
cd /home/ubuntu/incoming/mc-node-bootstrap-1.21.11
sha256sum -c SHA256SUMS
```

只允许在所有项目均为 `OK` 后继续。

## 12. 创建固定目录布局

以下布局有意复刻已经通过验收的腾讯云节点，以便日常 Runbook 可直接复用：

```bash
sudo install -d -o ubuntu -g ubuntu -m 0750 \
  /home/ubuntu/mods \
  /home/ubuntu/config \
  /home/ubuntu/headlessMC \
  /home/ubuntu/headlessMC/HeadlessMC/specifics/hmc-specifics \
  /home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods \
  /home/ubuntu/headlessMC/srv/hmc-client/.minecraft/mods-disabled/server-only \
  /home/ubuntu/headlessMC/server-tests
```

在复制前再次确认目标不是已有生产节点。假设包根目录为
`/home/ubuntu/incoming/mc-node-bootstrap-1.21.11`：

```bash
bundle_root=/home/ubuntu/incoming/mc-node-bootstrap-1.21.11
client_root=/home/ubuntu/headlessMC/srv/hmc-client/.minecraft

install -m 0644 \
  "$bundle_root/artifacts/server/fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar" \
  /home/ubuntu/fabric-server-mc.1.21.11-loader.0.19.5-launcher.1.1.2.jar

install -m 0644 "$bundle_root/artifacts/server/mods/"*.jar /home/ubuntu/mods/

install -m 0644 "$bundle_root/artifacts/hmc/headlessmc-launcher.jar" \
  /home/ubuntu/headlessMC/headlessmc-launcher.jar
install -m 0755 "$bundle_root/artifacts/hmc/connect.bash" \
  /home/ubuntu/headlessMC/connect.bash
install -m 0644 \
  "$bundle_root/artifacts/hmc/hmc-specifics-1.21.11-2.4.0-fabric-release.jar" \
  /home/ubuntu/headlessMC/HeadlessMC/specifics/hmc-specifics/

install -m 0644 "$bundle_root/artifacts/client-mods/"*.jar "$client_root/mods/"
```

WorldEdit 只放在服务端 `/home/ubuntu/mods`。HMC 客户端必须保留 Fabric API、
GDMC、HMC-Specifics 和 Visual Probe 四个 JAR。GDMC 虽提供服务端 HTTP 能力，但
它的自定义 registry 会在 Fabric 登录时同步，因此客户端缺少同版本 GDMC 会断线。

## 13. 配置固定的 HeadlessMC 离线身份

创建 `/home/ubuntu/headlessMC/HeadlessMC/config.properties`：

```bash
install -d -m 0750 /home/ubuntu/headlessMC/HeadlessMC

if [ -e /home/ubuntu/headlessMC/HeadlessMC/config.properties ]; then
  printf '%s\n' 'ABORT: existing HeadlessMC config requires review' >&2
  exit 1
fi

cat > /home/ubuntu/headlessMC/HeadlessMC/config.properties <<'EOF'
hmc.java.versions=/usr/lib/jvm/java-21-openjdk-amd64/bin/java;/usr/lib/jvm/java-1.21.0-openjdk-amd64/bin/java
hmc.offline=true
hmc.offline.username=HeadlessBuilderExample
hmc.offline.uuid=21aba0fbe87f35f9837e8e78f7e22cad
EOF

chmod 0600 /home/ubuntu/headlessMC/HeadlessMC/config.properties
```

用户名和 UUID 必须稳定，否则 OP 身份与 playerdata 会发生漂移。新建服务器第一次
启动后，应在服务端控制台执行：

```text
op HeadlessBuilderExample
```

在 Render Worker 登录前完成 OP 授权，避免当前 `PLAYER_SPECTATOR` camera backend
因反复执行 `/gamemode`、`/tp` 失败而产生重试和踢出。

## 14. 初始化服务端配置

Minecraft EULA 必须由运营者明确接受；Agent 不得把未确认的接受动作隐藏在脚本中。
确认后才创建：

```bash
printf '%s\n' 'eula=true' > /home/ubuntu/eula.txt
```

裸机上可创建最小 `server.properties`；Minecraft 首次运行会补全默认项：

```bash
if [ -e /home/ubuntu/server.properties ]; then
  printf '%s\n' 'ABORT: existing server.properties requires review' >&2
  exit 1
fi

cat > /home/ubuntu/server.properties <<'EOF'
server-ip=
server-port=59916
online-mode=false
white-list=false
enforce-whitelist=false
enable-command-block=false
view-distance=8
simulation-distance=6
motd=Minecraft Environment Factory
EOF
```

预创建 GDMC 配置：

```bash
printf '%s\n' '{"http_port":9000,"http_host":"localhost"}' \
  > /home/ubuntu/config/gdmc_http_interface.json
```

当前 GDMC 1.8.4 在既有节点上即使配置为 `localhost`，仍观察到 `*:9000`。因此该
配置不是安全边界；云安全组和主机防火墙必须拒绝公网访问 `9000`。

## 15. 安装 GDPC / Python 生成器环境

不要把 Python 包安装到系统 Python：

```bash
python3 -m venv /home/ubuntu/headlessMC/generator-venv
/home/ubuntu/headlessMC/generator-venv/bin/python -m pip install --upgrade pip
/home/ubuntu/headlessMC/generator-venv/bin/python -m pip install 'gdpc==8.1.0'
/home/ubuntu/headlessMC/generator-venv/bin/python -c 'import gdpc; print(gdpc.__version__)'
```

若目标不能访问 PyPI，应在相同 Ubuntu/Python/CPU 环境中预取 wheelhouse：

```bash
python3 -m venv /tmp/mc-wheel-builder
/tmp/mc-wheel-builder/bin/python -m pip download \
  --dest /tmp/mc-wheelhouse 'gdpc==8.1.0'
```

把整个 wheelhouse 放入部署包，然后在目标机安装：

```bash
/home/ubuntu/headlessMC/generator-venv/bin/python -m pip install \
  --no-index \
  --find-links /home/ubuntu/incoming/mc-node-bootstrap-1.21.11/python-wheels \
  'gdpc==8.1.0'
```

不要在 Windows 上随意下载 wheel 后假设它们可用于 Linux；含二进制依赖时必须匹配
Python ABI、Linux 平台和 x86_64 架构。

## 16. Minecraft/Fabric 缓存策略

### 16.1 APT 与 Mojang/Fabric 可达

这是 `ONLINE` 和典型 `GITHUB_BLOCKED` 模式。GitHub 制品从包中取得，首次启动时
允许 Fabric Server 和 HeadlessMC 从 Mojang/Fabric 下载服务端、客户端、libraries
与 assets。

先运行：

```bash
cd /home/ubuntu/headlessMC
./connect.bash \
  --game-dir /home/ubuntu/headlessMC/srv/hmc-client/.minecraft \
  --server 127.0.0.1:59916 \
  --validate-only
```

验证通过不代表客户端缓存已经下载；真正的首次 HMC 启动可能下载约 500–700 MiB，
并需要数分钟。它必须在 Minecraft Server 完全 READY 之后进行。

### 16.2 Mojang/Fabric 也不可达

在授权联网的 Ubuntu 24.04 x86_64 staging node 上先完成一次干净安装与启动，再生成
私有缓存包。应包括：

- 服务端 launcher 首次运行生成的 `libraries/` 与 `versions/`；
- HMC 客户端 `.minecraft/assets/`、`libraries/`、`versions/` 和 `.fabric/`；
- HeadlessMC 自身首次运行生成的必要运行库与 Linux x86_64 natives；
- 固定 mods 与配置模板。

不得打包：

- `world/`、`saves/` 或任何生产世界；
- `logs/`、`crash-reports/`；
- `.minecraft/visual-probe/session.json`；
- HeadlessMC account/token 文件；
- `servers.dat`、playerdata 或其他运行身份残留；
- SSH、云厂商、Microsoft/Minecraft 凭据。

既有腾讯云客户端缓存约 586 MiB，其中 assets 约 441 MiB、libraries 约 67 MiB、
versions 约 30 MiB。不要只转移 `mods/` 后声称是“完全离线包”。

缓存包含 Minecraft 文件，不应上传到公共 Git 仓库、公共 COS Bucket 或公开下载页。
只在获得授权并符合适用许可的私有环境间转移。

### 16.3 APT 也不可达

优先从已经安装并验收的腾讯云自定义镜像创建新实例。离线收集 `.deb` 容易遗漏
传递依赖、安全更新和架构差异，仅作为次选。若必须使用：

- 在同一 Ubuntu 24.04 point release、同一 x86_64 架构收集；
- 保存包名、版本、APT source 与 SHA-256 manifest；
- 安装后再次运行第 10 节的版本与 OpenGL 验证；
- 不混用其他 Ubuntu 版本或 Debian 软件包。

## 17. 首次启动顺序

安装完成后，进入 `Minecraft Server Agent Operations Runbook.md` 的冷启动流程，
但首次启动增加两个 gate：

1. Server 启动并出现 `Done (`；
2. 在 Server 控制台执行 `op HeadlessBuilderExample`；
3. 确认 GDMC `/version` 返回 `1.21.11`；
4. 再启动 `hmc-render`；
5. 等待 HeadlessMC 下载/装配缓存并加入 `127.0.0.1:59916`；
6. 重新读取本次启动产生的 Probe `session.json`；
7. 要求 `/v1/status` 返回 `READY`、`world_loaded=true`；
8. 完成一次真实 PNG 捕获，而不是只检查端口。

不要使用 HeadlessMC `-lwjgl` 或 `--stub-renderer` 做 PNG 验收。工作路径是 Xvfb +
Mesa llvmpipe + 正常 LWJGL/OpenGL。

## 18. 网络安全必须先于公网开放

腾讯云安全组建议：

- `22/tcp`：只允许运维来源 IP；
- `59916/tcp`：只允许明确批准的 Minecraft 客户端来源 IP；
- `9000/tcp`：不创建公网入站规则；
- `8766/tcp`：不创建公网入站规则；
- 其他入站：默认拒绝。

若启用 UFW，必须先确认 SSH 放行和腾讯云控制台的带外恢复能力，避免把自己锁在
服务器外：

```bash
sudo ufw status verbose
sudo ufw allow OpenSSH
sudo ufw allow from APPROVED_PUBLIC_IP to any port 59916 proto tcp
sudo ufw deny 9000/tcp
sudo ufw deny 8766/tcp
```

将 `APPROVED_PUBLIC_IP` 替换为操作者确认的实际公网 TCP 来源。不要猜测，也不要把
占位符原样执行。是否执行 `sudo ufw enable` 是一次可能中断远程访问的主机级变更，
必须在 SSH 和带外恢复路径确认后单独决定。

服务启动后一定检查实际监听：

```bash
ss -ltnp | awk 'NR == 1 || /:59916|:9000|:8766/'
```

预期：`59916` 按安全组策略提供服务，`8766` 仅 loopback；即便 `9000` 显示通配
监听，它也必须被云和主机防火墙阻断公网访问。

## 19. 初装验收清单

只有全部通过，状态才从 `BARE_NODE` 变为 `PROVISIONED_COLD` 或 `HOT_READY`：

- [ ] OS 为 Ubuntu 24.04 x86_64；
- [ ] Java 21、Screen、Xvfb、xauth、Mesa、Python venv 可用；
- [ ] Xvfb 下 `glxinfo -B` 返回真实 OpenGL renderer；
- [ ] 所有固定制品哈希匹配第 7 节；
- [ ] Server mods 只有预期的 Fabric API、GDMC、WorldEdit；
- [ ] Client mods 只有预期的 Fabric API、GDMC、HMC-Specifics、Visual Probe；
- [ ] WorldEdit 未放进活动 Client mods；
- [ ] HMC-Specifics 同时位于 HMC specifics cache 与 Client mods；
- [ ] 固定 offline username/UUID 已配置，`HeadlessBuilderExample` 已 OP；
- [ ] Server 日志出现 `Done (`，`59916` 与 `9000` 健康；
- [ ] HMC 使用 Screen pseudo-TTY 和真实 Xvfb renderer；
- [ ] Probe 为 `READY` 且 `world_loaded=true`；
- [ ] 一张真实 PNG 可打开且不是空白/占位图；
- [ ] `9000` 与 `8766` 不可从公网访问；
- [ ] 日志、Probe token、账号文件未进入制品包；
- [ ] 安装记录保存了 OS、包版本、制品哈希、网络模式和测试结果。

初装验收不需要生成 cabin，也不应借机修改已有世界。世界写入能力应在独立、受
Adapter 约束的 S0/回归测试中验证。

当前 Visual Probe V0.1 的 `world_revision=0` 不是可用的同步栅栏。初装验收可以
确认真实渲染链路，但不得据此宣称已经具备 V0.2 的确定性 world-sync 能力。

## 20. 常见初装失败

| Symptom | Cause | Action |
|---|---|---|
| `java: command not found` | APT 依赖未安装 | 安装 OpenJDK 21；不要让 HMC 临时下载未知 Java 替代固定系统运行时 |
| Java 版本低于 21 | OS 默认 Java 不符合 Minecraft 1.21.11 | 安装 Java 21，并让 `connect.bash --java` 指向正确路径 |
| GitHub 超时 | 云主机到 GitHub 链路不稳定 | 使用可信工作站 + SHA-256 + SCP/私有 COS；不要使用不明代理 |
| HMC-Specifics 下载成功但重启又下载 | 只放入 Client mods，未放入 HMC specifics cache，或允许自动下载 | 将固定 JAR 放入两个规定位置；保持 `hmc.auto.download.specifics=false` |
| Mojang/Fabric 下载失败 | 不是 GitHub 问题，而是 game CDN 不可达 | 使用私有、清理过的完整缓存；只复制 mods 不够 |
| `NoClassDefFoundError` / native load error | 缓存来自错误 CPU/OS，或 libraries 不完整 | 在 Ubuntu 24.04 x86_64 staging node 重新预热与打包 |
| `glxinfo` 无 renderer | Mesa/Xvfb/GLX 依赖不完整 | 修复系统包后再启动 HMC；不要切换到 `-lwjgl` 掩盖问题 |
| JLine 初始化失败 | HMC 没有 pseudo-TTY | 使用 GNU Screen，不用普通 `nohup` |
| Fabric registry remap 失败 | Client 缺少同版本 GDMC | 恢复已验收 GDMC JAR并核对哈希 |
| Probe `NO_WORLD` | Server 未 READY、客户端未加入或被踢 | 先修复 Server/OP/连接，不要截屏 |
| 首次 HMC 启动长时间无 Probe | 正在下载 500–700 MiB 客户端缓存，或下载卡住 | 看当前 HMC 日志和网络流量；不要重复启动第二个 worker |
| Server OOM 或系统开始换页 | 4 GiB 节点余量不足 | 停止扩展测试，检查 RSS/swap，降低距离或升级实例规格 |

## 21. 交接给日常运维

完成初装验收后：

1. 记录节点状态为 `PROVISIONED_COLD` 或 `HOT_READY`；
2. 后续启动、停止、Screen、日志和健康检查全部转入
   `Minecraft Server Agent Operations Runbook.md`；
3. 不再重复运行本手册的目录初始化或配置覆盖步骤；
4. 任何版本升级重新回到“新兼容性环境”处理，而不是在生产节点原地漂移；
5. 世界写入仍必须单独读取 `TASK_STATE.md` 与
   `Minecraft Environment Adapter — SKILL.md`。

## 22. 上游参考

- Fabric Meta server launcher API：`https://meta.fabricmc.net/`
- Fabric Java 21 guidance：`https://docs.fabricmc.net/players/installing-java/linux`
- HeadlessMC releases：`https://github.com/headlesshq/headlessmc/releases`
- HMC-Specifics releases：`https://github.com/headlesshq/hmc-specifics/releases`
- GDMC HTTP Interface 1.8.4：
  `https://github.com/Niels-NTG/gdmc_http_interface/releases/tag/v1.8.4`
- WorldEdit 7.4.2：`https://modrinth.com/plugin/worldedit/version/7.4.2`

上游页面用于来源追溯；实际安装仍以固定版本和本手册验收哈希为准。
