# AGENTS.md — Codex App 项目规则

这份文件在 **OpenAI Codex App**(桌面端)中被自动加载。Codex 负责隔离并行 Worktree、定时 Automation、高强度外部推理场景。

## 项目速览

**Marzneshin Reality 2026 硬 fork** — Python 3.12 + FastAPI + SQLAlchemy + Marznode gRPC 多节点 + Vite/React/TS dashboard。面向商业化机场 >200 付费用户 + 多节点。AGPL-3.0。详见 [CLAUDE.md](./CLAUDE.md) 和 [NOTICE.md](./NOTICE.md)。

## 构建与测试命令

**后端**:
```bash
python -m venv .venv && source .venv/bin/activate    # Unix
# 或 .venv\Scripts\activate                          # Windows

pip install -r requirements.txt
cp .env.example .env                                  # 编辑 DB URL、JWT secret
alembic upgrade head                                  # DB migration
python main.py                                        # 启动(127.0.0.1:8000)

# 测试
pytest tests/                                         # 当前覆盖率低
```

**前端**:
```bash
cd dashboard
pnpm install
pnpm run build            # 输出到 dashboard/dist
pnpm run test             # vitest
pnpm run lint             # biome
```

**Docker(含 marznode 数据面)**:
```bash
docker-compose up -d
docker-compose logs -f marzneshin
```

## 验证流程(完工前必跑)

Agent 在认为任务完成前必须执行:
1. `pytest tests/` 后端测试通过(不得引入新的 fail)
2. `cd dashboard && pnpm run build` 前端构建成功
3. `cd dashboard && pnpm run lint` biome 无新增错误
4. 如改动涉及 DB schema: 生成 Alembic 迁移 + 在本地跑 `alembic upgrade head` 验证
5. 如改动涉及 `hardening/` / `deploy/` / `ops/`: 必须附 README 或单元测试

## 编码规则

### 禁止(违反即返工)

- **禁止删除上游文件头版权声明**(AGPL-3.0 合规)
- **禁止硬编码 secret**:任何 token、密钥、密码必须走 `.env` + `python-decouple`
- **禁止硬编码用户可见字符串**:UI 文本走 i18n,后端响应 message 走统一错误码
- **禁止 `git reset --hard` / `git push --force main` / `rm -rf`**
- **禁止空 except**:`except: pass` 全仓禁用,必须有处理
- **禁止跳过 hooks**:`--no-verify` 禁用
- **禁止在生产路径使用 mock 数据**:开发/测试 fixture 只在 `tests/` 下
- **禁止未加索引的用户列表查询**:>200 用户场景下必须有索引

### 必须

- **新功能先建分支**:`feat/<name>` / `hardening/<name>` / `fix/<name>` / `deploy/<name>` / `ops/<name>`
- **每逻辑单元一次 commit**:commit message 写 "为什么" 不仅仅是 "做了什么"
- **Python**: type hints 覆盖所有 public function;SQLAlchemy 2.0 typed mappings(`Mapped[...]`)
- **TS/React**: 严格模式,组件 props 必须 typed,避免 `any`
- **DB 迁移**: `alembic revision --autogenerate -m "..."`,生成后必须人工审核 SQL
- **自研模块**(`hardening/`、`deploy/`、`ops/`): 目录根放 `README.md` + `LICENSE`(独立于 AGPL 时)
- **引入新依赖前**:在 PR 描述中说明理由 + license 兼容性(必须与 AGPL-3.0 兼容)

## 委派场景(Codex 擅长的)

- **隔离 Worktree 并行任务**:SNI 选型器 + IP 限制器 + CF Tunnel 脚本三个 greenfield 模块可并行 worktree 开发
- **定时 Automation**:每日跑一次 `upstream-sync-check`(fetch Marzneshin upstream,diff 出新 commit,生成报告)
- **长推理任务**:SQL 查询优化、索引规划、N+1 诊断

## 不适合委派给 Codex 的

- 浏览器/UI 视觉验证(交给 Antigravity + Claude-in-Chrome)
- 交互式对用户确认的决策(留在 Claude Code 主会话)

## 提示词模板

每次发任务给 Codex 时,指令中必须包含:

```
目标: <一句话>
影响文件: <精确路径>
完成判据: <跑什么命令 / 什么输出表明完成>
分支: <feat/xxx 或 hardening/xxx 等>
commit 策略: <原子化还是打包>
返回: 分支名 + 变更文件清单 + 测试结果输出
```

## 参考文件

- [`CLAUDE.md`](./CLAUDE.md) — CTO 铁律 + 项目技术栈 + 特殊注意事项
- [`GEMINI.md`](./GEMINI.md) — Antigravity 规则(同项目不同平台)
- [`NOTICE.md`](./NOTICE.md) — AGPL-3.0 合规说明
- [`compass_artifact_*.md`](./compass_artifact_wf-5103cc40-b39f-4d20-9217-61987475be44_text_markdown.md) — Reality 2026 加固清单
- [`docs/ai-cto/`](./docs/ai-cto/) — 项目状态记忆(VISION / STATUS / DECISIONS / COMPETITORS / AUDIT / ROADMAP)
