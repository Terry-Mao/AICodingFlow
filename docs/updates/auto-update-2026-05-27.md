# 产品变更报告：2026-05-27

扫描窗口：`2026-05-27T00:00:00Z`（含）至 `2026-05-28T00:00:00Z`（不含）。

## 用户可见变更

- 修复 `install.sh` 在仓库级 agent 指令移动到根目录 `AGENTS.md` 后的源码树识别逻辑。通过管道或远程方式安装时，如果当前目录已经是有效 checkout，安装脚本会继续使用该源码树，避免递归 clone 并重新运行安装流程。来源：PR #180。

## Bug fixes

- `install.sh` 的源码树检测从检查 `.agents/AGENTS.md` 调整为检查根目录 `AGENTS.md`，与当前仓库结构保持一致。来源：PR #180。

## 行为变更

- Product change report automation 生成了 `2026-05-26 至 2026-05-27` 的时间序列报告，并在 ledger 中记录已覆盖的 PR，减少后续重复扫描同一批已报告变更的风险。来源：PR #177。

## 内部工程变更

- 本次报告扫描跳过了已记录在 `docs/updates/auto-update-2026-05-26-to-2026-05-27.md` 的 7 个 PR，仅处理该报告之后仍需记录的更新。来源：PR #177。

## 风险或待验证

- `install.sh` 的源码树识别现在依赖根目录 `AGENTS.md`、`.agents/skills` 和 `.github/workflows` 同时存在；后续如果仓库布局再次调整，需要同步更新安装检测条件。来源：PR #180。

## 可能需要同步的长期文档

- 如果长期安装文档说明了源码树检测条件，应同步更新为根目录 `AGENTS.md`，避免仍引用旧的 `.agents/AGENTS.md` 路径。来源：PR #180。

## Source references

- PR #177: https://github.com/Terry-Mao/AICodingFlow/pull/177
- PR #180: https://github.com/Terry-Mao/AICodingFlow/pull/180
