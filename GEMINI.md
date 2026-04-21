# Antigravity Workspace Rules — Marzneshin Reality 2026 Fork

这份规则在 **Antigravity IDE**(Google Agent-First IDE)中激活。不重复 CLAUDE.md 中的项目特定规则(那里放 CTO 铁律和技术栈);这里放委派给 AG Agent 执行时必守的**通用代码质量与安全回退**原则。

## 通用代码质量

- **读取优先,再改动**:修改任何文件前先读完整文件;跨文件修改前先扫调用方
- **最小变更原则**:PR diff 越小越易审;与任务无关的重构另开分支
- **不过度抽象**:三次重复再抽象;不为"将来可能"预留扩展点
- **不写多余注释**:命名能表达的不写注释;只写 "WHY" 层注释(workaround、奇怪约束、invariant)
- **不加空异常处理**:捕获异常必须有处理逻辑(log / fallback / re-raise);`except: pass` 禁用
- **不写 mock / 占位数据交付**:按钮不可点击 = 未完成;硬编码 "测试用户" "¥99" = 未完成
- **错误处理必须区分系统边界**:外部输入/第三方 API 必须校验,内部函数之间信任契约

## 安全回退(铁律,违反即返工)

- **先创建 Git 分支**:`git checkout -b <type>/<task-name>`(类型见 CLAUDE.md 命名规范)
- **禁止破坏性命令**:`git reset --hard`、`git checkout -- .`、`rm -rf /`、`git push --force main`
- **每逻辑单元 commit 一次**:不累积 10+ 文件的"巨型 commit"
- **禁止跳过 hooks**:`--no-verify`、`--no-gpg-sign` 禁用(除非用户明确要求)
- **禁止删除重建**:文件编码坏了、格式乱了、有 bug 了,先 `git checkout -- file` 恢复再改;不能"删掉重写"
- **禁止硬编码 secret**:`.env` 以外不得出现任何 token / 密钥 / DB 密码 / Xray UUID
- **UI 文本必须走 i18n**:dashboard/src/ 下所有面向用户的字符串必须通过 i18n key(不硬编码中英文)
- **环境配置必须分离**:API 地址、CF 凭据、SMTP 配置通过 `.env`、`VITE_*` 环境变量,不写死

## 委派场景(Antigravity 擅长的)

- **浏览器验证**:用 Claude-in-Chrome 验证 dashboard 关键页面(登录/用户列表/节点列表)的五态(空/加载/成功/错误/部分)
- **Stitch UI 设计**:面板加固向导的新页面(CF Tunnel 配置、SNI 选型结果展示等)用 Stitch 起草
- **AI 图像**:营销物料、README 截图、文档插画

## 不适合委派给 AG 的

- **加固核心逻辑**(`hardening/*`)— 高安全敏感,留在 Claude Code 本地执行
- **DB schema 迁移** — Alembic 自动生成需要人工 review 与测试
- **生产部署脚本**(`deploy/*`)— 出问题影响所有节点,不交 Agent

## 质量哲学

- **AGPL-3.0 合规是产品生存前提**,任何改动都检查是否破坏 `LICENSE` / `NOTICE.md`
- **Reality 加固是核心差异化**,触碰 Xray/Reality 配置的任何改动必须配 test fixture
- **商业化机场要求稳定性 > 新功能**,宁可慢,不要崩
- **多节点容错**是护城河,所有涉及 `app/marznode/*` 的改动必须考虑单节点失败场景

## 每次委派必须给 Agent 说明

1. 任务目标 + 关联哪个产品功能
2. 受影响文件(精确到 path)
3. 验收标准(跑什么命令 / 什么 UI 流程能证明完成)
4. 返回什么:分支名 + 修改文件清单 + 测试结果
