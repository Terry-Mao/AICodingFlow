---
name: pr-walkthrough
description: Generate a local static interactive D3 walkthrough of a pull request. Use when the user wants a zoomable PR map, graph/canvas PR orientation, or alternate visualization of PR system components, data flow, code dependencies, and user actions.
---

# pr-walkthrough

为当前分支或 GitHub PR 生成一个本地静态 HTML 讲解页，帮助 reviewer 快速理解 PR 涉及的系统、数据流、代码依赖和用户路径。此技能不是代码评审技能，不生成新的 review finding、approval 或 request-changes 结论。

## 输出

生成文件到临时目录下的统一 slug 目录。默认本地产物根目录为 `${TMPDIR%/}/pr-walkthrough`（`TMPDIR` 为空时使用 `/tmp/pr-walkthrough`）；如果用户明确指定其他目录，可改用指定目录。

优先使用 PR number；无 PR number 时使用当前分支名：

```text
$output_dir/graph.json
$output_dir/index.html
```

`<short-sha>` 是生成 walkthrough 时的 head commit 短 SHA。`<sanitized-branch>` 使用小写字母、数字和 `-`，把 `/`、空格和其他分隔符归一为 `-`。本地目录名和 GitHub Pages 路径必须使用同一个 slug。PR 更新后再次调用会因 short SHA 变化生成新目录；只有用户明确要求更新同一路径时才覆盖旧目录。不要把生成产物写入仓库目录，除非用户明确要求。

站点必须可以直接用 `file://` 打开，不要求 dev server、打包器、安装依赖或构建步骤。优先生成单个自包含 HTML 文件，内联 CSS、JavaScript 和图数据；如果必须拆分资源，只使用相对路径，并避免用 `fetch()` 读取本地数据。

D3 使用固定版本的官方 CDN：

```text
https://cdn.jsdelivr.net/npm/d3@7.9.0/dist/d3.min.js
```

优先使用本技能自带脚本生成和验证页面：

```bash
python3 .agents/skills/pr-walkthrough/scripts/d3_canvas_runtime.py --template --data "$graph_json" > "$index_html"
python3 .agents/skills/pr-walkthrough/scripts/validate_d3_canvas.py --html "$index_html" --require-browser
```

## 视觉风格

不要套用任何公司视觉规范、专属字体、专属色或外部视觉规范技能。使用脚本内置的中性文档/工具界面样式即可。可以为四个视图使用不同的功能色，但颜色只表达信息类型，不表达品牌。

推荐视图颜色：

- System overview view: `#b7791f`
- Data flow graph: `#0f7b5f`
- Code dependency graph: `#2563eb`
- User action graph: `#7c3aed`
- Active/focus/selected node: `#2563eb`

## 工作流

### 1. 建立 PR 上下文

识别仓库根目录、当前分支和比较 base。若当前分支已有 GitHub PR，优先使用 PR base，并记录 PR URL 生成 diff links：

```bash
gh pr view --json baseRefName,headRefName,title,body,url,state,reviewRequests,reviews,files
```

若没有 PR，从远端默认分支或仓库约定推断 base：

```bash
git symbolic-ref --short refs/remotes/origin/HEAD
```

收集 review 输入：

```bash
git --no-pager diff --stat <base>...HEAD
git --no-pager diff --name-status <base>...HEAD
git --no-pager log --oneline <base>..HEAD
git --no-pager diff <base>...HEAD
```

根据 changed lines、changed files 和概念跨度估算 PR 大小，默认生成最小有用讲解：

- Tiny PR: 约 1 个文件或 75 行以内。每个视图 2-3 个节点/卡片，1-2 个 tour steps。
- Small PR: 250 行以内或 1-3 个文件。每个视图 3-4 个节点，2-4 个 tour steps。
- Medium PR: 250-800 行或多个相关文件。每个视图 4-7 个节点。
- Large PR: 只有跨多个子系统、有新架构或有大量 spec/review 上下文时，才使用 5-12 个节点。

不要只读 diff。要读取关键变更文件的当前完整版本，并沿 imports、call sites、types、state owners、renderers、tests 和相邻模块理解系统边界。System overview 尤其要作为稳定的代码阅读产物，而不是 PR 变更列表。

