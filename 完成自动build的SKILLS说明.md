你现在这个任务，本质不是“让 AI 去点网页”，而是**把分支编译出包网站背后的出包流程，沉淀成一个可复用、可校验、可追踪的自动化 skill**。

我建议你按下面这条路线走。你没有代码库权限这件事，**目前不一定影响**，因为你的 agent 主要是调用“出包网站/出包服务”的能力，而不是自己 clone 代码、编译代码。

---

## 一、先明确：你的 skill 要做什么，不要做什么

你的 skill 不应该一上来就做成“模拟人操作网页”。更合理的目标是：

> 用户给出代码库、代码分支、组件、点分号、集成分支、集成节点、出包信息等参数，skill 调用公司内网出包系统的接口创建编译任务，并持续查询状态，最后返回任务结果、日志链接、包下载地址或失败原因。

它大概分三层：

```text
AI Agent Skill
   ↓
出包流程编排逻辑
   ↓
内网出包网站后端 API
```

尽量不要走：

```text
AI Agent → 模拟浏览器点击页面 → 提交表单
```

除非后端接口很难稳定调用，或者公司要求必须通过 UI 自动化。

---

## 二、第一阶段：把网站的“真实流程”摸清楚

你今天已经看了 POST payload，这是很好的开始。但只看一个 POST 还不够，你要把完整链路补全。

你需要在 F12 里重点记录这些请求：

| 阶段           | 你要找的东西                              |
| -------------- | ----------------------------------------- |
| 页面初始化     | 网站加载默认配置时调用了哪些接口          |
| 获取代码库列表 | repo 列表接口                             |
| 获取分支列表   | branch 列表接口，是否依赖 repo            |
| 获取组件列表   | 组件、版本、依赖关系接口                  |
| 获取点分号     | 点分号字段是手填还是接口返回              |
| 获取集成分支   | integration branch 接口                   |
| 获取集成节点   | integration node 接口                     |
| 提交出包       | 真正创建任务的 POST 接口                  |
| 查询任务状态   | 轮询接口，一般返回 running/success/failed |
| 查看日志       | 日志接口或日志 URL                        |
| 获取产物       | 包下载地址、制品库地址、任务详情页        |

你下一次操作网页时，建议这样做：

1. 打开 F12 → Network。
2. 勾选 Preserve log。
3. 清空已有请求。
4. 从打开页面、选择默认配置、点击出包，完整操作一遍。
5. 找到关键 POST 请求，右键 Copy as cURL。
6. 同时保存页面上相关 GET 请求。
7. 导出 HAR 文件，但注意：**HAR 里可能有 cookie、token、内网地址，不要随便发给外部或公开上传。**

---

## 三、你要整理一份“接口地图”

不要急着写代码。先整理成表格。这个表格非常关键，后面写 skill 就靠它。

建议你建一个文档，长这样：

```text
接口名称：创建出包任务

Method: POST
URL: /api/build/create

请求头：
- Content-Type: application/json
- Cookie: 登录态
- X-CSRF-Token: 是否需要
- Authorization: 是否需要

请求体字段：
- repoId: 代码库 ID，必填
- branchName: 代码分支，必填
- componentList: 配套组件，必填/可选
- pointVersion: 点分号，必填
- integrationBranch: 集成分支，必填
- integrationNode: 集成节点，必填
- packageInfo: 出包信息，必填
- buildType: 默认值 xxx
- env: 默认值 xxx

响应：
- taskId: 出包任务 ID
- detailUrl: 任务详情页
- status: 创建成功/失败
- message: 错误信息
```

然后每个接口都照这个格式整理。

尤其要区分三类字段：

### 1. 用户真正需要填写的字段

例如：

```text
代码库
代码分支
点分号
出包说明
```

### 2. 可以从默认配置继承的字段

例如：

```text
默认组件
默认集成节点
默认编译类型
默认环境
```

### 3. 必须通过前置接口动态获取的字段

例如：

```text
repoId
branchId
componentId
nodeId
csrfToken
taskTemplateId
```

