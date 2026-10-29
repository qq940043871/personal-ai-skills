# 组件库（Component Library）

> 用法：Step 3 按需复制片段。片段基于 Tailwind CDN + FontAwesome 6 + CSS 变量（变量定义见 html-prototype-spec §2）。
> 所有片段默认已套行业主色变量，不要在组件里写死行业色值。
>
> ⚠️ 前置检查：片段引用了 `--primary / --primary-light / --primary-dark / --secondary / --price-up / --price-down / --price-flat / --success / --warning / --error / --text-price / --border` 等变量。**缺任何一个都会静默失效**（样式不生效且控制台无报错）——复制片段前先确认 `<style>` 的 `:root` 已按 spec §2 完整粘贴。
>
> 图标一律使用 **Font Awesome 6** 名称。禁止 v4 语法：`fa-star-o → fa-regular fa-star`、`fa-check-circle → fa-circle-check`、`fa-times-circle → fa-circle-xmark`。

## 目录

- A. 基础：按钮 / 标签徽章 / 表单控件
- B. 导航：通栏 / 头部搜索 / 主导航 / 分类导航 / 面包屑 / 分页 / Tabs
- C. 展示：Banner / 快捷入口 / 行情条 / 行情卡 / 产品卡 / 供应商卡 / 走势图 / 专区条目 / 资讯卡
- D. 反馈：Toast / Modal / Drawer / 骨架屏 / 空状态
- E. 页脚
- F. 动效层：环境探测与降级 / 3D 倾斜 / 滚动视差 / 极光与聚光 / 粒子网络 / 全息地球 / 光效套件 / 错峰进场 / 滚动进度 / 性能红线

> §F 是**渐进增强层**，不是必选项。用它的前提是先读完 F0：任何片段都不能让内容"不跑动效就看不见"。

---

## A. 基础组件

### A1. 按钮

```html
<!-- 主要 -->
<button class="h-10 px-6 rounded text-white text-sm font-medium transition hover:opacity-90 active:opacity-80" style="background:var(--primary);">立即询价</button>
<!-- 次要 -->
<button class="h-10 px-6 rounded text-sm font-medium transition" style="border:1px solid var(--primary);color:var(--primary);background:#fff;">加入询盘</button>
<!-- 文字 -->
<button class="text-sm" style="color:var(--primary);">查看更多 ></button>
<!-- 强调 CTA（Banner 上） -->
<button class="h-11 px-8 rounded text-white font-medium hover:opacity-90" style="background:var(--secondary);">立即询价</button>
```

| 尺寸 | 高度 | 字号 |
|------|------|------|
| lg | 48px | 16px |
| md（默认） | 40px | 14px |
| sm | 32px | 14px |

规则：一个视窗内主按钮 ≤1 个视觉层级；禁用态加 `.opacity-50 pointer-events-none`。

### A2. 标签 / 徽章

```html
<!-- 规格标签 -->
<span class="inline-block text-xs px-2 py-0.5 rounded mr-1" style="background:var(--primary-light);color:var(--primary);">HRB400</span>
<!-- 角标（认证/直供） -->
<span class="absolute top-2 left-2 text-[10px] px-1.5 py-0.5 rounded text-white" style="background:var(--primary);">认证</span>
<span class="absolute top-2 left-[46px] text-[10px] px-1.5 py-0.5 rounded text-white" style="background:var(--secondary);">直供</span>
<!-- 数字角标 -->
<span class="text-white rounded-full px-1.5 text-[10px] leading-4" style="background:var(--secondary);">3</span>
```

### A3. 表单控件

```html
<!-- 输入框 -->
<input class="h-10 w-full border rounded px-3 text-sm outline-none focus:border-[var(--primary)]" style="border-color:var(--border);" placeholder="请输入">
<!-- 错误态：加红色边框与提示 -->
<input class="h-10 w-full border rounded px-3 text-sm outline-none" style="border-color:var(--error);">
<div class="text-xs mt-1" style="color:var(--error);"><i class="fa fa-circle-exclamation mr-1"></i>该字段必填</div>
<!-- 下拉 -->
<select class="h-10 border rounded px-2 text-sm bg-white" style="border-color:var(--border);"><option>吨</option><option>kg</option></select>
<!-- 多选标签（筛选器用） -->
<span class="cursor-pointer text-xs px-3 py-1.5 rounded-full border" style="border-color:var(--primary);color:var(--primary);background:var(--primary-light);">沙钢 ×</span>
```

---

## B. 导航组件

### B1. 顶部通栏

```html
<div style="background:var(--primary-dark);color:#C9D4E0;height:32px;">
  <div class="container-x h-8 flex items-center justify-between text-xs">
    <div class="flex items-center gap-4">
      <span><i class="fa fa-phone mr-1"></i>400-800-0000</span>
      <span class="hidden md:inline">行业 slogan（虚构）</span>
    </div>
    <div class="flex items-center gap-4">
      <a class="hover:text-white cursor-pointer">中文/EN</a>
      <a class="hidden sm:inline hover:text-white cursor-pointer">手机版</a>
      <a class="hidden md:inline hover:text-white cursor-pointer">帮助中心</a>
      <span class="hidden sm:inline border-l border-white/20 pl-4"><a class="hover:text-white cursor-pointer">登录</a> / <a class="hover:text-white cursor-pointer">注册</a></span>
    </div>
  </div>
</div>
```

### B2. 头部（Logo + 搜索 + 操作区）

```html
<header class="sticky top-0 z-50 bg-white shadow-sm">
  <div class="container-x flex items-center justify-between gap-4 py-4 flex-wrap">
    <div class="flex items-center gap-2 shrink-0">
      <div class="w-10 h-10 rounded flex items-center justify-center text-white text-xl" style="background:var(--primary);"><i class="fa fa-cube"></i></div>
      <div>
        <div class="text-2xl font-semibold leading-6" style="color:var(--primary);">平台名</div>
        <div class="text-[11px] text-gray-400">行业定位短语</div>
      </div>
    </div>
    <div class="flex-1 lg:max-w-[560px]">
      <div class="relative">
        <input id="searchInput" class="w-full h-12 border-2 rounded-lg px-4 pr-24 text-sm outline-none" style="border-color:var(--primary);" placeholder="搜索行业词：牌号/规格/供应商">
        <button onclick="doSearch()" class="absolute right-0 top-0 h-full px-6 text-white text-sm font-medium rounded-r-lg" style="background:var(--primary);"><i class="fa fa-search mr-1"></i>搜索</button>
      </div>
      <div class="flex gap-3 mt-2 text-xs text-gray-400 flex-wrap">
        <span>热搜：</span><a class="cursor-pointer hover:text-[var(--secondary)]">热词1</a>
      </div>
    </div>
    <div class="flex items-center gap-4 text-xs text-gray-500 shrink-0">
      <div class="flex items-center gap-1 cursor-pointer hover:text-[var(--secondary)]"><i class="fa fa-file-invoice text-lg"></i>询价单<span class="text-white rounded-full px-1.5 text-[10px]" style="background:var(--secondary);" id="inquiryBadge">0</span></div>
      <div class="hidden sm:flex items-center gap-1 cursor-pointer hover:text-[var(--secondary)]"><i class="fa fa-cart-shopping text-lg"></i>购物车</div>
      <div class="hidden md:flex items-center gap-1 cursor-pointer hover:text-[var(--secondary)]"><i class="fa fa-envelope text-lg"></i>消息</div>
    </div>
  </div>
</header>
```

搜索交互：

```javascript
function doSearch(){
  var v = document.getElementById('searchInput').value.trim();
  if(!v){ showToast('请输入搜索内容','warn'); return; }
  showToast('搜索：'+ v +'（原型演示）','info');
}
document.getElementById('searchInput').addEventListener('keydown', function(e){ if(e.key==='Enter') doSearch(); });
```

