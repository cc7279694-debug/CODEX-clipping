# Phase 2：OpenFilm Studio 实际剪辑验证

日期：2026-10-31  
状态：**PARTIAL / BLOCKED**。未达到 READY_FOR_USER_CHECK 或 ACCEPTED / FROZEN 的阶段门禁。

## 实际环境与安全范围

- OpenFilm 本地 CLI **0.2.7**；Node.js 24.18.1，桌面应用附带 FFmpeg 和 FFprobe 9.0.2。T01 在工作站根目录执行 `pwsh -NoProfile -File .\openfilm-local.ps1 --version`，退出码 0，输出 `0.2.7`。
- CLI 入口位于本地安装程序的 `OpenFilm/resources/app.asar.unpacked/node_modules/openfilm/bin/openfilm.mjs`；这里以工作站相对路径描述，不公开机器用户名或绝对路径。
- 原 `openfilm-local.ps1` 将部分状态目录设在工作站其他位置。为使本轮生成内容限于测试项目，T03 等使用测试项目中的 `openfilm-phase2.ps1` 调用同一份本地 CLI，并将项目状态、缓存及 `TEMP` / `TMP` 定向到测试目录；关闭自动更新和自动打开浏览器，示例索引使用本地文件。未调用 `npx openfilm@latest`、执行全局 npm 安装或重新下载程序。
- 测试只使用自制合成内容。未修改 OpenFilm 安装、剪映草稿或个人素材；未配置或调用付费云服务，未上传测试音视频。

## 测试工程

测试目录：`AI-Video-Workspace/tests/openfilm-phase2/`。实际 OpenFilm 结构由 `film.html` 定义 1080×1920 竖屏画布，包含三个独立 iframe 镜头及一条独立音频轨。静态检查确认引用可解析到项目内文件；这不是 Studio 加载或视频渲染通过的证明。

| 时间线 | 工程文件 | 内容 |
| --- | --- | --- |
| 0–4 秒 | `scenes/a.html` | “我不会编程” |
| 4–8 秒 | `scenes/b.html` | 模拟开发界面与“但是我开始用 AI 做 APP” |
| 8–12 秒 | `scenes/c.html` | 模拟手机界面与“这是我的第一个作品” |

主要文件：`film.html`、`scenes/a.html`、`scenes/b.html`、`scenes/c.html`、`scenes/common.css`、`generate_audio.py`、`assets/bed.wav`、`openfilm-phase2.ps1`、`examples-offline.json` 和 `validate_project.py`。`assets/bed.wav` 是脚本生成的 12 秒合成音频，仅保存在本地测试目录；公开仓库不含音频文件。浏览器 UI 可编辑性及镜头动画效果仍未验证。

## 测试结果

| 项目 | 状态 | 证据与边界 |
| --- | --- | --- |
| T01 CLI 运行 | PASS | 现有本地启动脚本返回 OpenFilm 0.2.7，退出码 0。 |
| T02 创建工程 | PASS（静态检查） | 使用本地 OpenFilm 工程格式编写 `film.html`、三个镜头页和音轨；`validate_project.py` 退出码 0，检查了画布、时间位置、本地引用、标题文本及 12 秒 WAV。未证明 OpenFilm 能加载或播放。 |
| T03 画面检查 | BLOCKED | 在测试目录设置隔离环境后执行 `& .\openfilm-phase2.ps1 look`，退出码 1。Studio 未连接，Playwright 访问本机地址时报 `net::ERR_NETWORK_ACCESS_DENIED`；没有生成关键帧或全片检查图。中文显示、裁切、构图、镜头绘制及重复绘制稳定性均未验证。 |
| T04 Studio 编辑 | BLOCKED / WAITING_USER_CHECK | 独立 Studio 后台服务曾启动，但本机回环 TCP 连接被拒绝（`EACCES`）；项目未打开，未修改或保存标题，未验证重开后保留。图形界面控制不可用。本地 `runtime/studio-api-evidence.json` 只记录后台启动与请求失败，不公开本机日志或会话密钥。 |
| T05 视频导出 | NOT_RUN | T03 所依赖的本机连接受阻，未执行 OpenFilm render，没有 MP4。不能声称输出为 1080×1920、30 fps、H.264 或包含音轨。 |
| T06 导出检查 | NOT_RUN | 没有 OpenFilm 导出文件，因此文件、时长、画幅、帧率、编码、完整解码、画面和音轨检查均未执行；主观观看与试听也未进行。 |

先前独立 FFmpeg 合成视频通过不代表本次 OpenFilm 画面检查或导出通过。不能使用纯 FFmpeg 成片替代本阶段的 OpenFilm render。

