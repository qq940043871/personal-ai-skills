---
name: dev-uniapp-to-miniprogram
description: 把 uni-app（Vue3）项目移植成原生微信小程序工程，并做静态 + 业务双层自检后上传。当用户说「参考 X 项目开发一个微信小程序」「把 uni-app 项目改成小程序」「uni-app 转小程序」「移植成小程序」，或需要在空目录里新建一个可上传的原生小程序工程时使用。产出：含 project.config.json 的原生小程序工程 + 已通过校验的页面/数据层 + 上传结果。
agent_created: true
author: hasWhere
allowed-tools:
disable: false
---

# uni-app → 原生微信小程序 移植

## 为什么走原生而不是 uni-app 编译

`workbuddy_sites_deploy` 靠**磁盘特征**判定小程序目录：`project.config.json` / `app.wxss` / `app.acss` / `app.ttss`，或含 `pages` 数组的 `app.json`。
uni-app 源码目录里什么都没有，必须先跑 `build:mp-weixin` 产出 `dist/build/mp-weixin`——多一层构建就可能失败。**直接写原生工程更稳，且不依赖任何 npm 依赖。**

## 核心映射表

| uni-app / Vue3 | 原生小程序 |
|---|---|
| `<view>/<text>/<image>` | 同名，WXML 直接用 |
| `<scroll-view scroll-x>` 做横向排列 | **不要用** —— 见第 8 步，改成 `display:flex; flex-wrap:wrap` |
| `uni.xxx()` | `wx.xxx()` |
| `uni.chooseImage({sizeType,sourceType})` | `wx.chooseMedia({count,mediaType:['image'],sourceType,sizeType})`，路径取 `res.tempFiles[0].tempFilePath` |
| `uni.navigateTo/switchTab/navigateBack` | `wx.` 同名，**switchTab 不能带参** |
| `reactive()` store + `computed()` | 纯 JS 模块 + 页面 `onShow` 拉快照 `setData` |
| `<script setup>` + `defineProps/defineEmits` | `Component({properties, observers, methods})` + `triggerEvent` |
| `v-if / v-else-if / v-else` | `wx:if / wx:elif / wx:else` |
| `v-for="x in list" :key="id"` | `wx:for="{{list}}" wx:key="id"`（字符串数组用 `wx:key="*this"`） |
| `@click.stop` | `catchtap`（阻止冒泡） |
| `:style="{...}"` | `style="..."`，**必须字符串拼接** |
| `{{ a > b }}` 等表达式 | 支持；但 `{{}}` 内不要写函数调用、复杂逻辑，提前在 JS 里算好 |
| `@media (min-width:768px)` 平板分支 | 直接删（小程序是手机端） |
| `uni.scss` 全局变量 | `app.wxss` 里写字面量 |

## 步骤

### 1. 摸清源工程（不要凭猜）
读：`store/`（业务灵魂）、`pages.json`（页面与 tabBar）、`manifest.json`、`App.vue`、`uni.scss`，以及每个 `pages/*/*.vue` 和 `components/*.vue`。
用 `wc -l` 排出体积，**优先精读 store 和主页面**。

### 2. 判定哪些要砍
明确告诉用户砍了什么、为什么。通常砍：
- 平板/横屏布局页（含 `PadLandLayout`/`LeftNav`/`RightPanel` 一类组件）
- `web-view` 指向 `localhost` 的 3D/外部页
- 巨型弹窗组件 → 拆成独立页面（1000 行的 `MemberManageModal` 别硬搬）

### 3. 资源必须压缩（最容易翻车的一步）
**小程序主包上限 2MB。** 先 `ls -la` 看资源：
- 大图（几百 KB~几 MB）→ 用 Pillow 压到 160~240px JPEG q82（脚本见 `assets/make_assets.py`），一张约 5KB
- **头像素材要做成「满圆贴图」**：原图常是「方形底色 + 内圆」结构，直接缩放会在圆形容器里露出方底四角；当方底与内圆颜色接近时（浅蓝方底 + 稍浅蓝内圆）还会出现一圈看不清的接缝。做法：测出内圆 → 裁到内切圆 → 圆外像素填成圆底色（带羽化），五张口径就统一了
- 大模型/视频（几十 MB）→ 直接不带
- tab 图标保留原样，但**单张必须 < 40KB**，否则小程序报错

