extends SceneTree
## 数据层无头自检：地图完整性、钥匙门序连通性（软锁检测）、战斗公式。
## 运行（项目目录下）：
##   godot --headless --path . --import        （先刷新脚本类缓存）
##   godot --headless -s test/autotest.gd

const LEGEND := "#.><CYBRstkwXcSg12adybrPF$"
const DIRS4 := [Vector2i(1, 0), Vector2i(-1, 0), Vector2i(0, 1), Vector2i(0, -1)]

var fails := 0

func _initialize() -> void:
	_check_maps()
	_check_connectivity()
	_check_combat()
	if fails == 0:
		print("AUTOTEST PASS")
	else:
		print("AUTOTEST FAIL x%d" % fails)
	quit(0 if fails == 0 else 1)

func _fail(msg: String) -> void:
	fails += 1
	print("  [FAIL] " + msg)

# ---------- 地图完整性 ----------

func _check_maps() -> void:
	var p_count := 0
	var f_count := 0
	var keys := {"y": 0, "b": 0, "r": 0}
	var doors := {"y": 0, "b": 0, "r": 0}
	for fi in FloorData.FLOORS.size():
		var f: Dictionary = FloorData.FLOORS[fi]
		var m: Array = f["map"]
		if m.size() != FloorData.ROWS:
			_fail("楼层 %d 行数 %d ≠ %d" % [fi, m.size(), FloorData.ROWS])
		var up := 0
		var down := 0
		var core_count := 0
		for y in m.size():
			var line: String = m[y]
			if line.length() != FloorData.COLS:
				_fail("楼层 %d 第 %d 行长度 %d ≠ %d" % [fi, y, line.length(), FloorData.COLS])
			for x in line.length():
				var ch := line[x]
				if not LEGEND.contains(ch):
					_fail("楼层 %d 非法字符 '%s'" % [fi, ch])
				match ch:
					">":
						up += 1
					"<":
						down += 1
					"C":
						core_count += 1
					"P":
						p_count += 1
					"F":
						f_count += 1
					"y", "b", "r":
						keys[ch] += 1
					"Y", "B", "R":
						doors[ch.to_lower()] += 1
		var expect_core := 1 if int(f.get("core_hp", 0)) > 0 else 0
		if core_count != expect_core:
			_fail("楼层 %d 家庭之心数量 %d ≠ %d" % [fi, core_count, expect_core])
		if fi == 0:
			if up != 1 or down != 0:
				_fail("第 1 层楼梯配置错误（应只有上楼）")
		elif fi == FloorData.FLOORS.size() - 1:
			if up != 0 or down != 1:
				_fail("顶层楼梯配置错误（应只有下楼）")
		else:
			if up != 1 or down != 1:
				_fail("楼层 %d 楼梯配置错误（应上下各一）" % fi)
		# 粗检：累计钥匙必须不少于累计门
		for c in ["y", "b", "r"]:
			if doors[c] > keys[c]:
				_fail("楼层累计：%s门 %d 扇 > %s钥匙 %d 把" % [c, doors[c], c, keys[c]])
	if p_count != 1:
		_fail("P 数量 %d ≠ 1" % p_count)
	if f_count != 1:
		_fail("F 数量 %d ≠ 1" % f_count)

# ---------- 连通性 + 软锁检测（贪心迭代开门 BFS） ----------

