# Agent Gov

`agent-gov` 是一个面向 Codex / Claude 长周期软件开发的项目治理 skill 和一键初始化工具。它的目标不是替代你的测试、代码审查或项目设计，而是把 agent 开发过程中容易丢失的规格、会话上下文、验证证据、审阅结论和交接信息固化到仓库文件中。

当前 npm 包名：

```bash
@airpot/agent-gov
```

## 借鉴的开源项目与公开资料

`agent-gov` 借鉴了以下项目或公开材料的设计思想。这里的“借鉴”指治理机制、工作流模式和文档结构，不表示 vendoring、运行时依赖或自动安装这些项目。

| 项目 / 资料 | 链接 | 融入到 `agent-gov` 的内容 |
| --- | --- | --- |
| SkVM | https://github.com/SJTU-IPADS/SkVM | 借鉴 profile -> optimize -> validate 的迭代思想，用于 skill 开发、评估和审阅-修正闭环。 |
| OpenSpec | https://github.com/Fission-AI/OpenSpec | 借鉴 proposal、design、tasks、archive 的规格变更结构；`agent-gov` 已内嵌实现，不依赖全局 OpenSpec CLI。 |
| OpenAI Harness Engineering | https://openai.com/index/harness-engineering/ | 借鉴 harness 作为可执行反馈面、验证命令注册、证据记录和回归检查的思想。 |
| claude-mem | https://github.com/thedotmack/claude-mem | 借鉴 repo-local 长期记忆、摘要化存储、检索优先和记忆提升/审阅机制。 |
| TencentDB-Agent-Memory | https://github.com/TencentCloud/TencentDB-Agent-Memory | 借鉴长会话记忆分层、上下文卸载、可检索记忆、recall 上下文预算和事实回溯边界，用于 session offload、truth-first grounding 和 memory-as-advisory 设计。 |
| caveman | https://github.com/juliusbrussee/caveman | 借鉴上下文经济、token budget、压缩安全检查和精简输出机制；未采纳其 persona 风格。 |
| superpowers | https://github.com/obra/superpowers | 借鉴可复用 capability / skill 分发、薄说明面和跨工具组织方式。 |
| andrej-karpathy-skills | https://github.com/multica-ai/andrej-karpathy-skills | 借鉴先澄清、简单优先、精准改动、目标驱动验证，落实为 `implementation_discipline` gate。 |
| mattpocock/skills | https://github.com/mattpocock/skills | 借鉴小而明确的 skill 组织方式、轻量说明面和按场景激活的 skill 包结构，用于 profile 化初始化和 `SKILL.md` 入口收敛。 |
| dictionary-of-ai-coding | https://github.com/mattpocock/dictionary-of-ai-coding | 借鉴统一 AI coding 术语表的思想，生成 `docs/AI_CODING_GLOSSARY.md`；已吸收 AX/DX、primary/secondary source、context pointer、compaction 等治理相关术语，但不镜像完整词典。 |
| agent-coding-playbook | https://github.com/bravekingzhang/agent-coding-playbook | 借鉴 task 风险分级、自治边界、human-in-the-loop 和 review 证据化的工作流思想。 |
| Agent-Coding-Governance-Methodology | https://github.com/johnrucnapier-sketch/Agent-Coding-Governance-Methodology | 借鉴长期 agent coding 治理、证据化结论、旧文档漂移治理和 review gate 思想，用于 task-board、governance-gc、mechanical checks 和 review-fix-review。 |

## 能力范围

`agent-gov` 当前主要提供以下能力。

### 治理体量 profile

初始化时可以用 `--governance-profile core|standard|full` 控制生成规模。

- `core`：最小治理面，包含内嵌规格、harness、项目目录契约、会话接续、runlog、基础评分和迁移检查。
- `standard`：已有项目默认档，推荐给多数已有项目，增加 workflow profiles、requirements interview gate、task-board、feature 阶段文档、domain glossary、memory、context budget、session event stream、dev map、mechanical checks、baseline、skill hygiene、禁用态 MCP policy、governance-gc 和 harness evolution。
- `full`：空白项目默认档，完整框架，额外增加 subagent 编排、Codex/Claude 原生适配、hooks、tooling/security 配置和 skill distribution。

未显式传 `--governance-profile` 时，空白项目默认 `full`，已有项目默认 `standard`。空白项目判定会忽略 `.git`、常见编辑器目录和空目录。只需要最小接续能力时用 `core`，已有项目需要完整接管时显式传 `full`。

