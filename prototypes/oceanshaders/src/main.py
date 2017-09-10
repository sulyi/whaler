from direct.actor.Actor import Actor
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight,
    LPoint3, LVector3, LVector4,
    PStatClient)

import ocean


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.debug = False
        if self.debug:
            PStatClient.connect()
            self.bufferViewer.toggleEnable()
            self.camera.place()

        self.world_size = 128

        panoramic_view = LPoint3(0.0, -300.0, 60.0), LVector3(0.0, -15.0, 0.0)
        model_view = LPoint3(0.0, -35.0, 5.0), LVector3(0.0, -10.0, 0.0)

        self.camera_pos, self.camera_hpr = model_view

        self.skybox = self.loader.loadModel("models/morningbox/morningbox")
        self.water = ocean.WaterNodeHelper(
            self, self.world_size, self.world_size, 2, 128, 128, LVector3(0, 0, 0), False)

        self.model = Actor("models/flying_cloud/FLYING_L-tailed")
        lower, upper = self.model.get_tight_bounds()
        half_length = (lower[0] - upper[0]) / 2
        self.head = 0.75 * half_length
        self.tail = -0.9 * half_length

        self.pivot = self.render.attach_new_node("boatpivot")
        self.pivot_interval = self.pivot.hprInterval(10, LPoint3(-360, 0, 0))
        self.pivot_interval.loop()

        self.init_scene()

    def init_environment(self):
        print "Initializing environment"
        # lighting
        ambient_light = AmbientLight("ambientLight")
        ambient_light.set_color(LVector4(0.2, 0.2, 0.2, 1.0))
        self.render.set_light(self.render.attach_new_node(ambient_light))

        directional_light = DirectionalLight('directionalLight')
        directional_light.set_color(LVector4(1.0, 1.0, 0.8, 0.0))
        directional_light_np = self.render.attach_new_node(directional_light)
        directional_light_np.set_pos(600.0, -400.0, 300.0)
        directional_light_np.look_at(0.0, 0.0, 0.0)
        self.render.set_light(directional_light_np)

        self.skybox.set_scale((self.world_size / 2, self.world_size / 2, self.world_size / 4))
        self.skybox.set_bin('background', 1)
        self.skybox.set_depth_write(0)
        self.skybox.set_light_off()
        self.skybox.reparent_to(self.render)

        self.water.is_raining = False

        self.water.water_shader_hlp.dampening = 0.96
        self.water.water_shader_hlp.acceleration = 10

        # time of the day
        self.water.ocean_shader_hlp.deep_colour = LVector4(0.0, 0.3, 0.5, 0.2)
        self.water.ocean_shader_hlp.shallow_colour = LVector4(0.0, 1.0, 1.0, 0.1)
        self.water.ocean_shader_hlp.reflection_colour = LVector4(0.85, 1.0, 1.0, 0.25)
        self.water.ocean_shader_hlp.water_amount = 0.4
        self.water.ocean_shader_hlp.reflection_amount = 4.0
        self.water.ocean_shader_hlp.hdr_multiplier = 0.3
        # weather
        self.water.ocean_shader_hlp.bump_scale = 0.05
        self.water.ocean_shader_hlp.bump_speed = (0.0, 0.0)
        self.water.ocean_shader_hlp.teeth = 0.9
        self.water.ocean_shader_hlp.wave_freq = 0.23
        self.water.ocean_shader_hlp.speed0 = (-2.0, 0)
        self.water.ocean_shader_hlp.speed1 = (1.0, 1.0)
        self.water.ocean_shader_hlp.wave_amp = 0.3

    def init_camera(self):
        print "Initializing camera"
        self.camLens.set_near(0.1)
        self.camera.set_pos(self.camera_pos)
        self.camera.set_hpr(self.camera_hpr)

    def init_scene(self):
        self.init_environment()
        self.init_camera()

        self.pivot.setPos(0, 0, 0)

        self.model.set_pos(0, 10, 0)
        self.model.set_h(90)
        self.model.reparent_to(self.pivot)

        self.render.set_shader_input('time', 0)
        self.taskMgr.add(self.update_task, 'update')

    def update_camera(self):
        if not self.debug:
            self.camera.set_pos(self.camera_pos)
            self.camera.set_hpr(self.camera_hpr)
        self.water.ocean_shader_hlp.set_eye_pos(self.camera.get_pos(), self.camera.get_mat())

    def update_task(self, task):
        self.render.set_shader_input('time', task.time)
        self.update_camera()
        pos = self.model.get_pos(self.water.water_np)

        x, y = self.water.water_shader_hlp.get_texture_pos(self.tail + pos.x, pos.y)
        self.water.water_shader_hlp.push_water(x, y, 0, 0.45)
        x, y = self.water.water_shader_hlp.get_texture_pos(self.head + pos.x, pos.y)
        self.water.water_shader_hlp.push_water(x, y, 0, 0.475)

        self.water.update(task.time)
        z = self.water.ocean_shader_hlp.get_height(pos.x, pos.y)
        self.model.set_z(self.water.water_np, z)
        return task.cont


if __name__ == '__main__':
    app = MyApp()
    app.run()
