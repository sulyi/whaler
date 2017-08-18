#!/usr/bin/env python
import sys

from direct.actor.Actor import Actor
from direct.gui.DirectGui import DirectButton, DirectLabel
from direct.interval.LerpInterval import LerpTexOffsetInterval
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    AmbientLight, DirectionalLight,
    CardMaker,
    TextureStage, TransparencyAttrib,
    TextNode, NodePath,
    WindowProperties,
    LMatrix3, LPoint2, LPoint3, LVecBase3, LVecBase4,
)
# from panda3d.bullet import BulletWorld


def create_plane(name, width, height, x_segments, y_segments):
    maker = CardMaker('grid')
    maker.set_frame(0, 1, 0, 1)
    np = NodePath(name)
    dx = 1.0 / x_segments
    dy = 1.0 / x_segments
    u = 0.0
    for x in range(x_segments):
        v = 0.0
        for y in range(y_segments):
            maker.set_uv_range(LPoint2(u, v), LPoint2(u + dx, v + dy))
            v += dy
            node = np.attach_new_node(maker.generate())
            node.set_hpr(0, -90, 0)
            node.set_pos(float(x) - float(x_segments) / 2, float(y) - float(y_segments) / 2, 0)
        u += dx
    np.set_scale(float(width) / x_segments, float(height) / y_segments, 1)
    np.flatten_strong()
    return np


class BoneControl(object):
    def __new__(cls, armature, joint, parent=None):
        if joint is None:
            return None
        return super(BoneControl, cls).__new__(cls)

    def __init__(self, armature, joint, parent=None):
        self.armature = armature
        self.node_path = self.armature.model.controlJoint(None, 'modelRoot', joint.get_name())
        if parent is None:
            self.origin = armature.model.attach_new_node('%s-origin' % self.node_path.get_name())
        else:
            self.node_path.reparent_to(parent.node_path)
            self.origin = parent.origin.attach_new_node('%s-origin' % self.node_path.get_name())
        self.origin.set_transform(self.node_path.get_transform())

    def _set_rotation(self, respect_to, rotation, coordinates):
        if coordinates is None or all(coordinates):
            self.node_path.set_hpr(respect_to, rotation)
        else:
            for flag, func, arg in zip(
                    coordinates,
                    [self.node_path.set_h, self.node_path.set_p, self.node_path.set_r],
                    rotation):
                if flag:
                    func(respect_to, arg)

    def _set_scale(self, respect_to, scale, coordinates):
        if coordinates is None or all(coordinates):
            self.node_path.set_scale(respect_to, scale)
        else:
            for flag, func, arg in zip(
                    coordinates,
                    [self.node_path.set_sx, self.node_path.set_sy, self.node_path.set_sz],
                    scale):
                if flag:
                    func(respect_to, arg)

    def get_local_pos(self):
        return self.node_path.get_pos(self.origin)

    def get_local_rot(self):
        return self.node_path.get_hpr(self.origin)

    def get_local_scale(self):
        return self.node_path.get_scale(self.origin)

    def get_global_pos(self):
        return self.node_path.get_pos(self.armature.root)

    def get_global_rot(self):
        return self.node_path.get_hpr(self.armature.root)

    def get_global_scale(self):
        return self.node_path.get_scale(self.armature.root)

    def set_local_pos(self, translation):
        self.armature.is_dirty = True

        self.node_path.set_pos(self.origin, translation)

    def set_local_rot(self, rotation, coordinates=None):
        self.armature.is_dirty = True

        self._set_rotation(self.origin, rotation, coordinates)

    def set_local_scale(self, scale, coordinates=None):
        self.armature.is_dirty = True

        self._set_scale(self.origin, scale, coordinates)

    def set_global_pos(self, translation):
        self.armature.is_dirty = True

        self.node_path.set_pos(self.armature.root, translation)

    def set_global_rot(self, rotation, coordinates=None):
        self.armature.is_dirty = True

        self._set_rotation(self.armature.root, rotation, coordinates)
    
    def set_global_scale(self, scale, coordinates=None):
        self.armature.is_dirty = True

        self._set_scale(self.armature.root, scale, coordinates)
    
    def track(self, target, point=None):
        self.armature.is_dirty = True

        if point is None:
            self.node_path.look_at(target.node_path)
        else:
            self.node_path.look_at(target.node_path, point)

    def stretch_to(self, target):
        self.armature.is_dirty = True

        self.track(target)
        curr_distance = self.node_path.get_distance(target.node_path)
        orig_distance = self.origin.get_distance(target.origin)

        self.node_path.set_sy(curr_distance / orig_distance)