| 场景 | 推荐 profile | 原因 |
| --- | --- | --- |
| 只想让长会话可接续，项目还很小 | `core` | 保留 spec、harness、session、runlog 和评分，治理面最小。 |
| 空白项目从 0 建立 agent-ready 生产流水线 | `full` | 一次性启用 subagent、native adapter、tooling/security 和 skill distribution。 |
| 已有项目想纳入 agent 开发治理 | `standard` | 覆盖 task-board、requirements gate、memory/context、dev map、baseline、mechanical checks 和治理 GC。 |
| 跨模块重构、发布、迁移或多 agent 协作 | `full` | 额外启用 subagent、native adapter、tooling/security 和 skill distribution。 |
| 不确定选哪个 | 省略参数 | 让初始化器按空白/已有项目自动选择。 |

1. 项目治理初始化
   - 生成 `AGENTS.md`，可选生成 `CLAUDE.md`。
   - 记录技术栈、固定目录结构、远程开发环境类型。
   - 默认保留已有文件，除非显式使用 `--force`。

2. 内嵌规格管理
   - 生成 `.agent/spec.json` 和 `openspec/` 目录。
   - 通过 `scripts/agent_spec.py` 管理 proposal、design、tasks、archive。
   - 不依赖全局 OpenSpec CLI，也不会自动安装外部 OpenSpec。

3. Harness 工程管理
   - 生成 `.agent/harness.json` 和 `scripts/agent_validate.py`。
   - 按技术栈预填 build、test、lint、typecheck 等验证命令。
   - 通过 runlog 记录验证证据。

4. 长会话和跨会话接续
   - 生成 `.agent/sessions/` 和 `.agent/tools/agent_session.py`。
   - 支持 `start`、`checkpoint`、`compact`、`bootstrap`、`resume`、`doctor`、`events`。
   - 生成 `.agent/sessions/events.jsonl` 作为 append-only 会话事件流，记录 session start、checkpoint、bootstrap、compact 和 archive 事件，方便新会话先读取最近事实。
   - 适合 VS Code Remote 中长期使用 Codex，避免把关键上下文只留在聊天记录里。

5. repo-local 长期记忆
   - 生成 `.agent/memory.json`、`.agent/memory/events.jsonl` 和 `agent_memory.py`。
   - 支持 `timeline`、`search`、`detail`、`ingest-session`。
   - `search` 默认受 recall 输出预算约束，长记录通过 `detail <id>` 按需读取。
   - 只存摘要、决策、验证和检索线索，不存原始聊天记录和密钥。

6. 上下文预算管理
   - 生成 `.agent/context.json` 和 `agent_context.py`。
   - 跟踪 `AGENTS.md`、会话 bootstrap、memory digest、spec 文档、subagent 输出等上下文大小。
   - 支持本地 token 估算、压缩建议和压缩前后语义校验。

7. 工作流和实现纪律
   - 生成 `.agent/workflow.json`、`.agent/workflow-profiles.json`、`.agent/task-board.json`、`.agent/risk-zones.json`、`.agent/review-policy.json`、`.agent/worktrees.json`、implementation plan、debugging record、`docs/DOMAIN_GLOSSARY.md` 和 feature stage 模板。
   - 支持 `tiny`、`bugfix`、`standard`、`full` 四种 workflow profile，让流程重量匹配任务风险和规模。
   - 生成 `scripts/agent_task.py` 和 `docs/features/`，把任务状态、raw/refined goal、任务拆解、阶段文档和交付结论固化到仓库。
   - 非问答请求默认先进入 intake：分类任务类型和风险，保留原始用户目标，写出 refined goal、非目标、约束、成功证据和确认/假设状态。
   - 非 tiny 任务进入 design / plan / implementation / review / done 前，需要先完成 requirements interview：共享理解、未决问题、代码/文档交叉核对和领域术语更新都要落到 task-board。
   - `tiny` 使用轻量 checklist，`bugfix` 使用 reproduction/root-cause/fix/regression 链，`standard/full` 使用可审阅 task graph；任务进入实现、验证、交付或 done 前必须完成相应拆解证据。
   - 覆盖风险分级、自治边界、规格审批、计划质量、实现纪律、diff 可追踪、TDD/调试证据、审阅顺序、人审证据、完成证明。
   - 实现纪律吸收了 `andrej-karpathy-skills` 的核心思想：先澄清假设，优先简单直接实现，避免无根据抽象，保持 diff 精准，定义可验证成功标准。