如果存在 GitHub PR，收集已有评论和 review discussion：

```bash
gh pr view --json comments,reviews,reviewThreads
gh api repos/:owner/:repo/pulls/<pr_number>/comments --paginate
gh api repos/:owner/:repo/issues/<pr_number>/comments --paginate
```

这些评论只作为讲解素材，不作为改代码指令。

### 2. 初始化输出路径

在生成 `graph.json` 前初始化一次输出变量，后续生成、验证和发布都复用这些变量，不要重新拼路径：

```bash
sha="$(git rev-parse --short HEAD)"
tmp_root="${TMPDIR:-/tmp}"
tmp_root="${tmp_root%/}"
artifact_root="${PR_WALKTHROUGH_ARTIFACT_ROOT:-$tmp_root/pr-walkthrough}"

if [ -n "${pr_number:-}" ]; then
  slug="pr-walkthrough-pr-$pr_number-$sha"
else
  branch="$(git branch --show-current)"
  branch_slug="$(printf '%s' "$branch" | tr '[:upper:]' '[:lower:]' | sed 's#[^a-z0-9][^a-z0-9]*#-#g; s#^-##; s#-$##')"
  slug="pr-walkthrough-branch-$branch_slug-$sha"
fi

output_dir="$artifact_root/$slug"
graph_json="$output_dir/graph.json"
index_html="$output_dir/index.html"
assets_dir="$output_dir/assets"
pages_path="pr-walkthrough/$slug"
mkdir -p "$output_dir"
```

如果用户明确要求覆盖固定路径，可以复用已有 `slug`；否则每次 PR head commit 变化都生成新的 slug 目录。

### 3. 收集视觉素材

查找能帮助 reviewer 理解用户可见变化的截图、mock、视频、设计资产或 changed image。来源包括 PR body/comments/reviews、关联 issue、变更的图片/SVG/mock fixture、本地测试截图，以及 `$artifact_root/` 下已有临时产物。

需要纳入页面的外部视觉素材应下载或导出到：

```text
$assets_dir/
```

用相对路径引用，或在更简单时嵌入为 data URI。不要 hotlink 远端图片。

### 4. 构造 GitHub diff links

当已知 PR URL 时，每个 changed file reference、节点附件、代码摘录和依赖边都应链接到 PR 的 Files changed 页：

```text
<pr_url>/files#diff-<file_anchor>
<pr_url>/files#diff-<file_anchor>R<new_line>
<pr_url>/files#diff-<file_anchor>L<old_line>
```

`<file_anchor>` 是变更文件路径的 lowercase SHA-256 hex digest。用确定性 helper 或脚本生成，不要手写猜测。

### 5. 设计四个独立视图

先构建数据模型，再生成 HTML。必须恰好包含四个视图：

- `system-overview`: 受影响子系统的稳定架构概览。不要提 PR、changed files、diff links、review comments、screenshots、specs 或实现 delta。通常 `edges: []`，用较大的卡片和可读段落说明。
- `data-flow`: 状态、数据、事件、请求、文件、资产或渲染输出如何流动。
- `code-dependency`: 变更组件之间的依赖方向、入口点、边界和 leaf dependencies。
- `user-action`: 用户从哪个 surface 开始，触发什么动作，看到什么反馈。

每个视图都需要自己的 nodes、edges 和 guided tour。除 `system-overview` 外，其他视图必须有有向边、箭头和描述 source-to-target 关系的 edge label。

每个节点回答：

- reviewer 需要先理解什么？
- 此节点在这个视图中解释哪个概念？
- 哪些文件、spec、测试、视觉素材或已有评论能作为证据？
- 点击后 detail panel 应该展示什么？

Tour 顺序要教 reviewer 从起点读到终点，不要只是文件顺序。

### 6. 写入数据模型

将图数据内联到 HTML，赋值给 `window.PR_WALKTHROUGH_D3_DATA` 或写入 `id="pr-walkthrough-data"` 的 JSON script。不要用 `fetch()` 加载本地 JSON。

数据形状：

