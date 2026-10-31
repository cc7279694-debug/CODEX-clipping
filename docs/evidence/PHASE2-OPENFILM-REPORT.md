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