8. 审阅-修正闭环
   - `tiny`、`bugfix`、`standard`、`full` 的完成态都要求 review-fix-review；tiny 无 task-board 时证据写入 active session、runlog 或 `.agent/intake/`。
   - 高风险和 critical 风险工作要求记录 human review evidence。
   - 每个改动文件需要归类为 requested、necessary-support、incidental 或 risky。
   - 自动审阅和模型总结只能作为 precheck，不能替代测试、构建或必需的人审。

9. Subagent 编排治理
   - 生成 `.agent/subagents.json`、`.agent/role-contracts.json` 和 `.agent/templates/subagent-task.md.tmpl`。
   - 支持 searcher、explorer、worker、verifier、spec_reviewer、quality_reviewer、reviewer、coordinator 等角色定义。
   - 要求 disjoint write boundary、`===SNAPSHOT===` JSON 摘要、spec review 先于 quality review。
   - 固化“发现问题的人不能自己修”：verifier/reviewer 只报告和路由 findings，不直接修改实现文件。
   - 不强制使用 subagent；只有当前平台和上级指令允许时才使用。

10. Codex / Claude 原生适配
   - 生成 `.codex/config.toml`、`.codex/hooks.json`、`.codex/agents/governance-*.toml`。
   - 可选生成 `.claude/settings.json`、`.claude/agents/governance-*.md`。
   - 这些原生配置是 `.agent/` 中性治理策略的薄投影。

11. 能力、安全、评估和知识治理
    - 生成 `.agent/manifest.json`，集中记录 required paths、JSON schema、JSONL store 和评分维度，减少多脚本重复维护。
    - 生成 `.agent/capabilities.json`、`.agent/tooling.json`、`.agent/security.json`、`.agent/evals.json`、`.agent/mechanical-checks.json`、`.agent/baselines.json`。
    - 生成 `.agent/dev-map.json`、`.agent/harness-evolution.json`、`.agent/mcp-policy.json`、`.agent/governance-gc.json`。
    - 生成 `scripts/agent_capabilities.py`、`agent_skill_hygiene.py`、`agent_tooling.py`、`agent_security.py`、`agent_score.py`、`agent_verify.py`、`agent_gc.py`。
    - 生成 `docs/` 知识库、AI coding 术语表、ADR/RFC/postmortem 模板和治理健康评分。
    - `.agent/capabilities.json` 明确区分 Skill、Tool、MCP/integration、native adapter，并为每项能力记录 capability class、权限、owner、risk 和验证命令。
    - `docs/DEV_MAP.md` 和 `.agent/dev-map.json` 提供项目级入口地图：从哪里读起、哪些模块归谁、改动前先看什么、常见模式是什么；它是导航索引，不是全仓库文件清单。
    - `.agent/harness-evolution.json` 把低级错误和重复失败归类为 rule gap、skill gap、script gap、workflow gap、role contract gap、tool/MCP gap、knowledge gap、session gap 或 context gap，并可用 `agent_gc.py classify` 记录 incident，反向推动框架修订。
    - `.agent/skill-hygiene.json` 和 `agent_skill_hygiene.py` 只做只读扫描，检查本地 skill 的 frontmatter、source/hash、过期风险、软链接和风险命令信号；不会自动删除、覆盖或注入 canary。
    - `.agent/mcp-policy.json` 默认 `optional-disabled-by-default`，只定义 MCP 接入的信任边界、审批、凭据和审计规则，不默认启用外部集成。
    - MCP / 外部集成凭据必须留在 vault 或 proxy 边界之后，不能把原始 token、key、cookie 放进仓库、harness、sandbox 或 `.agent/`。
    - `agent_gc.py` 提供非破坏性的 doc-gardening / governance-gc，用于发现过期文档、owner 缺口、过期任务、过期 baseline、配置指针漂移和 MCP policy 风险。
    - `agent_score.py` 会把关键治理 JSON / JSONL 的解析、schema 有效性、`agent_verify.py` 机械快照和 `agent_gc.py` 漂移报告作为门禁，避免基础配置或治理漂移损坏时仍然给出 pass。
    - `agent_verify.py` 提供硬机械检查和 before/after baseline 对比，覆盖 JSON/JSONL、required paths、feature templates、task-board、role contracts、模板渲染、测试数量基线和本地 Markdown links。