### B3. 主导航 + 全部分类面板

```html
<nav class="text-white" style="background:var(--primary);">
  <div class="container-x flex items-center h-12">
    <button onclick="togglePanel('catPanel')" class="flex items-center gap-2 px-4 h-full font-semibold" style="background:var(--primary-dark);"><i class="fa fa-bars"></i>全部分类</button>
    <div class="flex items-center overflow-x-auto whitespace-nowrap">
      <a class="px-4 h-12 flex items-center hover:bg-black/10 cursor-pointer">首页</a>
      <a class="px-4 h-12 flex items-center hover:bg-black/10 cursor-pointer">找货源</a>
      <a class="px-4 h-12 flex items-center hover:bg-black/10 cursor-pointer">行情中心</a>
      <a class="px-4 h-12 flex items-center hover:bg-black/10 cursor-pointer">求购大厅</a>
      <a class="px-4 h-12 flex items-center hover:bg-black/10 cursor-pointer">供应商</a>
    </div>
  </div>
  <div id="catPanel" class="hidden container-x">
    <div class="grid grid-cols-2 md:grid-cols-5 gap-4 py-4 px-4 bg-white rounded-b-lg shadow-lg text-xs text-gray-600" id="catPanelBody"></div>
  </div>
</nav>
```

数据渲染（categories 数据结构见 §C 区或 html-prototype-spec §4）：

```javascript
function renderCatPanel(categories){
  document.getElementById('catPanelBody').innerHTML = categories.map(function(c){
    return '<div><div class="font-semibold mb-2" style="color:var(--primary);">'+c.name+'</div>'
      +'<div class="grid gap-1">'+c.children.map(function(s){return '<a class="hover:text-[var(--secondary)] cursor-pointer">'+s+'</a>';}).join('')+'</div></div>';
  }).join('');
}
function togglePanel(id){ var el=document.getElementById(id); el.classList.toggle('hidden'); }
```

### B4. Hero 左侧分类导航

```html
<aside class="col-span-12 lg:col-span-2 hidden lg:block">
  <div class="card" id="heroCats"></div>
</aside>
```
```javascript
function renderHeroCats(cats){
  document.getElementById('heroCats').innerHTML = cats.map(function(c,i){
    return '<a class="flex items-center justify-between px-4 py-3 text-sm hover:bg-gray-50 cursor-pointer '
      +(i<cats.length-1?'border-b':'')+'"><span>'+c+'</span><i class="fa fa-angle-right text-gray-300"></i></a>';
  }).join('');
}
```

### B5. 面包屑

```html
<div class="container-x py-3 text-xs text-gray-400">
  <a class="cursor-pointer hover:text-[var(--primary)]">首页</a> <i class="fa fa-angle-right mx-1"></i>
  <a class="cursor-pointer hover:text-[var(--primary)]">板材</a> <i class="fa fa-angle-right mx-1"></i>
  <span class="text-gray-600">热轧板卷</span>
</div>
```

### B6. Tabs

```html
<div class="flex border-b">
  <div class="px-5 py-3 text-sm font-medium cursor-pointer border-b-[3px]" style="color:var(--primary);border-color:var(--primary);">产品详情</div>
  <div class="px-5 py-3 text-sm text-gray-500 cursor-pointer border-b-[3px] border-transparent">规格参数</div>
</div>
```
通用切换：点击时移除兄弟项行内样式，给当前项加主色 + 下边框，同时切换对应 panel 的 `hidden`。

### B7. 分页

```html
<div class="flex items-center justify-center gap-2 text-sm mt-6 flex-wrap">
  <button class="h-8 px-3 border rounded text-gray-500 hover:border-[var(--primary)]">上一页</button>
  <button class="h-8 w-8 rounded text-white" style="background:var(--primary);">1</button>
  <button class="h-8 w-8 border rounded hover:border-[var(--primary)]">2</button>
  <span class="text-gray-400">…</span>
  <button class="h-8 px-3 border rounded hover:border-[var(--primary)]">下一页</button>
</div>
```

---

## C. 展示组件

### C1. Banner 轮播

```html
<div class="col-span-12 lg:col-span-7">
  <div class="relative card" style="height:380px;" id="bannerBox"></div>
</div>
```
```javascript
const banners = [
  {kicker:'产地直供 · 当日可发', title:'主标题（行业卖点）', desc:'规格/服务短语', cta:'立即询价'},
  {kicker:'第二屏卖点', title:'标题2', desc:'描述2', cta:'马上找货'}
];
function renderBanner(){
  var box = document.getElementById('bannerBox');
  box.innerHTML = banners.map(function(b,i){
    return '<div class="banner-slide absolute inset-0 flex items-center px-12 transition-opacity duration-500 '+(i?'opacity-0':'')+'" style="background:linear-gradient(120deg,var(--primary),var(--primary-dark));">'
      +'<div class="text-white"><div class="text-xs tracking-widest mb-3" style="color:var(--secondary);">'+b.kicker+'</div>'
      +'<div class="text-4xl font-semibold mb-3">'+b.title+'</div><div class="text-sm text-gray-300 mb-6">'+b.desc+'</div>'
      +'<button class="px-8 py-3 rounded font-medium hover:opacity-90" style="background:var(--secondary);">'+b.cta+'</button></div></div>';
  }).join('')
  +'<div class="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">'+banners.map(function(b,i){return '<span class="banner-dot h-1.5 rounded-full '+(i?'w-2 bg-white/40':'w-6 bg-white')+'"></span>';}).join('')+'</div>';
}
var bIdx=0;
setInterval(function(){
  bIdx=(bIdx+1)%banners.length;
  document.querySelectorAll('.banner-slide').forEach(function(el,i){ el.style.opacity=i===bIdx?'1':'0'; });
  document.querySelectorAll('.banner-dot').forEach(function(el,i){ el.className='banner-dot h-1.5 rounded-full '+(i===bIdx?'w-6 bg-white':'w-2 bg-white/40'); });
},4000);
```

### C2. 快捷入口（Hero 右）

```html
<div class="col-span-12 lg:col-span-3">
  <div class="grid grid-cols-4 lg:grid-cols-2 gap-3">
    <a class="card p-3 flex flex-col items-center gap-1 cursor-pointer"><i class="fa fa-file-circle-plus text-2xl" style="color:var(--primary);"></i><span class="text-xs">发布采购</span></a>
    <a class="card p-3 flex flex-col items-center gap-1 cursor-pointer"><i class="fa fa-store text-2xl" style="color:var(--primary);"></i><span class="text-xs">免费开店</span></a>
    <a class="card p-3 flex flex-col items-center gap-1 cursor-pointer"><i class="fa fa-envelopes-bulk text-2xl" style="color:var(--primary);"></i><span class="text-xs">我要报价</span></a>
    <a class="card p-3 flex flex-col items-center gap-1 cursor-pointer"><i class="fa fa-scale-balanced text-2xl" style="color:var(--primary);"></i><span class="text-xs">阳光采购</span></a>
  </div>
</div>
```

### C3. 行情滚动条

