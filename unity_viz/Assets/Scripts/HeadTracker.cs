using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

// Moves the camera with the headset. Unity's XR plug-ins render from the
// camera's transform and do not move it themselves, so without this the image
// stays fixed to the face. It belongs on the camera that sits under the XR
// rig; StateReceiver puts it there with Attach(). It sets the local pose, so
// the rig (StateReceiver.xrRig) still places the tracking space in the scene.
// Without a headset it does nothing.
public class HeadTracker : MonoBehaviour
{
    static readonly List<InputDevice> headsets = new List<InputDevice>();

    readonly List<InputDevice> found = new List<InputDevice>();
    InputDevice head;
    float nextSearch;

    // Sets the scene up for a headset: Camera.main becomes a direct child of
    // `rig` and gets a HeadTracker. With no `rig` given, a new "XR Rig" object
    // is the rig, so no other object of the scene moves. Returns false, and changes
    // nothing, while there is no headset or no camera: the camera then keeps
    // the fixed view of ManifestLoader, and the caller can try again later.
    public static bool Attach(ref Transform rig)
    {
        Camera cam = Camera.main;
        InputDevices.GetDevicesWithCharacteristics(InputDeviceCharacteristics.HeadMounted, headsets);
        if (cam == null || headsets.Count == 0)
        {
            return false;
        }
        if (rig == null || rig == cam.transform)
        {
            rig = new GameObject("XR Rig").transform;
        }
        if (cam.transform.parent != rig)
        {
            cam.transform.SetParent(rig, false);
        }
        if (cam.GetComponent<HeadTracker>() == null)
        {
            cam.gameObject.AddComponent<HeadTracker>();
        }
        cam.nearClipPlane = Mathf.Min(cam.nearClipPlane, 0.05f);
        return true;
    }

    void OnEnable()
    {
        Application.onBeforeRender += Apply;
    }

    void OnDisable()
    {
        Application.onBeforeRender -= Apply;
    }

    // Twice per frame, as the hands are read: in Update for scripts that use
    // the camera, and right before rendering for the freshest head pose.
    void Update()
    {
        Apply();
    }

    void Apply()
    {
        if (!head.isValid)
        {
            if (Time.unscaledTime < nextSearch)
            {
                return;
            }
            nextSearch = Time.unscaledTime + 1f;
            InputDevices.GetDevicesWithCharacteristics(InputDeviceCharacteristics.HeadMounted, found);
            if (found.Count == 0)
            {
                return;
            }
            head = found[0];
        }

        Vector3 position;
        if (head.TryGetFeatureValue(CommonUsages.centerEyePosition, out position))
        {
            transform.localPosition = position;
        }
        Quaternion rotation;
        if (head.TryGetFeatureValue(CommonUsages.centerEyeRotation, out rotation))
        {
            transform.localRotation = rotation;
        }
    }
}
