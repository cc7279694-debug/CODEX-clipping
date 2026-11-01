# 安装和测试记录

更新时间：2026-11-01。仅使用合成素材测试，未处理正式视频。

## Phase 3C-R1：PARTIAL / WAITING_USER_RUN（2026-11-01）

用户在普通 PowerShell 重试时遇到配置文件 UTF-8 / GBK 编码不匹配，发生在下载前。脚本现已修复；53 项离线测试及实际 venv 的 GBK 模式预检通过。真实下载仍 **NOT_RUN**，等待用户重试。详情见 [Phase 3C 报告](docs/evidence/PHASE3C-REPORT.md)。

用户报告普通 PowerShell 访问 PyPI 和 Hugging Face 两个官方元数据接口均为 HTTP 200；wheel 和权重是否可下载尚未验证。独立 Python 3.12.4 环境已用本地 `ensurepip` 准备 pip 24.0，未安装 ASR 包。现有 41 项测试及新增 9 项采集脚本离线模拟测试共 50 项通过；脚本可供用户在普通终端运行，候选依赖锁和许可证需后续复核。真实下载、模型加载、CPU int8、离线推理和中文识别均 **NOT_RUN**。详见 [Phase 3C 报告补验记录](docs/evidence/PHASE3C-REPORT.md) 和 [操作指南](docs/PHASE3C-R1-GUIDE.md)。Phase 2C 仍待人工检查。

## Phase 3C：BLOCKED，等待独立验收

远端基线已核对；本地独立 Python 3.12.4 环境仍缺 pip、ASR 依赖与模型。PyPI 请求超时；Hugging Face 元数据一次 HTTP 200，但后续请求与模型权重检查超时，不能认定可靠下载。普通 Windows 用户终端连接状态 **UNKNOWN**。本轮现有 41 项逻辑回归通过；真实模型加载、离线推理、中文识别及真人质量均 **NOT_RUN**。模型自填 manifest 不构成官方来源验证。最小用户终端对照、官方文件与离线导入条件见 [Phase 3C 报告](docs/evidence/PHASE3C-REPORT.md)。Phase 3B 整体仍为 PARTIAL；Phase 2C 仍为 PARTIAL / WAITING_USER_CHECK。

## 当前状态

- 用户已安装 OpenFilm 0.2.7 到工作区 `OpenFilm/`。安装包 SHA-256 与 GitHub 官方 0.2.7 发布资产一致；Windows 签名状态为 NotSigned，该哈希核对不等同于数字签名认证。
- OpenFilm 官方 Skill 位于 `vendor-skills/openfilm/SKILL.md`，固定提交 `b7673b585e3e9c3b434fe663e68619cc1984ae8b`，文件及 MIT 许可证哈希与官方一致。该目录尚未注册到 Codex 自动发现的位置；npm/GitHub 命令行网络受限，官方 `npx skills add openfilm/openfilm` 在线安装未完成。
- 桌面应用包含 OpenFilm CLI、FFmpeg、FFprobe 和 Chromium。通过工作区隔离环境直接调用本地 CLI，`--help` 和官方手册可正常输出；doctor 本地检查检测到 FFmpeg、FFprobe、Chromium 和 GPU。Phase 2 的 Studio 项目加载和 OpenFilm 导出尚未通过，见下文。
- 本地启动脚本 `openfilm-local.ps1` 已验证 `--version`、`--help` 与无参数手册输出；仅为进程设置隔离路径，不代表 Skill 已自动注册。
- OpenFilm 所带 FFmpeg、FFprobe 均为 9.0.2，未修改系统 PATH。Node.js 24.18.1 和 Python 3.12.4 可用；`py` 默认指向旧版 Python 2.7。
- ffmpeg-skill 本地副本位于 `vendor-skills/ffmpeg-skill/`，78 个文件的 Git blob 哈希与固定提交 `9bbb609922581582ab2d765f47ba05d9e08b27d4` 的官方树一致，尚未自动注册。`vendor-skills/ffmpeg-skill-doctor.json` 是早前未在 PATH 找到 FFmpeg 时的历史诊断。
- video-editing 仓库尚未完整安装；整体许可证未见明确说明。中文转录和英文翻译模型尚未安装或验证。

