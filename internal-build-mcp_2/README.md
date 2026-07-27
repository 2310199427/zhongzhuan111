# Internal Build MCP

这是一个面向企业内部“分支编译出包平台”的 Python MCP Server。公司 CLI Agent 已经是 MCP Client，因此本项目只实现 Server：Agent 把自然语言转换为工具参数，Server 完成校验、安全编排和平台调用。

项目默认是完全离线的 dry-run 模式，不需要公司网络、真实 Token、Cookie、SSO 或真实接口。当前本地开发阶段的测试全部使用 mock；回公司后必须替换 `.env` 中的 `base_url`、接口路径、Token 或可信身份来源，并按真实响应格式适配客户端。

## 架构

```text
用户 -> 公司 CLI Agent（MCP Client） -> FastMCP stdio Server
     -> BuildService（校验/身份/权限/payload/审计）
        -> dry-run 进程内 store
        -> BuildPlatformClient（仅 BUILD_DRY_RUN=false）
           -> 公司出包平台
```

stdio 模式由 CLI Agent 启动本地子进程，通过标准输入/输出交换 MCP 消息。程序不会向 stdout 打印日志；审计事件只写 stderr。即使回到公司，单用户本地 CLI 场景仍可继续使用 stdio。只有需要集中部署、多用户共享、跨主机访问、统一网关认证或服务治理时，才应评估远程 Streamable HTTP。

## 两种使用方式

### 本地离线 dry-run

