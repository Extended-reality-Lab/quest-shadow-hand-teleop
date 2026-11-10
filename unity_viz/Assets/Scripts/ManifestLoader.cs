using System;
using System.IO;
using UnityEngine;
using UnityEngine.Rendering;

// Builds the MuJoCo scene from scene/scene_manifest.json (written by
// scene/export_manifest.py). Visual only: no Rigidbody, no Collider.
// Every value in the manifest is already in Unity's frame; nothing is converted here.
public class ManifestLoader : MonoBehaviour
{
    [Tooltip("Path to scene_manifest.json. Empty = <repo>/scene/scene_manifest.json")]
    public string manifestPath = "";

    [Tooltip("Move Camera.main to the first view of the MuJoCo viewer. Skipped when a headset drives the camera.")]
    public bool setCamera = true;

    void Start()
    {
        Build();
    }

    [ContextMenu("Rebuild")]
    public void Build()
    {
        string path = string.IsNullOrEmpty(manifestPath)
            ? Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "scene", "scene_manifest.json"))
            : manifestPath;
        if (!File.Exists(path))
        {
            Debug.LogError("ManifestLoader: file not found: " + path);
            return;
        }
        SceneManifest manifest = JsonUtility.FromJson<SceneManifest>(File.ReadAllText(path));
        if (manifest == null || manifest.bodies == null)
        {
            Debug.LogError("ManifestLoader: could not read " + path);
            return;
        }

        Clear();
        Shader shader = Shader.Find("Universal Render Pipeline/Lit");
        if (shader == null)
        {
            shader = Shader.Find("Standard");
        }

        int geomCount = 0;
        foreach (ManifestBody body in manifest.bodies)
        {
            GameObject bodyObject = new GameObject(body.id);
            bodyObject.transform.SetParent(transform, false);
            bodyObject.transform.localPosition = ToVector3(body.position);
            bodyObject.transform.localRotation = ToQuaternion(body.rotation);
            if (body.geoms == null)
            {
                continue;
            }
            foreach (ManifestGeom geom in body.geoms)
            {
                AddGeom(bodyObject.transform, geom, shader);
                geomCount++;
            }
        }

        // A camera under a rig (the XR rig, StateReceiver.xrRig) follows the
        // headset; only a free camera is moved to the viewer's first view.
        if (setCamera && (Camera.main == null || Camera.main.transform.parent == null))
        {
            SetCamera(manifest.camera);
        }
        Debug.Log("ManifestLoader: " + manifest.bodies.Length + " bodies, " + geomCount + " geoms from " + path);
    }

    void AddGeom(Transform parent, ManifestGeom geom, Shader shader)
    {
        GameObject geomObject = new GameObject(geom.name);
        geomObject.transform.SetParent(parent, false);
        geomObject.transform.localPosition = ToVector3(geom.position);
        geomObject.transform.localRotation = ToQuaternion(geom.rotation);
        if (geom.vertices == null || geom.triangles == null)
        {
            Debug.LogWarning("ManifestLoader: geom without a mesh: " + geom.name);
            return;
        }

        int count = geom.vertices.Length / 3;
        Vector3[] vertices = new Vector3[count];
        for (int i = 0; i < count; i++)
        {
            vertices[i] = new Vector3(geom.vertices[3 * i], geom.vertices[3 * i + 1], geom.vertices[3 * i + 2]);
        }
        Mesh mesh = new Mesh();
        mesh.name = geom.name;
        if (count > 65535)
        {
            mesh.indexFormat = IndexFormat.UInt32;
        }
        mesh.vertices = vertices;
        mesh.triangles = geom.triangles;
        mesh.RecalculateNormals();
        mesh.RecalculateBounds();
        geomObject.AddComponent<MeshFilter>().sharedMesh = mesh;

        Material material = new Material(shader);
        material.color = geom.rgba != null && geom.rgba.Length == 4
            ? new Color(geom.rgba[0], geom.rgba[1], geom.rgba[2], geom.rgba[3])
            : Color.gray;
        geomObject.AddComponent<MeshRenderer>().sharedMaterial = material;
    }

    void SetCamera(ManifestCamera view)
    {
        Camera cam = Camera.main;
        if (cam == null || view == null || view.position == null || view.position.Length != 3
            || view.look_at == null || view.look_at.Length != 3)
        {
            return;
        }
        cam.transform.position = transform.TransformPoint(ToVector3(view.position));
        cam.transform.LookAt(transform.TransformPoint(ToVector3(view.look_at)), Vector3.up);
        if (view.fov_deg > 0)
        {
            cam.fieldOfView = view.fov_deg;
        }
        cam.nearClipPlane = 0.01f;
    }

    void Clear()
    {
        for (int i = transform.childCount - 1; i >= 0; i--)
        {
            GameObject child = transform.GetChild(i).gameObject;
            if (Application.isPlaying)
            {
                Destroy(child);
            }
            else
            {
                DestroyImmediate(child);
            }
        }
    }

    static Vector3 ToVector3(float[] v)
    {
        return v != null && v.Length == 3 ? new Vector3(v[0], v[1], v[2]) : Vector3.zero;
    }

    static Quaternion ToQuaternion(float[] q)
    {
        return q != null && q.Length == 4 ? new Quaternion(q[0], q[1], q[2], q[3]) : Quaternion.identity;
    }
}

// The manifest format. Field names match the JSON keys, so JsonUtility can read it.
[Serializable]
public class SceneManifest
{
    public int version;
    public string frame;
    public string units;
    public string source;
    public ManifestCamera camera;
    public ManifestBody[] bodies;
}

[Serializable]
public class ManifestCamera
{
    public float[] position;
    public float[] look_at;
    public float fov_deg;
}

[Serializable]
public class ManifestBody
{
    public string id;
    public float[] position;
    public float[] rotation;
    public ManifestGeom[] geoms;
}

[Serializable]
public class ManifestGeom
{
    public string name;
    public string type;
    public float[] position;
    public float[] rotation;
    public float[] rgba;
    public float[] vertices;
    public int[] triangles;
}
