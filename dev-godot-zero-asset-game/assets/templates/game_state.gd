extends Node
## 自动加载单例（autoload 名：Game）：玩家数值、钥匙、核心血量、楼层状态与存档。
## 楼层地图与交互在 FloorMap，本单例只管「账本」。

signal stats_changed
signal message_posted(text: String)
signal preview_changed(text: String)
signal core_failed

const SAVE_PATH := "user://save.json"
const PLAYER_INIT := {"hp": 1000, "atk": 10, "def": 10, "gold": 0, "keys": {"y": 1, "b": 0, "r": 0}}

var player: Dictionary = {}
var floor_index := 0
var entry_spawn := "P"          # 进入本层时的落点字符：P / < / >
var core_hp := 0
var core_hp_max := 0
var kills := 0
var total_steps := 0
var floor_state: Dictionary = {}   # {"楼层号": {"removed": {"x,y": true}}}，保证杀过的怪/开过的门/拿过的道具不刷新
var snapshot: Dictionary = {}      # 进入楼层时的状态快照，核心失守后回滚用
var encountered: Dictionary = {}   # 魔物图鉴：字符 -> {"kills": 击败数}，首次照面即登记
var core_pressure := 0             # 上一步的侵蚀速率（存活焦虑虫数），HUD 展示用
var tutorial_seen := false         # 侵蚀层规则教学弹窗只弹一次

func _ready() -> void:
	start_new()

# ---------- 状态流转 ----------

func start_new() -> void:
	player = PLAYER_INIT.duplicate(true)
	floor_index = 0
	entry_spawn = "P"
	kills = 0
	total_steps = 0
	floor_state = {}
	encountered = {}
	core_pressure = 0
	tutorial_seen = false
	snapshot = {}
	core_hp = 0
	core_hp_max = 0
	notify()

func setup_floor(index: int) -> void:
	## 每次进入楼层时调用：设定核心、打快照、自动存档。
	floor_index = index
	var f: Dictionary = FloorData.FLOORS[index]
	core_hp_max = int(f.get("core_hp", 0))
	core_hp = core_hp_max
	core_pressure = 0
	_make_snapshot()
	_save()
	notify()

func retry_floor() -> void:
	## 核心失守后重开本层：回到进入本层那一刻的状态。
	player = (snapshot["player"] as Dictionary).duplicate(true)
	core_hp = int(snapshot["core_hp"])
	var removed: Dictionary = get_removed(floor_index)
	removed.clear()
	var snap_removed: Dictionary = snapshot["removed"]
	for id in snap_removed:
		removed[id] = true
	notify()

func _make_snapshot() -> void:
	snapshot = {
		"player": player.duplicate(true),
		"core_hp": core_hp,
		"removed": get_removed(floor_index).duplicate(),
	}

# ---------- 楼层状态（防刷：拿过的不再出现） ----------

func get_removed(index: int) -> Dictionary:
	var k := str(index)
	if not floor_state.has(k):
		floor_state[k] = {"removed": {}}
	return floor_state[k]["removed"]

func mark_removed(index: int, id: String) -> void:
	get_removed(index)[id] = true

# ---------- 交互接口 ----------

func use_key(color: String) -> bool:
	if int(player["keys"].get(color, 0)) > 0:
		player["keys"][color] = int(player["keys"][color]) - 1
		notify()
		return true
	return false

func apply_item(ch: String) -> void:
	## ch 为地图字符，见 ItemData.ITEMS。
	var it: Dictionary = ItemData.ITEMS[ch]
	match it["kind"]:
		"hp_s", "hp_l":
			player["hp"] = int(player["hp"]) + int(it["hp"])
			emit_message("%s：HP +%d" % [it["name"], int(it["hp"])])
		"gem_a":
			player["atk"] = int(player["atk"]) + int(it["atk"])
			emit_message("%s：攻击 +%d" % [it["name"], int(it["atk"])])
		"gem_d":
			player["def"] = int(player["def"]) + int(it["def"])
			emit_message("%s：防御 +%d" % [it["name"], int(it["def"])])
		"key_y", "key_b", "key_r":
			var color: String = it["kind"].right(1)
			player["keys"][color] = int(player["keys"].get(color, 0)) + 1
			emit_message("捡到%s。" % it["name"])
	notify()

func win_battle(m: Dictionary, loss: int) -> void:
	player["hp"] = int(player["hp"]) - loss
	player["gold"] = int(player["gold"]) + int(m["gold"])
	kills += 1
	if loss > 0:
		emit_message("击败%s！损血 %d，金币 +%d" % [m["name"], loss, int(m["gold"])])
	else:
		emit_message("毫发无伤地击败了%s！金币 +%d" % [m["name"], int(m["gold"])])
	notify()

