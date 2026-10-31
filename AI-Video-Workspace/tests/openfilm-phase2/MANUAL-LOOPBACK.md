# 普通 Windows 会话：回环连接手动诊断

请在自己的 Windows 用户会话中打开普通 PowerShell 或 Windows 终端，无需管理员权限；不要在 Codex 的受限终端里运行。切换到本测试文件夹后运行：

```powershell
powershell -NoProfile -File .\diagnose-loopback.ps1
```

也可以在 Windows 文件资源管理器中进入 `AI-Video-Workspace/tests/openfilm-phase2/`，在地址栏输入 `powershell` 并回车，再粘贴上面的命令。执行完请将显示的文字结果发回对话。

脚本仅在 `127.0.0.1` 的随机端口创建一次临时监听和连接，并测试一个字节的往返；各连接及读取步骤限制为 3 秒，结束时关闭监听和连接。不会连接外部地址、修改系统设置、读取个人素材或写入文件，也不会启动 OpenFilm。

结果含义：

- 出现 `LISTEN_PASS`、`CONNECT_PASS`、`DATA_ROUNDTRIP_PASS`：普通 Windows 用户会话的这一次回环测试通过。若 Codex 环境中的同类测试被拒绝，可作为执行环境存在差异的证据；这**不代表 OpenFilm、Chromium、Studio 或导出已通过**。
- 出现 `LISTEN_PASS` 后 `FAILED`：监听成功，但本次连接、接受连接或数据往返失败；请保留完整输出供分析。
- 直接出现 `FAILED`，没有 `LISTEN_PASS`：监听未能建立；请保留完整输出供分析。

出现失败不等于已经确定原因。不要为了这项检查修改防火墙、代理、安全软件或其他系统设置。