要求 Python 3.11 或 3.12。安装 [uv](https://docs.astral.sh/uv/) 后执行：

```powershell
cd internal-build-mcp
Copy-Item .env.example .env
uv sync --extra dev
uv run pytest
uv run python -m app.server
```

`.env.example` 已默认配置 `BUILD_DRY_RUN=true`。此时：

- `preview_build` 只返回结构化预览，不返回完整平台 payload；
- `create_build` 生成递增 ID，例如 `MOCK-TASK-000001`；
- 每个 task 独立记录状态，第一次查询为 `running`，后续为 `succeeded`；
- 日志包含模拟敏感文本，但返回前会脱敏；
- 产物和详情地址使用 `.invalid` 示例域名；
- 仍执行参数校验、ActorProvider、权限钩子、payload 白名单构造和审计。

mock store 只存在于当前进程，Server 重启后任务会丢失，ID 也会从 1 重新开始。这是离线调试设计，不是生产持久化方案。

### 回公司连接真实平台

1. 复制 `.env.example` 为 `.env`，保持该文件不进入版本控制。
2. 把 `BUILD_PLATFORM_BASE_URL` 和四个 `*_PATH` 替换为内部接口配置。
3. 配置真实 Token，或修改 `BuildPlatformClient` 使用公司规定的 Cookie/身份透传机制。
4. 将 `BUILD_DRY_RUN=false`。
5. 用公司 CLI/SSO/JWT 身份实现替换 `EnvironmentActorProvider`。
6. 在 `security.py` 实现 repository 和 task 权限校验。
7. 按真实响应适配 `platform_client.py`/`build_service.py` 的字段提取。
8. 根据接口文档确认 `_build_create_payload` 中带 TODO 的映射。
9. 先在隔离测试环境通过 mock 和联调测试，再允许生产出包。

切换前尤其要确认创建请求超时的处理方式。本项目不会自动重试创建请求，因为第一次请求可能已成功，重试会产生重复任务。

## MCP Tools

| Tool | 作用 |
|---|---|
| `ping()` | 检查 Server 是否存活，并返回当前 dry-run 状态 |
| `preview_build(...)` | 校验输入、身份和权限，返回安全的结构化预览 |
| `create_build(...)` | dry-run 创建 mock 任务，真实模式调用创建接口 |
| `get_build_status(task_id)` | 查询并映射 queued/running/succeeded 等状态 |
| `get_build_logs(task_id, tail=200)` | 查询最多 1–2000 行并脱敏 |
| `get_build_artifacts(task_id)` | 查询任务产物地址 |

创建和预览只接受 `repository`、`branch`、`cmc_version`、`inner_version_tdd`、`inner_version_fdd`、`description`。任何 Tool 都不接受 `trigger`、`employeeNo`、`employee_no`、`userId`、`operatorId`、`ownerId`、`creator` 或 `submitter`。

## MCP Inspector dry-run

保持 `.env` 中 `BUILD_DRY_RUN=true`，在项目目录执行：

```powershell
npx @modelcontextprotocol/inspector uv --directory . run python -m app.server
```

Inspector 页面打开后：

1. 连接 stdio Server，先调用 `ping`；
2. 调用 `preview_build`，确认响应没有 `payload` 或 `sanitized_payload`；
3. 调用两次 `create_build`，确认返回不同的 `MOCK-TASK-` ID；
4. 分别查询两个 ID，确认每个任务第一次 `running`、第二次 `succeeded`；
5. 调用日志工具，确认模拟 secret 显示为 `[REDACTED]`；
6. 调用产物工具，确认返回 `example.invalid` URL。

`npx` 首次运行可能需要访问公共 npm registry。不能联网时，可在有缓存/已安装 Inspector 的环境运行，不影响 Python 单元测试。

## 公司 CLI Agent 通用示例

不同 Agent 的配置键名可能不同，以下仅展示通用 stdio 形态：

```json
{
  "mcpServers": {
    "internal-build-mcp": {
      "command": "uv",
      "args": ["--directory", "<LOCAL_PROJECT_PATH>/internal-build-mcp", "run", "python", "-m", "app.server"],
      "env": {
        "BUILD_DRY_RUN": "true",
        "BUILD_ACTOR_NAME": "Mock Developer",
        "BUILD_ACTOR_EMPLOYEE_NO": "MOCK-EMPLOYEE-000001",
        "BUILD_PLATFORM_TOKEN": "replace-with-placeholder-token"
      }
    }
  }
}
```

不要把真实 Token 或工号提交到 Agent 配置模板、README、测试或代码仓库。生产环境优先使用 CLI Agent 的可信身份透传，而不是静态工号环境变量。

## 环境变量

- `BUILD_DRY_RUN`：默认 `true`；只有 `false` 才访问 HTTP 平台。
- `BUILD_PLATFORM_BASE_URL`：平台基础地址；示例使用不可路由 `.invalid`。
- `BUILD_PLATFORM_*_API_NAME`：脱敏接口名称，仅用于文档辨识。
- `BUILD_PLATFORM_*_PATH`：创建、状态、日志、产物路径；`{task_id}` 会安全替换。
- `BUILD_PLATFORM_TOKEN`：平台认证占位；敏感，禁止记录或提交。
- `BUILD_PLATFORM_TIMEOUT_SECONDS`：HTTP 超时秒数。
- `BUILD_ACTOR_NAME`、`BUILD_ACTOR_EMPLOYEE_NO`：仅本地测试 Actor。
- `BUILD_DEFAULT_*`：原始出包 payload 的默认字段。字符串 `false` 与布尔 `false` 不能互换。

完整默认值和所有变量见 `.env.example`。

## payload 映射与不确定点

`_build_create_payload` 使用逐字段白名单，不会透传用户对象。当前映射包括：repository 到 `git_project`，branch 到 `git_branch`/`node_branch`，版本字段到同名目标及 `point`，description 到 `remark`，Actor 工号到 `trigger`。

回公司后需确认：

- `node_branch` 是否永久等于 `git_branch`；
- `git_marp_branch`/`git_marp_no` 是否通过平台默认配置接口动态获取；
- `git_branch_dpd` 是否跟随用户 branch；
- `pck_model`/`project_name` 是否按 repository 映射；
- `inner_version_ruet` 是否需要用户输入；
- `remark` 是否就是页面出包说明；
- 真实响应中的 task ID、状态、日志、产物字段名。

若要增加 repository 到 `pck_model`/`project_name` 的映射，建议新增受控配置表并在 service 内按允许的 repository 查表，找不到时拒绝，而不是接受用户直接传值。动态 `git_marp_no` 应通过独立只读客户端获取、校验格式，再交给 payload 构造器。

## 安全说明

`trigger` 是安全边界，不是普通业务输入。若用户能修改工号替他人出包，通常意味着身份与业务参数混淆、服务端信任客户端字段或缺少授权校验。MCP Server 禁止该输入并从 ActorProvider 获取身份，但这只是纵深防御；真正的出包平台后端仍必须验证 Token 对应主体是否允许以该 trigger 操作，不能信任 MCP 传来的工号。

状态、日志和产物查询同样调用 `authorize_task_access`，防止猜测 task ID 读取他人数据。当前两个授权函数是显式的 allow-all 占位，生产上线前必须实现。审计日志会掩码工号并脱敏 Token、Cookie、Authorization、Bearer 和 Password，但仍应限制日志访问权限。

## 测试与禁网保证

```powershell
uv run pytest
```

HTTP 测试使用 `respx` 严格路由：未 mock 请求会失败。`tests/conftest.py` 还会阻止 socket 连接，因此整个测试套件不能访问真实网络。测试数据只使用 `.invalid` 域名和 `MOCK-*`/`placeholder-*` 值。

## 常见问题

- 启动后没有输出：stdio Server 正在等待 MCP Client，这是正常行为。
- JSON-RPC 被污染：检查是否有代码向 stdout `print`；审计必须留在 stderr。
- `.env` 未生效：确认命令工作目录是项目根目录。
- 真实模式提示缺少客户端：应通过 `app.server` 启动，它会在真实模式创建客户端。
- 404：检查路径模板和 task ID 字段，不要把真实路径写进测试。
- 401/403：检查公司认证与授权，但不要把 Token 打印到终端或日志。
- 非 JSON 响应：可能是网关登录页、错误代理或路径错误；客户端会安全拒绝。
- dry-run 找不到任务：mock store 是进程内的，重启后需重新创建。
