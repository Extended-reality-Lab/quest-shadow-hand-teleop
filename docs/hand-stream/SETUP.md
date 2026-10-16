# Hand stream: setup and running

Two programs:

- `quest_app/`: a Godot 4 Android app that runs on the Quest and sends the
  hand skeleton over Wi-Fi (UDP).
- `pc_receiver/`: a Python receiver (standard library only) that shows and
  logs the data on a Mac or Windows PC.

The data format is in [PROTOCOL.md](PROTOCOL.md).

## 1. PC receiver (Mac or Windows)

Needs Python 3.9 or newer. No packages to install.

macOS / Linux, from the repo root:

```
python3 pc_receiver/receiver.py --port 9000
```

Windows (PowerShell or cmd), from the repo root:

```
py pc_receiver\receiver.py --port 9000
```

At start it prints the PC's LAN address, for example
`Point the headset at 192.168.43.17:9000`. Options:

- `--log hands.jsonl`: append every valid datagram as one JSON line, with the
  PC receive time `rx_time` added.
- `--timeout 0.5`: seconds without packets before a hand shows
  `LOST (no packets)`.
- `--bind 0.0.0.0`: local address to listen on.

If macOS asks whether Python may accept incoming connections, click **Allow**.
On Windows, allow Python through the firewall on the network you use (private
network). Without admin rights, use a phone hotspot marked as a private network.

### Test without a headset

Terminal 1:

```
python3 pc_receiver/receiver.py --port 9000
```

Terminal 2:

```
python3 pc_receiver/fake_sender.py --host 127.0.0.1 --port 9000 --seconds 25
```

Expected: L and R update at about 60 Hz; R shows `LOST (tracking)` for 2 s
every 5 s; L shows `LOST (no packets)` for 1.5 s every 11 s; `malformed 0`.

Unit tests:

```
python3 -m unittest discover -s pc_receiver -v
```

## 2. Headset preparation (once per headset; human steps)

1. Install the **Meta Horizon** app on a phone and pair the headset.
2. Create or join a Meta developer organisation at
   <https://developers.meta.com/horizon/> (needed for developer mode).
3. In the Horizon app: Devices → the headset → Headset settings →
   **Developer mode** → on. Restart the headset.
4. Connect the headset to the computer by USB-C. Inside the headset accept
   **Allow USB debugging** (tick "Always allow from this computer").
5. In the headset: Settings → Movement tracking → **Hand and body tracking**
   → on. Put the controllers down so the headset switches to hands.
6. Check the connection on the computer:

   ```
   adb devices -l
   ```

   The headset must be listed as `device` (not `unauthorized`).

`adb` is in the Android SDK `platform-tools` folder. On macOS with Android
Studio defaults: `~/Library/Android/sdk/platform-tools/adb`. On Windows:
`%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe`, or download only the
platform-tools zip from <https://developer.android.com/tools/releases/platform-tools>
(no installer, no admin rights needed).

## 3. Install the app

If you already have `quest_hand_stream.apk`:

```
adb install -r quest_hand_stream.apk
```

Start it in the headset from **Library → Unknown sources → Hand Stream**, or
from the computer:

```
adb shell monkey -p edu.oregonstate.handstream -c android.intent.category.LAUNCHER 1
```

The app shows a small text panel with the target address and the state of each
hand, and a small sphere on every tracked joint (left blue, right orange).

App log (warnings, chosen address, data folder):

```
adb logcat -s godot
```

## 4. Network and PC address

By default the app **broadcasts** to `255.255.255.255:9000`. Any receiver on
the same Wi-Fi network gets the data without setup.

University Wi-Fi often blocks broadcast and device-to-device traffic. If the
receiver shows `LOST (no packets)` for both hands while the app runs, connect
the headset and the PC to a **phone hotspot** and try again.

To send to one specific PC instead of broadcasting, write a config file on the
headset. No rebuild is needed. Replace the address with the one the receiver
prints:

```
printf '[stream]\nhost="192.168.43.17"\nport=9000\n' > hand_stream.cfg
adb push hand_stream.cfg /data/local/tmp/hand_stream.cfg
adb shell run-as edu.oregonstate.handstream sh -c 'cp /data/local/tmp/hand_stream.cfg files/hand_stream.cfg'
```

Then restart the app:

```
adb shell am force-stop edu.oregonstate.handstream
adb shell monkey -p edu.oregonstate.handstream -c android.intent.category.LAUNCHER 1
```

`run-as` works only for debug builds. The app prints its data folder at start
(`Hand Stream: user data dir = ...` in `adb logcat -s godot`); the config file
belongs in that folder. To go back to broadcast, delete the file:

```
adb shell run-as edu.oregonstate.handstream rm files/hand_stream.cfg
```

## 5. Build the APK yourself

Tested with Godot 4.7.2 (standard build, not .NET) and the Godot OpenXR
Vendors plugin 5.1.0.

1. Install a JDK 17 (for example Eclipse Temurin 17) and the Android SDK
   (Android Studio, or the command-line tools with `platform-tools`,
   `build-tools;35.0.0` and `platforms;android-35`).
2. Download Godot 4.7.2 from <https://godotengine.org/download/archive/>
   and the matching **export templates** (Editor → Manage Export Templates →
   Download and Install).
3. Download `godotopenxrvendorsaddon.zip` from
   <https://github.com/GodotVR/godot_openxr_vendors/releases/tag/5.1.0-stable>
   and copy its `asset/addons/godotopenxrvendors` folder to
   `quest_app/addons/godotopenxrvendors`. It is not committed (about 80 MB of
   binaries).
4. Open `quest_app/project.godot` in Godot. Editor → Editor Settings →
   Export → Android: set **Java SDK Path** to the JDK 17 home and **Android
   SDK Path** to the SDK folder. Godot creates a debug keystore itself.
5. Project → Install Android Build Template.
6. Project → Export → preset **Android Quest** → Export Project (debug), or
   headless from the repo root:

   ```
   godot --headless --path quest_app --install-android-build-template --export-debug "Android Quest" ../build/quest_hand_stream.apk
   ```

   The path is relative to `quest_app/`, so the APK lands in the repo's
   `build/` folder (ignored by git).

Key settings already in the project: OpenXR enabled, hand tracking extension
on, stage reference space; export preset with the Meta plugin, hand tracking
(optional), Quest 2 / 3 / Pro support, Gradle build, `INTERNET` permission,
package `edu.oregonstate.handstream`.

## 6. Demo video checklist

Record the PC screen (receiver) and the headset view (Quest casting or
`scrcpy`) side by side.

1. Receiver running, app started, both hands in view: `L TRACKED | R TRACKED`.
   Move a hand; its wrist numbers change.
2. Hide the right hand behind your back: `R LOST (tracking)` within 0.5 s,
   packets keep arriving (rate stays).
3. Bring the right hand back: `R TRACKED`.
4. Same with the left hand.
5. Take the headset off (it sleeps) or close the app: both hands
   `LOST (no packets)`.
6. Put it back on: both hands return to `TRACKED`.

## Known limits

- UDP: packets can be lost; the receiver counts them (`lost`).
- `t_us` is the headset clock, not synchronised with the PC.
- The stage origin depends on the guardian setup; re-centring moves it.
