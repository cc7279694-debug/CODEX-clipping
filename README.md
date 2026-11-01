# CODEX-clipping

个人 Windows AI 视频剪辑工作站的交接资料，供 ChatGPT、Codex 与本人继续讨论、规划和验证。主要用途是 AI、科技成长与生活 VLOG；风格为自然、有电影感、偶尔幽默。

## 先读这里

- [Phase 4A 报告](docs/evidence/PHASE4A-REPORT.md)：ClipPlan 与 OpenFilm 合成工程已通过 79 项本地测试及官方解析器静态检查；Studio 播放、声音、可编辑性待用户检查，实际帧率尚未确认。
- [Phase 4 主规划](docs/PHASE4-MASTER-PLAN.md)、[ClipPlan V1](docs/PHASE4A-CLIPPLAN-SCHEMA.md) 与 [验收标准](docs/PHASE4A-ACCEPTANCE.md)。
- Phase 3C-R1：官方文件核验与离线依赖安装、真实模型加载、一次自制中文语音转写及字幕冒烟通过；输出为繁体，简体转换未实现，原生进程完整离线隔离和真人质量待验证。详见 [Phase 3C 报告](docs/evidence/PHASE3C-REPORT.md)。
- Phase 3C-R1 用户终端预检的中文 Windows 编码错误已修复；53 项本地测试通过，真实下载、模型加载及中文识别仍未运行，详见 [补验报告](docs/evidence/PHASE3C-REPORT.md)。
- [Phase 3C-R1 下载准备和操作指南](docs/PHASE3C-R1-GUIDE.md)：用户报告普通 PowerShell 两项官方元数据访问 HTTP 200；下载脚本完成并通过模拟测试，真实 wheel、模型、加载、离线推理与中文识别仍 **NOT_RUN**，候选依赖锁及许可证待核查。
- [Phase 3C 中文 ASR 环境补验](docs/evidence/PHASE3C-REPORT.md)：**BLOCKED**；41 项逻辑回归通过，但官方依赖和模型尚未可靠取得，实际模型加载、离线推理及中文识别均 **NOT_RUN**；普通 Windows 用户终端连接状态待核对。
- [Phase 3B 开发与测试记录](docs/evidence/PHASE3B-REPORT.md)：基础代码 **DEV_COMPLETE / READY_FOR_REVIEW**，整体 **PARTIAL**；41 项逻辑和安全测试通过，官方依赖与模型下载 **BLOCKED**，中文 ASR、真实模型加载和真人质量测试 **NOT_RUN**。
- [Phase 3B 使用说明](docs/PHASE3B-USAGE.md)：独立本地 CLI 只输出字幕、低电平候选和可撤销审核 JSON，不执行剪切。语音保护证据不完整时不生成删除建议。

- [Phase 2C 收尾记录](docs/evidence/PHASE2C-CLOSEOUT.md)：**PARTIAL / WAITING_USER_CHECK**。用户已接受当前用途的 60 fps，30 fps 输出未测试；标题修改保存重开和完整试听待人工确认。
- [Phase 3A 中文口播粗剪技术方案](docs/PHASE3A-PLAN.md)：**READY_FOR_REVIEW（仅方案）**；本机语音识别、时间戳、误删和资源耗时均未测试。
- [OpenFilm Studio Phase 2 历史报告](docs/evidence/PHASE2-OPENFILM-REPORT.md)：保留早期回环连接阻塞、用户手动预览与后续 60 fps 导出检查证据。公开源码不包含音频，请先运行测试目录的 `generate_audio.py` 生成合成音频。

- [JianyingEditor Skill Phase 1 报告](AI-Video-Workspace/phase-1/PHASE1_REPORT.md)：当时状态为 **BLOCKED**。官方仓库访问返回 404，未安装 Skill，也未创建剪映草稿。
- [剪映接入环境与安全审查](AI-Video-Workspace/SETUP_REPORT.md) 和 [集中测试记录](AI-Video-Workspace/TEST_REPORT.md)：此前一轮状态为 **BLOCKED**。剪映 MCP 未安装或注册，没有生成可供剪映打开的测试草稿。
- [整体工作站状态](STATUS.md)：OpenFilm 的 Skill 已有本地副本，使用桌面版自带的工具做过 FFmpeg 合成测试；已有用户手动预览和导出文件技术检查；标题修改保存重开与完整试听仍待确认。
- [剪映创作风格](AI-Video-Workspace/STYLE.md) 与 [通用创作风格](STYLE.md)。
- [工作站使用说明](docs/WORKSTATION_README.md)、[合成测试说明](synthetic-test/README.md)。
- [合成时间线计划](AI-Video-Workspace/tests/synthetic-fixtures/edit-plan.json) 为计划文件，不是剪映草稿。

报告记录的是当时的检查结果，并非任何时刻都保持不变。后续继续工作时先读取最新文件并复查环境；不要把未运行、未知或计划中的项目说成已通过。为保护隐私，公开副本已将本机用户名、真实绝对路径替换为占位符，本地执行前应重新确认真实路径。

## 安全边界

仅使用合成测试素材进行环境验证，真实用户视频和已有剪映草稿须按用户后续授权处理；原文件只读，不覆盖或删除。未经授权不得上传素材、调用云端转写、购买服务或改动系统安全设置。首选剪映 MCP 的发布清理存在竞态风险，且本机版本兼容性未知，未通过安全与兼容门禁前不得向真实草稿目录发布。

仓库不包含 OpenFilm 桌面程序、Python 虚拟环境、视频、音频、个人草稿、密钥及生成的测试输出。脚本需要在有相应依赖的本地环境中重新配置；第三方项目可能有自己的网络或文件写入行为，运行前先阅读其文档和源码。

## 第三方 Skill

- [OpenFilm Skill](vendor-skills/openfilm/)：来自 [openfilm/openfilm](https://github.com/openfilm/openfilm)，核查提交 `b7673b585e3e9c3b434fe663e68619cc1984ae8b`，MIT，许可证随副本保留。该 Skill 是入口说明，不包含完整 OpenFilm 桌面应用或 CLI。
- [ffmpeg-skill](vendor-skills/ffmpeg-skill/)：来自 [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)，核查提交 `9bbb609922581582ab2d765f47ba05d9e08b27d4`，MIT，许可证随副本保留。自定义目录中的副本不代表已被 Codex 自动发现或激活。

向 GPT 提问时可提供仓库地址，并让它读取相关报告；能否直接读取 GitHub 取决于当次对话是否具有可用的网页或 GitHub 访问能力。仓库可访问并不代表 GPT 能直接访问你电脑上的本地程序、草稿或文件。