把压缩后的资源放在 `images/` 下。**引用方式见第 7 步——不要直接写 `/images/xxx.jpg`，这条路径在预览环境里解析不到。**

### 4. 写工程骨架
```
app.js  app.json  app.wxss  project.config.json  sitemap.json
utils/store.js         ← 业务数据层（CommonJS）
components/<name>/{index.js,index.json,index.wxml,index.wxss}
pages/<name>/{<name>.js,.json,.wxml,.wxss}
images/
tools/                 ← 自检脚本，packOptions.ignore 掉
```
`project.config.json` 关键字段：`compileType: "miniprogram"`、无 AppID 时 `"appid": "touristappid"`、`setting.es6: true`。
`packOptions.ignore` 里加上 `tools` 目录。

### 5. 数据层设计（store.js 移植要点）
- 模块级 `let members = loadMembers()`，`getMembers()` 返回引用，页面前 `clone()` 再 setData
- `wx.getStorageSync/setStorageSync` 做持久化；所有写操作末尾 `persistMembers()`
- **把 Vue 的 computed 改成普通函数**（`getFamilyStats()`、`getCoupleBond()`）
- **把弹窗状态改成 return 值**：原 `doCheckin` 写 `checkinModal` 对象，改成 `return { member, task, evolved, newStage, verse }`，页面拿到后 setData
- tabBar 间跳转要传参 → 用模块级 `setPendingXxx()/consumePendingXxx()`

### 6. 页面要点
- 页面 `data` 里**先声明所有会 setData 的字段**（含空数组 `[]`、空对象 `{}`），漏声明会静默不生效
- 复杂视图模型在 JS 里算好再 setData（growPercent、doneRate、scoreLabel…），WXML 只做展示
- `bindtap` 取参用 `e.currentTarget.dataset.xxx`，`data-member-id` → `dataset.memberId`
- 定时器（比武动画等）存 `this.timers`，`onUnload`/`onHide` 里 `clearTimeout`

### 7. 头像/图片：优先内联 base64，别赌路径（**最容易误诊的一步**）

#### 7.1 先分清是哪一种「坏」（关键！）

现场看到的「图标有问题」是两类完全不同的病，**修法相反**，必须先分清：

| 现象 | 病因 | 修法 |
|---|---|---|
| 图片位置是个**破图小方块**（灰底 + 折角纸页 + 绿色山形的那种图标） | **资源根本没加载出来** → 路径/打包问题 | 见 7.2 |
| 图片显示了，但**是方块 / 圆外露出一圈色底 / 脸被圆边裁掉** | 圆角裁切没生效 → 样式问题 | 见 7.4 |

**只看用户截图里的「破图小方块」就能立刻排除掉所有构图、配色、裁切问题**——那是加载失败，不是画得不好。

#### 7.2 根因：`<image src="/images/...">` 的前导斜杠在预览环境里解析不到

- tabBar 的 `iconPath` 写的是 **`images/tab/home.png`（无前导斜杠）**，能被正确解析
- `<image src="/images/avatars/xxx.jpg">`（**带前导斜杠**）在预览运行时里解析失败 → **全站图片一起破图**

迷惑点：报障经常是「**只有爸爸的图标有问题**」。其实五张全坏，只是**底色高饱和（浅蓝/粉）的那张在白色卡片上最扎眼**，其余几张贴白底「看着还像圆的」没人报。**用户点名某一个人 ≠ 只有那一个人坏了。**

> 顺带说清：真机微信要求 `/images/...`（根绝对路径），而预览环境恰好相反。**两边都要通，就别用路径。**

#### 7.3 首选方案：把图片内联成 base64

生成 `utils/avatars.js`（脚本见 `assets/gen_avatars_b64.py`），`store.js` 里 `const AVATARS = require('./avatars.js')` 即可。

要点：
- 格式 `data:image/jpeg;base64,<...>`，**串里绝对不能有换行/空白**（微信遇到换行直接不显示，且不报错）
- 生成时**按定长切块再 `join('')`**，既保证是单行、又避免出现几千字符的超长行（编辑器/工具会截断）
- 200×200、q85 约 5~9KB/张，base64 后约 8~12KB/张，5 张共 ~55KB——对 2MB 主包毫无压力
- 图片**仍然留在 `images/`**（保留素材、方便重新生成），只是不再被引用

