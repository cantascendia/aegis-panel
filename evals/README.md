# Evals — Golden Trajectories + Regression + Capability

> 项目级 eval 集,按手册 §35 Eval-Driven Development 流程组织。
> 配套铁律 #12: 无 eval 的 agent 配置改动不得进 main(见 `.claude/rules/eval-gate.md`)。

## 目录

- `golden-trajectories/`: 5+ 黄金轨迹,定义 CTO 在标准任务下的期望行为
- `regression/`: 历史 bug / 事故场景,防回归
- `capability/`: 新能力扩展验证

## 触发命令(手册 §35)

- `/cto-eval init` — 首次创建结构(已完成 - PR #NNN)
- `/cto-eval audit` — 审视现有 eval 集是否需扩充
- `/cto-eval add [任务描述]` — 加新 trajectory
- `/cto-eval run` — 跑全部 eval

## yaml 模板(每条 trajectory)

```yaml
id: NNN-task-slug
description: 一句话描述
input: 用户在会话中输入的提示词
expected_steps:
  - 步骤 1
  - 步骤 2
forbidden_actions:
  - 禁止做的事 1
  - 禁止做的事 2
acceptance_criteria:
  - 可验证的完成标准 1
  - 可验证的完成标准 2
priority: P0  # P0/P1/P2
```

## 集成

- **eval-runner sub-agent**(已建,见 `.claude/agents/eval-runner.md`)异步并行执行 yaml,输出 pass/fail 报告
- CI 集成: 修改 `CLAUDE.md` / `.claude/commands/*` / `.claude/agents/*` / `.agents/skills/*/SKILL.md` 时,PR 必须配套 eval(铁律 #12)
- 推荐工具: Braintrust(trajectory 级 scoring + CI/CD)/ LangSmith(节点级)/ Promptfoo(红队)/ 本地脚本(yaml 对比)

## 当前状态

- 5 P0 golden trajectory 入库(本 init PR)
- 2 regression case (L-018 + L-015)
- 0 capability case

## 维护

- 新增轨迹: `/cto-eval add` 走交互式
- 每次改 CLAUDE.md / commands / skills 必须跑 regression 集
