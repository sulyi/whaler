import random

import copy
from direct.interval.LerpInterval import LerpTexOffsetInterval
from panda3d.core import (
    Camera, CardMaker, CullFaceAttrib, Filename, FrameBufferProperties, GraphicsOutput, GraphicsPipe, LPlane, LPoint2,
    LPoint2d, LPoint3, LPoint3d, LVector3, LVector3d, LVector4, NodePath, OrthographicLens, PlaneNode, PNMImage,
    RenderState, Shader, TexGenAttrib, Texture, TextureStage, TransparencyAttrib, WindowProperties)
from panda3d.egg import CS_zup_right, EggData, EggPolygon, EggVertex, EggVertexPool, load_egg_data


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


def create_egg_plane(name, width, height, segments_x, segments_y, filename=None):
    data = EggData()
    vp = EggVertexPool('s')
    data.add_child(vp)

    width = float(width)
    height = float(height)

    d_width = width / segments_x
    d_height = height / segments_y
    dx = 1.0 / segments_x
    dy = 1.0 / segments_y
    for y in range(segments_y):
        ty = 1.0 - y * dy
        for x in range(segments_x):
            tx = x * dx
            x_pos = float(x) * d_width - width / 2.0
            y_pos = float(y) * d_height - height / 2.0
            tex_coord = [[tx, ty], [tx + dx, ty], [tx + dx, ty - dy], [tx, ty - dy]]
            add_square(data, vp, x_pos, y_pos, d_width, d_height, tex_coord)

    if filename is not None:
        data.set_coordinate_system(CS_zup_right)
        data.write_egg(Filename(filename))
    node = load_egg_data(data)
    np = NodePath(node)
    np.set_name(name)
    return np


def add_square(data, vp, x, y, w, h, tex_coord=None):
    if tex_coord is None:
        tex_coord = [[1, 0], [1, 1], [0, 1], [0, 0]]
    e_poly = EggPolygon()
    data.add_child(e_poly)
    in_position = [[x, y, 0], [x + w, y, 0], [x + w, y + h, 0], [x, y + h, 0]]
    for i in range(4):
        ev = EggVertex()
        ev.set_pos(LPoint3d(*in_position[i]))
        ev.set_uv(LPoint2d(*tex_coord[i]))
        ev.set_normal(LVector3d(0, 0, 1))
        e_poly.add_vertex(vp.add_vertex(ev))


class ShaderHelper(object):
    _shader = None

    def __init__(self, target, base):
        self.target = target
        self.base = base

        if self._shader is None:
            raise NotImplementedError(
                "Child class of AbstractShaderHelper needs to override _shader attribute")
        else:
            self.target.set_shader(self._shader)

    def set_shader_input(self, name, *args):
        self.target.set_shader_input(name, *args)

    def update(self):
        raise NotImplementedError("Child class of AbstractShaderHelper needs to override update method")


class TextureShaderHelper(ShaderHelper):
    def __init__(self, target, base, width, height, size):
        super(TextureShaderHelper, self).__init__(target, base)

        self._size = size
        self._width = width
        self._height = height

    def get_texture_pos(self, px, py):
        x = int((px + self._width / 2.0) / self._width * self._size)
        y = int((py + self._height / 2.0) / self._height * self._size)
        return x, y


