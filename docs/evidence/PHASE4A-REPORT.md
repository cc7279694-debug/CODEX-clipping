# Phase 4A：ClipPlan 与 OpenFilm 工程生成验证

日期：2026-11-01  
状态：**READY_FOR_REVIEW / READY_FOR_USER_CHECK**；限合成测试与静态结构，不代表真人素材剪辑或 Studio 可编辑性已验收。

## 基线和范围

开始时公开仓库 `main` 为 `e5518e3c27f48d3154cbbe992628ca8fc9c263e6`。本地工作目录没有 `.git`，无法执行普通 `git status/pull` 或声称工作区干净；相关已有文件与基线逐项比对，本地 README 与公开 README 的不同内容各自保留。仅使用本地 OpenFilm 0.2.7、其 FFmpeg / FFprobe 和独立 Python，不下载模型、不处理真人素材，不修改现有工程、ASR 内核或剪映草稿。

原候选合成素材仅 3 秒、360×640 和 6 秒音频，不满足本次规格。因此使用 [合成素材脚本](../../scripts/phase4a_generate_synthetic.py) 在新测试目录生成两段 7.5 秒、1080×1920、30 fps 的无声纯色视频和 15 秒合成测试音频；FFprobe 验证时长、尺寸及帧率通过。视频不包含真人口播，不能据此证明口播听感安全。

## 交付内容

- [Phase 4 主规划](../PHASE4-MASTER-PLAN.md)、[ClipPlan 约定](../PHASE4A-CLIPPLAN-SCHEMA.md)、[验收清单](../PHASE4A-ACCEPTANCE.md)。
- `src/codex_clipping/clipplan.py`：源哈希及 FFprobe、时间/轨道、审核与撤销、审核内容摘要绑定；决策仅生成计划，不改素材。
- `src/codex_clipping/openfilm_adapter.py`：需要显式授权输出根，在其下独占创建新工程、复制并核验素材，写入 `film.html`、`clipplan.json` 和 `source-map.json`。
- [合成工程生成脚本](../../scripts/phase4a_create_demo.py) 对本轮已生成的测试项目再次运行会拒绝现有路径；不能用它覆盖既有工程。
- 本机工程目录：`AI-Video-Workspace/tests/phase4a/projects/openfilm-project/`；原合成素材在 `AI-Video-Workspace/tests/phase4a/fixtures/`。重复生成一致性副本位于同级 `repeat-verification/`，均为独立新建文件，保留不删除。公开仓库不包含生成的音视频或本机测试产物。

## 实际时间线

| 轨道 | 输出时间（秒） | 源文件范围（秒） | 音频及审核 |
| --- | --- | --- | --- |
| 主画面 | 0–7.5 | 合成视频 A，0–7.5 | 无音轨；测试脚本模拟 accepted |
| 主画面 | 7.5–15 | 合成视频 B，0–7.5 | 无音轨；测试脚本模拟 accepted |
| 背景音 | 0–15 | 本地合成音频，0–15 | 独立音频轨；测试脚本模拟 accepted |

计划记录 1080×1920、30 fps；本机 0.2.7 文档与解析器的 `film.html` 格式未确认帧率字段，**未将 30 fps 声称为 Studio 工程实际设置**。用户需在 Studio 的画布和帧率设置核对；实际帧率为 NOT_RUN。审核事件由测试脚本针对合成样本建立，只验证状态流程，不代表用户本人已审核任何素材，也不是身份认证。

## 真实测试结果

| 项目 | 状态 | 范围 |
| --- | --- | --- |
| 既有 58 项与新增 21 项定向测试 | PASS | `python -m unittest discover -s tests -q`，79 项通过；新增 ClipPlan 13 项、adapter 8 项，部分以替身模拟 FFprobe 和文件，不代表 Studio 实测。 |
| 源范围、时长、同轨和跨主画面／人声重叠、ID、丢失路径及审核状态 | PASS（定向测试） | 审核摘要绑定具体内容，篡改后拒绝；非零或未知源起点沿用已有 FFprobe 安全拒绝。证据文本和 JSON 摘要不认证人或素材语义。 |
| 未授权／已有目标、目录穿越、源哈希 | PASS（定向及实际合成项目） | 显式授权根、目标直接新子目录；源和副本哈希比对，重复尝试已有工程被拒绝，原合成素材哈希不变。 |
| 重复生成一致性 | PASS（实际合成项目） | 以相同计划在另一新目录生成，两份 `film.html`、计划、映射及三份素材副本 SHA-256 一致；不覆盖首个工程。 |
| OpenFilm 正式文件格式 | PASS（静态解析） | 本机 0.2.7 官方 `film-doc.mjs` 的 `readFilmFile` 返回 `problems=[]`；解析出 1080×1920、2 轨、两个视频和一个音频，源时间及 at 与表格一致，引用文件存在。官方解析器自身不检查所有轨道重叠，另由 ClipPlan 校验。 |
| B-roll／人声保护 | PASS（规则与解析测试） | B-roll 限在主画面覆盖范围内、在上层且静音；主视频原声保持，主画面内嵌声音与独立 voice 重叠会拒绝。人工试听和真人语义保全 **NOT_RUN**。 |
| Studio 打开、预览、声音、保存并再编辑 | WAITING_USER_CHECK | 不在当前环境自动操作 Studio；静态解析不能证明真实加载、时间线播放、声音或可编辑性。 |
| 项目实际 30 fps、导出和画面质量 | NOT_RUN | 计划和素材标注 30 fps 不代表 Studio 工程设置生效；本阶段不做导出。 |

## 保护与当前限制

适配器只创建新工程，不编辑已有工程；实际剪辑以 OpenFilm 的 `#t=源起,源止` 和 `at=时间线起点` 进行引用，不重编码源视频。系统当前仅支持正常速度、音量 1、整毫秒导出；不匹配会受控失败。B-roll 音轨和跨轨规则属于保守结构限制，不保证人声可听清、语义没有丢失；正式素材需人工复核。受控审核历史可防无意改动后沿用确认，但 JSON 可被人为改写，不证明审核人身份。

路径限制和哈希检查用于避免常规覆盖和意外变化；它们不能防止有权限的其他进程在校验与写入之间恶意替换文件或目录，实际运行假设工作区无恶意并发修改。本轮未生成字幕、未翻译、未运行语义自动删剪、未导出视频。

## 用户 Studio 手动检查

1. 打开 OpenFilm Studio，打开工作站下 `AI-Video-Workspace/tests/phase4a/projects/openfilm-project/` 目录。选择工程时以 `film.html` 所在目录为准。
2. 检查是否显示竖屏画布、两条轨道、三段素材；顺序应是第一段纯色 0–7.5 秒、第二段不同纯色 7.5–15 秒，音频从头至尾。
3. 播放整段，确认画面切换与音频均正常。为验证保存重开，可打开同级的 `repeat-verification/` 合成副本，轻微调整一个片段并保存；关闭再打开此副本，确认修改保留。主测试工程和个人工程无需修改。
4. 查看 Studio 显示的帧率；若为 60 fps，请如实报告，不把计划中的 30 fps 当成已经生效。

若 Studio 无法加载、没有声音或不允许编辑，请记录实际现象。人工结果反馈后才可进行对应验收，不能将解析器结果直接登记为 Studio PASS。

Phase 2C 的标题保存重开与完整试听仍为 WAITING_USER_CHECK；Phase 3B / 3C 的真人质量、完整原生离线隔离仍未通过。阶段完成后等待 ChatGPT 独立审查，不进入 4B、4C 或 4D。