**验证 base64 真能还原**（别只检查语法）：
```python
raw = base64.b64decode(uri[23:]); Image.open(io.BytesIO(raw)).load()  # 能 load 才算过
```

另外给 `<image>` 挂 `binderror` 兜底（加载失败就换成 emoji，至少不是破图）：
```html
<image wx:if="{{item.avatarUrl}}" class="mc-avatar-img" src="{{item.avatarUrl}}"
       mode="aspectFill" binderror="onAvatarError" data-id="{{item.id}}" />
```

#### 7.4 次要问题：圆角要写在 `<image>` 本身，别只靠父容器裁

只靠父容器的 `overflow:hidden + border-radius:50%` 裁 `<image>` 不可靠，失效时头像会变**方块**。
```css
.mc-avatar-img { width: 100%; height: 100%; display: block; border-radius: 50%; }
```
`.bond-avatar`、`.photo-preview` 这类**类名直接挂在 `<image>` 上**的写法本来就是对的。

> 注意：这一条是**样式层**的加固，**不是**「破图」的病因。别把它当成万能解释——上一版技能就是这么误诊的：截图里明明是破图小方块，却归因到圆角裁切，白跑一整轮。

#### 7.5 排查动作
```bash
grep -rn "<image" --include="*.wxml" .          # 列出所有图片
grep -rn "src=\"/" --include="*.wxml" .         # 找带前导斜杠的路径（重点嫌疑）
grep -rn "images/" --include="*.json" .         # 对比 tabBar 的无斜杠写法
```

### 8. 横向排列：用 `flex-wrap`，不要用 `scroll-view`（血泪坑）

**运行时的 `scroll-view` 是一个没有任何 overflow 边界的普通块**——既不裁切内容，也不能横向滚动。两个症状：

**症状 A：浮标压住内容。** 同一行里 `scroll-view` 旁边还有兄弟元素（分数条、徽标）时，标签从 `scroll-view` 里**裸溢出**，而兄弟元素按正常流排在 `scroll-view` 的**计算宽度之后**，于是被溢出的标签压在下面：

```
[爸爸][妈妈][ 👵奶奶 ← 溢出部分 ][ 小宝 ]
              └── 浮标按正常流排在这里，盖住标签
```

**症状 B：后面的成员根本点不到。** 没有滚动能力 → 溢出的第 4、5 个成员既看不见也点不了，用户永远选不到它们。

**复现/确诊方法**（比嘴解释快）：按页面 CSS 用 Playwright 渲一张对照图，其中把 `scroll-view` 当普通块处理（`view,scroll-view{display:block}`），rpx 按 `屏宽/750` 换算。浮标落点与用户截图一致 → 确诊。

**改法（所有横排行一律照此办理）：**

| | 改前 | 改后 |
|---|---|---|
| WXML | `<scroll-view scroll-x class="X" show-scrollbar="{{false}}">` | `<view class="X">` |
| 容器 CSS | `.X { white-space: nowrap; }` | `.X { display: block; width: 100%; }` |
| 行 CSS | `.X-row { display: inline-flex; }` | `.X-row { display: flex; flex-wrap: wrap; }` |
| 同行浮标 | 和 `scroll-view` 同一个 flex 父容器 | 父容器改普通块，浮标改 `display:inline-flex` **独立成行** |

要点：
- **容器上的 `white-space: nowrap` 必须删掉** —— flex 容器带 `nowrap` 会阻止换行，删掉才会 wrap。标签自己的 `white-space: nowrap` 保留（那只是防止标签内文字折行，不影响换行）
- 既然不再滚动，就把 `scroll-view` 直接换成 `<view>`，省掉组件的额外语义
- 浮标与内容同行 = 永远有层叠风险，**独立成行最省心**

**验收**（别只看语法）：
```python
# 渲染后量一遍：有没有元素超出页面右边界，应为 0
pg.evaluate("() => [...document.querySelectorAll('.item')]"
            ".filter(e => e.getBoundingClientRect().right > 屏宽).length")
```
再截图肉眼确认没有重叠、所有人都在屏内。

