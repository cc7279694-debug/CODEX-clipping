# Phase 2A：OpenFilm 回环连接诊断与定向补验

日期：2026-10-31  
状态：**PARTIAL / BLOCKED**；基于 Phase 2 提交 `801160bef5ab35732de010e7b4e2459144c02e81`。本报告保留并补充此前 Phase 2 记录，不替代该记录。

## 证据

1. 只读复核 Phase 2 报告、隔离启动脚本与本地失败记录。已有 Studio 证据记录服务启动初始化成功及请求 `fetch failed`，没有证明项目打开；已有 `look` 日志记录 `net::ERR_NETWORK_ACCESS_DENIED`。此前独立回环探测的 EACCES 不在上述 Studio JSON 或 `look` 日志中，不能将它们混作同一条日志证据。
2. 本次在 Codex 当前执行环境中进行一次独立 Python TCP 最小测试：只绑定 `127.0.0.1`、由系统分配端口，监听成功；随后连接同一地址失败，产生 `PermissionError`，`errno 13`、Windows `WinError 10013`，进程退出码 1。测试不依赖 OpenFilm 或 Chromium。
3. `finally` 已关闭测试 socket；事后按该次端口检查，未发现残留监听。未重复连接、未开启公网监听。
4. 普通 Windows 用户会话的对照结果 **NOT_RUN**，需要用户在普通 PowerShell 中手动执行 `AI-Video-Workspace/tests/openfilm-phase2/diagnose-loopback.ps1`。使用说明见同目录 `MANUAL-LOOPBACK.md`；脚本仅进行单次本机回环测试，不修改系统设置，不写文件，不运行 OpenFilm。

## 根因判断

| 方向 | 当前结论 |
| --- | --- |
| A. Codex 沙箱或执行环境限制 | 当前执行环境中，独立于 OpenFilm 的回环 TCP 连接被拒绝，**受限事实已复现**；尚不能仅凭此证明具体是哪一层策略导致。 |
| B. OpenFilm 服务监听/端口 | 上一轮隔离 Studio 启动时监听初始化成功；未成功收到项目请求，完整服务链路 **UNKNOWN**。此次 Python 独立复测不证明 Studio 服务正常。 |
| C. Chromium / Playwright 限制 | 旧 `look` 出现 `ERR_NETWORK_ACCESS_DENIED`；单独归因于 Chromium 或 Playwright 的证据不足，**UNKNOWN**。 |
| D. OpenFilm 0.2.7 本身 | 现有结果不足以认定该版本有或没有产品故障，**UNKNOWN**。 |

若普通 Windows 用户会话中监听、连接和数据传递均通过，而 Codex 环境仍失败，则支持当前执行环境受限；这并不等于 OpenFilm、Chromium 或渲染通过。若普通会话同样失败，则需另外调查，不能直接认定防火墙、杀毒软件、代理或 UAC 是原因。

## 定向补验结果

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| 当前执行环境最小监听 | PASS | 独立 Python TCP listener 成功绑定并监听本机随机端口。 |
| 当前执行环境最小连接 | BLOCKED | 同一进程的本机连接被拒绝；Windows 10013。 |
| 普通 Windows 会话对照 | WAITING_USER_CHECK | 尚未由用户手动执行；无对照证据。 |
| OpenFilm `look` / 三镜头画面、中文、构图、动画 | NOT_RUN | 本次前置连接条件不满足；保留 Phase 2 的失败记录，不重复尝试。 |
| Studio 打开、用户修改标题、保存、重开 | NOT_RUN / WAITING_USER_CHECK | 尚无可用连接及用户实际操作。 |
| 官方 `render`、FFprobe、完整解码 | NOT_RUN | 本次连接前置条件未满足，没有产生新的 MP4。 |
| 用户观看与试听 | NOT_RUN | 本次没有新的 OpenFilm 成片。 |

没有修改或删除 Phase 2 失败证据、OpenFilm 软件安装、剪映草稿或个人素材；未修改防火墙、杀毒、代理、UAC 或系统网络安全策略。仅在用户提供普通 Windows 会话结果且连接条件满足后，才可进一步评估官方 `look`、Studio 和 `render` 的定向补验；不能因本次最小测试结果而标记 Phase 2 已通过。
