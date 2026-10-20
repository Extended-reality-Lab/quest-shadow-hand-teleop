import time

import mujoco
import mujoco.viewer

XML = """
<mujoco>
  <worldbody>
    <body pos="0 0 1">
      <joint name="hinge" type="hinge" axis="0 1 0" damping="2"/>
      <geom type="capsule" fromto="0 0 0 0 0 -0.5" size="0.03" mass="1"/>
    </body>
  </worldbody>
  <actuator>
    <position name="motor" joint="hinge" kp="50"/>
  </actuator>
</mujoco>
"""

model = mujoco.MjModel.from_xml_string(XML)
data = mujoco.MjData(model) # so here we have data about current state of the simulation. 


with mujoco.viewer.launch_passive(model, data) as viewer:  # open the window and start the simulation
    while viewer.is_running():
        #  so here every 2 seconds the target angle flips between +1 and -1 rad
        data.ctrl[0] = 1.0 if int(data.time) % 4 < 2 else -1.0
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)
