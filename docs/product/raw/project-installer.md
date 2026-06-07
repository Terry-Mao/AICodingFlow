# 项目安装脚本

AICodingFlow 提供仓库级安装脚本 `install.sh`，用于把 workflow automation 和
Codex skills 同步到目标项目。它面向新项目接入和已有项目刷新 AICodingFlow 文件，
不负责初始化目标项目的 issue triage 配置，也不覆盖目标项目自己的仓库本地 companion
skills。

## 安装入口

安装脚本支持两种入口：

- 从 AICodingFlow 仓库 clone 后运行 `./install.sh --target /path/to/target-repo`。
- 通过远程一行命令下载脚本并执行；当脚本不是从有效 AICodingFlow 源 checkout 运行时，
  脚本会 clone AICodingFlow 源仓库后再运行真实安装流程，避免误把当前工作目录当作安装源。

`--target` 指定目标仓库目录，未提供时使用当前目录。目标路径必须已经是目录。脚本依赖
`bash`、`git` 和 `rsync`；远程一行安装还需要 `curl`。

## 同步范围

安装会同步以下 AICodingFlow 管理的目录到目标项目：

- `.agents/skills/`
- `.github/agents/`
- `.github/scripts/`
- `.github/aicodingflow-tests/`
- `.github/workflows/`

普通 skills 可以复制或更新。仓库本地 companion skills，也就是
`.agents/skills/*-repo/SKILL.md`，不会由安装脚本安装到目标项目；目标项目已有的 companion
skills 会保留。此类 companion guidance 应由维护者或对应 `update-*` self-improvement
流程在有证据时创建和更新。

`.github/agents`、`.github/scripts`、`.github/aicodingflow-tests` 和 `.github/workflows` 会按 AICodingFlow
源目录同步。目标项目 `.github` 下不属于这些同步目录的文件不会被删除，例如目标项目自己的
Dependabot 配置、`.github/tests` 或其他 GitHub 设置文件。

`.github/aicodingflow-tests` 是 AICodingFlow 上游托管的 workflow/script 测试目录，未来安装
或同步可能覆盖其中内容。目标项目自己的测试应放在项目原有测试结构中；如果测试属于
`.github` 相关逻辑，优先使用 `.github/tests/`，不要直接修改
`.github/aicodingflow-tests/`。

AICodingFlow 源仓库中的 `.github/workflows/ci.yml` 是参考最小 CI，不会由安装脚本同步到
目标项目。目标项目应保留自己的 CI 编排，并在 CI 成功路径中 dispatch 已安装的
`review-pr.yml` 来触发 AI PR Review；这样刷新 AICodingFlow managed workflows 时不会覆盖
目标项目自己的 CI 编排。

安装脚本自身的测试文件 `test_install_script.py` 不会安装到目标项目，因为它只验证
AICodingFlow 源仓库的安装脚本行为。

## 预览与后续初始化

使用 `--dry-run` 时，安装脚本只报告将要同步或跳过的内容，不写入目标项目文件，也不会创建
目标目录结构。

安装完成后，如果目标项目是首次接入 issue triage 自动化，可以手动运行
`$bootstrap-issue-config`。该 bootstrap 步骤会使用 GitHub CLI 分析目标仓库 labels、
issues 和 contributors，并可能创建 GitHub labels 或更新 `.github/CODEOWNERS`。它不是
安装脚本的一部分，也不需要定期运行。

来源：PR #148，Issue #146；PR #154，Issue #152；PR #158，Issue #157；PR #180；PR #204，Issue #202。
