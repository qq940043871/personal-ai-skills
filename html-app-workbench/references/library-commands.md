# 存储与发布命令参考（妙搭 / lark-apps）

原型之后的落地：发布成链接、上真数据库。所有命令来自 lark-apps skill，**运行时以 `lark-cli apps +<cmd> --help` 输出为准**；认证、`--as user`、exit 码协议见 lark-shared。本文件不定义新命令。

## 路径判定（先选路，再执行）

| 用户诉求 | 路径 | 步骤 |
|---|---|---|
| 自己本地用 | 不发布 | 交付 index.html 即止 |
| 要分享链接，数据在各设备本地 | **静态发布** | 下方 3 步链 |
| 数据要进真库（换设备不丢 / 多人读写） | **全栈升级** | 下方 6 步链 |

注意：妙搭 html 类型应用**没有前端直连数据库的通道**；要真库必须走 full_stack。所以原型阶段的 `WorkbenchDB` 接口（见文末 SDK 契约）设计成可整体替换——升级时页面代码不改，只换数据层实现。

## 静态发布 3 步链

```bash
# ① 创建 html 应用 → 取 data.app.app_id
lark-cli apps +create --name "XX工作台" --app-type html --description "一句话描述"

# ② 发布（先过下方体积红线）→ 取 data.url 即发布态链接
lark-cli apps +html-publish --app-id app_xxx --path ./index.html

# ③ 交付前放开可见范围（默认仅创建者可见，直接发别人打不开）
lark-cli apps +access-scope-set --app-id app_xxx --scope tenant   # 或 public / specific
```

体积红线（任一超限客户端直接拒绝，先量再发）：单个 `.html` ≤10MB；打包 tar.gz ≤20MB；未压缩总量 ≤200MB。单文件工作台正常远低于 1MB，基本不会触线；超限说明混入了外链资源或内嵌大图，回到硬性规则 2 排查。

## 全栈升级 6 步链（真数据库）

```bash
# ① 创建 full_stack 应用（自带 dev/online 多环境，勿再 +db-env-create）
lark-cli apps +create --name "XX工作台" --app-type full_stack --description "..."

# ② 拉源码到本地
lark-cli apps +init --app-id app_xxx --dir ./xx-workbench

# ③ 建表（dev 环境；SQL 由 assets/templates/schema-template.json 生成）
lark-cli apps +db-execute --app-id app_xxx --environment dev \
  --sql "CREATE TABLE records (id TEXT PRIMARY KEY, title TEXT NOT NULL, ...);" --yes

# ④ 验结构（--format pretty 直接看 DDL）
lark-cli apps +db-table-get --app-id app_xxx --table records --environment dev --format pretty

# ⑤ 导种子数据（高危，需 --yes；文件 .csv/.json ≤1MB、≤5000 行，超限分批）
lark-cli apps +db-data-import --app-id app_xxx --table records --file ./seed.csv --environment dev --yes

# ⑥ 部署上线：本地改动必须先 commit + push（+release-create 部署的是远端 sprint/default，不是本地工作区）
cd ./xx-workbench && git add . && git commit -m "feat: XX工作台" && git push origin sprint/default
lark-cli apps +release-create --app-id app_xxx                     # 记下 release_id
lark-cli apps +release-get --app-id app_xxx --release-id <id>      # 轮询：finished→online_url；failed→error_logs
```

`+init` 完成后**必须**执行 `cat <project-path>/.agents/skills/plugin-guide/SKILL.md` 读仓库插件指引（插件目录、实例配置、调用代码生成方式都在里面）；文件不存在则跳过。

## SDK 契约（前端数据层）

原型阶段使用 `assets/templates/sdk-init.js` 的 `WorkbenchDB`（ES5 + localStorage），接口固定为：

```
WorkbenchDB.init(schema)              // 注册表结构（schema-template.json），空表自动灌 seed
WorkbenchDB.list(table [,filterFn])   // 全量/过滤读取，返回行数组（新→旧）
WorkbenchDB.insert(table, row)        // 返回 {ok, errors, row}；自动补 id / created_at
WorkbenchDB.update(table, id, patch)  // 局部更新，返回 {ok, errors, row}
WorkbenchDB.remove(table, id)         // 删除一行
WorkbenchDB.seed(table)               // 手动重灌种子数据（会覆盖，需先确认）
WorkbenchDB.clear(table)              // 清空（破坏性，必须走确认弹层）
```

升级 full_stack 后：**不要臆造服务端 SDK 函数名**——以仓库内 `.agents/skills/plugin-guide/SKILL.md` 和项目脚手架代码为准，把 WorkbenchDB 的 localStorage 实现换成同接口的服务端实现（服务器 API + `+db-execute` 同源的 SQL），页面渲染代码不动。

## lint 避坑清单

交付前逐条对照（历史踩坑沉淀）：

**ES5 语法（最常见翻车点）**
- [ ] 无箭头函数 `=>`、无 `let/const`、无模板字符串反引号
- [ ] 无 `async/await`、无 `fetch`、无 class、无解构/展开 `...`、无默认参数
- [ ] 遍历用 `for` 循环或 `forEach/filter/map/indexOf`（都是 ES5 安全项）；不用 `find/some 的箭头写法/includes`（`includes` 用 `indexOf(...) !== -1` 替代）
- [ ] 字符串拼接用 `+`，对象字面量不留尾逗号

**命令与参数**
- [ ] 环境参数是 `--environment dev|online`，旧名 `--env` 已移除、传了报 validation 错
- [ ] 未开多环境的应用其库在 `online`，必须显式 `--environment online`（默认 `dev` 分支不存在会报错）
- [ ] `+db-execute` 是 high-risk-write：执行一律要 `--yes`；会删/丢数据的语句先 `--dry-run` 给用户确认，不要静默补 `--yes`；返回 `confirmation_required`（exit 10）时按协议向用户确认后重试
- [ ] 多条 SQL 默认逐条独立提交，中途失败**前面的已落地**；要么按报错里的 `(at statement N of M)` 只跑剩余语句，要么显式写 `BEGIN … COMMIT`
- [ ] `+db-data-import/export` 限额：≤1MB 且 ≤5000 行，超限分批
- [ ] 本地文件参数（`--file/--output/--path`）用工作目录内相对路径，绝对路径会被拒

**DSDK 错误码（旧环境资料库 lint）**
历史项目中出现过 DSDK008、DSDK011 等 DSDK 前缀错误码，属于平台内部 lint、无公开文档。处理原则：**以报错输出的 hint 文本为准**，先对照上面的 ES5 清单和「SDK 是否 init 后才调用、是否重复 init」排查；修复后重跑检查确认。遇到新错误码时把「码 ↔ 原因 ↔ 修法」补进本清单，攒成速查表。

## 发布护栏（交付链接前必读）

- `+list` 的 `is_published=true` 只说明历史上发布过，**不代表本次内容已部署**；必须有本轮 `+html-publish` 成功返回或 `+release-get finished`。
- 开发态链接 `https://miaoda.feishu.cn/app/{app_id}` 只是管理/继续开发入口，**不能当分享链接**。
- 发布态链接：html → `+html-publish` 的 `data.url`；全栈 → `+release-get` 的 `online_url`。
- 发布态链接默认**仅创建者可见**：交付时先告知，再问是否 `+access-scope-set` 放开（可先 `+access-scope-get` 查当前范围）。
- 重新发布同一应用复用原 `app_id`，重跑 `+html-publish` / `+release-create` 即可，不要新建应用。
