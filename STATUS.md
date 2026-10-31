# 安装和测试记录

更新时间：2026-10-31。仅使用合成素材测试，未处理正式视频。

## 当前状态

- 用户已安装 OpenFilm 0.2.7 到工作区 `OpenFilm/`。安装包 SHA-256 与 GitHub 官方 0.2.7 发布资产一致；Windows 签名状态为 NotSigned，该哈希核对不等同于数字签名认证。
- OpenFilm 官方 Skill 位于 `vendor-skills/openfilm/SKILL.md`，固定提交 `b7673b585e3e9c3b434fe663e68619cc1984ae8b`，文件及 MIT 许可证哈希与官方一致。该目录尚未注册到 Codex 自动发现的位置；npm/GitHub 命令行网络受限，官方 `npx skills add openfilm/openfilm` 在线安装未完成。
- 桌面应用包含 OpenFilm CLI、FFmpeg、FFprobe 和 Chromium。通过工作区隔离环境直接调用本地 CLI，`--help` 和官方手册可正常输出；doctor 本地检查检测到 FFmpeg、FFprobe、Chromium 和 GPU，尚未验证 OpenFilm Studio 或 OpenFilm 导出。
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
| OpenFilm Studio、项目编辑和视频渲染 | NOT_RUN |
| 可修改项目 | 保存了 JSON 时间说明和测试脚本；不是剪映工程，JSON 没有驱动此次渲染 |

正式素材需要用户另行指定和授权。未上传视频、未购买服务，也未修改系统 PATH。
