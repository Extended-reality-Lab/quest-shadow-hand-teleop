using System;
using System.Collections.Generic;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// Moves the scene that ManifestLoader built to the poses MuJoCo sends
// (teleop/run.py, UDP 127.0.0.1:9001, format in docs/integration/DATA.md).
// Put it on the same GameObject as ManifestLoader. Visual only: it applies the
// latest state as it is, with no physics and no smoothing yet (#29).
public class StateReceiver : MonoBehaviour
{
    [Tooltip("UDP port of the MuJoCo state stream (teleop/run.py --unity-port).")]
    public int port = 9001;

    [Tooltip("Parent of the XR camera. Moved to the headset's tracking origin (the 'stage' pose), so the rendered hand is on the real hand. Leave empty without a headset.")]
    public Transform xrRig;

    readonly object stateLock = new object();
    byte[] latest;      // newest datagram, written by the receive thread, under stateLock
    int receivedCount;  // under stateLock

    UdpClient client;
    Thread thread;
    volatile bool running;

    int appliedCount;
    float lastDataTime = -1f;
    long shownSeq = -1;
    readonly Dictionary<string, Transform> parts = new Dictionary<string, Transform>();

    void OnEnable()
    {
        try
        {
            client = new UdpClient(new IPEndPoint(IPAddress.Loopback, port));
        }
        catch (SocketException e)
        {
            Debug.LogError("StateReceiver: cannot listen on 127.0.0.1:" + port + ": " + e.Message);
            client = null;
            return;
        }
        running = true;
        UdpClient socket = client;
        thread = new Thread(() => ReceiveLoop(socket));
        thread.IsBackground = true;
        thread.Start();
    }

    void OnDisable()
    {
        running = false;
        if (client != null)
        {
            client.Close();  // makes the blocking Receive throw, which ends the thread
            client = null;
        }
        if (thread != null)
        {
            thread.Join(500);
            thread = null;
        }
    }

    void ReceiveLoop(UdpClient socket)
    {
        IPEndPoint from = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            byte[] bytes;
            try
            {
                bytes = socket.Receive(ref from);
            }
            catch (ObjectDisposedException)
            {
                return;
            }
            catch (SocketException)
            {
                if (!running)
                {
                    return;
                }
                continue;  // Windows reports an old ICMP error here; harmless
            }

            lock (stateLock)
            {
                latest = bytes;
                receivedCount++;
            }
        }
    }

    void Update()
    {
        byte[] bytes;
        int count;
        lock (stateLock)
        {
            bytes = latest;
            count = receivedCount;
        }
        if (bytes == null || count == appliedCount)
        {
            return;
        }
        appliedCount = count;

        // Parsed here, on the main thread, where every Unity API is allowed.
        MujocoState state = null;
        try
        {
            state = JsonUtility.FromJson<MujocoState>(Encoding.UTF8.GetString(bytes));
        }
        catch (Exception)
        {
            state = null;  // a broken datagram: skip it
        }
        if (state == null)
        {
            return;
        }
        lastDataTime = Time.unscaledTime;
        shownSeq = state.seq;
        Apply(state.bodies);
        Apply(state.objects);
        if (xrRig != null && Complete(state.stage))
        {
            // Absent until the teleop has re-centred; then the headset's tracking
            // origin, in the frame of this object like the bodies, wherever the rig
            // itself is parented.
            xrRig.SetPositionAndRotation(transform.TransformPoint(Position(state.stage)),
                transform.rotation * Rotation(state.stage));
        }
    }

    void Apply(MujocoPose[] poses)
    {
        if (poses == null)
        {
            return;
        }
        foreach (MujocoPose pose in poses)
        {
            Transform part = Complete(pose) ? FindPart(pose.id) : null;
            if (part != null)
            {
                part.localPosition = Position(pose);
                part.localRotation = Rotation(pose);
            }
        }
    }

    static bool Complete(MujocoPose pose)
    {
        return pose != null && pose.p != null && pose.p.Length == 3 && pose.q != null && pose.q.Length == 4;
    }

    static Vector3 Position(MujocoPose pose)
    {
        return new Vector3(pose.p[0], pose.p[1], pose.p[2]);
    }

    static Quaternion Rotation(MujocoPose pose)
    {
        return new Quaternion(pose.q[0], pose.q[1], pose.q[2], pose.q[3]);
    }

    // The child that ManifestLoader built for this body id; looked up again
    // when the scene was rebuilt or the name was missing.
    Transform FindPart(string id)
    {
        if (string.IsNullOrEmpty(id))
        {
            return null;
        }
        Transform part;
        if (parts.TryGetValue(id, out part) && part != null)
        {
            return part;
        }
        part = transform.Find(id);
        if (part != null)
        {
            parts[id] = part;
        }
        return part;
    }

    void OnGUI()
    {
        bool live = lastDataTime >= 0f && Time.unscaledTime - lastDataTime < 0.5f;
        string text = live ? "MuJoCo: seq " + shownSeq : "MuJoCo: no data";
        GUI.Box(new Rect(10, 10, 200, 24), text);
    }
}

// The state message. Field names match the JSON keys, so JsonUtility can read it.
[Serializable]
public class MujocoState
{
    public int v;
    public long seq;
    public double sim_time;
    public double send_time;
    public MujocoPose[] bodies;
    public MujocoPose[] objects;
    public MujocoPose stage;  // headset tracking origin; p empty until the teleop has re-centred
}

[Serializable]
public class MujocoPose
{
    public string id;
    public float[] p;
    public float[] q;
    public string grasp;
}
