import mujoco

model = mujoco.MjModel.from_xml_path("assets/shadow_hand/scene_right.xml")
print("joints:", model.njnt)
print("actuators:", model.nu)
for i in range (model.njnt):
    j = model.joint(i)
    print (f"joint {i}: name={j.name}, type={j.type}, pos={j.pos}, axis={j.axis}, damping={j.damping} range={j.range[0]} {j.range[1]}")

for i in range (model.nu):
    a = model.actuator(i)
    print (f"actuator {i}: name={a.name}, trntype={a.trntype}, trnid={a.trnid}, kp={a.gainprm[0]}, bias={a.biasprm[0]} ctrlrange={a.ctrlrange[0]} {a.ctrlrange[1]} " )


