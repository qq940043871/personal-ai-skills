# Blender MCP 接入与 agent 建模工作流

## 本机已装好的配置（2026-10-31 实测，无需重装）

- Blender：`C:\Users\qq940\AppData\Local\Programs\Blender Foundation\Blender 4.5\blender.exe`（4.5.14 LTS，probe 脚本能自动找到）
- MCP 插件：`%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\blender_mcp.py`
- WorkBuddy `~/.workbuddy/mcp.json`：`{"command": "...uvx.exe", "args": ["mcp-for-blender"]}`（mcp-for-blender 分支，非 ahujasid 原版，工具接口兼容）
- uvx：anaconda 自带
- ⚠️ 每次开 Blender 后要在 3D 视口侧栏（N 键）BlenderMCP 面板点 **Start MCP Server**，socket 9876 才会监听

## 安装（三件套，新机器参考）

1. **Blender**：https://www.blender.org/download/ ，装完确认 `blender --version` 可用（或记住安装路径，probe 脚本能找到）。
2. **blender-mcp 插件（Blender 端，socket server）**：
   - 下载 https://github.com/ahujasid/blender-mcp 的 `addon.py`
   - Blender → Edit → Preferences → Add-ons → Install → 选 addon.py → 勾选启用
   - 4.2+ 也可走 Extensions 搜索安装（装完在 `extensions/blender_org/blender_mcp*`）
   - 在 3D 视口侧栏（N 键）找到 BlenderMCP 面板 → **Start MCP Server**（默认端口 9876）
3. **MCP server（agent 端）**：装 [uv](https://docs.astral.sh/uv/) 后，在 `~/.workbuddy/mcp.json` 的 `mcpServers` 里加：

```json
"blender": { "command": "uvx", "args": ["blender-mcp"] }
```

   写完后在 WorkBuddy 连接器管理页右上角自定义连接器入口对新 server 点「信任」才会激活。

## Agent 建模工作流（效率生死线）

Blender MCP 是盲操作：每个截图回环好几秒。**用对工具，效率差十倍**：

| 要做的事 | 用什么 | 别用什么 |
|---|---|---|
| 建几何/材质/灯光 | `execute_blender_code`（一次一轮整段 Python） | 一步步 create_primitive + set_property |
| 看效果 | **只在关键节点** `get_viewport_screenshot` | 每一步都截图 |
| 长流水线（生成/导出） | 保存 .blend 后走 CLI（`blender --background --python`） | 经 MCP 逐条跑 |
| 查场景状态 | `get_scene_info` / `get_object_info` | 凭记忆猜对象名 |

### 建模规范（与姊妹技能资产对齐）

1. **真实尺寸（米）**：储罐 Ø32m 就是 32，别按"看起来差不多"。
2. **原点底部中心**：落地时 `position:[x,0,z]` 直接用。
3. **每设备一个 Collection**，命名 `ASSET_<id>`（如 `ASSET_TANK-01`）——export_webgl.py 的 `--collection` 按这个逐个导出。
4. **绝不依赖选中态**：headless/远程操作下 `primitive_cylinder_add` 之后旧物体仍处于选中态，`transform.rotate/scale` 会带着全场一起动（实测坑：细节"消失"，其实全转到别处了）。正确姿势：创建前 `select_all(DESELECT)`，创建后用**数学方式**设 `rotation_euler` 再立即 `transform_apply`。
5. **倒角优先**：工业设备真实感第一来源是边缘高光，板件/壳体全加 BEVEL（width 0.02~0.06, segments 2）。
6. **人体工学尺寸不随主体缩放**：栏杆永远 1.1m、踏距 0.32m、门高 2.1m。罐子可以 Ø32m，栏杆不能放大成 3m。
7. **材质走 Principled BSDF**：Base Color 用 sRGB²·² 转线性（见 gen_models_blender.py 的 `mat()`），别直接塞 sRGB 值（会发白）。

### 建模前先跟用户对清单

- 让用户给：照片 / CAD / 设备清单 / 估算尺寸（任一即可，全没有就按行业惯例估）
- 确认建模清单：哪些设备、每个的 LOD 级别（hero 主角 / mid 常规 / bg 远景减面）
- **先建 hero 设备给用户看一眼截图**，确认风格再铺开——别一口气建完 12 个设备然后被推倒重来

## 已知坑位

- **MCP server 连不上**：先看 Blender 里 MCP Server 是否点了 Start（socket 9876）；再确认 uvx 在 PATH。
- **Blender 崩了/卡了**：MCP 操作的是真实 Blender 进程，注意先保存 .blend 再做危险操作（删除/布尔）。
- **导出走 CLI 不是 MCP**：`export_webgl.py` 用 Blender 自带 Python 跑，系统 python 没有 bpy 模块。
- **贴图文件路径**：Blender 材质引用的贴图若是绝对路径，换机器/发布前要 Pack（File → External Data → Pack Resources），否则导出 GLB 丢贴图。