```html
<div class="card flex items-center overflow-hidden" style="border-left:4px solid var(--secondary);">
  <div class="px-4 py-2.5 font-semibold text-white shrink-0 text-xs" style="background:var(--secondary);"><i class="fa fa-bolt mr-1"></i>行情快报</div>
  <div class="overflow-hidden flex-1"><div id="ticker" class="flex whitespace-nowrap text-xs py-2"></div></div>
  <a class="px-3 text-gray-400 shrink-0 cursor-pointer hover:text-[var(--secondary)]">更多 ></a>
</div>
```
```javascript
// ticker: {name, price, chg, dir:'up|down|flat'}
function renderTicker(ticker){
  var html = ticker.map(function(t){
    var cls=t.dir==='up'?'t-up':(t.dir==='down'?'t-down':'t-flat');
    var icon=t.dir==='up'?'fa-arrow-trend-up':(t.dir==='down'?'fa-arrow-trend-down':'fa-minus');
    return '<div class="px-5 flex items-center gap-1"><span class="text-gray-500">'+t.name+'</span>'
      +'<span class="font-semibold">'+t.price.toLocaleString()+'</span><span class="'+cls+'"><i class="fa '+icon+' mr-0.5"></i>'+(t.chg>0?'+':'')+t.chg+'%</span></div>';
  }).join('');
  var el=document.getElementById('ticker'); el.innerHTML=html+html;
  var x=0;
  setInterval(function(){ x-=1; if(-x>=el.scrollWidth/2) x=0; el.style.transform='translateX('+x+'px)'; },30);
}
```
CSS：`.t-up{color:var(--price-up)} .t-down{color:var(--price-down)} .t-flat{color:var(--price-flat)}`

### C4. 行情卡片（行情看板网格用）

**数据驱动**（同 spec §3.3「禁止复制粘贴卡片 HTML」）：

```javascript
// q: {name, price, chg, delta, time, unit}
function marketCard(q){
  var cls=q.chg>=0?'t-up':'t-down';
  var icon=q.chg>=0?'fa-arrow-trend-up':'fa-arrow-trend-down';
  return '<div class="card p-4">'
    +'<div class="text-sm text-gray-500 mb-2">'+q.name+'</div>'
    +'<div class="flex items-baseline gap-3">'
    +'<span class="text-2xl font-semibold">'+q.price.toLocaleString()+'</span>'
    +'<span class="'+cls+' text-sm"><i class="fa '+icon+'"></i> '+(q.chg>0?'+':'')+q.chg+'%</span>'
    +'<span class="'+cls+' text-xs">'+(q.delta>0?'+':'')+q.delta+'</span></div>'
    +'<div class="text-xs text-gray-400 mt-2">'+q.time+' 更新 · '+q.unit+'</div></div>';
}
```

### C5. 产品卡片

```javascript
// product: {icon, title, price, specs:[], supplier, tags:[认证,直供]}
function productCard(p){
  return '<div class="card cursor-pointer"><div class="relative flex items-center justify-center h-32" style="background:linear-gradient(135deg,var(--primary-light),#D6E2EE);">'
    +'<i class="fa '+p.icon+' text-5xl" style="color:#9DB4CC;"></i>'
    +p.tags.map(function(t,i){return '<span class="absolute top-2 text-[10px] px-1.5 py-0.5 rounded text-white" style="left:'+(2+i*44)+'px;background:'+(i?'var(--secondary)':'var(--primary)')+';">'+t+'</span>';}).join('')
    +'</div><div class="p-3"><div class="font-medium text-[13px] leading-snug h-10 line-clamp-2">'+p.title+'</div>'
    +'<div class="mt-1.5 font-semibold" style="color:var(--text-price);">'+p.price+'</div>'
    +'<div class="mt-2 flex flex-wrap gap-1">'+p.specs.map(function(s){return '<span class="spec-tag">'+s+'</span>';}).join('')+'</div>'
    +'<div class="mt-2 text-[11px] text-gray-400 truncate">'+p.supplier+'</div>'
    +'<div class="mt-2.5 grid grid-cols-2 gap-2">'
    +'<button onclick="event.stopPropagation();inquire()" class="py-1.5 rounded text-white text-xs" style="background:var(--primary);">立即询价</button>'
    +'<button onclick="event.stopPropagation();addInquiry(this)" class="py-1.5 rounded text-xs" style="border:1px solid var(--primary);color:var(--primary);">加入询盘</button>'
    +'</div></div></div>';
}
```

询盘联动：

```javascript
var inquiryCount=0;
function addInquiry(btn){
  inquiryCount++;
  document.getElementById('inquiryBadge').textContent=inquiryCount;
  btn.textContent='已加入 ✓'; btn.style.opacity=.6;
  showToast('已加入询盘单','success');
}
function inquire(){ showToast('进入询价流程（原型演示）','info'); }
```

### C6. 供应商卡片

```javascript
// s: {name, cert, year, auth, main, deal}
function supplierCard(s){
  return '<div class="card p-4"><div class="flex items-center gap-3 mb-3">'
    +'<div class="w-11 h-11 rounded-lg flex items-center justify-center text-white text-lg shrink-0" style="background:var(--primary);"><i class="fa fa-warehouse"></i></div>'
    +'<div><div class="font-semibold text-[13px] leading-tight">'+s.name+'</div>'
    +'<div class="text-[11px] mt-0.5" style="color:var(--secondary);">'+s.cert+' · '+s.year+'</div></div></div>'
    +'<div class="text-xs text-gray-500 mb-2">认证：'+s.auth+'</div>'
    +'<div class="text-xs text-gray-500 mb-2">主营：'+s.main+'</div>'
    +'<div class="text-xs mb-3" style="color:var(--primary);">'+s.deal+'</div>'
    +'<div class="grid grid-cols-2 gap-2"><button class="py-1.5 rounded text-xs text-white" style="background:var(--primary);">进入店铺</button>'
    +'<button class="py-1.5 rounded text-xs" style="border:1px solid var(--primary);color:var(--primary);">立即联系</button></div></div>';
}
```

### C7. 价格走势图（Chart.js）

```javascript
function renderPriceChart(labels, spot, future){
  new Chart(document.getElementById('priceChart'), {
    type:'line',
    data:{ labels:labels, datasets:[
      {label:'现货价', data:spot, borderColor:'#1E3A5F', backgroundColor:'rgba(30,58,95,0.12)', fill:true, tension:.3, borderWidth:2, pointRadius:0},
      {label:'期货价', data:future, borderColor:'#FF6A00', borderDash:[5,4], fill:false, tension:.3, borderWidth:2, pointRadius:0}
    ]},
    options:{
      maintainAspectRatio:false, responsive:true,
      interaction:{mode:'index',intersect:false},
      plugins:{legend:{position:'top',align:'end',labels:{boxWidth:12,font:{size:11}}}},
      scales:{
        y:{ticks:{font:{size:11},callback:function(v){return v.toLocaleString();}},grid:{color:'#F0F0F0'}},
        x:{ticks:{font:{size:11}},grid:{display:false}}
      }
    }
  });
}
```
要点：折线主色随行业（可改读 CSS 变量），关闭点标记，Y 轴千分位，容器固定 256px 高。

### C8. 采购 / 供应专区条目

```html
<div class="bg-gray-50 rounded-lg p-3 cursor-pointer hover:bg-gray-100">
  <div class="text-gray-400 text-xs mb-1">采购螺纹钢</div>
  <div class="font-semibold text-sm">HRB400E Φ20<span class="text-xs text-gray-400 ml-1">×500 吨</span></div>
  <div class="text-xs text-gray-400 mt-1">江苏南京 · 钢厂直提 <span class="ml-2" style="color:var(--secondary);">11小时前</span></div>
</div>
```

### C9. 资讯卡片

```html
<div class="card p-4 cursor-pointer">
  <span class="inline-block text-[11px] px-2 py-0.5 rounded mb-2" style="background:var(--primary-light);color:var(--primary);">行情分析</span>
  <div class="font-semibold text-sm mb-1 hover:text-[var(--secondary)]">资讯标题（一句话结论）</div>
  <div class="text-xs text-gray-400">2026-09-19 · 来源</div>
</div>
```

---

## D. 反馈组件

### D1. Toast（顶部居中，2.5s 自动消失）