## 需要的人工检查与后续条件

在具备可用本机连接的环境中，用 OpenFilm Studio 打开上述**测试项目文件夹**，确认三个镜头及时间线，查看预览画面和中文文字；修改其中一个标题、保存，关闭并重新打开同一测试项目，确认修改保留。若 Studio 同样无法加载或连接，应记录实际错误，不操作其他项目。

在本机连接问题解决并完成 T03 后，还需使用官方 OpenFilm render 导出到测试目录内的唯一新文件，执行 FFprobe 和完整解码检查；完整观看和试听需人工单列。只有实际工程加载与画面检查、OpenFilm 渲染及导出技术检查通过，且用户确认 Studio 编辑保存后，才能进入 ACCEPTED / FROZEN。

本报告和必要工程文本可以公开；生成的视频、音频、会话密钥以及本机日志不上传。当前尚无本阶段 MP4 供人工检查。

## Phase 2B：人工加载证据与定向补验

状态：**PARTIAL / BLOCKED**。以下是后续新增证据，不修改上述 Phase 2 历史结果。

用户报告已在 Windows 的 OpenFilm Studio 中成功打开 `openfilm-phase2`，并称第一镜头中文画面正常。用户提供的当前截图可直接确认：Studio 已打开该工程；画布为 **1080×1920、9:16**，时间线时长 **12 秒**，检查器显示 **2 条轨道、4 个片段**；时间线上有 `a`、`b`、`c` 三段各 4 秒的镜头及 `bed.wav` 的 12 秒音轨。

该截图预览的是约 7 秒处的**第二镜头 B**，中文“但是我开始用 AI 做 APP”可见。第一镜头中文正常属于用户报告，本张截图未直接展示。截图的帧率设置栏显示 **60 fps**；用户文字提到 30 fps，两者不一致，因此该图不证明 30 fps，最终输出帧率仍需以导出文件的 FFprobe 结果为准。

Studio 项目加载子项有人工证据，但整项 T04 **未通过**：此次没有证明三个镜头的实际播放和动画、标题修改、保存及重开后保留。执行环境的电脑操作接口 `cua.getState` 连接超时，本轮无法继续通过该接口观察或操作界面；没有进行新的本机网络重试。

已在 `AI-Video-Workspace/tests/openfilm-phase2b/` 建立独立测试副本，六个工程文件的 SHA-256 与复制前原件逐一一致；没有复制运行状态或日志，也没有编辑副本。其余实际状态如下：

| 项目 | Phase 2B 状态 | 说明 |
| --- | --- | --- |
| Windows Studio 加载原测试工程 | PASS（人工提供的加载证据） | 用户报告成功打开，截图显示工程、轨道和第二镜头预览；不代表编辑或渲染通过。 |
| 三镜头播放、动画、中文及音频 | WAITING_USER_CHECK | 本截图仅展示 B 的一个静态画面；连续播放、A 和 C 的画面与听感未由本轮独立验证。 |
| 修改副本标题、保存并重新打开 | NOT_RUN / WAITING_USER_CHECK | 副本已建立但未修改；原工程未更改。 |
| 官方 OpenFilm `render` 导出 MP4 | NOT_RUN / WAITING_USER_CHECK | 没有运行 render，未生成本轮 MP4；帧率和音轨不能预先登记为通过。 |
| FFprobe、完整解码与人工试听 | NOT_RUN | 没有本轮导出文件可检查。 |

### 待用户在副本中手动验证

1. 在 OpenFilm 打开 `AI-Video-Workspace/tests/openfilm-phase2b/` 测试工程副本；保留原 `openfilm-phase2/` 不变。
2. 播放 0–12 秒，分别检查 A、B、C 的文字、画面和动画，并确认是否听到音频。
3. 在副本中将 C 镜头标题改一个容易辨认的小变化，保存后关闭并重新打开副本，确认修改仍保留。记录实际观察结果。
4. 如可从 OpenFilm 导出，请明确设置 **30 fps**，输出到副本目录内一个此前不存在的新 MP4 文件；不要覆盖已有文件或上传媒体。记下实际路径与导出结果，交由 Codex 后续执行 FFprobe 与完整解码检查。界面名称以你当前版本实际显示为准。

用户截图和报告不证明渲染或完整编辑验收；当前总体仍为 PARTIAL / BLOCKED，不能标记 ACCEPTED / FROZEN。本轮没有修改原项目源码、个人素材或系统安全配置，没有上传媒体。

## Phase 2B：最终验收补充记录

状态：**PARTIAL / BLOCKED**；以下为本轮新增证据，保留上述所有历史记录。

