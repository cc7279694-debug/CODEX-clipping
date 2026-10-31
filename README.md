# CODEX-clipping

个人 Windows AI 视频剪辑工作站的交接资料，供 ChatGPT、Codex 与本人继续讨论、规划和验证。主要用途是 AI、科技成长与生活 VLOG；风格为自然、有电影感、偶尔幽默。

## 先读这里

- [剪映接入环境与安全审查](AI-Video-Workspace/SETUP_REPORT.md) 和 [集中测试记录](AI-Video-Workspace/TEST_REPORT.md)：最近一轮状态为 **BLOCKED**。剪映 MCP 未安装或注册，没有生成可供剪映打开的测试草稿。
- [整体工作站状态](STATUS.md)：OpenFilm 的 Skill 已有本地副本，使用桌面版自带的工具做过 FFmpeg 合成测试；OpenFilm 自身的项目编辑、导出仍未验证。
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
