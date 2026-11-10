using System.Collections.Generic;
using UnityEngine;
using UnityEngine.XR;

// Moves the camera with the headset. Unity's XR plug-ins render from the
// camera's transform and do not move it themselves, so without this the image
// stays fixed to the face. Add it to the camera that sits under the XR rig.
// It sets the local pose, so the rig (StateReceiver.xrRig) still places the
// tracking space in the scene. Without a headset it does nothing.
public class HeadTracker : MonoBehaviour
{
    readonly List<InputDevice> found = new List<InputDevice>();
    InputDevice head;
    float nextSearch;

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