很多页面上显示的是名字，但 POST payload 里传的是 ID。这个一定要注意。

---

## 四、第二阶段：先用 curl/Postman/脚本复现，不要直接写 agent

你要先证明一件事：

> 不打开网页，只用接口，也能创建一次出包任务。

这是整个任务的分水岭。

你可以从 F12 里 Copy as cURL，然后在内网机器上执行。注意，不要把个人 cookie 写死到代码里，这只能用于本地验证。

验证路线：

```text
1. 使用浏览器登录内网网站
2. F12 复制 create build 请求为 cURL
3. 在命令行执行这个 cURL
4. 看是否能创建任务
5. 如果失败，检查 cookie、csrf token、referer、origin、动态字段
6. 成功后，再改其中一个低风险参数，比如出包说明
7. 再次提交，确认接口可控
```

如果 cURL 能跑通，就说明你不需要 UI 自动化，后面可以直接封装 API。

如果 cURL 跑不通，常见原因有：

| 问题                | 现象       | 处理方式                            |
| ------------------- | ---------- | ----------------------------------- |
| Cookie 过期         | 401/403    | 需要登录态管理                      |
| CSRF token 缺失     | 403        | 从页面或初始化接口获取 token        |
| Referer/Origin 校验 | 403        | 保留必要请求头                      |
| 动态字段缺失        | 400        | 补齐页面初始化接口返回的字段        |
| 参数 ID 不匹配      | 创建失败   | 先调列表接口获取合法 ID             |
| 权限不足            | 403/无权限 | 找导师/平台负责人申请服务账号或权限 |

---

## 五、第三阶段：设计 skill 的输入输出

你的 skill 不要把所有 payload 字段都暴露给用户。用户只应该填业务上能理解的字段。

建议输入设计成这样：

```json
{
  "repo": "代码库名称或ID",
  "branch": "代码分支",
  "point_version": "点分号",
  "components": [
    {
      "name": "组件名",
      "version": "组件版本"
    }
  ],
  "integration_branch": "集成分支",
  "integration_node": "集成节点",
  "package_info": "出包说明",
  "use_default_config": true,
  "dry_run": false
}
```

输出建议这样：

```json
{
  "success": true,
  "task_id": "123456",
  "status": "running",
  "detail_url": "http://内网地址/build/task/123456",
  "message": "出包任务已创建",
  "submitted_config": {
    "repo": "xxx",
    "branch": "feature/xxx",
    "point_version": "xxx"
  }
}
```

最终任务完成后可以返回：

```json
{
  "success": true,
  "task_id": "123456",
  "status": "success",
  "artifact_url": "http://内网地址/artifact/xxx",
  "log_url": "http://内网地址/log/xxx",
  "duration": "18m23s"
}
```

失败时返回：

```json
{
  "success": false,
  "task_id": "123456",
  "status": "failed",
  "error_stage": "compile",
  "error_message": "组件 xxx 拉取失败",
  "log_url": "http://内网地址/log/xxx",
  "suggestion": "请检查组件版本或分支权限"
}
```

---

## 六、第四阶段：写一个独立的 API Client

在写 agent skill 之前，你应该先写一个普通脚本或小模块，专门负责跟出包网站后端交互。

结构可以这样：

```text
build_skill/
  README.md
  skill.md
  config.example.yaml
  client.py
  workflow.py
  models.py
  tests/
    test_payload_mapping.py
```

`client.py` 负责接口调用：

```python
class BuildServiceClient:
    def __init__(self, base_url, session):
        self.base_url = base_url
        self.session = session

    def get_default_config(self):
        pass

    def search_repo(self, repo_name):
        pass

    def list_branches(self, repo_id):
        pass

    def list_components(self, repo_id, branch):
        pass

    def create_build_task(self, payload):
        pass

    def get_task_status(self, task_id):
        pass

    def get_task_result(self, task_id):
        pass
```

`workflow.py` 负责业务流程：