```html
<div id="toast" class="fixed top-16 left-1/2 -translate-x-1/2 z-[100] hidden">
  <div class="px-4 py-2 rounded-lg text-sm shadow-lg" id="toastBody"></div>
</div>
```
```javascript
function showToast(msg, type){
  var k=type||'info';
  // 底色与前景色必须成对：success/warn 底色偏亮，白字对比度不足 4.5:1，须用深色字
  var bg={success:'#52C41A',warn:'#FAAD14',error:'#CF1322',info:'#1E3A5F'};
  var fg={success:'#0B2E00',warn:'#3D2A00',error:'#FFFFFF',info:'#FFFFFF'};
  var icons={success:'fa-circle-check',warn:'fa-triangle-exclamation',error:'fa-circle-xmark',info:'fa-circle-info'};
  var body=document.getElementById('toastBody');
  body.style.background=bg[k]; body.style.color=fg[k];
  body.innerHTML='<i class="fa '+icons[k]+' mr-1"></i>'+msg;
  document.getElementById('toast').classList.remove('hidden');
  clearTimeout(window.__toastTimer);
  window.__toastTimer=setTimeout(function(){ document.getElementById('toast').classList.add('hidden'); },2500);
}
```
> 调用方式：`showToast('请输入搜索内容','warn')`。`type` ∈ success / warn / error / info，缺省 info。四组配色的对比度见 html-prototype-spec §6。

### D2. Modal

```html
<div id="modalMask" class="fixed inset-0 bg-black/40 z-[90] hidden flex items-center justify-center px-4">
  <div class="bg-white rounded-lg w-full max-w-md overflow-hidden">
    <div class="flex items-center justify-between px-5 py-3 border-b"><span class="font-semibold">标题</span><i class="fa fa-xmark cursor-pointer text-gray-400" onclick="closeModal()"></i></div>
    <div class="p-5 text-sm text-gray-600">内容区（如：选择供应商、确认规格）</div>
    <div class="px-5 py-3 border-t flex justify-end gap-2"><button class="h-9 px-4 rounded border text-sm" onclick="closeModal()">取消</button><button class="h-9 px-4 rounded text-white text-sm" style="background:var(--primary);" onclick="closeModal();showToast('操作成功','success')">确定</button></div>
  </div>
</div>
```
开关：`classList.toggle('hidden')`；ESC 与遮罩点击均应关闭。

### D3. 移动端抽屉（分类/筛选）

```html
<div id="drawerMask" class="fixed inset-0 bg-black/40 z-[80] hidden" onclick="closeDrawer()"></div>
<div id="drawer" class="fixed left-0 top-0 h-full w-4/5 max-w-xs bg-white z-[85] -translate-x-full transition-transform duration-300">
  <div class="p-4 font-semibold border-b">全部分类</div>
  <div class="p-4 overflow-y-auto h-[calc(100%-57px)]" id="drawerBody"></div>
</div>
```
开关：mask `hidden` + drawer 切换 `-translate-x-full / translate-x-0`。

### D4. 骨架屏

```html
<div class="card p-3 animate-pulse">
  <div class="h-32 rounded bg-gray-200"></div>
  <div class="h-3 bg-gray-200 rounded mt-3 w-3/4"></div>
  <div class="h-3 bg-gray-200 rounded mt-2 w-1/2"></div>
</div>
```
原型中默认直接渲染数据；模拟加载时首帧挂骨架，300ms 后替换。

### D5. 空状态

```html
<div class="text-center py-16">
  <i class="fa fa-box-open text-5xl text-gray-300"></i>
  <div class="text-sm text-gray-400 mt-3">没有符合条件的商品</div>
  <button class="mt-4 h-9 px-5 rounded text-white text-sm" style="background:var(--primary);">清空筛选条件</button>
</div>
```

---

## E. 页脚

```html
<footer style="background:var(--primary-dark);color:#A9B8C7;">
  <div class="container-x grid grid-cols-2 md:grid-cols-4 gap-6 py-10 text-xs">
    <div><div class="text-white font-semibold mb-3 text-sm">平台服务</div>
      <div class="grid gap-2"><a class="cursor-pointer hover:text-white">帮助中心</a><a class="cursor-pointer hover:text-white">交易保障</a><a class="cursor-pointer hover:text-white">商家入驻</a></div></div>
    <div><div class="text-white font-semibold mb-3 text-sm">采购支持</div>
      <div class="grid gap-2"><a class="cursor-pointer hover:text-white">发布询价</a><a class="cursor-pointer hover:text-white">招投标</a></div></div>
    <div><div class="text-white font-semibold mb-3 text-sm">关于平台</div>
      <div class="grid gap-2"><a class="cursor-pointer hover:text-white">公司介绍</a><a class="cursor-pointer hover:text-white">联系我们</a></div></div>
    <div><div class="text-white font-semibold mb-3 text-sm">联系我们</div>
      <div class="grid gap-2"><span><i class="fa fa-phone mr-1"></i>400-800-0000</span><span><i class="fa fa-location-dot mr-1"></i>城市 · 园区（虚构）</span></div></div>
  </div>
  <div class="border-t border-white/10"><div class="container-x py-4 text-xs text-center text-gray-400">© 2026 平台名 · 行业B2B平台 某ICP备 0000000000 号-1（虚构）</div></div>
</footer>
```

---

## F. 动效层

> 目的：让门户首页有"工业级数据终端"的临场感。约束：**一切动效都是装饰**——关掉 JS、触屏、系统开启"减少动态效果"时，内容必须完整可读。
> 规范出处：html-prototype-spec §5.1；质量门禁见 SKILL.md §7「视觉与动效」分组。

### F0. 环境探测与降级（其他片段的前置，必须先放）

F0-1 把探测对象放在脚本最前（`THEME` 之后、任何 `init*` 之前）：

```javascript
var FX=(function(){
  var rm=window.matchMedia&&window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var fine=window.matchMedia&&window.matchMedia('(hover: hover) and (pointer: fine)').matches;
  return {reduced:rm, fine:fine, on:!rm&&!!window.requestAnimationFrame,
          raf:window.requestAnimationFrame.bind(window)};
})();
/* 深色底取色：主题色本身太暗，canvas 里用提亮后的分量值传给 rgba() */
function fxTint(hex,amt){ return hexToRgbArr(shade(hex,amt)).join(','); }
```

三个开关的用途，别混：

| 字段 | 含义 | 用在哪 |
|------|------|--------|
| `FX.on` | 允许跑动效（未开减动 + 有 rAF） | canvas、视差、错峰进场的总闸 |
| `FX.fine` | 精确指针（鼠标，非触屏） | 3D 倾斜 / 区域聚光 / 磁吸按钮 |
| `FX.reduced` | 系统开了减动 | 只用来**跳过收尾动画**（如数字光晕），不负责隐藏 |

F0-2 样式里必须有减动降级块（机检会查这个媒体查询，缺了直接判 ERROR）：

```css
@media (prefers-reduced-motion:reduce){
  *,*::before,*::after{animation-duration:.01ms!important;animation-iteration-count:1!important;transition-duration:.01ms!important;}
  .reveal,.fx-stagger>*{opacity:1!important;transform:none!important;}
  [data-tilt]{transform:none!important;}
  .fx-aurora,.fx-scan,.fx-canvas,.fx-spot,.globe-orbit,.globe-orbit-2,#fxProgress{display:none!important;}
}
```

> ⚠️ 两条铁律：
> 1. **隐藏态不能挂在默认选择器上**。`.reveal{opacity:0}` 一旦写进 `:root` 级规则，JS 挂掉时内容就永久消失。正确写法是让 JS 先给根节点加 `.fx-anim`，隐藏态写成 `.fx-anim .reveal{opacity:0}`；错峰进场同理——宿主类 `.fx-stagger` 由 JS 添加（F7）。
> 2. **不用 `filter:blur` 做大面积柔光**。这个尺寸的模糊会把合成开销推高一个量级，柔边一律用径向渐变的透明过渡实现（F3）。

### F1. 3D 倾斜卡片

给任意卡片加 `data-tilt="角度"`（建议值见下表），位移与倾角由 F0 的**指针效果**统一驱动（F5-2）。CSS：