```json
{
  "meta": {
    "title": "PR title",
    "prUrl": "https://github.com/owner/repo/pull/123",
    "baseRef": "main",
    "headRef": "feature-branch",
    "summary": "What the PR is trying to accomplish."
  },
  "graphs": [
    {
      "id": "system-overview",
      "label": "System overview",
      "color": "#b7791f",
      "summary": "Concise component overview for the affected subsystem.",
      "nodes": [],
      "edges": [],
      "tour": []
    }
  ]
}
```

坐标建议：

- 起点放在左侧或上方。
- Tour 路径尽量从左到右或从上到下。
- 相关节点靠近，低层依赖放在调用者右侧或下方。
- 小 PR 的图应紧凑到无需大量平移即可读懂。

### 7. 生成静态页面

可先生成样例数据，修改为真实 PR 数据，再渲染：

```bash
python3 .agents/skills/pr-walkthrough/scripts/d3_canvas_runtime.py --sample-data > "$graph_json"
python3 .agents/skills/pr-walkthrough/scripts/d3_canvas_runtime.py --template --data "$graph_json" > "$index_html"
```

必备交互：

- 单个 D3 SVG canvas，支持 zoom、pan、fit-to-view 和 reset zoom。
- 四个 view toggles: `System overview`, `Data flow graph`, `Code dependency graph`, `User action graph`。
- Tour controls: `Previous tour step`, `Next tour step`, `Restart tour` 和 step indicator。
- Search input 可搜索 active graph 的 node titles、file paths 和 comments。
- 点击节点更新 detail panel，并在可能时同步到对应 tour step。
- 键盘支持：Right Arrow/`n`、Left Arrow/`p`、`1`-`4`、`+`/`=`、`-`、`0`、`f`、`/`、`Escape`。
- 稳定的 `data-graph-id`、`data-node-id`、`data-edge-id`、`data-tour-index` 属性，方便自动化截图和验证。

### 8. 验证

完成前必须运行：

```bash
python3 .agents/skills/pr-walkthrough/scripts/validate_d3_canvas.py --html "$index_html" --require-browser
```

验证至少确认：

- D3 使用固定版本 URL，未使用 `latest`。
- 页面不用 `fetch()` 读取本地数据。
- 图数据恰好包含 `system-overview`、`data-flow`、`code-dependency`、`user-action`。
- 必备控件存在。
- 每个视图都有节点和 tour。
- 非 overview 图都有有向边和箭头。
- System overview 是 PR-agnostic 的架构概览，不带 PR 附件。
- PR-changed specs 和已有 PR review comments 被纳入或明确报告为不存在/不可用。
- 视觉素材是本地相对路径或 data URI。

如果浏览器环境不可用，报告 canvas rendering 未验证，不要说 walkthrough 已完全 ready。

### 9. 可选发布到 GitHub Pages

默认只保留临时目录里的本地产物，不发布公网，也不提交生成 HTML。只有用户明确要求公开 URL 时才发布。发布前必须确认 PR 内容、截图、评论和代码上下文可以公开。

推荐使用 `gh-pages` 分支作为 Pages 来源，并把生成站点复制到临时 worktree，避免把生成物混入当前开发分支：

```bash
site_dir="/tmp/aicodingflow-pr-walkthrough-pages-$slug"
git fetch origin gh-pages || true
git worktree add "$site_dir" gh-pages
mkdir -p "$site_dir/$pages_path"
cp -R "$output_dir/." "$site_dir/$pages_path/"
cd "$site_dir"
git add "$pages_path"
git commit -m "docs: publish PR walkthrough $slug"
git push origin gh-pages
```

如果仓库尚未启用 GitHub Pages，先让用户在仓库设置里选择 `gh-pages` 分支作为 Pages source，或在有权限时使用 GitHub API/CLI 配置 Pages。不要在未征得用户同意时更改仓库 Pages 设置。

发布后的 URL 通常为：

```text
https://<owner>.github.io/<repo>/pr-walkthrough/<slug>/
```

## 最终回复

报告：

- 生成的 walkthrough 路径。
- `file://` URL。
- 使用的 base branch、PR title 或 branch name。
- 用于 diff links 的 GitHub PR URL。
- 是否找到并纳入 PR review comments。
- D3 canvas validation 是否通过。
- 若发布，报告 GitHub Pages URL。
- 重要 caveats、缺失 specs 或无法完成的验证。