```python
def create_branch_build(request):
    # 1. 获取默认配置
    # 2. 校验 repo
    # 3. 校验 branch
    # 4. 补齐组件、集成分支、集成节点
    # 5. 组装 payload
    # 6. dry_run 时只返回 payload，不提交
    # 7. 提交出包任务
    # 8. 返回 task_id 和详情链接
    pass
```

这样做的好处是：
即使后面 AI agent 框架换了，你的核心能力也不用重写。

---

## 七、第五阶段：把它封装成 AI Agent Skill

skill 文档可以写成这样：

```md
# Skill: branch_build_package

## 能力说明

该 skill 用于在公司内网分支编译出包系统中创建分支出包任务，并查询任务状态、日志和产物信息。

## 适用场景

- 为指定代码库和分支创建编译出包任务
- 使用默认配置快速出包
- 根据用户指定的组件、点分号、集成分支、集成节点创建出包任务
- 查询已提交出包任务的状态
- 返回日志链接、任务详情页和产物地址

## 不适用场景

- 绕过权限访问代码库
- 绕过审批流程
- 使用他人 cookie 或 token
- 修改用户未确认的高风险配置
- 自动删除、回滚、覆盖已有产物

## 输入参数

- repo: 代码库名称或 ID
- branch: 代码分支
- point_version: 点分号
- components: 配套组件列表，可选
- integration_branch: 集成分支，可选
- integration_node: 集成节点，可选
- package_info: 出包说明
- use_default_config: 是否使用默认配置
- dry_run: 是否只校验不提交

## 执行流程

1. 读取用户输入。
2. 如果 use_default_config=true，先获取网站默认配置。
3. 根据 repo 查询代码库 ID。
4. 根据 repo 查询分支，校验 branch 是否存在。
5. 获取组件、集成分支、集成节点候选项。
6. 补齐缺省字段。
7. 构造出包 payload。
8. 如果 dry_run=true，只返回待提交配置。
9. 如果 dry_run=false，提交出包任务。
10. 返回 task_id、任务详情页和初始状态。
11. 如果用户要求等待结果，则轮询任务状态。
12. 任务完成后返回日志、产物链接和失败原因。

## 失败处理

- 参数缺失：提示用户补充必要字段。
- repo 不存在：返回可选代码库候选项。
- branch 不存在：返回相近分支候选项。
- 权限不足：提示申请代码库或出包平台权限。
- 出包失败：返回失败阶段、错误信息和日志链接。
- 接口异常：返回 HTTP 状态码、traceId/requestId。
```

---

## 八、你现在最应该做的 10 件事

按优先级来：

### 1. 找到“创建出包任务”的 POST 接口

这是核心接口。你已经开始看 payload 了，继续深入。

你要记住：

```text
URL
Method
Request Headers
Payload
Response
```

尤其是 response 里有没有：

```text
taskId
buildId
jobId
detailUrl
traceId
```

---

### 2. 找到“查询任务状态”的接口

创建任务只是第一步，skill 还要知道任务有没有成功。

通常页面会有这种请求：

```text
GET /api/build/task/{taskId}
GET /api/build/status?id=xxx
POST /api/job/query
```

你可以在出包后盯着 Network，看页面是不是每隔几秒请求一次接口。

---

### 3. 找到“任务详情页”的 URL 规则

比如：

```text
/build/detail/123456
/task?id=123456
/package/task/123456
```

这个很重要，因为 agent 最后可以直接把详情页返回给用户。

---

### 4. 找到“默认配置”来自哪里

你说你选了一下默认配置。这里要弄清楚：

默认配置是：

```text
前端写死的？
后端接口返回的？
根据用户/代码库/分支动态生成的？
```

如果是后端接口返回的，你的 skill 就应该先调用默认配置接口，而不是把默认值写死。

---

### 5. 确认 payload 里的字段含义

不要只保存 payload，要给每个字段标注含义。

例如：

```json
{
  "repoId": "代码库ID",
  "branch": "代码分支名",
  "componentIds": "组件ID列表",
  "integrationNodeId": "集成节点ID",
  "packageDesc": "出包说明"
}
```