12. Agent runtime 框架采用门禁
    - 对 `agent` 和 `hybrid` 目标，默认是 framework-first，而不是让开发者猜要不要用框架。
    - `.agent/agent-runtime.json` 会生成 `runtime_adoption`：primary adapter、recommended adapters、package plan、pre-implementation gate 和 manual LLM exception 契约。
    - 默认 Skill-first agent 会给出 Strands 安装计划；需要结构化输出时会给出 Pydantic AI 计划；需要长流程/状态图时会给出 LangGraph 计划。
    - 初始化不会静默执行 `pip`、`uv`、`npm` 等安装命令；依赖变更仍归应用层，通过 spec/task/review-fix/validation 落地。
    - 直接手写 LLM 调用、绕过成熟 runtime adapter，只能作为例外：必须记录 rationale、owner、review evidence 和 validation evidence。

## 不做什么

- 不替代真实测试、构建、人工审查或安全审计。
- 不把 Codex/Claude 聊天记录当作持久状态。
- 不把 `.agent/memory/` 当作团队规范真相源；真相源应落在 spec、task-board、feature docs、ADR/RFC/postmortem、runlog 和 validation 里。
- 不把自动审阅、模型总结或 agent 自评当作必需的人审证据。
- 不保存 npm token、SSH key、API key 等密钥。
- 不允许原始凭据进入仓库、harness、sandbox 或 `.agent/`；外部集成必须通过 vault / proxy 边界。
- 不强制安装外部 OpenSpec CLI。
- 不强制使用 subagent，也不强制指定模型。
- 不自动清理本地 skill，也不默认启用 canary 注入；skill hygiene 只是只读发现问题。
- 不会默认覆盖已有项目文件；需要覆盖时显式传 `--force`。

## 快速使用

在目标仓库根目录运行：

```bash
npx @airpot/agent-gov@latest
```

指定技术栈和固定目录结构：

```bash
npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service
```

使用完整治理档：

```bash
npx @airpot/agent-gov@latest --tech-stack python,typescript --layout service --governance-profile full
```

初始化指定路径：

```bash
npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh
```

只安装 bundled agent-gov skill，不初始化治理文件：

```bash
npx @airpot/agent-gov@latest install-skill /path/to/repo
```

检查 npm 包和目标项目中的 skill 安装状态：

```bash
npx @airpot/agent-gov@latest doctor /path/to/repo
```

安装项目级 skill 后，重启或 reload Codex，让新的 skill 被发现。

## 纳入已有项目

已有项目可以直接纳入 `agent-gov`，推荐按“先观察、再初始化、再校准”的顺序执行。

1. 在独立分支或干净 worktree 中先做 dry run：

```bash
npx @airpot/agent-gov@latest init . --tech-stack python,typescript --layout service --governance-profile standard --dry-run
```

2. 确认将要创建的文件后再初始化：

```bash
npx @airpot/agent-gov@latest init . --tech-stack python,typescript --layout service --governance-profile standard
```

3. 如果已有项目目录结构已经固定，不希望创建新目录：

```bash
npx @airpot/agent-gov@latest init . --layout minimal --no-create-layout
```

非 `src/tests` 结构的老项目，使用 `existing` 布局并显式声明要治理的目录：

```bash
npx @airpot/agent-gov@latest init . --layout existing --dir cmd,pkg,internal --no-create-layout
```

默认不会覆盖已有文件。遇到已有 `AGENTS.md`、`CLAUDE.md`、`Makefile`、`docs/` 或 `.agent/` 文件时，先人工合并差异；只有确认要替换生成文件时才使用 `--force`。如果只是更新 bundled agent-gov skill，使用：

`--dry-run` 会区分 `would create`、`unchanged`、`preserved append-only` 和 `conflicts`。其中 `preserved append-only` 表示 runlog、session events、memory events 或 context stats 这类追加型历史会被保留；`conflicts` 表示已有文件和将生成内容不同，需要人工合并或明确使用 `--force`。

```bash
npx @airpot/agent-gov@latest install-skill . --force-skill
```

纳入后先跑基础治理检查，再按项目实际命令调整 `.agent/harness.json`：

```bash
python3 scripts/agent_check.py
python3 scripts/agent_score.py doctor
python3 scripts/agent_validate.py --list
python3 scripts/agent_runtime.py doctor
python3 scripts/agent_runtime.py report --json
python3 scripts/agent_gc.py doctor
python3 scripts/agent_score.py score --write
```

随后优先补齐 `docs/DEV_MAP.md`、`.agent/harness.json` 和 `.agent/project-layout.json`，让后续新会话可以先读项目入口地图，再按真实验证命令推进。

## 常用初始化参数

```bash
npx @airpot/agent-gov@latest [root] [options]
```

常用参数：