```css
[data-tilt]{--rx:0deg;--ry:0deg;--ty:0px;--mx:50%;--my:50%;position:relative;
  transform:perspective(1100px) rotateX(var(--rx)) rotateY(var(--ry)) translate3d(0,var(--ty),0);
  transition:transform .55s var(--ease),box-shadow var(--dur) var(--ease),border-color var(--dur) var(--ease);}
[data-tilt].fx-live{transition:transform .13s linear,box-shadow var(--dur) var(--ease),border-color var(--dur) var(--ease);}
[data-tilt]:hover{--ty:-4px;box-shadow:var(--sh-lg);border-color:rgba(var(--primary-rgb),.26);}
[data-tilt]::after{content:"";position:absolute;inset:0;border-radius:inherit;z-index:3;pointer-events:none;
  background:radial-gradient(340px circle at var(--mx) var(--my),rgba(255,255,255,.14),transparent 64%);
  opacity:0;transition:opacity .4s var(--ease);}
[data-tilt]:hover::after{opacity:1;}
```

| 元素 | `data-tilt` | 说明 |
|------|-------------|------|
| 产品卡 | `7` | 主视觉，倾角最大 |
| 供应商卡 / 行情卡 / 服务卡 | `6` | |
| 资讯卡 / 紧凑条目 | `5` | |
| 中小面板（约 1/3 宽） | `3`–`4` | 面积小，倾角要收敛 |

> 为什么用 CSS 变量而不是直接改 `transform`：`.card-lift` 自己的悬浮上抬也是一条 `transform` 规则，两者同权重时后者按源序胜出。变量驱动让 tilt 与上抬能叠加共存；`.fx-live` 只在指针进入时挂上，把过渡时长从 `.55s` 压到 `.13s`，跟手不拖影。

### F2. 滚动视差

给承载层加 `data-parallax="系数"`。系数取 **负值**（背景层比内容慢半拍、往上走），绝对值控制在 `.06`–`.18`：

```html
<div class="hero-grid" data-parallax="-.16"></div>
```

```javascript
/* 滚动视差：按 data-parallax 系数位移，位移量按容器高度封顶 */
function initParallax(){
  if(!FX.on) return;
  var els=[].slice.call(document.querySelectorAll('[data-parallax]'));
  if(!els.length) return;
  var ticking=false;
  function apply(){
    ticking=false;
    var vh=window.innerHeight;
    for(var i=0;i<els.length;i++){
      var el=els[i], r=el.parentNode.getBoundingClientRect();
      if(!r.height) continue;
      var max=r.height*.18;                                   /* 位移封顶：容器高度的 18% */
      var y=(r.top+r.height/2-vh/2)*(parseFloat(el.getAttribute('data-parallax'))||0);
      y=Math.max(-max,Math.min(max,y));                       /* 夹住，防止长页面拉飞 */
      el.style.transform='translate3d(0,'+y.toFixed(1)+'px,0)';
    }
  }
  function onScroll(){ if(!ticking){ ticking=true; FX.raf(apply); } }
  window.addEventListener('scroll',onScroll,{passive:true});
  window.addEventListener('resize',onScroll);
  apply();
}
```

> 视差层必须是 `position:absolute;inset:0` 的**背景层**，且外层 `overflow:hidden`，否则位移会把父容器撑出滚动条。`ticking` 标志把滚动回调压到每帧最多一次。

### F3. 极光光斑 · 雷达扫描 · 区域聚光（Hero 动效层）

承载结构（放在 Hero 内层，`pointer-events:none` 不挡点击）：

```html
<div class="fx-layer">
  <div class="hero-grid" data-parallax="-.16"></div>
  <div class="fx-aurora"><span class="fx-a1"></span><span class="fx-a2"></span><span class="fx-a3"></span></div>
  <canvas id="fxNet" class="fx-canvas"></canvas>
  <div class="fx-scan"></div>
  <div class="fx-spot"></div>
</div>
```

```css
.fx-layer{position:absolute;inset:0;overflow:hidden;pointer-events:none;}
.fx-canvas{position:absolute;inset:0;width:100%;height:100%;display:block;}

/* 极光光斑：柔边径向渐变 + 只动 transform；不用 filter:blur */
.fx-aurora{position:absolute;inset:-12%;pointer-events:none;}
.fx-aurora span{position:absolute;aspect-ratio:1/1;border-radius:50%;will-change:transform;}
.fx-a1{width:min(720px,60%);left:-9%;top:-26%;background:radial-gradient(circle,rgba(var(--primary-rgb),.60),rgba(var(--primary-rgb),0) 66%);animation:fxAuroraA 28s var(--ease) infinite alternate;}
.fx-a2{width:min(500px,42%);right:-4%;top:-10%;background:radial-gradient(circle,rgba(var(--secondary-rgb),.24),rgba(var(--secondary-rgb),0) 64%);animation:fxAuroraB 22s var(--ease) infinite alternate;}
.fx-a3{width:min(480px,42%);left:36%;bottom:-30%;background:radial-gradient(circle,rgba(126,184,255,.20),rgba(126,184,255,0) 66%);animation:fxAuroraC 34s var(--ease) infinite alternate;}
@keyframes fxAuroraA{from{transform:translate3d(0,0,0) scale(1);}to{transform:translate3d(9%,7%,0) scale(1.16);}}
@keyframes fxAuroraB{from{transform:translate3d(0,0,0) scale(1.08);}to{transform:translate3d(-11%,9%,0) scale(.93);}}
@keyframes fxAuroraC{from{transform:translate3d(0,0,0) scale(.96);}to{transform:translate3d(-7%,-9%,0) scale(1.2);}}

/* 雷达扫描线 */
.fx-scan{position:absolute;left:0;right:0;top:-36%;height:36%;pointer-events:none;
  background:linear-gradient(180deg,transparent,rgba(var(--secondary-rgb),.05) 58%,rgba(190,220,255,.055) 88%,transparent);
  animation:fxScan 9.5s linear infinite;}
@keyframes fxScan{from{transform:translate3d(0,0,0);}to{transform:translate3d(0,378%,0);}}

/* 区域聚光：跟随指针，坐标由 JS 写入宿主上的 --sx / --sy */
.fx-spot{--sx:50%;--sy:50%;position:absolute;inset:0;pointer-events:none;opacity:0;transition:opacity .55s var(--ease);
  background:radial-gradient(560px circle at var(--sx) var(--sy),rgba(255,255,255,.085),transparent 60%);}
.fx-spot.on{opacity:1;}
```

- 极光用 `--primary-rgb` / `--secondary-rgb` 取色，换行业主题时三色光斑自动跟随；第三色写死为中性冷蓝，作为跨行业的"屏幕光"。
- 深色区块想要同款聚光，直接在该区块内再插一个 `<div class="fx-spot"></div>` 即可，**不需要改 JS**（F5-2 按 class 批量收集）。
- 每个 `.fx-*` 层都要 `pointer-events:none`，否则 Hero 上的按钮点不动。

### F4. 粒子网络（canvas）

```html
<canvas id="fxNet" class="fx-canvas"></canvas>
```

