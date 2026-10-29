// ===== 平板三栏布局专用工具（模板） =====
// 用途：窗口宽度监听、断点判断、三栏布局状态（收起/展开）、内容视图切换
// 复制到项目 utils/pad-layout-helper.js 后，按需调整 LAYOUT 数值

import { ref, computed, onMounted, onUnmounted } from 'vue'

// ===== 断点常量（单位 dp/CSS px） =====
// 对照 Android 的 layout-swXXXdp-land 思路
export const BREAKPOINTS = {
  PHONE: 0,          // 手机竖屏
  PHONE_LAND: 600,   // 手机横屏/小折叠
  TABLET_PORT: 680,  // 小平板竖屏/分屏
  TABLET_LAND: 853,  // 小米平板5 标准横屏逻辑宽
  TABLET_LG: 960,    // 大屏平板横屏
}

// ===== 三栏布局尺寸常量（dp/CSS px） =====
export const LAYOUT = {
  LEFT_NAV: 220,      // 左栏固定宽度
  RIGHT_PANEL: 220,   // 右栏固定宽度
  BOTTOM_BAR: 70,     // 底部通栏高度
  LEFT_COLLAPSED: 72, // 左栏收起后宽度（仅头像）
  GAP: 12,            // 栏间距
}

// ===== 窗口状态（响应式） =====
export function useWindowState() {
  const windowWidth = ref(853)
  const windowHeight = ref(533)
  const isLandscape = ref(true)

  function update() {
    try {
      const info = uni.getWindowInfo()
      windowWidth.value = info.windowWidth
      windowHeight.value = info.windowHeight
      isLandscape.value = info.windowWidth > info.windowHeight
    } catch {
      // H5 兜底
    }
  }

  onMounted(() => {
    update()
    try { uni.onWindowResize(update) } catch {}
  })
  onUnmounted(() => {
    try { uni.offWindowResize(update) } catch {}
  })

  return { windowWidth, windowHeight, isLandscape }
}

// ===== 断点判断 =====
export function useBreakpoint(windowWidth) {
  const breakpoint = computed(() => {
    const w = windowWidth.value
    if (w >= BREAKPOINTS.TABLET_LG) return 'tablet-lg'
    if (w >= BREAKPOINTS.TABLET_LAND) return 'tablet-land'
    if (w >= BREAKPOINTS.TABLET_PORT) return 'tablet-port'
    if (w >= BREAKPOINTS.PHONE_LAND) return 'phone-land'
    return 'phone'
  })

  // 是否进入三栏布局（平板横屏）
  const isThreeColumn = computed(() =>
    breakpoint.value === 'tablet-land' || breakpoint.value === 'tablet-lg'
  )
  // 是否主从布局（小平板竖屏）
  const isMasterDetail = computed(() => breakpoint.value === 'tablet-port')
  const isTabletLand = computed(() => isThreeColumn.value)

  return { breakpoint, isTabletLand, isThreeColumn, isMasterDetail }
}

// ===== 三栏布局状态 =====
export function useLayoutState() {
  const leftCollapsed = ref(false)
  const rightCollapsed = ref(false)
  const middleView = ref('home')   // 中栏当前视图
  const rightTab = ref('detail')   // 右栏当前 Tab

  const leftWidth = computed(() =>
    leftCollapsed.value ? LAYOUT.LEFT_COLLAPSED : LAYOUT.LEFT_NAV
  )
  const rightWidth = computed(() =>
    rightCollapsed.value ? 0 : LAYOUT.RIGHT_PANEL
  )

  function toggleLeft() { leftCollapsed.value = !leftCollapsed.value }
  function toggleRight() { rightCollapsed.value = !rightCollapsed.value }
  function setMiddleView(view) { middleView.value = view }
  function setRightTab(tab) { rightTab.value = tab }

  return {
    leftCollapsed, rightCollapsed,
    middleView, rightTab,
    leftWidth, rightWidth,
    toggleLeft, toggleRight,
    setMiddleView, setRightTab,
  }
}
