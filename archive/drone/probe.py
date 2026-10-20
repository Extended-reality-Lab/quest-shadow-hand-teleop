import mujoco 


# the model is loaded here once and we can not change - mass geomerty - motors 
model = mujoco.MjModel.from_xml_path("assets/x2/scene.xml")


data = mujoco.MjData(model)


print(f"qpos length: {model.nq}")
print(f"actuators:   {model.nu}")
print(f"total mass:  {sum(model.body_mass)} kg")
print(f"timestep:    {model.opt.timestep} s")




data.qpos[2] = 5.0
mujoco.mj_forward(model, data )


for step in range (1000):
    mujoco.mj_step(model, data)
    if step % 100 == 0:
        print(f"t= {data.time:5.2f} s z= {data.qpos[2]:7.3f} m ")