- **USER_REPORTED_PASS — Studio 加载与预览**：用户本轮确认已在 Windows OpenFilm Studio 成功打开并预览三镜头测试工程，反馈测试正常。这是用户人工报告，不是 Codex 自动验证；该报告没有逐项确认标题修改、保存与重开、听音或 30 fps。此前截图直接展示第二镜头，设置栏显示 60 fps；导出帧率仍需检查实际文件。
- **WAITING_USER_CHECK — 修改标题并保存重开**：只读核对 `AI-Video-Workspace/tests/openfilm-phase2b/` 副本的六个必要工程文件，其哈希仍与原工程一致，未发现标题改动证据；这不代表软件无法编辑，也不能证明保存或重开是否成功。
- **NOT_RUN — OpenFilm 正式导出**：对限定测试目录的只读检查未发现完整 12 秒导出 MP4。预览缓存中的片段不等于正式成片；本轮没有运行官方 `render`。
- **NOT_RUN — 成片技术检查**：没有正式导出文件，故其 FFprobe 时长、分辨率、帧率、编码、音轨及完整解码均未验证；成片的人工观看和试听也未验证。
- **BLOCKED — 当前执行环境本机连接**：本轮独立 Python 最小回环检查中，监听成功，但同进程连接被拒绝，返回 Windows 10013、errno 13；测试 socket 已关闭。未重复尝试，不据此推断具体策略来源或 OpenFilm 产品故障。

### 待完成的人工作业

在普通 Windows 桌面会话中，用 OpenFilm Studio 打开 `AI-Video-Workspace/tests/openfilm-phase2b/` 副本，修改一个标题，保存、关闭并重新打开以确认修改保留。然后在 Studio 中显式选择 30 fps，导出到副本目录内此前不存在的新文件名，避免覆盖其他文件；提供实际导出文件位置及人工检查结果后，由 Codex 对该文件进行只读 FFprobe 与完整解码检查。用户操作及导出结果未到达前，不得标记保存重开或导出通过。

本轮未修改系统网络安全设置、原工程或个人素材；未上传媒体。只有标题修改保存重开、实际导出、技术检查及相应人工验收均通过，才可申请 **ACCEPTED / FROZEN**。

### Phase 2B 导出文件补充检查

状态：**PARTIAL / WAITING_USER_CHECK**。用户在本机指定的导出目录提供了一个测试 MP4；以下记录只针对该文件。单凭文件内容无法独立证明具体导出操作方式，也不能确认导出使用的是原工程还是测试副本。原工程的 Studio 加载和预览为此前用户确认，历史记录保留。

| 检查 | 结果 | 证据与范围 |
| --- | --- | --- |
| 格式与时长 | PASS | FFprobe 退出码 0：12.000 秒、1080×1920、H.264 视频；文件大小 6,642,844 字节。 |
| 帧率 | 不符合目标 | 实测 **60 fps**，与本阶段目标 **30 fps** 不一致；不能登记 30 fps 通过。 |
| 音轨与完整解码 | PASS | AAC、48 kHz、双声道、12 秒；FFmpeg `-xerror` 完整音视频解码退出码 0。 |
| 音量检测 | PASS（非静音） | `volumedetect` 显示平均约 -34.8 dB、峰值约 -24.7 dB；不能代替人的完整试听和听感判断。 |
| 三镜头抽帧 | PASS（抽样） | 在约 2、6、10 秒分别目视三张关键帧，中文标题与三个镜头内容正确，未发现明显裁剪；第三镜头右下角页码“03 — 03”完整。此项只证明三个抽样时刻，不代表全片动画或连续画面均已审核。 |
| 标题修改、保存与重开 | WAITING_USER_CHECK | 当前只读核对中，原工程和 Phase 2B 副本的六个必要文件 SHA-256 仍逐一相同，未发现保存后的标题改动证据；不能据此推断用户是否做过临时修改，重开结果仍需用户确认。 |
| 完整观看与试听 | WAITING_USER_CHECK | 完整画面、动画和主观听感仍需人工确认。 |

测试文件 SHA-256：`8c67adbffeb1c31a24f898e003156b7940742989691308145b20f36220937f8b`。文件名与真实绝对路径不在公开报告中记录，测试视频、抽帧、音频和本机日志不上传。

后续需确认标题修改后保存并重新打开是否保留；对于 30 fps 与当前 60 fps 的差异，是否重新按目标导出由用户决定。如需严格完成原 30 fps 目标，还须获得新的 30 fps 输出并重新验证。当前不满足阶段全部门禁，不申请 **ACCEPTED / FROZEN**。