如果遇到不知道的字段，可以做小实验：

```text
只改出包说明 → 看哪个字段变了
只换分支 → 看哪个字段变了
只换组件 → 看哪个字段变了
只换集成节点 → 看哪个字段变了
```

这样你就能反推出字段含义。

---

### 6. 做一个 dry-run 模式

这是非常重要的安全设计。

dry-run 不真正提交出包，只做：

```text
校验参数
补齐默认值
生成最终 payload
展示即将提交的配置
```

这样你作为实习生开发时更安全，也方便导师 review。

---

### 7. 不要硬编码你的个人 cookie

开发阶段可以临时用，但正式方案不要这样。

正式方案应该问清楚公司内部 agent 的认证机制：

```text
agent 是否有自己的服务账号？
是否能继承用户登录态？
是否有统一 SSO token？
是否允许调用该出包系统 API？
是否需要申请白名单？
```

这是你需要找导师或平台负责人确认的点。

你可以这样问导师：

> 我已经通过 F12 初步定位到出包系统的创建任务接口。后续如果做成 agent skill，需要确认认证方式：是让 agent 使用服务账号调用出包接口，还是继承当前用户身份？另外，是否已有正式 API 文档或调用白名单流程？

这句话很专业，也不会显得你不知道怎么做。

---

### 8. 加权限和确认机制

出包不是普通查询，它会消耗资源，也可能影响集成环境。所以 skill 里应该设计确认机制。

例如：

```text
低风险：查询配置、查询任务状态 → 不需要二次确认
中风险：创建出包任务 → 需要用户确认
高风险：覆盖正式版本、发布生产、触发集成主干 → 必须明确确认
```

agent 在真正提交前可以输出：

```text
即将创建出包任务：

代码库：xxx
分支：feature/xxx
点分号：xxx
集成分支：xxx
集成节点：xxx
组件：xxx
出包说明：xxx

是否确认提交？
```

---

### 9. 保存日志和 traceId

每次调用接口都要记录：

```text
requestId / traceId
taskId
调用时间
提交人
最终 payload 摘要
接口返回 message
```

不要记录敏感信息：

```text
cookie
token
完整 Authorization
密码
内部密钥
```

如果出错，你可以拿 traceId 找平台同学排查。

---

### 10. 先做最小可用版本

不要一开始就支持所有复杂场景。

你的 V1 可以只支持：

```text
使用默认配置
指定代码库
指定分支
指定点分号
填写出包说明
提交任务
返回 taskId 和详情页
查询任务状态
```

V2 再支持：

```text
自定义组件
自定义集成分支
自定义集成节点
失败原因分析
日志摘要
产物地址提取
批量出包
```

---

## 九、推荐你的整体时间路线

### 第 1 天：抓包和整理接口

目标：

```text
整理出创建任务接口、状态查询接口、默认配置接口。
```

产物：

```text
接口地图文档
一次成功出包的完整 payload
一次成功出包的 response
```

---

### 第 2 天：复现接口调用

目标：

```text
用 curl 或 Postman 在内网复现一次创建出包任务。
```

产物：

```text
可复现的请求
字段含义表
接口错误码记录
```

---

### 第 3 天：写 API client

目标：

```text
不用 agent，只用脚本完成创建任务和查询状态。
```

产物：

```text
client.py
create_build_task()
get_task_status()
dry_run()
```

---

### 第 4 天：写 skill 文档和编排逻辑

目标：

```text
把脚本封装成 agent 能调用的 skill。
```

产物：

```text
skill.md
workflow.py
输入输出 schema
错误处理说明
```

---

### 第 5 天：找导师 review

目标：

```text
确认权限、认证、接口稳定性、安全边界。
```

你要重点问：

```text
1. 是否允许 agent 直接调用这些接口？
2. 是否有正式 API 文档？
3. agent 应该用服务账号还是用户身份？
4. 是否需要审批或白名单？
5. 出包任务是否需要二次确认？
6. 出包失败日志在哪里看？
```

