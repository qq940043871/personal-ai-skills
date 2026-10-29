// ===== 小米平板横屏专用工具（模板） =====
// 用途：横屏判断、窗口信息、安全区、屏幕旋转监听
// 复制到项目 utils/pad-land-helper.js 后，按需调整断点数值

// 获取窗口信息（宽高，单位 dp/CSS px）
export function getWinInfo() {
  return uni.getWindowInfo()
}

// 获取系统安全区（横屏手势横条/刘海）
export function getSafeArea() {
  const sys = uni.getSystemInfoSync()
  return sys.safeArea
}

// 判断当前是否横屏（宽 > 高）
export function isLandscape() {
  const { windowWidth, windowHeight } = getWinInfo()
  return windowWidth > windowHeight
}

// 判断是否为平板横屏（横屏且宽度达到阈值）
// 小米平板5 横屏物理 2560x1600，逻辑宽约 800~960dp
export function isPadLand(minWidth = 800) {
  const { windowWidth, windowHeight } = getWinInfo()
  return windowWidth > windowHeight && windowWidth >= minWidth
}

// 屏幕旋转监听（用于：竖屏时锁回横屏、横竖屏切换时切换布局）
export function onRotateWatch(callback) {
  uni.onWindowResize((res) => {
    callback({
      w: res.windowWidth,
      h: res.windowHeight,
      landscape: res.windowWidth > res.windowHeight,
      safe: getSafeArea(),
    })
  })
}
