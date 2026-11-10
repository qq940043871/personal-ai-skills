class_name UIKit
## UI 工具：中文系统字体与主题。零素材方案——直接用系统自带字体。
## Windows 用微软雅黑；Android 上 SystemFont 不可靠，改为直接加载
## 系统自带 CJK 字体文件（/system/fonts/NotoSansCJK），避免中文变豆腐块。

const C_BG_DARK := Color(0.105882, 0.137255, 0.188235)
const C_PANEL := Color(0.16, 0.19, 0.25)
const C_GOLD := Color(0.95, 0.8, 0.4)
const C_TEXT_DIM := Color(0.62, 0.68, 0.76)

static func font() -> Font:
	if OS.has_feature("android"):
		for p in [
			"/system/fonts/NotoSansCJK-Regular.ttc",
			"/system/fonts/DroidSansFallback.ttf",
		]:
			if FileAccess.file_exists(p):
				var ff := FontFile.new()
				ff.load_dynamic_font(p)
				return ff
	var f := SystemFont.new()
	f.font_names = PackedStringArray([
		"Microsoft YaHei UI", "Microsoft YaHei", "SimHei", "SimSun",
	])
	return f

static func build_theme() -> Theme:
	var t := Theme.new()
	t.default_font = font()
	t.default_font_size = 18
	return t
