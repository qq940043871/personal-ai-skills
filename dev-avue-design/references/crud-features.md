# avue-crud 高级功能参考

## 目录

1. [树形表格](#树形表格)
2. [虚拟滚动](#虚拟滚动)
3. [卡片/网格模式](#卡片网格模式)
4. [行编辑（单元格编辑）](#行编辑)
5. [导入导出](#导入导出)
6. [拖拽排序](#拖拽排序)
7. [合计行](#合计行)
8. [父子表](#父子表)
9. [加载状态](#加载状态)
10. [CRUD 插件模式](#crud-插件模式)

---

## 树形表格

### 基本树表

```javascript
option: {
  rowKey: 'id',
  rowParentKey: 'parentId',
  defaultExpandAll: true,  // 默认展开所有
  column: [
    { label: '名称', prop: 'name' },
    { label: '编码', prop: 'code' },
  ],
}

// 数据需要有 id 和 parentId 字段
data: [
  { id: 1, parentId: 0, name: '父节点', code: 'P1' },
  { id: 2, parentId: 1, name: '子节点', code: 'C1' },
]
```

### 懒加载树表

```vue
<avue-crud :option="option" @tree-load="treeLoad">

option: {
  rowKey: 'id',
  lazy: true,
  column: [
    { label: '名称', prop: 'name', hasChildren: 'hasChildren' },
  ],
}

const treeLoad = (row, treeNode, resolve) => {
  getChildren(row.id).then(res => {
    resolve(res.data.data)
  })
}
```

注意：非懒加载时需去掉 `hasChildren` 字段。

---

## 虚拟滚动 (3.7.0+)

用于大数据量场景的虚拟滚动：

```javascript
option: {
  virtualize: true,
  height: 500,  // 必须为数字
  column: [
    {
      label: '名称',
      prop: 'name',
      width: 200,   // 虚拟滚动时 width 必须为数字
      fixed: true,   // 列自适应
    },
  ],
}
```

注意：虚拟滚动模式下 `width` 和 `height` 必须是数字类型。

自适应高度：

```javascript
option: {
  virtualize: true,
  height: 'auto',  // 自适应
}
```

---

## 卡片/网格模式 (3.4.0+)

将表格显示为卡片网格形式：

```javascript
option: {
  grid: true,           // 启用网格模式
  gridBtn: true,        // 显示切换按钮（默认true）
  gridSpan: 8,          // 每卡片占栅格数
  gridBackgroundImage: 'url(xxx)',  // 背景图
  gridBackground: '#f5f5f5',       // 背景色
}

// 背景色也可以是函数
option: {
  gridBackground: (row, index) => {
    return index % 2 === 0 ? '#f0f9ff' : '#fff'
  },
}
```

自定义卡片插槽：

```vue
<template #default="{ row, index }">
  <div class="custom-card">
    <h3>{{ row.name }}</h3>
    <p>{{ row.description }}</p>
  </div>
</template>
```

---

## 行编辑

### 基本行编辑

```javascript
option: {
  cellBtn: true,     // 显示行编辑按钮
  addRowBtn: true,   // 显示行新增按钮
  column: [
    {
      label: '名称',
      prop: 'name',
      cell: true,    // 该列可编辑
    },
    {
      label: '状态',
      prop: 'status',
      type: 'select',
      cell: true,
      dicData: [
        { label: '启用', value: 1 },
        { label: '禁用', value: 0 },
      ],
    },
  ],
}
```

### 首次进入编辑模式

```javascript
// 数据中设置 $cellEdit: true
data: [{ id: 1, name: 'test', $cellEdit: true }]
```

### 单击/双击编辑

```vue
<!-- 单击编辑 -->
<avue-crud @cell-click="cellClick">

const cellClick = (row, column, cell, event) => {
  row.$cellEdit = true
}

<!-- 双击编辑 -->
<avue-crud @cell-dblclick="cellDblClick">

const cellDblClick = (row, column, cell, event) => {
  row.$cellEdit = true
}
```

### 保存行编辑

数据必须包含 `rowKey`（默认 id）字段才能保存。

---

## 导入导出

### 导出 Excel

```javascript
option: {
  excelBtn: true,  // 显示导出按钮
}
```

需引入外部库：

```html
<script src="https://cdn.staticfile.net/FileSaver.js/2014-11-29/FileSaver.min.js"></script>
<script src="https://cdn.staticfile.net/xlsx/0.18.2/xlsx.full.min.js"></script>
```

### 编程式导出

```javascript
import { $Export } from '@smallwei/avue'

$Export.excel({
  title: '导出标题',
  columns: option.column,
  data: data.value,
})
```

### 导入 Excel

参考 `default/export/import` 示例。

---

## 拖拽排序

### 行拖拽排序

```javascript
option: {
  sortable: true,  // 启用行拖拽
  rowKey: 'id',    // 必须设置主键
}
```

需引入 Sortable.js：

```html
<script src="https://cdn.staticfile.net/Sortable/1.10.0-rc2/Sortable.min.js"></script>
```

监听排序事件：

```vue
<avue-crud @sortable-change="sortableChange">

const sortableChange = ({ newIndex, oldIndex }) => {
  // 处理排序逻辑
}
```

### 列拖拽排序 (3.5.2+)

```javascript
column: [
  {
    label: '名称',
    prop: 'name',
    columnSort: true, // 启用列拖拽
  },
]
```

监听事件：

```vue
<avue-crud @column-sortable-change="columnSortableChange">
```

---

## 合计行

### 内置合计

```javascript
option: {
  showSummary: true,
  sumColumnList: [
    { name: 'amount', type: 'sum' },      // 求和
    { name: 'price', type: 'average' },    // 平均值
    { name: 'count', type: 'count' },      // 计数
  ],
}
```

### 自定义合计

```vue
<avue-crud :summary-method="summaryMethod">

const summaryMethod = ({ columns, data }) => {
  const sums = []
  columns.forEach((column, index) => {
    if (index === 0) {
      sums[index] = '合计'
      return
    }
    const values = data.map(item => Number(item[column.property]))
    if (!values.every(isNaN)) {
      sums[index] = values.reduce((a, b) => a + b, 0).toFixed(2)
    } else {
      sums[index] = '-'
    }
  })
  return sums
}
```

---

## 父子表

```vue
<avue-crud :option="parentOption" :data="parentData" @row-click="parentRowClick">
  <!-- 子表通过展开行或独立组件实现 -->
  <template #expand="{ row }">
    <avue-crud :option="childOption" :data="row.children" />
  </template>
</avue-crud>
```

或使用独立组件封装子表，通过 `crud-children` 模式。

---

## 加载状态

```vue
<avue-crud :table-loading="loading">

const loading = ref(true)
// 数据加载完成后
loading.value = false
```

---

## CRUD 插件模式

### Mixin 模式（Options API）

```javascript
// @/mixins/crud.js
export default (app, option = {}) => {
  let optionObj = import.meta.glob(`../option/**/**`)[`../option/${option.name}.js`]
  let apiObj = import.meta.glob(`../api/**/**`)[`../api/${option.name}.js`]
  // ... mixin 逻辑
}

// 全局注册
// main.js
import crudCommon from '@/mixins/crud'
window.$crudCommon = crudCommon

// 使用
export default window.$crudCommon({
  data() { return {} },
  methods: {
    listBefore() {},
    listAfter() {},
    addBefore() { this.form.createUser = 'admin' },
    addAfter() {},
    updateBefore() {},
    updateAfter() {},
    delBefore() {},
    delAfter() {},
  }
}, {
  name: 'system/params',
  list: 'list',
  update: 'update',
  add: 'add',
  del: 'del',
  rowKey: 'id',
  pageNumber: 'pageNumber',
  pageSize: 'pageSize',
  res: (data) => ({ total: data.total, data: data.records }),
  total: 'total',
  data: 'records',
})
```

### 绑定辅助（Options API）

```vue
<avue-crud v-bind="bindVal" v-on="onEvent" v-model="form" v-model:page="page">

computed: {
  bindVal() {
    return {
      ref: 'crud',
      option: this.option,
      data: this.data,
      tableLoading: this.loading,
    }
  },
  onEvent() {
    return {
      'on-load': this.getList,
      'row-save': this.rowSave,
      'row-update': this.rowUpdate,
      'row-del': this.rowDel,
      'refresh-change': this.refreshChange,
      'search-reset': this.searchChange,
      'search-change': this.searchChange,
    }
  },
}
```

### API 文件模板

```javascript
// @/api/module/entity.js
import request from '@/router/axios'

export const getList = (current, size, params) => {
  return request({
    url: '/api/entity/list',
    method: 'get',
    params: { current, size, ...params },
  })
}

export const getDetail = (id) => {
  return request({
    url: '/api/entity/detail',
    method: 'get',
    params: { id },
  })
}

export const add = (data) => {
  return request({
    url: '/api/entity/submit',
    method: 'post',
    data,
  })
}

export const update = (data) => {
  return request({
    url: '/api/entity/submit',
    method: 'post',
    data,
  })
}

export const remove = (ids) => {
  return request({
    url: '/api/entity/remove',
    method: 'post',
    params: { ids },
  })
}
```

### Option 配置文件模板

```javascript
// @/option/module/entity.js
export default (safe) => {
  // safe => vue 的 this 对象 (Options API)
  return {
    index: true,
    align: 'center',
    headerAlign: 'center',
    border: true,
    stripe: true,
    column: [
      {
        label: '名称',
        prop: 'name',
        search: true,
        rules: [{ required: true, message: '请输入名称', trigger: 'blur' }],
      },
    ],
  }
}
```

---

## 配置动态切换

### 初始化加载

```vue
<avue-crud v-if="option.column" :option="option">

const option = ref({})
onMounted(() => {
  // 从服务器加载配置
  getConfig().then(res => {
    option.value = res.data
  })
})
```

### 动态切换配置

```javascript
const changeOption = (type) => {
  if (type === 'simple') {
    option.value = simpleOption
  } else {
    option.value = fullOption
  }
}
```

---

## 空状态自定义

```javascript
option: {
  emptyText: '暂无数据',  // 空状态文字
}
```

```vue
<!-- 自定义空状态 -->
<template #empty>
  <div class="custom-empty">
    <img src="empty.png" />
    <p>暂无数据，请添加</p>
  </div>
</template>
```

---

## 深层数据绑定

```javascript
// 数据结构: { id: 1, info: { address: '北京' } }
column: [
  {
    label: '地址',
    prop: 'address', // prop 仍然需要
    bind: 'info.address', // 绑定深层路径
  },
]
```

---

## 自定义按钮

```vue
<!-- 隐藏默认按钮，使用自定义 -->
option: { addBtn: false, editBtn: false, delBtn: false, viewBtn: false }

<!-- 自定义新增按钮 -->
<template #menu-left>
  <el-button type="primary" @click="$refs.crud.rowAdd()">自定义新增</el-button>
</template>

<!-- 自定义操作按钮 -->
<template #menu="{ row, index, type, size }">
  <el-button :size="size" type="text" @click="$refs.crud.rowEdit(row, index)">编辑</el-button>
  <el-button :size="size" type="text" @click="$refs.crud.rowView(row, index)">查看</el-button>
  <el-button :size="size" type="text" @click="$refs.crud.rowDel(row, index)">删除</el-button>
</template>

<!-- 自定义弹窗按钮 -->
<template #menu-form="{ type }">
  <el-button v-if="type === 'add'">自定义保存</el-button>
  <el-button v-if="type === 'edit'">自定义更新</el-button>
</template>
```