class OceanShaderHelper(TextureShaderHelper):
    _shader = Shader.load(
        Shader.SL_GLSL, vertex="shaders/vertex_ocean.vs", fragment="shaders/vertex_ocean.fs")

    def __init__(self, target, base, width, height, size, use_cubemap_only):
        super(OceanShaderHelper, self).__init__(target, base, width, height, size)
        self._use_cubemap_only = use_cubemap_only

        self._wave_freq, self._wave_amp, self._teeth = 0.028, 0.9, 1.5
        self._speed0, self._speed1 = (-1, 0), (-0.7, 0.7)
        self._bump_scale, self._bump_speed, self._texture_scale = 0.2, (0.015, 0.005), (25.0, 25.0)
        self._reflection_amount, self._water_amount = 1.0, 0.3
        self._deep_colour, self._shallow_colour, self._reflection_colour = (
            LVector4(0.0, 0.3, 0.5, 1.0), LVector4(0.0, 1.0, 1.0, 1.0), LVector4(0.95, 1.0, 1.0, 1.0)
        )
        self._fresnel_power, self._fresnel_bias, self._hdr_multiplier, self._reflection_blur = (
            5.0, 0.328, 0.471, 0.0
        )

        self._grid_ratio = LVector4(10, 10, 15, 5)

        alt_render = NodePath('altRender')
        self._clone = NodePath(copy.copy(self.target.node()))
        self._clone.reparent_to(alt_render)

        # Heightmap buffer and camera
        winprops = WindowProperties.size(self._size, self._size)
        props = FrameBufferProperties()
        props.set_aux_rgba(1)

        wave_buffer = base.graphicsEngine.make_output(
            base.pipe, "innerWaveBuffer", -1, props, winprops,
            GraphicsPipe.BFRefuseWindow, base.win.get_gsg(), base.win)
        wave_buffer.set_clear_color(LVector4(0.5, 0.5, 0.5, 0))

        quad_cam_node = Camera('wave-heightmap-quad-cam')
        lens = OrthographicLens()
        lens.set_film_size(width, height)
        lens.set_view_hpr(0, -90, 0)
        lens.set_film_offset(0, 0)
        lens.set_near_far(-1000, 1000)
        quad_cam_node.set_lens(lens)
        quad_cam_np = self._clone.attach_new_node(quad_cam_node)

        wave_buffer.get_display_region(0).set_camera(quad_cam_np)
        wave_buffer.get_display_region(0).set_active(1)

        self._wave_tex = Texture()
        wave_buffer.add_render_texture(self._wave_tex, GraphicsOutput.RTM_copy_ram, GraphicsOutput.RTP_aux_rgba_0)
        self._heightmap = PNMImage(self._size, self._size)

        self.target.set_transparency(TransparencyAttrib.MAlpha)

        if not self._use_cubemap_only:
            # Reflection plane
            z = self.target.get_z()
            self._reflection_plane = LPlane(LVector3(0, 0, 1), LPoint3(0, 0, z + 10))

            plane_node = PlaneNode('waterPlane')
            plane_node.set_plane(self._reflection_plane)
            # Buffer and reflection camera
            reflection_buffer = base.win.make_texture_buffer('waterBuffer', self._size, self._size)
            reflection_buffer.set_clear_color(LVector4(0, 0, 0, 1))

            cfa = CullFaceAttrib.make_reverse()
            rs = RenderState.make(cfa)

            self._reflection_cam_np = base.makeCamera(reflection_buffer)
            self._reflection_cam_np.reparent_to(base.render)

            water_cam = self._reflection_cam_np.node()
            water_cam.get_lens().set_fov(base.camLens.get_fov())
            water_cam.get_lens().set_near(1)
            water_cam.get_lens().set_far(5000)
            water_cam.set_initial_state(rs)

            # water textures
            # reflection texture, created in real-time by the 'water camera'
            tex0 = reflection_buffer.get_texture()
            tex0.set_wrap_u(Texture.WMClamp)
            tex0.set_wrap_v(Texture.WMClamp)
        else:
            tex0 = Texture()
        ts_reflection = TextureStage('reflection')
        self.target.set_texture(ts_reflection, tex0)

        # Distortion texture
        tex1 = base.loader.loadTexture("textures/waves200.tga")
        ts_distortion = TextureStage('distortion')
        self.target.set_texture(ts_distortion, tex1)

        # Texture stage for cube map
        self.ts_environ = TextureStage('environ')

        self.set_shader_input(
            'waveInfo', LVector4(self._wave_freq, self._wave_amp, self._bump_scale, self._teeth))
        self.set_shader_input(
            'param2',
            LVector4(
                self._bump_speed[0],
                self._bump_speed[1],
                self._texture_scale[0],
                self._texture_scale[1]))
        self.set_shader_input(
            'param3',
            LVector4(
                self._reflection_amount,
                self._water_amount,
                0.0,
                1.0 if self.use_cubemap_only else 0.0))
        self.set_shader_input(
            'param4', LVector4(self._fresnel_power, self._fresnel_bias, self._hdr_multiplier, self._reflection_blur))
        self.set_shader_input(
            'speed', LVector4(self._speed0[0], self._speed0[1], self._speed1[0], self._speed1[1]))
        self.set_shader_input('deepColor', self._deep_colour)
        self.set_shader_input('shallowColor', self._shallow_colour)
        self.set_shader_input('reflectionColor', self._reflection_colour)
        self.set_shader_input('gridRatio', self._grid_ratio)

    # read-only
    @property
    def use_cubemap_only(self):
        return self._use_cubemap_only

    @property
    def wave_freq(self):
        return self._wave_freq

    @property
    def wave_amp(self):
        return self._wave_amp

    @property
    def bump_speed(self):
        return self._bump_speed

    @property
    def teeth(self):
        return self._teeth

    @property
    def bump_scale(self):
        return self._bump_scale

    @property
    def texture_scale(self):
        return self._texture_scale

    @property
    def reflection_amount(self):
        return self._reflection_amount

    @property
    def water_amount(self):
        return self._water_amount

    @property
    def fresnel_power(self):
        return self._fresnel_power

    @property
    def fresnel_bias(self):
        return self._fresnel_bias

    @property
    def hdr_multiplier(self):
        return self._hdr_multiplier

    @property
    def reflection_blur(self):
        return self._reflection_blur

    @property
    def speed0(self):
        return self._speed0

    @property
    def speed1(self):
        return self._speed1

    @property
    def deep_colour(self):
        return self._deep_colour

    @property
    def shallow_colour(self):
        return self._shallow_colour

    @property
    def reflection_colour(self):
        return self._reflection_colour

    @property
    def grid_ratio(self):
        return self._grid_ratio

    @wave_freq.setter
    def wave_freq(self, value):
        self._wave_freq = value
        self.set_shader_input(
            'waveInfo',
            LVector4(
                self._wave_freq,
                self._wave_amp,
                self._bump_scale,
                self._teeth))

    @wave_amp.setter
    def wave_amp(self, value):
        self._wave_amp = value
        self.set_shader_input(
            'waveInfo',
            LVector4(
                self._wave_freq,
                self._wave_amp,
                self._bump_scale,
                self._teeth))

    @bump_scale.setter
    def bump_scale(self, value):
        self._bump_scale = value
        self.set_shader_input(
            'waveInfo',
            LVector4(
                self._wave_freq,
                self._wave_amp,
                self._bump_scale,
                self._teeth))

    @teeth.setter
    def teeth(self, value):
        self._teeth = value
        self.set_shader_input(
            'waveInfo',
            LVector4(
                self._wave_freq,
                self._wave_amp,
                self._bump_scale,
                self._teeth))

    @bump_speed.setter
    def bump_speed(self, value):
        self._bump_speed = value
        self.set_shader_input(
            'param2',
            LVector4(
                self._bump_speed[0],
                self._bump_speed[1],
                self._texture_scale[0],
                self._texture_scale[1]))

    @texture_scale.setter
    def texture_scale(self, value):
        self._texture_scale = value
        self.set_shader_input(
            'param2',
            LVector4(
                self._bump_speed[0],
                self._bump_speed[1],
                self._texture_scale[0],
                self._texture_scale[1]))

    @reflection_amount.setter
    def reflection_amount(self, value):
        self._reflection_amount = value
        self.set_shader_input(
            'param3',
            LVector4(
                self._reflection_amount,
                self._water_amount,
                0.0,
                1.0 if self.use_cubemap_only else 0.0))

    @water_amount.setter
    def water_amount(self, value):
        self._water_amount = value
        self.set_shader_input(
            'param3',
            LVector4(
                self._reflection_amount,
                self._water_amount,
                0.0,
                1.0 if self.use_cubemap_only else 0.0))

    @fresnel_power.setter
    def fresnel_power(self, value):
        self._fresnel_power = value
        self.set_shader_input(
            'param4',
            LVector4(
                self._fresnel_power,
                self._fresnel_bias,
                self._hdr_multiplier,
                self._reflection_blur))

    @fresnel_bias.setter
    def fresnel_bias(self, value):
        self._fresnel_bias = value
        self.set_shader_input(
            'param4',
            LVector4(
                self._fresnel_power,
                self._fresnel_bias,
                self._hdr_multiplier,
                self._reflection_blur))

    @hdr_multiplier.setter
    def hdr_multiplier(self, value):
        self._hdr_multiplier = value
        self.set_shader_input(
            'param4',
            LVector4(
                self._fresnel_power,
                self._fresnel_bias,
                self._hdr_multiplier,
                self._reflection_blur))

    @reflection_blur.setter
    def reflection_blur(self, value):
        self._reflection_blur = value
        self.set_shader_input(
            'param4',
            LVector4(
                self._fresnel_power,
                self._fresnel_bias,
                self._hdr_multiplier,
                self._reflection_blur))

    @speed0.setter
    def speed0(self, value):
        self._speed0 = value
        self.set_shader_input(
            'speed',
            LVector4(
                self._speed0[0],
                self._speed0[1],
                self._speed1[0],
                self._speed1[1]))

    @speed1.setter
    def speed1(self, value):
        self._speed1 = value
        self.set_shader_input(
            'speed',
            LVector4(
                self._speed0[0],
                self._speed0[1],
                self._speed1[0],
                self._speed1[1]))

    @deep_colour.setter
    def deep_colour(self, value):
        self._deep_colour = value
        self.set_shader_input('deepColor', self._deep_colour)

    @shallow_colour.setter
    def shallow_colour(self, value):
        self._shallow_colour = value
        self.set_shader_input('shallowColor', self._shallow_colour)

    @reflection_colour.setter
    def reflection_colour(self, value):
        self._reflection_colour = value
        self.set_shader_input('reflectionColor', self._reflection_colour)

    @grid_ratio.setter
    def grid_ratio(self, value):
        self._grid_ratio = value
        self.set_shader_input('gridRatio', self._grid_ratio)

    def set_shader_input(self, name, *args):
        super(OceanShaderHelper, self).set_shader_input(name, *args)
        self._clone.set_shader_input(name, *args)

    def update(self, time):
        self._clone.set_shader_input('time', time)
        # self._reflection_plane.set_w(0.1 - self.target.get_z() - self.get_height(0, 0))

    def set_skybox(self, cubemap):
        cubemap.set_minfilter(Texture.FT_linear_mipmap_linear)  # for reflection blur to work
        self.target.clear_texture(self.ts_environ)
        self.target.set_texture(self.ts_environ, cubemap)
        self.target.set_tex_gen(self.ts_environ, TexGenAttrib.M_eye_cube_map)

    def set_eye_pos(self, pos, mc=None):
        if mc is not None and not self._use_cubemap_only:
            # update matrix of the reflection camera
            mf = self._reflection_plane.get_reflection_mat()
            self._reflection_cam_np.set_mat(mc * mf)
        self.target.set_shader_input('eyePosition', LVector4(pos - self.target.get_pos(), 0))
        self._clone.set_shader_input('eyePosition', LVector4(pos - self.target.get_pos(), 0))

    def get_height(self, x, y):
        self._wave_tex.store(self._heightmap)
        self._heightmap.flip(False, True, False)
        f = self._heightmap.get_pixel(*self.get_texture_pos(x, y))
        return (f.get_red() / 255.0 - 0.5) * (2.0 * 1.75 * self._wave_amp + 0.2)