## 合成测试

使用桌面程序附带的 FFmpeg，`synthetic-test/runs/20261031-141624-577113/` 保存了测试结果和日志。

| 项目 | 实际结果 |
| --- | --- |
| 合成视频、静音检测、按预设剪辑点删除静音 | PASS；不代表自动生成剪辑点 |
| 竖屏裁切、缩放、基础调色、两路合成声音混合 | PASS；听感尚未检查 |
| 预先写好的中英文字幕烧录 | PASS；单帧检查字幕可见，不代表语音识别或翻译 |
| 360×640、H.264/AAC、4 秒、完整解码 | PASS |
| 中文语音识别、英文翻译、实际语音剪辑 | NOT_RUN |
| OpenFilm Studio、项目编辑和视频渲染 | Phase 2 后台启动及 look 已尝试，但本机回环连接受阻；项目编辑和渲染尚未完成，见下文 |
| 可修改项目 | 保存了 JSON 时间说明和测试脚本；不是剪映工程，JSON 没有驱动此次渲染 |

正式素材需要用户另行指定和授权。未上传视频、未购买服务，也未修改系统 PATH。

## OpenFilm Phase 2：PARTIAL / BLOCKED

已在 `AI-Video-Workspace/tests/openfilm-phase2/` 建立 OpenFilm `film.html`、三个 4 秒镜头页和本地 12 秒合成音轨，静态工程与本地引用检查通过。官方 `look` 由于本机回环连接被拒绝而失败，未生成检查图；Studio 后台曾启动，但工程未打开或修改，图形界面验收等待人工检查。OpenFilm `render` 与导出检查均 **NOT_RUN**，没有本阶段成片。详情见 [Phase 2 报告](docs/evidence/PHASE2-OPENFILM-REPORT.md)。

此前剪映 JianyingEditor Phase 1 的 BLOCKED 状态不变，参见 `AI-Video-Workspace/phase-1/PHASE1_REPORT.md`。

## OpenFilm Phase 2A：PARTIAL / BLOCKED

当前 Codex 执行环境中的独立 Python 回环监听成功，但连接同一随机端口被拒绝（Windows 10013）。这复现了与 OpenFilm 无关的本地连接受限现象；普通 Windows 用户会话尚未验证，具体策略来源、Chromium 和 OpenFilm 本身是否存在问题仍为 UNKNOWN。按门禁没有重复执行 `look`、Studio 编辑或 `render`。用户可按 `AI-Video-Workspace/tests/openfilm-phase2/MANUAL-LOOPBACK.md` 在普通 PowerShell 手动对照；结果不等同于 OpenFilm 验收。详情见 [Phase 2A 报告](docs/evidence/PHASE2A-CONNECTION-REPORT.md)。

## OpenFilm Phase 2B：PARTIAL / BLOCKED

用户报告已在 Windows OpenFilm Studio 打开原测试工程且第一镜头中文正常；本次截图直接显示第二镜头中文、1080×1920、12 秒、2 轨和 4 个片段，包含三段镜头及 `bed.wav` 音轨。截图帧率设置为 **60 fps**，不能作为 30 fps 输出的证据。已建立 `AI-Video-Workspace/tests/openfilm-phase2b/` 独立副本，六个文件的 SHA-256 与原工程一致；尚未修改副本。电脑操作接口连接超时，三个镜头的连续播放与动画、标题修改保存重开、OpenFilm 导出、FFprobe、解码及听感仍为 **NOT_RUN / WAITING_USER_CHECK**。Studio 加载子项已有用户证据，但 T04 整项未通过。操作步骤和证据边界见 [Phase 2 报告的 Phase 2B 记录](docs/evidence/PHASE2-OPENFILM-REPORT.md)。

