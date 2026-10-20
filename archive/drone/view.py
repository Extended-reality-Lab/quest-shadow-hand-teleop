import time 
import mujoco
import mujoco.viewer
model = mujoco.MjModel.from_xml_path("assets/x2/scene.xml")
data = mujoco.MjData(model)


data.qpos[2] = 5.0
mujoco.mj_forward(model, data)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)   # slow down to real time