class WaterShaderHelper(TextureShaderHelper):
    _shader = Shader.load(
        Shader.SL_GLSL, vertex="shaders/water.vs", fragment="shaders/water.fs")

    def __init__(self, base, width, height, size):
        cm = CardMaker('water-filter-stage-quad')
        cm.set_frame_fullscreen_quad()
        quad = NodePath(cm.generate())
        quad.set_depth_test(0)
        quad.set_depth_write(0)
        quad.set_color(LVector4(0.5, 0.5, 0.5, 1))

        super(WaterShaderHelper, self).__init__(quad, base, width, height, size)

        self._acceleration = 30
        self._dampening = 0.99

        self.is_texture_changed = False

        surface_buffer = base.win.make_texture_buffer('surface', self._size, self._size, Texture(), True)
        surface_buffer.set_clear_color(LVector4(0.5, 0.5, 0.5, 0))
        surface_buffer.set_sort(-1)

        quad_cam_node = Camera('water-filter-quad-cam')
        lens = OrthographicLens()
        lens.set_film_size(2, 2)
        lens.set_film_offset(0, 0)
        lens.set_near_far(-1000, 1000)
        quad_cam_node.set_lens(lens)
        quad_cam_np = self.target.attach_new_node(quad_cam_node)

        surface_buffer.get_display_region(0).set_camera(quad_cam_np)
        surface_buffer.get_display_region(0).set_active(1)

        self.vertex_tex = Texture()
        self._tex1 = Texture()
        self._temp_tex = surface_buffer.get_texture()

        self._screen_image = PNMImage(self._size, self._size)
        self._screen_image.fill(0.5, 0.5, 0.5)
        self.vertex_tex.load(self._screen_image)
        self._tex1.load(self._screen_image)
        self._temp_tex.load(self._screen_image)

        self._screen_image_new = None

        texd = base.loader.loadTexture("textures/dampening.tga")  # for dampening purpose
        self.target.set_texture(TextureStage('tex0'), self.vertex_tex)
        self.target.set_texture(TextureStage('tex1'), self._tex1)
        self.target.set_texture(TextureStage('dampening'), texd)

        self.set_shader_input(
            'param1', LVector4(
                self._size,
                self._size,
                self._acceleration,
                self._dampening))

    @property
    def acceleration(self):
        return self._acceleration

    @property
    def dampening(self):
        return self._dampening

    @acceleration.setter
    def acceleration(self, value):
        self._acceleration = value
        self.set_shader_input(
            'param1',
            LVector4(
                self._size,
                self._size,
                self._acceleration,
                self._dampening))

    @dampening.setter
    def dampening(self, value):
        self._dampening = value
        self.set_shader_input(
            'param1',
            LVector4(
                self._size,
                self._size,
                self._acceleration,
                self._dampening))

    def update(self):
        self._tex1.load(self._screen_image)
        self._temp_tex.store(self._screen_image)
        if self._screen_image_new is not None and self.is_texture_changed:
            self.vertex_tex.load(self._screen_image_new)
        else:
            self.vertex_tex.load(self._screen_image)
        self._screen_image_new = None
        self.vertex_tex.set_wrap_u(Texture.WMClamp)
        self.vertex_tex.set_wrap_v(Texture.WMClamp)
        self._tex1.set_wrap_u(Texture.WMClamp)
        self._tex1.set_wrap_v(Texture.WMClamp)

        self.is_texture_changed = False

    def push_water(self, x1, y1, r, v):
        if self._screen_image_new is None:
            self._screen_image_new = PNMImage(self._size, self._size)
            self._temp_tex.store(self._screen_image_new)
        frx = max(0, x1 - r)
        tox = min(self._size, x1 + r + 1)
        fry = max(0, y1 - r)
        toy = min(self._size, y1 + r + 1)
        for x in range(frx, tox):
            for y in range(fry, toy):
                self._screen_image_new.set_red(x, y, v)
        self.is_texture_changed = True


