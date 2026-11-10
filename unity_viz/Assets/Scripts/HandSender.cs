using System.Collections.Generic;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using UnityEngine;
using UnityEngine.XR.Hands;

// Sends the tracked hands to MuJoCo in the hand stream format v1
// (docs/hand-stream/PROTOCOL.md): the same datagrams the Quest app sends, so
// teleop/run.py needs no change. For the headset on a Link cable, where Unity
// is the OpenXR application on the PC and renders into the headset. The Quest
// app must not run on the PC at the same time: one OpenXR session per PC.
//
// Needs the XR Hands package and the OpenXR feature "Hand Tracking Subsystem"
// (docs/integration/HEADSET.md). Poses come in Unity's tracking space
// (left-handed, Z negated); they go out in the OpenXR stage frame, as the
// Quest app reports them.
public class HandSender : MonoBehaviour
{
    [Tooltip("Address of teleop/run.py (--port 9000).")]
    public string host = "127.0.0.1";
    public int port = 9000;

    // OpenXR XR_EXT_hand_tracking joint order, the same as JOINT_NAMES in
    // pc_receiver/protocol.py. By name: XRHandJointID numbers differ.
    static readonly XRHandJointID[] Order =
    {
        XRHandJointID.Palm, XRHandJointID.Wrist,
        XRHandJointID.ThumbMetacarpal, XRHandJointID.ThumbProximal, XRHandJointID.ThumbDistal, XRHandJointID.ThumbTip,
        XRHandJointID.IndexMetacarpal, XRHandJointID.IndexProximal, XRHandJointID.IndexIntermediate,
        XRHandJointID.IndexDistal, XRHandJointID.IndexTip,
        XRHandJointID.MiddleMetacarpal, XRHandJointID.MiddleProximal, XRHandJointID.MiddleIntermediate,
        XRHandJointID.MiddleDistal, XRHandJointID.MiddleTip,
        XRHandJointID.RingMetacarpal, XRHandJointID.RingProximal, XRHandJointID.RingIntermediate,
        XRHandJointID.RingDistal, XRHandJointID.RingTip,
        XRHandJointID.LittleMetacarpal, XRHandJointID.LittleProximal, XRHandJointID.LittleIntermediate,
        XRHandJointID.LittleDistal, XRHandJointID.LittleTip,
    };

    XRHandSubsystem subsystem;
    UdpClient client;
    IPEndPoint target;
    long seq;
    readonly StringBuilder json = new StringBuilder(4096);
    readonly StringBuilder joints = new StringBuilder(4096);
    string status = "hands: no XR hand subsystem";
    float nextSearch;

    void OnEnable()
    {
        IPAddress address;
        if (!IPAddress.TryParse(host, out address))
        {
            Debug.LogError("HandSender: host must be an IP address: " + host);
            enabled = false;
            return;
        }
        target = new IPEndPoint(address, port);
        client = new UdpClient();
        nextSearch = 0f;
    }

    void OnDisable()
    {
        Subscribe(null);
        if (client != null)
        {
            client.Close();
            client = null;
        }
    }

    void Update()
    {
        // The subsystem starts after OpenXR is up; look for it until it runs.
        if ((subsystem == null || !subsystem.running) && Time.unscaledTime >= nextSearch)
        {
            nextSearch = Time.unscaledTime + 1f;
            List<XRHandSubsystem> found = new List<XRHandSubsystem>();
            SubsystemManager.GetSubsystems(found);
            foreach (XRHandSubsystem candidate in found)
            {
                if (candidate.running)
                {
                    Subscribe(candidate);
                    break;
                }
            }
        }
    }

    void Subscribe(XRHandSubsystem next)
    {
        if (subsystem != null)
        {
            subsystem.updatedHands -= OnUpdatedHands;
        }
        subsystem = next;
        if (subsystem != null)
        {
            subsystem.updatedHands += OnUpdatedHands;
        }
    }

    void OnUpdatedHands(XRHandSubsystem sender, XRHandSubsystem.UpdateSuccessFlags flags,
        XRHandSubsystem.UpdateType updateType)
    {
        // Two updates per frame; the one before rendering is the freshest.
        if (updateType != XRHandSubsystem.UpdateType.BeforeRender || client == null)
        {
            return;
        }
        bool left = Send("left", sender.leftHand);
        bool right = Send("right", sender.rightHand);
        status = "hands -> " + host + ":" + port + "  left " + (left ? "TRACKED" : "LOST")
            + "  right " + (right ? "TRACKED" : "LOST");
    }

    // One datagram for this hand. Returns whether it was sent as tracked.
    bool Send(string hand, XRHand data)
    {
        bool tracked = data.isTracked;
        joints.Clear();
        if (tracked)
        {
            for (int i = 0; i < Order.Length; i++)
            {
                Pose pose;
                if (!data.GetJoint(Order[i]).TryGetPose(out pose))
                {
                    tracked = false;  // a joint without a pose: the whole hand counts as lost
                    joints.Clear();
                    break;
                }
                AppendJoint(pose, i == 0);
            }
        }

        json.Clear();
        json.Append("{\"v\":1,\"seq\":").Append(seq);
        json.Append(",\"t_us\":").Append((long)(Time.realtimeSinceStartupAsDouble * 1e6));
        json.Append(",\"hand\":\"").Append(hand).Append('"');
        json.Append(",\"tracked\":").Append(tracked ? "true" : "false");
        json.Append(",\"source\":\"unknown\"");  // XR Hands does not say optical or controller
        json.Append(",\"joints\":[").Append(joints).Append("]}");

        byte[] bytes = Encoding.UTF8.GetBytes(json.ToString());
        try
        {
            client.Send(bytes, bytes.Length, target);
        }
        catch (SocketException)
        {
            return false;  // the receiver is not there yet; the next frame tries again
        }
        seq++;
        return tracked;
    }

    // Unity tracking space (left-handed) -> OpenXR stage frame (right-handed):
    // Z of the position and X, Y of the quaternion change sign. w stays >= 0,
    // as in the Quest app. 4 decimals = 0.1 mm.
    void AppendJoint(Pose pose, bool first)
    {
        float qx = -pose.rotation.x, qy = -pose.rotation.y, qz = pose.rotation.z, qw = pose.rotation.w;
        if (qw < 0f)
        {
            qx = -qx; qy = -qy; qz = -qz; qw = -qw;
        }
        if (!first)
        {
            joints.Append(',');
        }
        joints.Append('[');
        AppendNumber(pose.position.x).Append(',');
        AppendNumber(pose.position.y).Append(',');
        AppendNumber(-pose.position.z).Append(',');
        AppendNumber(qx).Append(',');
        AppendNumber(qy).Append(',');
        AppendNumber(qz).Append(',');
        AppendNumber(qw).Append(']');
    }

    StringBuilder AppendNumber(float value)
    {
        return joints.Append(value.ToString("0.0000", CultureInfo.InvariantCulture));
    }

    void OnGUI()
    {
        GUI.Box(new Rect(10, 40, 420, 24), status);
    }
}