---

## 十、你这个任务的关键判断

你现在最重要的判断是：

### 情况 A：后端接口可以直接调用

这是最理想的。

你应该做：

```text
F12 抓接口
复现请求
封装 API client
写 agent skill
加参数校验和确认机制
```

### 情况 B：接口依赖复杂 token，但可以通过登录态调用

也可以做。

你应该做：

```text
研究 token 获取流程
不要硬编码 token
接入公司统一认证方式
让 agent 继承用户身份或使用服务账号
```

### 情况 C：后端接口不能稳定调用，只能操作页面

这是备选方案。

可以考虑：

```text
Playwright / Selenium UI 自动化
```

但这不是首选，因为 UI 容易变，维护成本高。

---

## 十一、你可以直接照着这个最小版本设计

### Skill 名称

```text
branch_build_package
```

### V1 能力

```text
使用默认配置，为指定代码库和分支创建分支编译出包任务。
```

### V1 输入

```json
{
  "repo": "xxx",
  "branch": "feature/xxx",
  "point_version": "1.2.3.4",
  "package_info": "测试 feature/xxx 分支出包",
  "dry_run": true
}
```

### V1 执行逻辑

```text
1. 获取默认配置
2. 查询 repo 是否存在
3. 查询 branch 是否存在
4. 生成最终出包 payload
5. dry_run=true 时返回 payload 摘要
6. dry_run=false 时提交任务
7. 返回 taskId 和详情页
8. 用户需要时继续查询状态
```

### V1 输出

```json
{
  "success": true,
  "task_id": "BUILD-20260709-001",
  "detail_url": "http://内网出包系统/task/BUILD-20260709-001",
  "status": "running",
  "message": "出包任务已提交"
}
```

---

## 十二、你没有代码库权限怎么办？

这件事要分开看。

### 不影响的部分

你仍然可以做：

```text
分析出包网站接口
整理 payload
复现创建出包任务
封装 skill
查询任务状态
返回详情页和日志
```

因为代码拉取和编译可能是由出包系统服务端完成的，不一定需要你本地访问代码库。

### 可能影响的部分

你可能做不了：

```text
校验某个分支是否真实存在
读取代码库内容
分析编译失败原因里的源码问题
自动判断组件兼容性
```

这些可以交给出包系统接口判断，或者后续申请权限。

你可以在 skill 里写清楚：

```text
该 skill 不直接访问代码库，只通过出包平台提供的接口校验代码库和分支信息。
```

这句话很关键，能降低权限问题带来的阻碍。

---

## 十三、你可以跟导师这样汇报

你可以直接用下面这段：

> 我准备把分支编译出包 skill 分成三步做。第一步先通过浏览器 F12 梳理出包网站的接口链路，包括默认配置、代码库/分支/组件查询、创建出包任务、任务状态查询、日志和产物链接。第二步先用 curl 或脚本在内网复现接口调用，确认不依赖页面点击。第三步再封装成 agent skill，支持 dry-run、参数校验、二次确认、任务提交和状态查询。
>
> 目前我还没有代码库权限，但这个 skill 初期不需要直接访问代码库，只需要调用出包平台接口。需要确认的是：agent 正式调用时应该使用服务账号、用户登录态，还是公司统一 SSO 认证；另外也想确认这些接口是否有正式文档或白名单申请流程。

这段很适合你现在的身份，既专业，也不会显得冒进。

---

## 十四、最终建议

你现在不要把重点放在“AI 怎么写”上，而是放在这三个问题上：

```text
1. 出包网站提交任务的真实 API 是什么？
2. 提交任务需要哪些字段，这些字段从哪里来？
3. agent 正式调用时用什么身份和权限？
```

只要这三个问题搞清楚，skill 本身其实就是一层稳定封装。

你下一步最值得做的是：**把那次 POST payload 以及相关 GET 请求整理成字段表**。字段表整理出来后，整个任务就会从“我不知道怎么做”变成“我只是在把一个接口流程产品化”。