func _check_connectivity() -> void:
	var carried := {"y": 0, "b": 0, "r": 0}
	for fi in FloorData.FLOORS.size():
		var f: Dictionary = FloorData.FLOORS[fi]
		var m: Array = f["map"]
		var start := Vector2i(-1, -1)
		var goal := Vector2i(-1, -1)
		var interest: Array[Vector2i] = []   # 钥匙/道具/魔物/NPC 都应可达
		var door_cells: Array[Vector2i] = []
		for y in m.size():
			var line: String = m[y]
			for x in line.length():
				var ch := line[x]
				match ch:
					"P", "<":
						start = Vector2i(x, y)
					">":
						goal = Vector2i(x, y)
					"Y", "B", "R":
						door_cells.append(Vector2i(x, y))
					"#", ".", "C":
						pass
					_:
						interest.append(Vector2i(x, y))
		if start.x < 0:
			_fail("楼层 %d 找不到出生点" % fi)
			continue
		var removed: Dictionary = {}
		var opened := {"y": 0, "b": 0, "r": 0}
		var reach: Dictionary = {}
		for iter in 24:
			reach = _bfs(m, start, removed)
			var have := {
				"y": int(carried["y"]), "b": int(carried["b"]), "r": int(carried["r"]),
			}
			for cell in interest:
				var ch: String = m[cell.y][cell.x]
				if reach.has(cell) and "ybr".contains(ch):
					have[ch] += 1
			var progressed := false
			for dcell in door_cells:
				if removed.has(dcell):
					continue
				var color: String = String(m[dcell.y][dcell.x]).to_lower()
				if int(have[color]) - int(opened[color]) <= 0:
					continue
				for d in DIRS4:
					if reach.has(dcell + d):
						removed[dcell] = true
						opened[color] += 1
						progressed = true
						break
			if not progressed:
				break
		if goal.x >= 0 and not reach.has(goal):
			_fail("楼层 %d：上楼楼梯不可达" % fi)
		for cell in interest:
			if not reach.has(cell):
				_fail("楼层 %d：'%s' @ %s 不可达（可能软锁）" % [fi, m[cell.y][cell.x], cell])
		# 剩余钥匙结转到下一层
		for cell in interest:
			var ch2: String = m[cell.y][cell.x]
			if "ybr".contains(ch2) and reach.has(cell):
				carried[ch2] = int(carried[ch2]) + 1
		for c in ["y", "b", "r"]:
			carried[c] = int(carried[c]) - int(opened[c])

func _bfs(m: Array, start: Vector2i, removed: Dictionary) -> Dictionary:
	var reach := {start: true}
	var queue: Array[Vector2i] = [start]
	while queue.size() > 0:
		var cur: Vector2i = queue.pop_front()
		for d in DIRS4:
			var nxt: Vector2i = cur + d
			if nxt.x < 0 or nxt.y < 0 or nxt.x >= FloorData.COLS or nxt.y >= FloorData.ROWS:
				continue
			if reach.has(nxt):
				continue
			var ch: String = m[nxt.y][nxt.x]
			if ch == "#":
				continue
			if "YBR".contains(ch) and not removed.has(nxt):
				continue  # 未开的门不可通过
			reach[nxt] = true
			queue.append(nxt)
	return reach

# ---------- 战斗公式 ----------

func _check_combat() -> void:
	var r := Combat.resolve(10, 10, MonsterData.DATA["s"])
	if not (r["can_win"] and int(r["hits"]) == 4 and int(r["loss"]) == 6):
		_fail("史莱姆战斗数值异常：%s" % str(r))
	r = Combat.resolve(10, 10, {"hp": 30, "atk": 12, "def": 10})
	if r["can_win"]:
		_fail("攻击不破防时应 can_win=false")
	r = Combat.resolve(24, 18, MonsterData.DATA["X"])
	if int(r["hits"]) != 26 or int(r["loss"]) != 500:
		_fail("魔王战斗数值异常：%s" % str(r))
	# 每层魔物用「该层入门属性估计」应可击败（防数值失衡）
	var stats := [
		{"atk": 10, "def": 10, "hp": 1200},
		{"atk": 14, "def": 12, "hp": 1600},
		{"atk": 16, "def": 14, "hp": 2200},
		{"atk": 20, "def": 16, "hp": 2600},
		{"atk": 24, "def": 18, "hp": 3200},
	]
	for fi in FloorData.FLOORS.size():
		var m: Array = FloorData.FLOORS[fi]["map"]
		for y in m.size():
			var line: String = m[y]
			for x in line.length():
				var ch := line[x]
				if not MonsterData.DATA.has(ch):
					continue
				var s: Dictionary = stats[fi]
				var res := Combat.resolve(int(s["atk"]), int(s["def"]), MonsterData.DATA[ch])
				if not res["can_win"]:
					_fail("楼层 %d 的%s以入门属性攻不破" % [fi, MonsterData.DATA[ch]["name"]])
				elif int(res["loss"]) >= int(s["hp"]):
					_fail("楼层 %d 的%s入门属性打必死（损血 %d）" % [fi, MonsterData.DATA[ch]["name"], int(res["loss"])])