class RiggingArmature(object):
    def __init__(self, name_prefix, model, render):
        self.name = name_prefix
        self.root = render
        self.model = model
        self.is_dirty = False

        joints = {joint.getName(): joint for joint in self.model.getJoints()}

        self.yard_control = BoneControl(
            self, joints.get('%s-yard-control' % name_prefix))
        self.brace_control_l = BoneControl(
            self, joints.get('%s-brace-control-l' % name_prefix))
        self.brace_control_r = BoneControl(
            self, joints.get('%s-brace-control-r' % name_prefix))
        self.brace_top_control_l = BoneControl(
            self, joints.get('%s-brace-top-control-l' % name_prefix))
        self.brace_top_control_r = BoneControl(
            self, joints.get('%s-brace-top-control-r' % name_prefix))
        self.brace_bottom_control_l = BoneControl(
            self, joints.get('%s-brace-bottom-control-l' % name_prefix))
        self.brace_bottom_control_r = BoneControl(
            self, joints.get('%s-brace-bottom-control-r' % name_prefix))

        self.band_frame = BoneControl(
            self, joints.get('%s-band-frame' % name_prefix))
        self.yard_frame = BoneControl(
            self, joints.get('%s-yard-frame' % name_prefix), self.band_frame)
        self.yard_frame_tail = BoneControl(
            self, joints.get('%s-yard-frame-tail' % name_prefix), self.yard_frame)
        self.scale_frame = BoneControl(
            self, joints.get('%s-scale-frame' % name_prefix), self.band_frame)
        self.yard_frame_l = BoneControl(
            self, joints.get('%s-yard-frame-l' % name_prefix), self.scale_frame)
        self.yard_frame_r = BoneControl(
            self, joints.get('%s-yard-frame-r' % name_prefix), self.scale_frame)
        self.yard_frame_tail_l = BoneControl(
            self, joints.get('%s-yard-frame-tail-l' % name_prefix), self.yard_frame_l)
        self.yard_frame_tail_r = BoneControl(
            self, joints.get('%s-yard-frame-tail-r' % name_prefix), self.yard_frame_r)
        self.brace_pole_l = BoneControl(
            self, joints.get('%s-brace-pole-l' % name_prefix))
        self.brace_pole_r = BoneControl(
            self, joints.get('%s-brace-pole-r' % name_prefix))

        self.band = BoneControl(
            self, joints.get('%s-band' % name_prefix))
        self.yard_l = BoneControl(
            self, joints.get('%s-yard-l' % name_prefix), self.band)
        self.yard_r = BoneControl(
            self, joints.get('%s-yard-r' % name_prefix), self.band)
        self.brace_upper_l = BoneControl(
            self, joints.get('%s-brace-upper-l' % name_prefix), self.yard_l)
        self.brace_upper_r = BoneControl(
            self, joints.get('%s-brace-upper-r' % name_prefix), self.yard_r)
        self.brace_lower_l = BoneControl(
            self, joints.get('%s-brace-lower-l' % name_prefix), self.brace_upper_l)
        self.brace_lower_r = BoneControl(
            self, joints.get('%s-brace-lower-r' % name_prefix), self.brace_upper_r)
        self.brace_lower_top_l = BoneControl(
            self, joints.get('%s-brace-lower-top-l' % name_prefix), self.brace_upper_l)
        self.brace_lower_top_r = BoneControl(
            self, joints.get('%s-brace-lower-top-r' % name_prefix), self.brace_upper_r)
        self.brace_lower_bottom_l = BoneControl(
            self, joints.get('%s-brace-lower-bottom-l' % name_prefix), self.brace_upper_l)
        self.brace_lower_bottom_r = BoneControl(
            self, joints.get('%s-brace-lower-bottom-r' % name_prefix), self.brace_upper_r)

    def update(self):
        if self.is_dirty:
            self._update()
            self.is_dirty = False

    def _update(self):
        # apply armature constrains
        self.band.set_local_rot(self.yard_control.get_local_rot(), coordinates=(True, True, False))

        self.band_frame.set_local_rot(self.yard_control.get_local_rot())
        self.band_frame.set_local_pos(self.yard_control.get_local_pos())

        self.yard_l.set_global_pos(self.yard_frame_tail.get_global_pos())
        self.yard_r.set_global_pos(self.yard_frame_tail.get_global_pos())

        self.scale_frame.set_global_scale(self.yard_control.get_global_scale())
        self.yard_frame_l.set_local_scale(1.0)
        self.yard_frame_r.set_local_scale(1.0)

        self.yard_l.track(self.yard_frame_tail_l)
        self.yard_r.track(self.yard_frame_tail_r)

        if self.brace_pole_l is not None:
            self.brace_pole_l.set_global_pos(
                (self.brace_top_control_l.get_global_pos() + self.brace_bottom_control_l.get_global_pos()) / 2)
            self.brace_pole_l.set_local_rot(
                (self.brace_top_control_l.get_local_rot() + self.brace_bottom_control_l.get_local_rot()) / 2)
            self.brace_upper_l.track(self.brace_pole_l)
            # track also handles:
            # self.brace_upper_l rotation self.brace_pole_l
            self.brace_lower_top_l.stretch_to(self.brace_top_control_l)
            self.brace_lower_bottom_l.stretch_to(self.brace_bottom_control_l)

        else:
            if self.brace_lower_l is not None:
                self.brace_upper_l.track(self.brace_control_l)
                # track also handles:
                # self.brace_upper_l rotate self.brace_control_l
                self.brace_lower_l.stretch_to(self.brace_control_l)
            else:
                self.brace_upper_l.stretch_to(self.brace_control_l)
                # track also handles:
                # self.brace_upper_l rotate self.brace_control_l
        if self.brace_pole_r is not None:
            self.brace_pole_r.set_global_pos(
                (self.brace_top_control_r.get_global_pos() + self.brace_bottom_control_r.get_global_pos()) / 2)
            self.brace_pole_r.set_local_rot(
                (self.brace_top_control_r.get_local_rot() + self.brace_bottom_control_r.get_local_rot()) / 2)
            self.brace_upper_r.track(self.brace_pole_r)
            # track also handles:
            # self.brace_upper_r rotation self.brace_pole_r
            self.brace_lower_top_r.stretch_to(self.brace_top_control_r)
            self.brace_lower_bottom_r.stretch_to(self.brace_bottom_control_r)
        else:
            if self.brace_lower_r is not None:
                self.brace_upper_r.track(self.brace_control_r)
                # track also handles:
                # self.brace_upper_r rotate self.brace_control_r
                self.brace_lower_r.stretch_to(self.brace_control_r)
            else:
                self.brace_upper_r.stretch_to(self.brace_control_r)
                # track also handles:
                # self.brace_upper_r rotate self.brace_control_r


class MyApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)

        self.debug = False
        self.has_focus = False
        self.pointer_is_dirty = True
        self.key_state = {
            'forward': False,
            'backward': False,
            'left': False,
            'right': False,
            'up': False,
            'down': False,
            'hud': False,
            'grab': False,
            'freecam': False,
            'wheel': 0
        }

        locked_cam_controls = {
            'moveforward': (self.wheel_up, None),
            'movebackward': (self.wheel_down, None),
            'grab3+': (self.wheel_up, None),
            'grab3-': (self.wheel_down, None),
            'moveup': (self._set_key, ['up']),
            'movedown': (self._set_key, ['down']),
            'moveleft': (self._set_key, ['left']),
            'moveright': (self._set_key, ['right']),
            'showhud': (self._set_key, ['hud']),
            'togglegrab': (self._set_key, ['grab']),
            'makecamfree': (self._set_key, ['freecam']),
            'exit': (self.clean_up, None)
        }

        locked_cam_keymap = {
            'moveup': ['w', 'arrow_up'],
            'movedown': ['s', 'arrow_down'],
            'moveright': ['d', 'arrow_right'],
            'moveleft': ['a', 'arrow_left'],
            'moveforward': ['shift-wheel_down'],
            'movebackward': ['shift-wheel_up'],
            'grab3+': ['wheel_up'],
            'grab3-': ['wheel_down'],
            'showhud': ['space'],
            'togglegrab': ['mouse1'],
            'makecamfree': ['shift'],
            'exit': ['escape']
        }

        self.controls = locked_cam_controls
        self.set_controls(locked_cam_keymap)

        self.is_hud = False
        self.selected = {
            'action': 'rotate',
            'mast': 'all',
            'sail': 'all'
        }

        self.disableMouse()
        self.sensitivity = 1.0

        self.worldsize = 1024

        self.water = create_plane('water', self.worldsize, self.worldsize, 64, 64)
        self.water.set_transparency(TransparencyAttrib.MAlpha)
        self.water.reparent_to(self.render)

        self.model = Actor("./models/flying_cloud/FLYING_L-tailed")

        self.model.set_pos(self.worldsize / 2, self.worldsize / 2, 25)
        self.model.reparent_to(self.render)

        masts = ['fore', 'main', 'mizzen']
        sails = ['', 'top', 'topgallant', 'royal', 'sky']

        self.armatures = {mast + sail: RiggingArmature(mast + sail, self.model, self.render)
                          for mast in masts for sail in sails}

        # self.world = BulletWorld()
        # info = self.world.getWorldInfo()
        # info.setWaterDensity(1.0)
        # info.setWaterOffset(25)
        # info.setWaterNormal(Vec3(0.0, 0.0, 1.0))

        self.init_environment()

        stern_cam = LPoint3(0.0, 1.47, 0.33), LVecBase3(180, -15, 0.0)
        locked_cam = [LPoint3(5.62585, -0.1185, 4.49804), LVecBase3(89.8116, -26.8503, 0)]
        self.lock_target = LPoint3(0.0, -0.1, 1.65)

        self.cam_pos, self.cam_rot = locked_cam
        self.update_current_camera = self.update_orbit_camera
        self.init_camera()

        self.gui = []
        self.init_gui()

        self.accept('window-event', self.win_event)
        self.taskMgr.doMethodLater(0.5, self.init_scene, 'initScene')
        # self.model.place()

    def init_gui(self):
        masts = ['all', 'fore', 'main', 'mizzen']
        sails = ['all', 'course', 'top', 'topgallant', 'royal', 'sky']
        actions = ['rotate', 'move', 'scale']

        button_maps = self.loader.loadModel("./models/button")

        action_label = DirectLabel(text="Action: %s" % self.selected['action'], text_fg=(1.0, 1.0, 1.0, 1.0),
                                 text_scale=0.06, text_pos=(-0.2, -0.015), text_align=TextNode.ALeft,
                                 geom=button_maps.find('**/button'), geom_scale=(1.2, 1.0, 1.0), relief=None,
                                 pos=(0.0, 0.0, 0.35))
        action_label.hide()
        self.gui.append(action_label)

        mast_label = DirectLabel(text="Mast: %s" % self.selected['mast'], text_fg=(1.0, 1.0, 1.0, 1.0),
                                 text_scale=0.06, text_pos=(-0.2, -0.015), text_align=TextNode.ALeft,
                                 geom=button_maps.find('**/button'), geom_scale=(1.2, 1.0, 1.0), relief=None,
                                 pos=(-0.4, 0.0, 0.1))
        mast_label.hide()
        self.gui.append(mast_label)

        sail_label = DirectLabel(text="Sail: %s" % self.selected['mast'], text_fg=(1.0, 1.0, 1.0, 1.0),
                                 text_scale=0.06, text_pos=(-0.2, -0.015), text_align=TextNode.ALeft,
                                 geom=button_maps.find('**/button'), geom_scale=(1.2, 1.0, 1.0), relief=None,
                                 pos=(0.4, 0.0, 0.1))
        sail_label.hide()
        self.gui.append(sail_label)

        def manage_selection(key, value):
            self.selected[key] = value if value != 'course' else ''
            action_label.configure(text="Action: %s" % self.selected['action'])
            mast_label.configure(text="Mast: %s" % self.selected['mast'])
            sail_label.configure(text="Sail: %s" % (self.selected['sail'] or 'course'))

        for i, action in enumerate(actions, -1):
            button = DirectButton(text=action, text_scale=0.06, text_pos=(0.0, -0.015), text_fg=(1.0, 0.82, 0.0, 1.0),
                                  geom=button_maps, geom_scale=(0.8, 1.0, 1.0), relief=None,
                                  pos=(0.4 * i, 0.0, 0.25),
                                  command=manage_selection, extraArgs=['action', action])
            button.hide()
            self.gui.append(button)

        for i, mast in enumerate(masts):
            button = DirectButton(text=mast, text_scale=0.06, text_pos=(0.0, -0.015), text_fg=(1.0, 0.82, 0.0, 1.0),
                                  geom=button_maps, geom_scale=(0.8, 1.0, 1.0), relief=None,
                                  pos=(-0.4, 0.0, -0.1 * i),
                                  command=manage_selection, extraArgs=['mast', mast])
            button.hide()
            self.gui.append(button)
        
        for i, sail in enumerate(sails):
            button = DirectButton(text=sail, text_scale=0.06, text_pos=(0.0, -0.015), text_fg=(1.0, 0.82, 0.0, 1.0),
                                  geom=button_maps.find('**/button'), geom_scale=(0.8, 1.0, 1.0), relief=None,
                                  pos=(0.4, 0.0, -0.1 * i),
                                  command=manage_selection, extraArgs=['sail', sail])
            button.hide()
            self.gui.append(button)

    def init_environment(self):
        # lighting
        ambient_light = AmbientLight("ambientLight")
        ambient_light.set_color(LVecBase4(0.2, 0.2, 0.2, 1.0))
        self.render.set_light(self.render.attach_new_node(ambient_light))

        directional_light = DirectionalLight("directionalLight")
        directional_light.set_color(LVecBase4(1.0, 1.0, 0.8, 1.0))
        directional_light_np = self.render.attach_new_node(directional_light)
        directional_light_np.set_pos(1200.0, -400.0, 300.0)
        directional_light_np.look_at(self.model)
        self.render.set_light(directional_light_np)

        self.render.set_shader_input('light', directional_light_np)

        # water
        # self.water.set_sx(self.worldsize * 2)
        # self.water.set_sy(self.worldsize * 2)
        self.water.set_pos(self.worldsize / 2, self.worldsize / 2, 25)  # sea level
        # ocean_shader = Shader.load(Shader.SL_GLSL,
        #                            vertex="shaders/oceanv.sh",
        #                            fragment="shaders/oceanf.sh",
        #                            )
        # ocean_shader = Shader.load(Shader.SL_GLSL,
        #                            vertex="shaders/ocean2.vs",
        #                            fragment="shaders/ocean2.fs",
        #                            )

        # ocean_shader = self.loader.loadShader("demomaster-0.8/share/shaders/ocean2.sha")
        #
        # waveFreq, waveAmp = 0.028, 1.8
        # speed0, speed1 = (-1, 0), (-0.7, 0.7)
        # bumpScale, bumpSpeed, textureScale = 0.2, (0.015, 0.005), (25.0, 25.0)
        # reflectionAmount, waterAmount = 1.0, 0.3
        # deepcolor, shallowcolor, reflectioncolor = (
        #     Vec4(0.0, 0.3, 0.5, 1.0), Vec4(0.0, 1.0, 1.0, 1.0), Vec4(0.95, 1.0, 1.0, 1.0)
        # )
        # fresnelPower, fresnelBias, hdrMultiplier, reflectionBlur = (
        #     5.0, 0.328, 0.471, 0.0
        # )
        # debuglevel, debuginfo = 0, (0.0, 0.0, 0.0, 0.0)
        # cubemap = 0.0

        # self.water.setShaderInput('waveInfo', Vec4(waveFreq, waveAmp, bumpScale, 0))
        # self.water.setShaderInput('param2', Vec4(bumpSpeed[0], bumpSpeed[1], textureScale[0], textureScale[1]))
        # self.water.setShaderInput('param3', Vec4(reflectionAmount, waterAmount, debuglevel, cubemap))
        # self.water.setShaderInput('param4', Vec4(fresnelPower, fresnelBias, hdrMultiplier, reflectionBlur))
        # self.water.setShaderInput('speed', Vec4(speed0[0], speed0[1], speed1[0], speed1[1]))
        # self.water.setShaderInput('deepcolor', deepcolor)
        # self.water.setShaderInput('shallowcolor', shallowcolor)
        # self.water.setShaderInput('reflectioncolor', reflectioncolor)
        # self.water.set_shader(ocean_shader)

        new_ts = TextureStage('1')
        self.water.set_texture(new_ts, self.loader.loadTexture("./models/water2.png"))
        self.water.set_tex_scale(new_ts, 4)
        LerpTexOffsetInterval(self.water, 200, (0.5, 1), (0, 0), textureStage=new_ts).loop()

    def init_camera(self):
        self.camLens.set_near(0.1)
        self.update_camera()

    def init_scene(self, task):
        self.taskMgr.add(self.update_task, "update")

    def set_controls(self, keymap):
        for control_name, keys in keymap.items():
            control = self.controls.get(control_name)
            if control is None:
                raise RuntimeError, "Unknown control in keymap"
            handler, args = control
            for k in keys:
                if args is not None:
                    self.accept(k, handler, args + [True])
                    self.accept(k + '-up', handler, args + [False])
                else:
                    self.accept(k, handler, [])

    def _set_key(self, key, down):
        if self.debug:
            print "Key set", key, down
        self.key_state[key] = down

    def wheel_up(self):
        if self.debug:
            print "Wheel up"
        self.key_state['wheel'] += 1

    def wheel_down(self):
        if self.debug:
            print "Wheel down"
        self.key_state['wheel'] -= 1

    def toggle_hud(self, visible):
        if self.debug:
            print "HUD chanced", visible

        props = WindowProperties()
        if visible:
            props.set_cursor_hidden(False)
            props.set_mouse_mode(WindowProperties.M_confined)
            self.win.request_properties(props)
            for obj in self.gui:
                obj.show()
        else:
            self.pointer_is_dirty = True
            props.set_mouse_mode(WindowProperties.M_absolute)
            props.set_cursor_hidden(True)
            self.win.request_properties(props)
            for obj in self.gui:
                obj.hide()

    def get_pointer_delta(self):
        mw = self.mouseWatcherNode
        if mw.has_mouse() and self.has_focus and not self.pointer_is_dirty:
            # get the window manager's idea of the mouse position
            d = LPoint3(mw.get_mouse(), self.key_state['wheel'])
        else:
            d = LPoint3(0.0, 0.0, 0.0)

        return d

    def recenter_pointer(self):
        self.pointer_is_dirty = False
        self.key_state['wheel'] = 0
        self.win.move_pointer(0,
                              int(self.win.get_properties().get_x_size() / 2),
                              int(self.win.get_properties().get_y_size() / 2))

    def win_event(self, win):
        if win == self.winList[0]:
            properties = win.get_properties()
            if not properties.get_open():
                self.clean_up()
            foreground = properties.get_foreground()
            if self.has_focus != foreground:
                # focus changed
                self.has_focus = foreground
                self.focus_event_handler(foreground)

    def focus_event_handler(self, focus):
        if self.debug:
            print "Focus change", focus
        props = WindowProperties()
        props.set_mouse_mode(WindowProperties.M_absolute)
        props.set_cursor_hidden(focus)
        self.win.request_properties(props)

    def clean_up(self):
        self.destroy()
        self.taskMgr.removeTasksMatching("*")
        sys.exit()

    def update_free_look_camera(self, task):
        # TODO: wsad control, collision

        d = self.get_pointer_delta()

        self.cam_rot[0] -= d.x * 40 * self.sensitivity
        self.cam_rot[1] += d.y * 40 * self.sensitivity

        self.update_camera()

    def update_orbit_camera(self, task):
        # TODO: wsad control

        d = self.get_pointer_delta()
        direction = self.lock_target - self.cam_pos
        distance = max(0.5, direction.length() * (1 + d.z * 0.1 * self.sensitivity))
        z = LVecBase3(0.0, 0.0, 1.0)
        y = z.cross(direction)
        new_direction = LMatrix3.rotateMat(-40 * d.y * self.sensitivity, y).xform(direction)
        check = LVecBase3(new_direction)
        check.normalize()
        if check.cross(z).length() > 0.125:
            new_direction = LMatrix3.rotateMat(40 * d.x * self.sensitivity, z).xform(new_direction)
            self.cam_rot[1] += 40 * d.y * self.sensitivity
        else:
            new_direction = LMatrix3.rotateMat(40 * d.x * self.sensitivity, z).xform(direction)
        new_direction.normalize()
        new_direction *= distance
        self.cam_rot[0] += 40 * d.x * self.sensitivity
        self.cam_pos = self.lock_target - new_direction

        self.update_camera()

    def update_camera(self):
        self.camera.set_pos(self.model, self.cam_pos)
        self.camera.set_hpr(self.model, self.cam_rot)

    def update_parts(self, task):
        masts = (['fore', 'main', 'mizzen']
                 if self.selected['mast'] == 'all' else [self.selected['mast']])
        sails = (['', 'top', 'topgallant', 'royal', 'sky']
                 if self.selected['sail'] == 'all' else [self.selected['sail']])

        parts = [mast + sail for mast in masts for sail in sails]

        d = self.get_pointer_delta()

        for part_name in parts:
            armature = self.armatures[part_name]

            if self.selected['action'] == 'rotate':
                rot = armature.yard_control.get_local_rot()
                armature.yard_control.set_local_rot(
                    LVecBase3(rot.x + d.x * 40 * self.sensitivity,
                              rot.y + d.z * 4 * self.sensitivity,
                              rot.z + d.y * 40 * self.sensitivity))
            elif self.selected['action'] == 'move':
                pos = armature.yard_control.get_local_pos()
                armature.yard_control.set_local_pos(
                    LVecBase3(pos.x - d.z * 0.2 * self.sensitivity,
                              pos.y - d.x * 2 * self.sensitivity,
                              pos.z - d.y * 2 * self.sensitivity))
            elif self.selected['action'] == 'scale':
                scale = armature.yard_control.get_local_scale()
                armature.yard_control.set_local_scale(
                    max(LVecBase3(0.03125), scale + d.z * 0.02 * self.sensitivity))

            armature.update()

    def update_task(self, task):
        # dt = task.time
        # self.world.doPhysics(dt, 10, 0.004)
        if self.is_hud != self.key_state['hud']:
            self.is_hud = self.key_state['hud']
            self.toggle_hud(self.is_hud)

        if not self.is_hud:
            if self.key_state['freecam']:
                self.update_current_camera(task)
            elif self.key_state['grab'] or self.key_state['wheel']:
                self.update_parts(task)
            self.recenter_pointer()
        return task.cont


app = MyApp()
app.run()