#### 8.1 纵向变体：`scroll-view` 在受限弹窗里会把内容漏到按钮上

同一个根因（**`scroll-view` 没有 overflow 边界**）的纵向版本，发生在「弹窗面板 `max-height` + flex 纵向三段（头/体/底）」里：

```css
.pdm-panel { max-height: 86vh; display:flex; flex-direction:column; overflow:hidden; }
.pdm-body  { flex:1; min-height:0; }        /* 是个 scroll-view scroll-y */
.pdm-footer{ flex-shrink:0; }               /* ← 常常忘了给背景色 */
```

`scroll-view` 不裁切 → body 内容溢出它的 flex 盒子，一路画到 footer 上。若 `.pdm-footer` **没有 `background`**，溢出的内容会**透过**按钮行显示出来，用户看到的就是「**按钮上糊着别的内容**」；面板的 `overflow:hidden` 只在面板边缘裁，**管不住 body 与 footer 之间**。

**典型报障**：「按钮遮挡内容」/「按钮旁边多出一段文字」。

**改法（双保险，两边环境都成立）：**

```css
.pdm-body {
  flex: 1; min-height: 0;
  overflow-y: auto;                /* 预览环境(webview)里真能裁 + 真能滚 */
  -webkit-overflow-scrolling: touch;
}
.pdm-footer {
  background: #FFFFFF;             /* 关键：不透明，漏出来也盖得住 */
  position: relative; z-index: 2;  /* 关键：始终压在内容之上 */
}
```

- **保留 `scroll-view`**：真机微信靠它滚动，上面两条 CSS 在真机无副作用（scroll-view 自身已处理滚动）
- 不要改成「去掉 `max-height` 让它自然长高」——长内容会顶出屏幕，更糟
- body 的 `padding-bottom` 别给太小（原 8rpx 会让滚到底的内容贴住按钮），给到 24rpx

**确诊/验收**（Playwright 渲染，比肉眼可靠）：
```python
# 1) 滚到底后，底部内容块是否完整落在 body 框内
body.scrollTop = body.scrollHeight
cond.getBoundingClientRect().bottom <= body.getBoundingClientRect().bottom + 1
# 2) 像素级：footer 矩形内「内容底色」的占比，修复前 27.6% → 修复后 0.03%
```
对照跑修复前/后两个变体，差值足够大才算真的修掉。

### 8.2 tabBar 与 WXML 的硬限制（踩过才写进来）

| 限制 | 说明 | 对策 |
|---|---|---|
| **tabBar 最多 5 项** | 想加第 6 个 tab 必须先腾位置；询问用户「哪个并入哪里」而不是自作主张删 | 换 icon：用 PIL 程序化生成（78×78 RGBA，超采样 8× 后缩小），灰色 `#8A8178` + 选中橙 `#FF8A65` 与现有一致 |
| **WXML 表达式不支持位运算** | `{{ (a/b*100) \| 0 }}` 直接语法错误或渲染空 | 一切计算（百分比、取整、条件拼接）在 JS 里算好 setData，WXML 只做展示 |
| **`wx.showActionSheet` 最多 6 项** | 成员切换、列表选择超过 6 项会被截断 | `slice(0, 6)` 兜底；成员可能变多时改用独立选择页 |
| **tabBar 页不能带参跳转** | `switchTab` 不支持 query | 模块级 `setPendingXxx()/consumePendingXxx()`；但若页面已改为「当前成员」视角，优先直接切视角再跳，比 pending 意图更直白 |

**单人视角重构模式**（全家多角色 → 默认单人）：store 加 `currentMemberId` 持久化 + `isOnboarded()/setCurrentMember()/getCurrentMember()`；未引导时各 tab 页 `onShow` 头部 `wx.reLaunch` 到 welcome 页（选身份 → 加入家庭）；全家数据（排行/结算/总览）收进一个「家庭」tab。切换身份用 actionSheet，删除当前成员要 `clearOnboarding()` 回引导。


