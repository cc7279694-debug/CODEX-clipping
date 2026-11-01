# Phase 4J：国内剪映工程桥接报告

日期：2026-11-01  
总体：**PARTIAL / 原生桥接 BLOCKED**。ClipPlan 的安全人工导入回退可供审查；没有生成或验证可被剪映 8.9 打开的原生草稿。

## 基线与环境

开始时远端 `main` 为 `301010bd35d4b03629ceb61390a7cf78bece474f`，与指定基线一致。本地工作目录没有 Git 元数据，不能运行标准 `git status/pull` 或声称干净；逐项核对现有文件并保留本地和远端各自不同的 README。此前本机及用户提供剪映版本为 8.9.0.13361，本轮未能在先前记录的路径和常见安装信息中重新核验，当前实际版本 UNKNOWN，不推断已卸载。未枚举、读取或修改个人草稿。

三项候选的固定提交、许可证、依赖、版本证据及覆盖/删除/加密风险见 [调研文档](../PHASE4J-JIANYING-BRIDGE.md)。`pyJianYingDraft` 0.3.1 被列为**后续隔离试验候选**；本轮没有安装或运行该库。官方 PyPI wheel-only 下载返回无匹配，官方页面则列有 wheel；随后一次官方链请求超时但异常未记录具体阶段，原因 UNKNOWN。没有使用未知镜像、绕过版本保护、调用加解密 DLL或降级剪映。

## 隔离合成素材与结果

复用 Phase 4A 测试源：A、B 各 7.5 秒、1080×1920、30 fps；音频 15 秒。使用已审核的合成 ClipPlan、已有 FFprobe，实际创建 `AI-Video-Workspace/tests/phase4j/manual-outputs/import-pack/`，内容为未裁切的 3 份素材副本、`timeline.json`、`clipplan.json` 和中文 README。工程外部未写入；没有创建原生草稿文件。

| 测试 | 状态 | 实际证据及边界 |
| --- | --- | --- |
| ClipPlan 所需字段与源映射 | PASS | 既有 V1 包含审核、哈希、源范围、目标起点、轨道和顺序；未修改既有 OpenFilm 适配器。 |
| 人工包两段素材与时间顺序 | PASS（结构） | 视频 A 源 0–7.5 秒 → 时间线 0 秒，B 源 0–7.5 秒 → 7.5 秒，总时长 15 秒；素材是原视频副本，不是预先分段的剪映工程。 |
| 独立音频映射 | PASS（结构） | 音频 0–15 秒映射至 0 秒独立计划轨；人工导入和播放均未验证。 |
| 路径、哈希、重复写入 | PASS | 三份副本哈希与来源匹配，源素材前后哈希不变，重复目标明确拒绝。 |
| 单元测试 | PASS | 原有 79 项和 6 项人工导入包定向测试，`python -m unittest discover -s tests -q` 共 85 项通过；部分使用模拟 FFprobe，另用真实合成素材完成上述集成检查。 |
| 原生隔离候选草稿生成及结构检查 | NOT_RUN | 候选库及依赖未取得，未自行臆造或运行第三方代码；不能以人工包代替草稿。 |
| 剪映 8.9 首页识别、打开、编辑、音频和保存重开 | BLOCKED / NOT_RUN | 无已验证的原生草稿和真实目录授权；尚无用户人工验收。不能标记兼容性 PASS。 |
| 真实草稿目录与索引写入 | NOT_RUN（未授权） | 未访问现有草稿、未修改索引或加密文件，也未进行 GUI 自动化和自动导出。 |

本次完整回归从工作区根目录执行：

```powershell
$env:PYTHONPATH = 'src'
& .\AI-Video-Workspace\phase3b\.venv\Scripts\python.exe -m unittest discover -s tests -q
```

实际合成包集成通过 `create_manual_import_pack(plan, source_root, output_root/'import-pack', ffprobe, allowed_output_root=output_root)` 执行；函数调用既有 ClipPlan 的 FFprobe 检查（`-show_streams -show_format -of json`），再逐文件核对哈希。对已有目标重复调用抛出 `FileExistsError`；没有重新覆盖或删除该包。

人工包只支持一条连续主画面与一条完整音乐轨，且素材副本需要用户自己在剪映中导入、裁剪和排列；不表示已经有可独立编辑的自动草稿。测试计划中的 accepted 来源于合成测试脚本，不代表用户完成真实素材审查。错误目录、未审计划、哈希变化或重名会拒绝；路径检查不保证抵御恶意并发替换。

## 下一步与人工授权门禁

如果要继续兼容性对照，请用户在剪映中新建并保存唯一命名的空白测试工程，关闭后只对该测试工程的明确目录或用户放在工作区的副本授予**只读**权限；最小操作见 [桥接文档](../PHASE4J-JIANYING-BRIDGE.md)。先检查文件格式和可能的加密标识，不调用 DLL 解密、不修改原目录，不动其他工程及全局索引。任何后续导入均应先说明方案，是否执行由用户决定。

Phase 4A 的 Studio 人工检查、Phase 2C 和 Phase 3 的既有未完成事项保持原有状态。本阶段没有正式视频剪辑，停止等待独立验收。