- `--tech-stack python,typescript`：记录技术栈，并预填常见验证命令。
- `--layout existing|minimal|python-app|node-app|web-app|service|library`：选择固定目录结构；`existing` 不附加默认目录，适合老项目配合 `--dir` 使用。
- `--governance-profile core|standard|full`：选择初始化体量；省略时空白项目默认 `full`，已有项目默认 `standard`。
- `--dir path`：追加需要创建和治理的目录，可重复使用。
- `--remote-kind ssh|devcontainer|wsl|local|unknown`：记录远程开发环境类型。
- `--no-claude`：不生成 Claude 相关适配文件。
- `--no-makefile`：不生成目标项目 `Makefile`。
- `--no-create-layout`：不创建固定目录结构，只记录配置。
- `--force`：允许覆盖已有生成文件。
- `--dry-run`：只展示将要创建或跳过的文件。
- `--skip-skill-install`：npm wrapper 专用，只运行初始化脚本，不复制 bundled agent-gov skill。
- `--force-skill`：npm wrapper 专用，覆盖目标仓库中的 bundled agent-gov skill。

## 初始化后常用命令

在已初始化的目标仓库中运行：

```bash
python3 scripts/agent_check.py
python3 scripts/agent_migrate.py doctor
python3 scripts/agent_spec.py doctor
python3 scripts/agent_spec.py list --json
python3 scripts/agent_validate.py --list
python3 scripts/agent_capabilities.py doctor
python3 scripts/agent_runlog.py doctor
python3 scripts/agent_tooling.py doctor
python3 scripts/agent_security.py doctor
python3 scripts/agent_task.py doctor
python3 scripts/agent_skill_hygiene.py doctor
python3 scripts/agent_verify.py doctor
python3 scripts/agent_gc.py doctor
python3 scripts/agent_score.py score --write
```

`core` 档不会生成 `agent_task.py`、`agent_verify.py`、`agent_gc.py`、memory/context 工具或原生 adapter；`standard` 档会生成禁用态 `.agent/mcp-policy.json`，但不会生成 subagent/native adapter/tooling/security/skill distribution 相关文件。运行命令时以实际生成的脚本为准。

任务看板和 feature 文档：

```bash
python3 scripts/agent_task.py list
python3 scripts/agent_task.py new feature-id --title "功能标题" --profile standard --risk medium
python3 scripts/agent_task.py update feature-id --requirements-status complete \
  --shared-understanding "范围、术语和验收标准已确认" \
  --domain-glossary-updated \
  --code-docs-cross-checked
python3 scripts/agent_task.py update feature-id --stage plan
python3 scripts/agent_task.py update feature-id --state review --stage verification
```

机械检查和 baseline 对比：

```bash
python3 scripts/agent_verify.py doctor
python3 scripts/agent_verify.py snapshot --name before-change --fail-on-issue
python3 scripts/agent_verify.py snapshot --name after-change --fail-on-issue
python3 scripts/agent_verify.py compare --before .agent/baselines/before-change.json --after .agent/baselines/after-change.json
```

治理 GC / 文档园艺：

```bash
python3 scripts/agent_gc.py doctor
python3 scripts/agent_gc.py doctor --fail-on-warning
python3 scripts/agent_gc.py report --json
python3 scripts/agent_gc.py classify --category script_gap --summary "失败原因和应补的治理能力"
```

会话接续：

```bash
python3 .agent/tools/agent_session.py start feature-name --goal "目标"
python3 .agent/tools/agent_session.py checkpoint --summary "当前进展" --next "下一步"
python3 .agent/tools/agent_session.py compact --summary "压缩摘要" --next "下一步"
python3 .agent/tools/agent_session.py bootstrap
python3 .agent/tools/agent_session.py events --limit 10
python3 .agent/tools/agent_session.py doctor
```

长期记忆和上下文预算：

```bash
python3 .agent/tools/agent_memory.py timeline --limit 10
python3 .agent/tools/agent_memory.py search "关键词"
python3 .agent/tools/agent_context.py scan --limit 10
python3 .agent/tools/agent_context.py suggest
```

## GitHub 安装方式

如果不通过 npm，也可以从 GitHub 安装 skill：

```text
Install skill from https://github.com/airpot/agent-gov/tree/main/.codex/skills/agent-gov
```

安装后同样需要重启或 reload Codex。

## 维护者发布检查

发布前在本目录运行：

```bash
npm run validate
```

维护者在 workspace 根目录发布前推荐运行完整 release gate：

```bash
make agent-gov-release-check
```

发布 npm 包：

```bash
npm publish --access public
```
