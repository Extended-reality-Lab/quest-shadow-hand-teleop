"""Hand stream format v1: joint names, parsing and validation.

Shared by receiver.py, fake_sender.py and test_protocol.py.
The format is documented in docs/hand-stream/PROTOCOL.md; keep the two in sync.
"""
import json
import math

VERSION = 1
HANDS = ("left", "right")
SOURCES = ("optical", "controller", "unknown")
MAX_DATAGRAM_BYTES = 8192
VALUES_PER_JOINT = 7  # px, py, pz, qx, qy, qz, qw

# OpenXR XR_EXT_hand_tracking order, same as Godot's XRHandTracker.HandJoint enum.
JOINT_NAMES = [
    "palm",
    "wrist",
    "thumb_metacarpal",
    "thumb_proximal",
    "thumb_distal",
    "thumb_tip",
    "index_metacarpal",
    "index_proximal",
    "index_intermediate",
    "index_distal",
    "index_tip",
    "middle_metacarpal",
    "middle_proximal",
    "middle_intermediate",
    "middle_distal",
    "middle_tip",
    "ring_metacarpal",
    "ring_proximal",
    "ring_intermediate",
    "ring_distal",
    "ring_tip",
    "little_metacarpal",
    "little_proximal",
    "little_intermediate",
    "little_distal",
    "little_tip",
]
JOINT_COUNT = len(JOINT_NAMES)  # 26
WRIST = JOINT_NAMES.index("wrist")
INDEX_TIP = JOINT_NAMES.index("index_tip")


class ProtocolError(ValueError):
    """Raised for a datagram that does not match format v1."""


def _is_int(value):
    # bool is a subclass of int in Python, so exclude it explicitly.
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    # json.loads accepts NaN and Infinity; they are not valid joint values.
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def parse(data):
    """Decode one datagram (bytes) and check it against v1.

    Returns the message as a dict. Raises ProtocolError for anything malformed.
    """
    if len(data) > MAX_DATAGRAM_BYTES:
        raise ProtocolError(f"datagram too large: {len(data)} bytes")
    try:
        msg = json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError) as exc:
        # ValueError covers bad UTF-8, bad JSON and huge integers; deep nesting
        # raises RecursionError. Neither may crash the receiver.
        raise ProtocolError(f"not valid UTF-8 JSON: {exc}") from exc

    if not isinstance(msg, dict):
        raise ProtocolError("top level is not a JSON object")
    if not _is_int(msg.get("v")) or msg["v"] != VERSION:
        raise ProtocolError(f"unsupported version: {msg.get('v')!r}")
    for key in ("seq", "t_us"):
        if not _is_int(msg.get(key)) or msg[key] < 0:
            raise ProtocolError(f"{key} must be a non-negative integer")
    if msg.get("hand") not in HANDS:
        raise ProtocolError(f"unknown hand: {msg.get('hand')!r}")
    if not isinstance(msg.get("tracked"), bool):
        raise ProtocolError("tracked must be true or false")
    if msg.get("source") not in SOURCES:
        raise ProtocolError(f"unknown source: {msg.get('source')!r}")

    joints = msg.get("joints")
    if not isinstance(joints, list):
        raise ProtocolError("joints must be a list")
    # A tracked hand carries every joint; a lost hand carries none.
    expected = JOINT_COUNT if msg["tracked"] else 0
    if len(joints) != expected:
        raise ProtocolError(f"expected {expected} joints, got {len(joints)}")
    for i, joint in enumerate(joints):
        if not isinstance(joint, list) or len(joint) != VALUES_PER_JOINT:
            raise ProtocolError(f"joint {i} must be a list of {VALUES_PER_JOINT} numbers")
        if not all(_is_number(x) for x in joint):
            raise ProtocolError(f"joint {i} contains a non-number")
    return msg


def make_message(seq, t_us, hand, tracked, source, joints):
    """Build a v1 message dict. Joint values are rounded to 4 decimals (0.1 mm)."""
    return {
        "v": VERSION,
        "seq": seq,
        "t_us": t_us,
        "hand": hand,
        "tracked": tracked,
        "source": source,
        "joints": [[round(x, 4) for x in joint] for joint in joints] if tracked else [],
    }


def encode(msg):
    """Serialize a message dict to compact UTF-8 JSON bytes."""
    return json.dumps(msg, separators=(",", ":")).encode("utf-8")