func tick_corrupters(n: int) -> void:
	## 玩家每走一步调用：n 为仍存活的焦虑虫数量，同时侵蚀核心。
	total_steps += 1
	core_pressure = n
	if core_hp_max > 0 and n > 0:
		var prev := int(core_hp)
		core_hp = maxi(core_hp - n, 0)
		if core_hp <= 0:
			core_failed.emit()
		elif prev > int(core_hp_max / 2.0) and core_hp <= int(core_hp_max / 2.0):
			emit_message("⚠ 家庭之心 %d/%d：被侵蚀过半！焦虑虫每步还在 -%d，优先清虫！" % [core_hp, core_hp_max, n])
		elif prev > int(core_hp_max / 5.0) and core_hp <= int(core_hp_max / 5.0):
			emit_message("⚠⚠ 家庭之心只剩 %d 点！马上消灭焦虑虫！" % core_hp)
	notify()

# ---------- 图鉴与商店 ----------

func meet_monster(ch: String) -> void:
	if not encountered.has(ch):
		encountered[ch] = {"kills": 0}

func register_kill(ch: String) -> void:
	meet_monster(ch)
	encountered[ch]["kills"] = int(encountered[ch]["kills"]) + 1

func kill_count(ch: String) -> int:
	if not encountered.has(ch):
		return 0
	return int(encountered[ch]["kills"])

func buy(id: String) -> bool:
	for g in ShopData.GOODS:
		if g["id"] != id:
			continue
		var price := int(g["price"])
		if int(player["gold"]) < price:
			emit_message("金币不足，还差 %d 枚。" % [price - int(player["gold"])])
			return false
		player["gold"] = int(player["gold"]) - price
		match id:
			"key_y", "key_b", "key_r":
				var c: String = id.right(1)
				player["keys"][c] = int(player["keys"].get(c, 0)) + 1
				emit_message("购入%s。" % g["name"])
			"hp_s":
				player["hp"] = int(player["hp"]) + 150
				emit_message("购入小血瓶：HP +150")
			"hp_l":
				player["hp"] = int(player["hp"]) + 400
				emit_message("购入大血瓶：HP +400")
			"atk_up":
				player["atk"] = int(player["atk"]) + 2
				emit_message("攻击强化：攻击 +2")
			"def_up":
				player["def"] = int(player["def"]) + 2
				emit_message("防御强化：防御 +2")
		notify()
		return true
	return false

# ---------- 信号转发 ----------

func notify() -> void:
	stats_changed.emit()

func emit_message(text: String) -> void:
	message_posted.emit(text)

func set_preview(text: String) -> void:
	preview_changed.emit(text)

# ---------- 存档 ----------

func _save() -> void:
	var data := {
		"player": player,
		"floor_index": floor_index,
		"entry_spawn": entry_spawn,
		"kills": kills,
		"total_steps": total_steps,
		"floor_state": floor_state,
		"encountered": encountered,
		"tutorial_seen": tutorial_seen,
	}
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f != null:
		f.store_string(JSON.stringify(data))

func has_save() -> bool:
	return FileAccess.file_exists(SAVE_PATH)

func clear_save() -> void:
	if has_save():
		DirAccess.remove_absolute(ProjectSettings.globalize_path(SAVE_PATH))

func load_save() -> bool:
	if not has_save():
		return false
	var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if f == null:
		return false
	var data = JSON.parse_string(f.get_as_text())
	if typeof(data) != TYPE_DICTIONARY:
		return false
	player = (data.get("player", PLAYER_INIT.duplicate(true)) as Dictionary).duplicate(true)
	for k in player["keys"]:
		player["keys"][k] = int(player["keys"][k])
	player["hp"] = int(player["hp"])
	player["atk"] = int(player["atk"])
	player["def"] = int(player["def"])
	player["gold"] = int(player["gold"])
	floor_index = int(data.get("floor_index", 0))
	entry_spawn = str(data.get("entry_spawn", "P"))
	kills = int(data.get("kills", 0))
	total_steps = int(data.get("total_steps", 0))
	floor_state = {}
	var fs = data.get("floor_state", {})
	if typeof(fs) == TYPE_DICTIONARY:
		for k in fs:
			var removed: Dictionary = {}
			var v = fs[k]
			if typeof(v) == TYPE_DICTIONARY and v.has("removed"):
				for id in v["removed"]:
					removed[str(id)] = true
			floor_state[str(k)] = {"removed": removed}
	encountered = {}
	var enc = data.get("encountered", {})
	if typeof(enc) == TYPE_DICTIONARY:
		for k in enc:
			encountered[str(k)] = {"kills": int(enc[k].get("kills", 0)) if typeof(enc[k]) == TYPE_DICTIONARY else 0}
	tutorial_seen = bool(data.get("tutorial_seen", false))
	notify()
	return true
