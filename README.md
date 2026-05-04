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
| caveman | https://github.com/juliusbrussee/caveman | 借鉴上下文经济、token budget、压缩安全检查和精简输出机制；未采纳其 persona 风格。 |
| superpowers | https://github.com/obra/superpowers | 借鉴可复用 capability / skill 分发、薄说明面和跨工具组织方式。 |
| andrej-karpathy-skills | https://github.com/forrestchang/andrej-karpathy-skills | 借鉴先澄清、简单优先、精准改动、目标驱动验证，落实为 `implementation_discipline` gate。 |

## 能力范围

`agent-gov` 当前主要提供以下能力。

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
   - 支持 `start`、`checkpoint`、`compact`、`bootstrap`、`resume`、`doctor`。
   - 适合 VS Code Remote 中长期使用 Codex，避免把关键上下文只留在聊天记录里。

5. repo-local 长期记忆
   - 生成 `.agent/memory.json`、`.agent/memory/events.jsonl` 和 `agent_memory.py`。
   - 支持 `timeline`、`search`、`detail`、`ingest-session`。
   - 只存摘要、决策、验证和检索线索，不存原始聊天记录和密钥。

6. 上下文预算管理
   - 生成 `.agent/context.json` 和 `agent_context.py`。
   - 跟踪 `AGENTS.md`、会话 bootstrap、memory digest、spec 文档、subagent 输出等上下文大小。
   - 支持本地 token 估算、压缩建议和压缩前后语义校验。

7. 工作流和实现纪律
   - 生成 `.agent/workflow.json`、`.agent/worktrees.json`、implementation plan 和 debugging record 模板。
   - 覆盖规格审批、计划质量、实现纪律、TDD/调试证据、审阅顺序、完成证明。
   - 实现纪律吸收了 `andrej-karpathy-skills` 的核心思想：先澄清假设，优先简单直接实现，避免无根据抽象，保持 diff 精准，定义可验证成功标准。

8. Subagent 编排治理
   - 生成 `.agent/subagents.json` 和 `.agent/templates/subagent-task.md.tmpl`。
   - 支持 searcher、explorer、worker、verifier、spec_reviewer、quality_reviewer、reviewer、coordinator 等角色定义。
   - 要求 disjoint write boundary、`===SNAPSHOT===` JSON 摘要、spec review 先于 quality review。
   - 不强制使用 subagent；只有当前平台和上级指令允许时才使用。

9. Codex / Claude 原生适配
   - 生成 `.codex/config.toml`、`.codex/hooks.json`、`.codex/agents/governance-*.toml`。
   - 可选生成 `.claude/settings.json`、`.claude/agents/governance-*.md`。
   - 这些原生配置是 `.agent/` 中性治理策略的薄投影。

10. 能力、安全、评估和知识治理
    - 生成 `.agent/capabilities.json`、`.agent/tooling.json`、`.agent/security.json`、`.agent/evals.json`。
    - 生成 `scripts/agent_capabilities.py`、`agent_tooling.py`、`agent_security.py`、`agent_score.py`。
    - 生成 `docs/` 知识库、ADR/RFC/postmortem 模板和治理健康评分。
    - `agent_score.py` 会把关键治理 JSON / JSONL 的解析和 schema 有效性作为硬门禁，避免基础配置损坏时仍然给出 pass。

## 不做什么

- 不替代真实测试、构建、人工审查或安全审计。
- 不把 Codex/Claude 聊天记录当作持久状态。
- 不保存 npm token、SSH key、API key 等密钥。
- 不强制安装外部 OpenSpec CLI。
- 不强制使用 subagent，也不强制指定模型。
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

初始化指定路径：

```bash
npx @airpot/agent-gov@latest init /path/to/repo --remote-kind ssh
```

只安装 bundled skills，不初始化治理文件：

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
npx @airpot/agent-gov@latest init . --tech-stack python,typescript --layout service --dry-run
```

2. 确认将要创建的文件后再初始化：

```bash
npx @airpot/agent-gov@latest init . --tech-stack python,typescript --layout service
```

3. 如果已有项目目录结构已经固定，不希望创建新目录：

```bash
npx @airpot/agent-gov@latest init . --layout minimal --no-create-layout
```

默认不会覆盖已有文件。遇到已有 `AGENTS.md`、`CLAUDE.md`、`Makefile`、`docs/` 或 `.agent/` 文件时，先人工合并差异；只有确认要替换生成文件时才使用 `--force`。如果只是更新 bundled skills，使用：

```bash
npx @airpot/agent-gov@latest install-skill . --force-skill
```

纳入后先跑基础治理检查，再按项目实际命令调整 `.agent/harness.json`：

```bash
python3 scripts/agent_check.py
python3 scripts/agent_score.py doctor
python3 scripts/agent_validate.py --list
python3 scripts/agent_score.py score --write
```

## 常用初始化参数

```bash
npx @airpot/agent-gov@latest [root] [options]
```

常用参数：

- `--tech-stack python,typescript`：记录技术栈，并预填常见验证命令。
- `--layout minimal|python-app|node-app|web-app|service|library`：选择固定目录结构。
- `--dir path`：追加需要创建和治理的目录，可重复使用。
- `--remote-kind ssh|devcontainer|wsl|local|unknown`：记录远程开发环境类型。
- `--no-claude`：不生成 Claude 相关适配文件。
- `--no-makefile`：不生成目标项目 `Makefile`。
- `--no-create-layout`：不创建固定目录结构，只记录配置。
- `--force`：允许覆盖已有生成文件。
- `--dry-run`：只展示将要创建或跳过的文件。
- `--skip-skill-install`：npm wrapper 专用，只运行初始化脚本，不复制 bundled skills。
- `--force-skill`：npm wrapper 专用，覆盖目标仓库中的 bundled skills。

## 初始化后常用命令

在已初始化的目标仓库中运行：

```bash
python3 scripts/agent_check.py
python3 scripts/agent_spec.py doctor
python3 scripts/agent_spec.py list --json
python3 scripts/agent_validate.py --list
python3 scripts/agent_capabilities.py doctor
python3 scripts/agent_runlog.py doctor
python3 scripts/agent_tooling.py doctor
python3 scripts/agent_security.py doctor
python3 scripts/agent_score.py score --write
```

会话接续：

```bash
python3 .agent/tools/agent_session.py start feature-name --goal "目标"
python3 .agent/tools/agent_session.py checkpoint --summary "当前进展" --next "下一步"
python3 .agent/tools/agent_session.py compact --summary "压缩摘要" --next "下一步"
python3 .agent/tools/agent_session.py bootstrap
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

发布 npm 包：

```bash
npm publish --access public
```