### Phase 2B 最终验收补充：PARTIAL / BLOCKED

用户本轮明确报告已在 Windows OpenFilm Studio 成功打开并预览三镜头工程，反馈测试正常，记为 **USER_REPORTED_PASS**，不等于自动验证或已确认标题保存重开、听音和 30 fps。副本六个必要文件与原工程哈希仍一致，尚无标题修改证据；测试目录未发现完整导出 MP4，预览缓存不计为成片。当前执行环境的独立 Python 回环监听成功，但连接被拒绝（Windows 10013、errno 13），测试资源已关闭；本轮未运行官方 render，导出文件的 FFprobe、音轨及完整解码均为 **NOT_RUN**。标题修改保存重开与普通桌面导出为 **WAITING_USER_CHECK**。当前不能标记 ACCEPTED / FROZEN；详细记录见 [Phase 2 报告](docs/evidence/PHASE2-OPENFILM-REPORT.md)。

### Phase 2B 用户导出补充：PARTIAL / WAITING_USER_CHECK

用户随后提供的测试 MP4 已检查：12.000 秒、1080×1920、H.264、**60 fps**，AAC 48 kHz 双声道；FFprobe 和完整音视频解码通过。实际 60 fps 与阶段目标 30 fps 不一致。约 2、6、10 秒三帧的中文和镜头内容可见，未发现明显裁剪；音量检测有非零音频，但这不等于完整观看或试听通过。原工程与测试副本六个文件哈希仍相同，未发现标题保存改动；保存并重开仍待用户确认。单凭 MP4 不能独立确认导出操作方式或使用了哪个工程。严格 30 fps 目标尚未满足，不申请 ACCEPTED / FROZEN；详见 [Phase 2 报告](docs/evidence/PHASE2-OPENFILM-REPORT.md)。

## OpenFilm Phase 2C：PARTIAL / WAITING_USER_CHECK

用户已明确接受现有 **60 fps** 规格用于当前用途；此前 **30 fps 输出测试仍为 NOT_RUN**，历史结果保留。现有 12 秒竖屏导出的 FFprobe、完整解码和三个时间点抽帧证据继续有效。标题修改、保存与重开，以及完整人工试听，仍等待用户确认；音量检测不能代替试听。尚未申请 ACCEPTED / FROZEN。详情见 [Phase 2C 收尾记录](docs/evidence/PHASE2C-CLOSEOUT.md)。

## Phase 3A：方案准备

本阶段准备本地中文口播粗剪的技术方案、依赖与验收标准；本机中文语音识别、字幕时间戳误差、静音检测误删以及资源和耗时测试均为 **NOT_RUN**。不得将现有 ffmpeg-skill 仓库副本视为已自动注册。详情见 [Phase 3A 方案](docs/PHASE3A-PLAN.md)。

## Phase 3B：基础代码 READY_FOR_REVIEW，整体 PARTIAL

已实现只读元数据与静音分析、本地 ASR 预检和适配、SRT、保守建议、接受／拒绝／撤销的新 JSON 审核流程；不提供真实剪切。41 项标准库单元测试通过，仅证明相应逻辑与安全行为。已知静音纯音测试识别到预设 2–4 秒区间；真实阻塞流程写出四类分析文件，源 SHA-256 前后一致，ASR 未完成时字幕保持空且明确 NOT_RUN。

官方 PyPI 与 Hugging Face 有限请求均超时；独立 Python 3.12.4 环境已建，但尚无实际 ASR 包、模型、依赖 lock、模型 revision 或文件哈希。依赖准备 **BLOCKED**；中文 TTS 不可靠、中文冒烟、真实模型加载及离线推理、真人质量和实际模型性能均 **NOT_RUN**。首测候选为多语言 base、CPU int8、单进程有限线程。Phase 2C 的标题保存重开与完整试听仍为 WAITING_USER_CHECK，未标记 ACCEPTED。详情见 [Phase 3B 报告](docs/evidence/PHASE3B-REPORT.md)。
