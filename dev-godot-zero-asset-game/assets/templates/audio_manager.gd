extends Node
## 自动加载单例（autoload 名：Sound）：零素材合成音效与芯片音乐。
## 启动时用代码合成 PCM → AudioStreamWAV；BGM 为无缝循环 wav，后台线程合成。

const SFX_RATE := 22050
const MUSIC_RATE := 16000

var muted := false
var sfx: Dictionary = {}
var _music: Dictionary = {}
var _music_done := false
var _want_bgm := ""
var _sfx_players: Array = []
var _music_player: AudioStreamPlayer

func _ready() -> void:
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_sfx_players.append(p)
	_music_player = AudioStreamPlayer.new()
	_music_player.volume_db = -13.0
	add_child(_music_player)
	_build_sfx()
	# BGM 音量较大、合成耗时，延迟到窗口出现后再合成
	get_tree().create_timer(0.3).timeout.connect(_build_music)

# ---------- 播放接口 ----------

func play(name: String) -> void:
	if muted or not sfx.has(name):
		return
	for p in _sfx_players:
		if not p.playing:
			p.stream = sfx[name]
			p.volume_db = -5.0
			p.play()
			return
	_sfx_players[0].stream = sfx[name]
	_sfx_players[0].play()

func bgm(name: String) -> void:
	_want_bgm = name
	_apply_music()

func set_muted(m: bool) -> void:
	muted = m
	_apply_music()

func _apply_music() -> void:
	if muted or _want_bgm == "" or not _music_done:
		_music_player.stop()
		return
	var st: AudioStreamWAV = _music.get(_want_bgm)
	if st == null:
		return
	if _music_player.stream != st or not _music_player.playing:
		_music_player.stream = st
		_music_player.play()

func _build_music() -> void:
	if _music_done:
		return
	_music["title"] = _render_song(84.0,
		[["E4",1],["G4",1],["A4",2], ["G4",1],["E4",1],["D4",2], ["C4",1],["D4",1],["E4",2], ["G4",2],["E4",2],
		 ["A4",1],["G4",1],["E4",2], ["G4",1],["A4",1],["C5",2], ["A4",2],["G4",2], ["E4",4]],
		[["C3",4],["G2",4],["A2",4],["E2",4],["F2",4],["C3",4],["G2",4],["C3",4]])
	_music["main"] = _render_song(132.0,
		[["G4",1],["C5",1],["E5",1],["G5",1], ["E5",2],["C5",2], ["D5",1],["E5",1],["F5",1],["D5",1], ["E5",2],["C5",2],
		 ["A4",1],["C5",1],["F5",1],["E5",1], ["D5",2],["G4",2], ["C5",1],["D5",1],["E5",1],["G5",1], ["E5",2],["D5",2],
		 ["C5",1],["E5",1],["G5",2], ["A5",1],["G5",1],["E5",2], ["F5",2],["E5",2], ["C5",4]],
		[["C3",2],["G2",2],["A2",2],["E2",2],["F2",2],["G2",2],["C3",2],["G2",2],
		 ["C3",2],["G2",2],["A2",2],["E2",2],["F2",2],["G2",2],["C3",2],["G2",2],
		 ["C3",2],["G2",2],["A2",2],["E2",2],["F2",2],["G2",2],["C3",2],["G2",2]])
	_music["tense"] = _render_song(150.0,
		[["A4",1],["B4",1],["C5",2], ["A4",2],["E4",2], ["F4",1],["E4",1],["D4",2], ["E4",4],
		 ["A4",1],["B4",1],["C5",2], ["D5",2],["C5",2], ["B4",1],["A4",1],["G#4",2], ["A4",4]],
		[["A2",1],["A2",1],["A2",1],["A2",1],["F2",1],["F2",1],["F2",1],["F2",1],
		 ["G2",1],["G2",1],["G2",1],["G2",1],["E2",1],["E2",1],["E2",1],["E2",1],
		 ["A2",1],["A2",1],["A2",1],["A2",1],["F2",1],["F2",1],["F2",1],["F2",1],
		 ["G2",1],["G2",1],["G2",1],["G2",1],["E2",1],["E2",1],["E2",1],["E2",1]])
	_music_done = true
	_apply_music()

# ---------- 合成基元 ----------

const SEMI := {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}

func _note_freq(name: String) -> float:
	if name == "--":
		return 0.0
	var oct := int(name.right(name.length() - 1))
	var midi := 12 * (oct + 1) + int(SEMI[name.left(name.length() - 1)])
	return 440.0 * pow(2.0, (midi - 69) / 12.0)

## 把一段音符写进缓冲：part = [波形, 起始秒, 时长秒, 频率, 音量]
func _osc(buf: PackedFloat32Array, start: float, dur: float, freq: float, wave: String, vol: float, rate: int, attack := 0.006, release := 0.05) -> void:
	if freq <= 0.0:
		return
	var n0 := int(start * rate)
	var n := int(dur * rate)
	var phase := 0.0
	var step := freq / rate
	for i in n:
		var t := float(i) / rate
		var env := 1.0
		if t < attack:
			env = t / attack
		if dur - t < release:
			env = minf(env, (dur - t) / release)
		phase += step
		var s := 0.0
		match wave:
			"square":
				s = 1.0 if fmod(phase, 1.0) < 0.5 else -1.0
			"tri":
				s = 2.0 * absf(2.0 * fmod(phase, 1.0) - 1.0) - 1.0
			"sine":
				s = sin(phase * TAU)
			"saw":
				s = 2.0 * fmod(phase, 1.0) - 1.0
			"noise":
				s = randf() * 2.0 - 1.0
		var idx := n0 + i
		if idx >= 0 and idx < buf.size():
			buf[idx] += s * vol * env