```javascript
/* 粒子网络：节点 + 就近连线 + 指针斥力 */
function initNet(){
  var cv=document.getElementById('fxNet');
  if(!cv||!cv.getContext||!FX.on) return;
  var ctx=cv.getContext('2d'), layer=cv.parentNode, sec=layer.parentNode;
  var W=0,H=0,pts=[],mx=-1e4,my=-1e4,alive=true;
  var C1=fxTint(THEME.primary,-.62), C2=fxTint(THEME.secondary,0), LINK=132;
  function resize(){
    var r=layer.getBoundingClientRect();
    if(!r.width||!r.height) return;
    var dpr=Math.min(window.devicePixelRatio||1,2);        /* DPR 封顶 2 */
    W=r.width; H=r.height;
    cv.width=Math.round(W*dpr); cv.height=Math.round(H*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    var n=Math.max(26,Math.min(88,Math.round(W*H/15000)));  /* 密度随面积自适应，封顶 88 */
    pts=[];
    for(var i=0;i<n;i++) pts.push({
      x:Math.random()*W, y:Math.random()*H,
      vx:(Math.random()-.5)*.24, vy:(Math.random()-.5)*.24,
      r:.8+Math.random()*1.4, hot:Math.random()<.18
    });
  }
  function frame(){
    if(!alive) return;
    ctx.clearRect(0,0,W,H);
    var i,j,p,a,b,dx,dy,d,al;
    for(i=0;i<pts.length;i++){
      p=pts[i];
      p.x+=p.vx; p.y+=p.vy;
      if(p.x<0||p.x>W) p.vx=-p.vx;
      if(p.y<0||p.y>H) p.vy=-p.vy;
      dx=p.x-mx; dy=p.y-my; d=dx*dx+dy*dy;
      if(d<21000&&d>1){ d=Math.sqrt(d); p.x+=dx/d*(1-d/145)*1.1; p.y+=dy/d*(1-d/145)*1.1; }  /* 指针斥力 */
    }
    ctx.lineWidth=.9;
    for(i=0;i<pts.length;i++){
      a=pts[i];
      for(j=i+1;j<pts.length;j++){
        b=pts[j]; dx=a.x-b.x; dy=a.y-b.y; d=Math.sqrt(dx*dx+dy*dy);
        if(d<LINK){ al=(1-d/LINK)*.52; ctx.strokeStyle='rgba('+C1+','+al.toFixed(3)+')';
          ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); }
      }
    }
    for(i=0;i<pts.length;i++){
      p=pts[i];
      if(p.hot){ ctx.shadowBlur=15; ctx.shadowColor='rgba('+C2+',.95)'; ctx.fillStyle='rgba('+C2+',.95)';
        ctx.beginPath(); ctx.arc(p.x,p.y,p.r*1.8,0,6.2832); ctx.fill(); ctx.shadowBlur=0; }
      else{ ctx.fillStyle='rgba('+C1+',.92)'; ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,6.2832); ctx.fill(); }
    }
    FX.raf(frame);
  }
  resize();
  FX.raf(frame);
  window.addEventListener('resize',resize);
  sec.addEventListener('pointermove',function(e){
    var r=layer.getBoundingClientRect(); mx=e.clientX-r.left; my=e.clientY-r.top;
  },{passive:true});
  sec.addEventListener('pointerleave',function(){ mx=my=-1e4; });
  if('IntersectionObserver' in window){                       /* 离屏暂停，省电省 CPU */
    new IntersectionObserver(function(es){
      es.forEach(function(en){
        if(en.isIntersecting&&!alive){ alive=true; FX.raf(frame); }
        else if(!en.isIntersecting&&alive){ alive=false; }
      });
    },{threshold:0}).observe(sec);
  }
}
```

> 三处硬性要求，缺一即扣分：**DPR 封顶 2**、**节点数封顶**、**IntersectionObserver 离屏暂停**（否则页面滚走后仍在烧 CPU）。

### F5. 光效套件（掠光 / 流光边框 / 磁吸 / 趋势线 / 数字光晕）

F5-1 三段 CSS，按需取用：

```css
/* 深色面板掠光：出栈瞬间回位（transition 0s），避免离场时反向扫一遍 */
.fx-sheen{position:relative;overflow:hidden;}
.fx-sheen::before{content:"";position:absolute;top:-60%;left:-70%;width:58%;height:220%;z-index:4;pointer-events:none;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.16),transparent);
  transform:skewX(-20deg) translate3d(-150%,0,0);transition:transform 0s;}
.fx-sheen:hover::before{transform:skewX(-20deg) translate3d(330%,0,0);transition:transform .9s var(--ease);}

/* 流光边框：一道光沿面板边沿循环（@property 不支持时退化为静态描边，不影响可读性） */
@property --fx-ang{syntax:"<angle>";initial-value:0deg;inherits:false;}
.fx-ring{--fx-ang:0deg;position:relative;}
.fx-ring::before{content:"";position:absolute;inset:0;border-radius:inherit;padding:1px;z-index:2;pointer-events:none;
  background:conic-gradient(from var(--fx-ang),transparent 0deg,transparent 248deg,rgba(var(--secondary-rgb),.85) 296deg,rgba(214,235,255,.9) 322deg,transparent 352deg);
  -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
          mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);
  -webkit-mask-composite:xor; mask-composite:exclude;
  animation:fxSpin 7.5s linear infinite;}
@keyframes fxSpin{to{--fx-ang:360deg;}}

/* 磁吸按钮：仅精确指针设备启用（JS 写入 --mgx / --mgy） */
.btn-primary.fx-magnet{--mgx:0px;--mgy:0px;transform:translate3d(var(--mgx),var(--mgy),0);
  transition:transform .2s var(--ease),box-shadow var(--dur) var(--ease);}
.btn-primary.fx-magnet:hover{transform:translate3d(var(--mgx),calc(var(--mgy) - 2px),0);}
.btn-primary.fx-magnet:active{transform:translate3d(var(--mgx),calc(var(--mgy) + 1px),0);}

/* 迷你趋势线绘制入场（polyline 需带 pathLength="100"） */
.spark{stroke-dasharray:100;stroke-dashoffset:100;animation:fxDraw 1.5s var(--ease) forwards;}
@keyframes fxDraw{to{stroke-dashoffset:0;}}

/* 数字滚动结束时的光晕脉冲 */
.fx-glow{animation:fxGlow 1.7s var(--ease);}
@keyframes fxGlow{35%{text-shadow:0 0 22px rgba(var(--secondary-rgb),.9);}}
```

用法：`.fx-ring` + `.fx-sheen` 常一起挂在深色面板上（`class="glass fx-ring fx-sheen p-5"`）；`.fx-magnet` 加在 Hero 主 CTA 上，同时必须有 `.btn-primary` 类（双类选择器抬高权重，才压得过 `:hover` 位移）；趋势线 `<polyline class="spark" pathLength="100" ...>`。

F5-2 指针效果统一驱动（倾斜 / 聚光 / 磁吸走同一套事件委托，所以 JS 动态渲染出的卡片无需重新绑定）：

```javascript
function initPointerFX(){
  if(!FX.on||!FX.fine) return;                              /* 触屏直接不装 */
  var spots=[].slice.call(document.querySelectorAll('.fx-spot'));
  var mags=[].slice.call(document.querySelectorAll('.fx-magnet'));
  var cur=null;
  function leave(){
    if(cur){ cur.classList.remove('fx-live'); cur.style.removeProperty('--rx'); cur.style.removeProperty('--ry'); cur=null; }
  }
  document.addEventListener('pointermove',function(e){
    var t=e.target&&e.target.closest?e.target.closest('[data-tilt]'):null;
    if(t!==cur){ leave(); if(t){ t.classList.add('fx-live'); cur=t; } }
    if(cur){
      var r=cur.getBoundingClientRect();
      var mx=parseFloat(cur.getAttribute('data-tilt'))||7;
      var px=(e.clientX-r.left)/r.width, py=(e.clientY-r.top)/r.height;
      cur.style.setProperty('--ry',((px-.5)*2*mx).toFixed(2)+'deg');
      cur.style.setProperty('--rx',((.5-py)*2*mx).toFixed(2)+'deg');
      cur.style.setProperty('--mx',(px*100).toFixed(1)+'%');
      cur.style.setProperty('--my',(py*100).toFixed(1)+'%');
    }
    var i,s,sr;
    for(i=0;i<spots.length;i++){
      s=spots[i]; sr=s.getBoundingClientRect();
      if(e.clientY>=sr.top&&e.clientY<=sr.bottom&&e.clientX>=sr.left&&e.clientX<=sr.right){
        s.style.setProperty('--sx',(e.clientX-sr.left).toFixed(0)+'px');
        s.style.setProperty('--sy',(e.clientY-sr.top).toFixed(0)+'px');
        s.classList.add('on');
      }else if(s.classList.contains('on')){ s.classList.remove('on'); }
    }
    for(i=0;i<mags.length;i++){
      var m=mags[i], mr=m.getBoundingClientRect();
      var dx=e.clientX-(mr.left+mr.width/2), dy=e.clientY-(mr.top+mr.height/2);
      var rad=Math.max(mr.width,mr.height)*.9;
      if(Math.sqrt(dx*dx+dy*dy)<rad){
        m.style.setProperty('--mgx',(dx*.22).toFixed(1)+'px');
        m.style.setProperty('--mgy',(dy*.28).toFixed(1)+'px');
      }else if(m.style.getPropertyValue('--mgx')){
        m.style.removeProperty('--mgx'); m.style.removeProperty('--mgy');
      }
    }
  },{passive:true});
  document.documentElement.addEventListener('mouseleave',leave);
  window.addEventListener('blur',leave);
}
```