### 9. 双层自检（**必做，别跳**）
```bash
# 静态层
python tools/validate.py
# 每个 js 过语法
for f in $(find . -name "*.js" -not -path "./node_modules/*"); do node --check "$f"; done
# 业务层：stub 掉 wx，把 store 全流程跑一遍
node tools/selftest.js
```
脚本模板在 `assets/`，复制后按当前项目改断言。

**validate.py 的坑**：
- 解析 WXML 标签前**必须先把引号内的属性值遮蔽**，否则 `wx:if="{{age <= 4}}"` 里的 `<` 会被误判成标签开头，报一堆假的「多余闭合标签」。
- 体积统计**必须按 `project.config.json` 的 `packOptions.ignore` 排除**，否则 `tools/` 里几张调试图就能让"总体积"虚高到 2.5MB、误报超过主包限制。

### 10. 上传
`workbuddy_sites_deploy`：
```json
{ "directory": "<abs path>", "action": "deploy",
  "userAskedToPublish": true, "appName": "短名", "domainPrefix": "ascii-slug" }
```
- 目录里（或其一级子目录）有 `project.config.json` → 自动走小程序路径，返回 `sites_miniprogram_app_created`
- 返回 **`deployed: false` 是正常的**：小程序没有分享链接；**不要谎称已发布**，也**不要写个 H5 顶替**
- 转达 `userMessage`（原文，保留加粗），然后 **STOP** —— 第 2 步由用户在小程序应用预览面板点右上角「分享」完成
- 不要自己编造「左侧边栏应用列表」这类路径

**点「分享」后报「小程序代码上传失败，请重试」的排查顺序**（2026-10-01 实战）：
1. **先查项目目录真实总量**（`du -sk` 各子目录），而不是只看 validate.py 的"打包体积"——`packOptions.ignore` 只对微信开发者工具和自制脚本生效，**平台上传器可能整目录压缩上传**，`tools/` 里 6.9MB 的调试图直接把包顶爆 2MB 上限，表现就是这句 toast
2. 时间线对比：如果"早期版本上传成功、加了大量本地工具产物后开始失败"，基本可锁定体积
3. 解法：把 tools/ 等大目录**整体移出小程序目录**（如 `../<project>-tools/`），再批量修脚本内路径（`dirname(dirname(__file__))` 型 ROOT、`require('../utils/…')` 型引用），修完在新位置重跑 selftest + validate
4. 结构排查清单：pages 四件套、usingComponents（注意 `/` 开头绝对路径）、tabBar 图标 ≤40KB、`node --check` 全部 JS、pages 无重复——都过了再怀疑服务端临时故障（让用户重试/发完整 toast 文字）
5. toast 文字常被截断，**让用户把冒号后面的完整错误发来**再定位

## 红线
- **横排一律 `display:flex; flex-wrap:wrap`，不要用 `scroll-view scroll-x`**（预览环境里它没有 overflow 边界：既压住后面的元素，又让后几个成员点不到）
- 换行容器上**不能留 `white-space: nowrap`**，它会阻止 flex 换行
- **受限高度弹窗（头/体/底三段）里的固定底栏必须给 `background` + `position:relative; z-index`**，中间那段的 `scroll-view` 要显式加 `overflow-y:auto`。否则内容会漏到按钮上，报障是「按钮遮挡内容」
- 报障先分清「移植 bug」还是「原设计如此」——先对比原项目代码；**是原设计且用户不满意就直接改设计，别拿「原项目也这样」当挡箭牌**（例：图鉴未获得显示 `？？？` 是原设计，但 5/22 收集时首屏全是问号，体验差 → 改成真容置灰）
- **看到「破图小方块」= 加载失败（路径/资源），先去查路径，别去调构图、配色、裁切**
- 图片别用 `/images/...` 这种前导斜杠路径，**优先内联 base64**（真机与预览环境的路径规则相反）
- base64 串里**不能有换行**，生成时切块 + `join('')`
- 用户只点名「某一个人的头像有问题」时，**先假设全站图片都坏了**，再去找为什么只有那张最明显
- 圆角一律写在 `<image>` 自己的类上，**不要只靠父容器 `overflow:hidden` 裁切**（这是样式加固，不是破图的病因）
- 不要在 personal 目录做删除操作
- 不要用 `rm` 清理，涉及文件删除先问用户
- 上传前确认所有文件已落盘（`ls` 复核），不要边写边传