func _to_wav(buf: PackedFloat32Array, rate: int, loop: bool) -> AudioStreamWAV:
	var bytes := PackedByteArray()
	bytes.resize(buf.size() * 2)
	for i in buf.size():
		bytes.encode_s16(i * 2, int(clampf(buf[i], -1.0, 1.0) * 32000.0))
	var w := AudioStreamWAV.new()
	w.format = AudioStreamWAV.FORMAT_16_BITS
	w.mix_rate = rate
	w.stereo = false
	if loop:
		w.loop_mode = AudioStreamWAV.LOOP_FORWARD
		w.loop_begin = 0
		w.loop_end = buf.size()
	w.data = bytes
	return w

func _render(dur: float, parts: Array) -> AudioStreamWAV:
	var buf := PackedFloat32Array()
	buf.resize(int(dur * SFX_RATE) + 1)
	for p in parts:
		_osc(buf, p[1], p[2], p[3], p[0], p[4], SFX_RATE)
	return _to_wav(buf, SFX_RATE, false)

func _render_song(bpm: float, melody: Array, bass: Array) -> AudioStreamWAV:
	var spb := 60.0 / bpm
	var total := 0.0
	for part in [melody, bass]:
		var t := 0.0
		for n in part:
			t += float(n[1]) * spb
		total = maxf(total, t)
	var buf := PackedFloat32Array()
	buf.resize(int(total * MUSIC_RATE) + 1)
	var t := 0.0
	for n in melody:
		var d := float(n[1]) * spb
		_osc(buf, t, d * 0.92, _note_freq(n[0]), "square", 0.14, MUSIC_RATE, 0.01, 0.04)
		t += d
	t = 0.0
	for n in bass:
		var d := float(n[1]) * spb
		_osc(buf, t, d * 0.95, _note_freq(n[0]), "tri", 0.2, MUSIC_RATE, 0.004, 0.03)
		t += d
	return _to_wav(buf, MUSIC_RATE, true)

# ---------- 音效清单 ----------

func _build_sfx() -> void:
	sfx["gem"] = _render(0.3, [
		["square", 0.0, 0.09, _note_freq("E5"), 0.4],
		["square", 0.1, 0.09, _note_freq("A5"), 0.4],
		["square", 0.2, 0.1, _note_freq("C#6"), 0.4]])
	sfx["potion"] = _render(0.26, [
		["sine", 0.0, 0.12, _note_freq("E4"), 0.6],
		["sine", 0.12, 0.14, _note_freq("A4"), 0.6]])
	sfx["key"] = _render(0.22, [
		["sine", 0.0, 0.08, _note_freq("A6"), 0.5],
		["sine", 0.09, 0.12, _note_freq("E6"), 0.5]])
	sfx["door"] = _render(0.26, [
		["square", 0.0, 0.18, 98.0, 0.5],
		["noise", 0.0, 0.07, 1.0, 0.25]])
	sfx["win"] = _render(0.36, [
		["square", 0.0, 0.09, _note_freq("C5"), 0.4],
		["square", 0.1, 0.09, _note_freq("E5"), 0.4],
		["square", 0.2, 0.15, _note_freq("G5"), 0.45]])
	sfx["blocked"] = _render(0.24, [["square", 0.0, 0.22, 92.0, 0.4]])
	sfx["stairs_up"] = _render(0.4, [
		["tri", 0.0, 0.1, _note_freq("C5"), 0.5],
		["tri", 0.1, 0.1, _note_freq("E5"), 0.5],
		["tri", 0.2, 0.1, _note_freq("G5"), 0.5],
		["tri", 0.3, 0.1, _note_freq("C6"), 0.5]])
	sfx["stairs_down"] = _render(0.4, [
		["tri", 0.0, 0.1, _note_freq("C6"), 0.5],
		["tri", 0.1, 0.1, _note_freq("G5"), 0.5],
		["tri", 0.2, 0.1, _note_freq("E5"), 0.5],
		["tri", 0.3, 0.1, _note_freq("C5"), 0.5]])
	sfx["core_tick"] = _render(0.09, [["sine", 0.0, 0.08, 220.0, 0.16]])
	sfx["core_fail"] = _render(0.9, [
		["saw", 0.0, 0.3, _note_freq("A3"), 0.35],
		["saw", 0.3, 0.3, _note_freq("E3"), 0.35],
		["saw", 0.6, 0.3, _note_freq("C3"), 0.35]])
	sfx["victory"] = _render(1.0, [
		["square", 0.0, 0.14, _note_freq("C5"), 0.4],
		["square", 0.15, 0.14, _note_freq("E5"), 0.4],
		["square", 0.3, 0.14, _note_freq("G5"), 0.4],
		["square", 0.45, 0.5, _note_freq("C6"), 0.5],
		["tri", 0.45, 0.5, _note_freq("E5"), 0.3]])
	sfx["click"] = _render(0.06, [["sine", 0.0, 0.05, 900.0, 0.4]])
	sfx["buy"] = _render(0.24, [
		["square", 0.0, 0.08, _note_freq("B5"), 0.4],
		["square", 0.09, 0.14, _note_freq("E6"), 0.4]])
