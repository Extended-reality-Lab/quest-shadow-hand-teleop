extends Node3D
## Streams both hand skeletons to a PC over UDP every frame.
## Format: docs/hand-stream/PROTOCOL.md (v1). One datagram per hand per frame.

const DEFAULT_HOST := "255.255.255.255"  # broadcast: works on a hotspot with no setup
const DEFAULT_PORT := 9000
const CONFIG_PATH := "user://hand_stream.cfg"  # optional override, see SETUP.md
const JOINT_COUNT := XRHandTracker.HAND_JOINT_MAX  # 26, OpenXR joint order
const HANDS := ["left", "right"]
const HAND_COLORS := {"left": Color(0.2, 0.6, 1.0), "right": Color(1.0, 0.5, 0.1)}
const VALID_POSE := XRHandTracker.HAND_JOINT_FLAG_POSITION_VALID | XRHandTracker.HAND_JOINT_FLAG_ORIENTATION_VALID

var host := DEFAULT_HOST
var port := DEFAULT_PORT
var udp := PacketPeerUDP.new()
var dest_ok := false  # false when the configured host cannot be resolved
var seq := 0
var last_warning_ms := -10000
var spheres := {"left": [], "right": []}  # one small sphere per joint, for the wearer

@onready var origin: XROrigin3D = $XROrigin3D
@onready var label: Label3D = $XROrigin3D/XRCamera3D/StatusLabel


func _ready() -> void:
	var xr := XRServer.find_interface("OpenXR")
	if xr and xr.is_initialized():
		get_viewport().use_xr = true
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)  # the headset paces frames
	else:
		push_warning("Hand Stream: OpenXR is not initialized")

	_load_config()
	print("Hand Stream: user data dir = ", OS.get_user_data_dir())
	udp.set_broadcast_enabled(true)  # needed for 255.255.255.255, harmless otherwise
	var err := udp.set_dest_address(host, port)
	dest_ok = err == OK
	if not dest_ok:
		push_warning("Hand Stream: bad destination %s:%d (error %d), not sending" % [host, port, err])
	print("Hand Stream: sending to %s:%d" % [host, port])
	_make_spheres()


func _process(_delta: float) -> void:
	var lines := ["Hand Stream -> %s:%d" % [host, port]]
	for hand in HANDS:
		var tracker := XRServer.get_tracker("/user/hand_tracker/" + hand) as XRHandTracker
		var msg := _build_message(hand, tracker)
		_send(msg)
		_update_spheres(hand, tracker, msg.tracked)
		lines.append("%s: %s (%s)" % [hand, "TRACKED" if msg.tracked else "LOST", msg.source])
	label.text = "\n".join(lines)


## Picks the default host, then reads host and port from user://hand_stream.cfg
## if the file exists.
func _load_config() -> void:
	if not OS.has_feature("android"):
		host = "127.0.0.1"  # run on a PC over Link: send to the receiver on the same PC
	if not FileAccess.file_exists(CONFIG_PATH):
		return  # no override: keep the default host
	var cfg := ConfigFile.new()
	var err := cfg.load(CONFIG_PATH)
	if err != OK:
		push_warning("Hand Stream: cannot parse %s (error %d), using broadcast" % [CONFIG_PATH, err])
		return
	host = str(cfg.get_value("stream", "host", DEFAULT_HOST))
	port = int(cfg.get_value("stream", "port", DEFAULT_PORT))
	print("Hand Stream: loaded ", CONFIG_PATH)


func _build_message(hand: String, tracker: XRHandTracker) -> Dictionary:
	var source := "unknown"
	var tracked := false
	if tracker:
		match tracker.hand_tracking_source:
			XRHandTracker.HAND_TRACKING_SOURCE_UNOBSTRUCTED:
				source = "optical"
			XRHandTracker.HAND_TRACKING_SOURCE_CONTROLLER:
				source = "controller"
		# Data emulated from a held controller is not a real hand: report it as lost.
		tracked = tracker.has_tracking_data and source != "controller"

	var joints := []
	if tracked:
		for j in JOINT_COUNT:
			# A joint without a valid pose would be sent as the origin: treat the hand as lost.
			if (tracker.get_hand_joint_flags(j) & VALID_POSE) != VALID_POSE:
				tracked = false
				joints = []
				break
			var xf: Transform3D = tracker.get_hand_joint_transform(j)
			var q := xf.basis.get_rotation_quaternion()
			if q.w < 0.0:
				q = -q  # q and -q are the same rotation; keep w >= 0 so samples are comparable
			joints.append([_r(xf.origin.x), _r(xf.origin.y), _r(xf.origin.z),
					_r(q.x), _r(q.y), _r(q.z), _r(q.w)])

	return {
		"v": 1,
		"seq": seq,
		"t_us": Time.get_ticks_usec(),
		"hand": hand,
		"tracked": tracked,
		"source": source,
		"joints": joints,
	}


## Rounds to 4 decimals (0.1 mm) to keep datagrams small.
func _r(x: float) -> float:
	return snappedf(x, 0.0001)


func _send(msg: Dictionary) -> void:
	if not dest_ok:
		return
	var err := udp.put_packet(JSON.stringify(msg).to_utf8_buffer())
	if err == OK:
		seq += 1
	elif Time.get_ticks_msec() - last_warning_ms > 1000:
		# Never block or crash when the PC is missing; warn at most once per second.
		last_warning_ms = Time.get_ticks_msec()
		push_warning("Hand Stream: send to %s:%d failed (error %d)" % [host, port, err])


func _make_spheres() -> void:
	for hand in HANDS:
		var material := StandardMaterial3D.new()
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
		material.albedo_color = HAND_COLORS[hand]
		var mesh := SphereMesh.new()
		mesh.radius = 0.006
		mesh.height = 0.012
		mesh.material = material
		for j in JOINT_COUNT:
			var sphere := MeshInstance3D.new()
			sphere.mesh = mesh
			sphere.visible = false
			origin.add_child(sphere)
			spheres[hand].append(sphere)


## Joint transforms are in XROrigin3D space, so the spheres are children of the origin.
func _update_spheres(hand: String, tracker: XRHandTracker, tracked: bool) -> void:
	for j in JOINT_COUNT:
		var sphere: MeshInstance3D = spheres[hand][j]
		sphere.visible = tracked
		if tracked:
			sphere.position = tracker.get_hand_joint_transform(j).origin