> 磁吸半径取元素长边的 `.9` 倍，位移系数 x `.22` / y `.28`（横向阻尼大于纵向，观感更稳）。`mouseleave` 与 `blur` 都要清态，否则切走再回来卡片会卡在倾斜位。

### F6. 全息地球（canvas 手写 3D，不引 three.js）

数据源用 `TRADE` Schema（结构见 html-prototype-spec §4.8），结构：

```html
<div class="globe-wrap">
  <div class="globe-halo"></div>
  <div class="globe-orbit"></div>
  <div class="globe-orbit-2"></div>
  <canvas id="globeCanvas"></canvas>
</div>
```

```css
.globe-wrap{position:relative;aspect-ratio:1/1;max-width:520px;margin:0 auto;}
.globe-halo{position:absolute;inset:-8%;border-radius:50%;
  background:radial-gradient(circle,rgba(var(--primary-rgb),.34),rgba(var(--secondary-rgb),.10) 46%,transparent 68%);}
.globe-orbit{position:absolute;inset:-2%;border-radius:50%;border:1px dashed rgba(255,255,255,.18);animation:fxSpinSlow 70s linear infinite;}
.globe-orbit-2{position:absolute;inset:6%;border-radius:50%;border:1px solid rgba(var(--secondary-rgb),.24);animation:fxSpinSlow 46s linear infinite reverse;}
@keyframes fxSpinSlow{to{transform:rotate(360deg);}}
#globeCanvas{position:absolute;inset:0;width:100%;height:100%;display:block;}
```

```javascript
/* 全息地球：球面网格 + 枢纽光点 + 大圆航线与在途光标。
   3D 投影手写在 canvas 2D 里（绕 Y 轴自转 + 轴向倾斜），不引第三方 3D 库。 */
function hubByName(n){
  for(var i=0;i<TRADE.hubs.length;i++){ if(TRADE.hubs[i].name===n) return TRADE.hubs[i]; }
  return null;
}
function initGlobe(){
  var cv=document.getElementById('globeCanvas');
  if(!cv||!cv.getContext||typeof TRADE==='undefined') return;
  var ctx=cv.getContext('2d'), W=0,H=0,R=0,rot=.6,pulse=0,alive=true, TILT=-.38;
  var CL=fxTint(THEME.primary,-.66), C2=fxTint(THEME.secondary,0);
  var routes=[];
  (TRADE.routes||[]).forEach(function(r){
    var a=hubByName(r.from), b=hubByName(r.to);
    if(a&&b) routes.push({a:a,b:b});
  });
  /* 经纬度 → 单位球坐标 */
  function sph(lat,lng){
    var la=lat*Math.PI/180, lo=lng*Math.PI/180;
    return [Math.cos(la)*Math.sin(lo), Math.sin(la), Math.cos(la)*Math.cos(lo)];
  }
  /* 绕 Y 轴自转 → 绕 X 轴倾斜 → 正交投影到屏幕；z 交给透明度用 */
  function toScreen(v,rad){
    var cs=Math.cos(rot), sn=Math.sin(rot);
    var x=v[0]*cs-v[2]*sn, z=v[0]*sn+v[2]*cs, y=v[1];
    var ty=y*Math.cos(TILT)-z*Math.sin(TILT), tz=y*Math.sin(TILT)+z*Math.cos(TILT);
    return {x:W/2+x*R*rad, y:H/2-ty*R*rad, z:tz};
  }
  function proj(lat,lng,rad){ return toScreen(sph(lat,lng), rad||1); }
  /* 球面线性插值：航线沿大圆走，不会穿过球体 */
  function slerp(a,b,t){
    var d=Math.max(-1,Math.min(1,a[0]*b[0]+a[1]*b[1]+a[2]*b[2]));
    var om=Math.acos(d), so=Math.sin(om);
    if(so<1e-5) return a.slice();
    var u=Math.sin((1-t)*om)/so, v=Math.sin(t*om)/so;
    return [a[0]*u+b[0]*v, a[1]*u+b[1]*v, a[2]*u+b[2]*v];
  }
  /* 逐段按深度衰减透明度：背面自然变淡，省掉手动裁半球 */
  function poly(pts,color,base,width){
    for(var i=1;i<pts.length;i++){
      var a=pts[i-1], b=pts[i];
      var al=base*(.30+.70*Math.max(0,((a.z+b.z)/2+1)/2));
      ctx.strokeStyle='rgba('+color+','+al.toFixed(3)+')';
      ctx.lineWidth=width;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke();
    }
  }
  function draw(){
    var i,j,pts;
    /* 球体轮廓高光：全息感的关键一笔（正交投影下轮廓恒为半径 R 的圆） */
    ctx.strokeStyle='rgba('+C2+',.26)'; ctx.lineWidth=1.2;
    ctx.beginPath(); ctx.arc(W/2,H/2,R,0,6.2832); ctx.stroke();
    ctx.strokeStyle='rgba('+CL+',.14)'; ctx.lineWidth=6;
    ctx.beginPath(); ctx.arc(W/2,H/2,R*1.005,0,6.2832); ctx.stroke();

    for(i=-60;i<=60;i+=30){                                   /* 纬线 */
      pts=[]; for(j=0;j<=60;j++) pts.push(proj(i,j*6));
      poly(pts,CL,i===0?.62:.52,.7);
    }
    for(i=0;i<360;i+=30){                                     /* 经线 */
      pts=[]; for(j=0;j<=24;j++) pts.push(proj(-90+j*7.5,i));
      poly(pts,CL,.30,.55);
    }
    for(i=0;i<routes.length;i++){                             /* 大圆航线 + 在途光标 */
      var A=sph(routes[i].a.lat,routes[i].a.lng), B=sph(routes[i].b.lat,routes[i].b.lng);
      pts=[];
      for(j=0;j<=26;j++){ var u=j/26; pts.push(toScreen(slerp(A,B,u),1+Math.sin(Math.PI*u)*.34)); }
      poly(pts,C2,.42,1.3);
      var t=(pulse*.30+i*.27)%1;
      var pos=toScreen(slerp(A,B,t),1+Math.sin(Math.PI*t)*.34);
      if(pos.z>-.2){
        ctx.shadowBlur=16; ctx.shadowColor='rgba('+C2+',.95)'; ctx.fillStyle='#FFFFFF';
        ctx.beginPath(); ctx.arc(pos.x,pos.y,3,0,6.2832); ctx.fill(); ctx.shadowBlur=0;
      }
    }
    (TRADE.hubs||[]).forEach(function(h,k){                   /* 枢纽光点 */
      var p=proj(h.lat,h.lng);
      if(p.z<-.12) return;
      var r=2.6*(h.size||1), hx=r*(3+Math.sin(pulse*1.5+k)*.7);
      var g=ctx.createRadialGradient(p.x,p.y,0,p.x,p.y,hx);
      g.addColorStop(0,'rgba('+C2+',.68)'); g.addColorStop(1,'rgba('+C2+',0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(p.x,p.y,hx,0,6.2832); ctx.fill();
      ctx.fillStyle='rgba(255,255,255,.96)';
      ctx.beginPath(); ctx.arc(p.x,p.y,r,0,6.2832); ctx.fill();
    });
  }
  function resize(){
    var r=cv.parentNode.getBoundingClientRect();
    if(!r.width) return;
    var dpr=Math.min(window.devicePixelRatio||1,2);
    W=r.width; H=r.height; R=Math.min(W,H)*.36;
    cv.width=Math.round(W*dpr); cv.height=Math.round(H*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
    draw();
  }
  function frame(){
    if(!alive) return;
    ctx.clearRect(0,0,W,H);
    rot+=.0022; pulse+=.016;                                  /* 自转 + 呼吸 */
    draw();
    FX.raf(frame);
  }
  resize();
  window.addEventListener('resize',resize);
  if(FX.on){
    FX.raf(frame);
    if('IntersectionObserver' in window){
      new IntersectionObserver(function(es){
        es.forEach(function(en){
          if(en.isIntersecting&&!alive){ alive=true; FX.raf(frame); }
          else if(!en.isIntersecting&&alive){ alive=false; }
        });
      },{threshold:0}).observe(cv.parentNode);
    }
  }
}
```