class WaterNodeHelper(object):
    def __init__(self, base, width, height, depth, segment_x, segment_y, pos, use_cubemap_only=True):
        self.is_raining = False
        self._next_rain_time = 0

        self._texture_size = 512

        # Vertex texture
        self.water_shader_hlp = WaterShaderHelper(base, width, height, self._texture_size)

        # Surface
        self.water_np = create_egg_plane('water', width, height, segment_x, segment_y)
        self.water_np.set_pos(0, 0, pos.z)
        self.water_np.reparent_to(base.render)
        self.ocean_shader_hlp = OceanShaderHelper(
            self.water_np, base, width, height, self._texture_size, use_cubemap_only)

        self.ocean_shader_hlp.set_shader_input('vtftex', self.water_shader_hlp.vertex_tex)
        self.ocean_shader_hlp.set_eye_pos(LVector3(0, 0, 0))

        # Faking caustics
        self.deep_water_np = create_egg_plane('deepwater', width, height, 1, 1)
        self.deep_water_np.set_pos(pos - LVector3(0.0, 0.0, depth))
        self.deep_water_np.reparent_to(base.render)

        ts_dp = TextureStage('caustics')
        self.deep_water_np.set_texture(ts_dp, base.loader.loadTexture("textures/water4.png"))
        self.deep_water_np.set_tex_scale(ts_dp, 4)
        LerpTexOffsetInterval(self.deep_water_np, 200, (0.5, 1), (0, 0), textureStage=ts_dp).loop()

        if use_cubemap_only:
            self.hide()
            cubemap_file = base.saveCubeMap("tmp/cube_#.jpg", size=256)
            if cubemap_file is not None:
                self.ocean_shader_hlp.set_skybox(base.loader.loadCubeMap(cubemap_file))
            self.show()

    def update(self, time):
        if self.is_raining:
            if time > self._next_rain_time:
                x1 = random.randint(self._texture_size / 5, self._texture_size * 4 / 5)
                y1 = random.randint(self._texture_size / 5, self._texture_size * 4 / 5)
                v = random.random() * 0.25 + 0.05
                r = random.randint(0, 3)
                self.water_shader_hlp.push_water(x1, y1, r, v)
                self._next_rain_time = time + random.random() * 0.5 + 0.15

        self.ocean_shader_hlp.update(time)
        self.water_shader_hlp.update()

    def hide(self):
        self.water_np.hide()
        self.deep_water_np.hide()

    def show(self):
        self.water_np.show()
        self.deep_water_np.show()