几个关键参数（调参先动这几个，别乱改结构）：

| 参数 | 当前值 | 作用 |
|------|--------|------|
| `TILT` | `-.38` | 地轴倾斜弧度，负值让北极朝观众 |
| `rot+=.0022` | 每帧自转 | 约 47s 转一圈，慢到不抢注意力 |
| 球半径 | `Min(W,H)*.36` | 四周留白给光环与轨道圈 |
| 航线弧高 | `1+sin(πu)*.34` | 航线离开球面的高度，太大就脱离球体 |
| 深度阈值 | 枢纽 `z<-.12` / 在途光标 `z<-.2` | 背面不画，避免"穿透球体"错觉 |
| `base` 透明度 | 纬线 `.52` / 赤道 `.62` / 经线 `.30` / 航线 `.42` | 太暗就看不出全息感（踩过这个坑） |

> 航线**必须**用 `slerp`（球面插值）而非线性插值——线性插值在长航线上会从球体内部穿过。这是"真 3D"与"贴图假装 3D"的分界线。

### F7. 错峰进场 · 滚动进度

F7-1 错峰进场：宿主加 `data-stagger`，子项依次浮现（步进 70ms）；宿主类由 JS 添加，JS 失效时子项默认可见。

```html
<div class="grid grid-cols-2 lg:grid-cols-4 gap-3" data-stagger>
  <div>…</div><div>…</div><div>…</div><div>…</div>
</div>
```

```javascript
function initStagger(){
  if(!FX.on||!('IntersectionObserver' in window)) return;
  var hosts=[].slice.call(document.querySelectorAll('[data-stagger]'));
  if(!hosts.length) return;
  var io=new IntersectionObserver(function(es){
    es.forEach(function(en){
      if(!en.isIntersecting) return;
      var kids=en.target.children;
      for(var i=0;i<kids.length;i++){
        kids[i].style.transitionDelay=(i*70)+'ms';
        kids[i].classList.add('fx-in');
      }
      /* 数字滚动延到子项浮现时再触发，否则动画会在不可见状态下跑完 */
      en.target.querySelectorAll('[data-count]').forEach(countUp);
      io.unobserve(en.target);
    });
  },{threshold:.05,rootMargin:'0px 0px -30px 0px'});
  hosts.forEach(function(h){ h.classList.add('fx-stagger'); io.observe(h); });
}
```

> 子项**不要**自己写 `opacity:0`。隐藏态在 `.fx-stagger>*` 上（F0-2 已含），宿主类由 JS 添加——这样 JS 失效时子项保持默认可见，不会出现"内容永远不显现"。
> 若同页还有非错峰容器里的 `[data-count]`，初始化时补一次（避开重复播放）：
> ```javascript
> document.querySelectorAll('[data-count]').forEach(function(el){
>   if(!(el.closest&&el.closest('[data-stagger]'))) countUp(el);
> });
> ```

F7-2 顶部滚动进度（纯装饰，减动时隐藏在 F0-2）：

```html
<div id="fxProgress"></div>
```
```css
#fxProgress{--p:0;position:fixed;top:0;left:0;width:100%;height:2px;z-index:60;pointer-events:none;
  background:linear-gradient(90deg,var(--primary),var(--secondary));
  box-shadow:0 0 10px rgba(var(--secondary-rgb),.75);transform:scaleX(var(--p));transform-origin:0 50%;}
```
```javascript
function initProgress(){
  var el=document.getElementById('fxProgress');
  if(!el) return;
  function upd(){
    var h=document.documentElement.scrollHeight-window.innerHeight;
    var p=h>0?((window.pageYOffset||document.documentElement.scrollTop)/h):0;
    el.style.setProperty('--p',Math.max(0,Math.min(1,p)).toFixed(4));
  }
  window.addEventListener('scroll',upd,{passive:true});
  window.addEventListener('resize',upd);
  upd();
}
```

### F8. 初始化顺序与性能红线

F8-1 初始化：`render*` 全部跑完再装动效（否则查询不到 JS 渲染出来的 `[data-tilt]` / `[data-stagger]`）：

```javascript
/* …… 所有 render*() 之后 …… */
initReveal();
initClock();
initProgress();
initParallax();
initPointerFX();
initStagger();
initNet();
initGlobe();
/* 错峰容器里的计数由 initStagger 在浮现时触发，这里跳过避免重复播放 */
document.querySelectorAll('[data-count]').forEach(function(el){
  if(!(el.closest&&el.closest('[data-stagger]'))) countUp(el);
});
```

F8-2 红线（机检逐条断言，见 SKILL.md §7）：

| # | 红线 | 为什么 |
|---|------|--------|
| 1 | 必须有 `@media (prefers-reduced-motion:reduce)` 降级块 | 无障碍；机检缺此媒体查询直接 ERROR |
| 2 | 隐藏态不得挂在默认选择器上（`.reveal{opacity:0}` 违规） | JS 失效即内容永久消失 |
| 3 | 动画只动 `transform` / `opacity` | 动 `width/height/top/left` 会触发重排，掉帧 |
| 4 | 大面积柔光禁用 `filter:blur` | 合成开销高一个量级；用径向渐变 |
| 5 | canvas 必须 DPR 封顶 2 + 节点数封顶 + IntersectionObserver 离屏暂停 | 否则高 DPI 屏 + 滚走后仍在满负荷 |
| 6 | 不引 three.js 等 3D 库 | 单文件零构建；3D 投影手写即可覆盖全息地球需求 |
| 7 | 首屏依赖的状态类**不能**用 CDN 运行时生成的 Tailwind 类（如 `opacity-0`） | CDN 抖动时类不生成 → 元素叠影/错位（真实踩坑：Banner 三张幻灯片叠成重影）。改用自带 CSS 类 |
| 8 | 标题不用 `background-clip:text` 通栏渐变 | 长中文标题在多行下渐变断裂，且对比度不可控 |

> §F 片段全部来自 `assets/portal-home.template.html` 的实测实现（机检 0 ERROR、gzip 后 25KB）。列表页 / 详情页按需取 F1（倾斜）、F2（视差）、F5（光效）、F7（错峰 / 进度）即可，**F4 粒子网络与 F6 全息地球只建议首页用一次**——同类强动效在一页里重复出现会互相打架、也拖垮体积预算。
