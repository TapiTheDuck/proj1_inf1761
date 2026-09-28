from __future__ import annotations

from typing import Any
from pathlib import Path
import time

import wgpu
from rendercanvas.glfw import RenderCanvas, loop

from camera2d import Camera2D
from transform import Transform
from disk import Disk
from quad import Quad
from node import Node
from shader import Shader
from pipeline import Pipeline
from scene import Scene
from renderer import Renderer
from engine import Engine

from texture import Texture
from sampler import Sampler
from textureset import TextureSet

canvas: RenderCanvas
device: wgpu.GPUDevice
context: Any
renderer: Renderer
camera: Camera2D
scene: Scene
last_t: float = 0.0


class SolarEngine(Engine):
  """Controla as velocidades de translação e rotação dos corpos celestes."""
  def __init__(
      self,
      mercury_orbit_trf: Transform,
      mercury_spin_trf: Transform,
      earth_orbit_trf: Transform,
      earth_spin_trf: Transform,
      moon_orbit_trf: Transform,

  ) -> None:
    self.mercury_orbit_trf = mercury_orbit_trf
    self.earth_orbit_trf = earth_orbit_trf
    self.earth_spin_trf = earth_spin_trf
    self.moon_orbit_trf = moon_orbit_trf
    self.mercury_spin_trf = mercury_spin_trf

  def update(self, dt: float) -> None:
    self.mercury_orbit_trf.rotate(45.0 * dt, 0, 0, 1)
    self.mercury_spin_trf.rotate(100.0 * dt, 0, 0, 1) 

    self.earth_orbit_trf.rotate(20.0 * dt, 0, 0, 1)
    self.earth_spin_trf.rotate(140.0 * dt, 0, 0, 1)
    self.moon_orbit_trf.rotate(90.0 * dt, 0, 0, 1)


def initialize(device: wgpu.GPUDevice, target_format: str) -> None:
  global camera
  camera = Camera2D(-5, 5, -5, 5)

  # Geometrias base
  disk_shape = Disk(device, radius=1.0, slices=64)
  quad_shape = Quad(device)

  # Sampler comum configurado com varname='smp'
  sampler = Sampler(device, "smp")

  # Caminho base das texturas
  base_path = Path(__file__).parent / "textures"

  # 1. Texturas configuradas com varname='tex'
  tex_space = Texture(device, "tex", str(base_path / "space.jpg"))
  tex_sun = Texture(device, "tex", str(base_path / "sun.png"))
  tex_mercury = Texture(device, "tex", str(base_path / "mercury.png"))
  tex_earth = Texture(device, "tex", str(base_path / "earth.png"))
  tex_moon = Texture(device, "tex", str(base_path / "moon.png"))

  # Montagem dos TextureSets
  ts_space = TextureSet([tex_space, sampler])
  ts_sun = TextureSet([tex_sun, sampler])
  ts_mercury = TextureSet([tex_mercury, sampler])
  ts_earth = TextureSet([tex_earth, sampler])
  ts_moon = TextureSet([tex_moon, sampler])

  # 2. Fundo (Espaço)
  trf_bg = Transform()
  trf_bg.translate(-5.0, -5.0, 0.0)
  trf_bg.scale(10.0, 10.0, 1.0)
  node_bg = Node(trf=trf_bg, apps=[ts_space], shps=[quad_shape])

  # 3. Sol (no centro)
  trf_sun = Transform()
  trf_sun.scale(1.1, 1.1, 1.0)
  node_sun = Node(trf=trf_sun, apps=[ts_sun], shps=[disk_shape])

  # 4. Mercúrio (órbita mais próxima)
  trf_mercury_orbit = Transform()
  trf_mercury_trans = Transform()
  trf_mercury_trans.translate(1.8, 0.0, 0.0)

  trf_mercury_spin = Transform()

  trf_mercury_geom = Transform()
  trf_mercury_geom.scale(0.18, 0.18, 1.0)
  node_mercury_geom = Node(trf=trf_mercury_geom, apps=[ts_mercury], shps=[disk_shape])
  node_mercury_spin = Node(trf=trf_mercury_spin, nodes=[node_mercury_geom])

  node_mercury_trans = Node(trf=trf_mercury_trans, nodes=[node_mercury_spin]) 
  node_mercury_orbit = Node(trf=trf_mercury_orbit, nodes=[node_mercury_trans])

  # 5. Terra
  trf_earth_orbit = Transform()
  trf_earth_trans = Transform()
  trf_earth_trans.translate(3.5, 0.0, 0.0)

  # Rotação própria da Terra separada
  trf_earth_spin = Transform()
  trf_earth_geom = Transform()
  trf_earth_geom.scale(0.38, 0.38, 1.0)
  node_earth_geom = Node(trf=trf_earth_geom, apps=[ts_earth], shps=[disk_shape])
  node_earth_spin = Node(trf=trf_earth_spin, nodes=[node_earth_geom])

  # 6. Lua (herda a translação da Terra, mas não a rotação no próprio eixo)
  trf_moon_orbit = Transform()
  trf_moon_trans = Transform()
  trf_moon_trans.translate(0.75, 0.0, 0.0)

  trf_moon_geom = Transform()
  trf_moon_geom.scale(0.12, 0.12, 1.0)
  node_moon_geom = Node(trf=trf_moon_geom, apps=[ts_moon], shps=[disk_shape])

  node_moon_trans = Node(trf=trf_moon_trans, nodes=[node_moon_geom])
  node_moon_orbit = Node(trf=trf_moon_orbit, nodes=[node_moon_trans])

  # Montagem da hierarquia da Terra
  node_earth_trans = Node(trf=trf_earth_trans, nodes=[node_earth_spin, node_moon_orbit])
  node_earth_orbit = Node(trf=trf_earth_orbit, nodes=[node_earth_trans])

  # 7. Shader e Pipeline
  shader = Shader(device, "../shaders/2d/shader.wgsl")

  shader.set_vertex_buffers([
    {
      "array_stride": 2 * 4,
      "step_mode": "vertex",
      "attributes": [{"format": "float32x2", "offset": 0, "var_name": "pos"}],
    },
    {
      "array_stride": 2 * 4,
      "step_mode": "vertex",
      "attributes": [{"format": "float32x2", "offset": 0, "var_name": "uv"}],
    },
  ])
  blend = {
    "color": {"src_factor": "src-alpha", "dst_factor": "one-minus-src-alpha", "operation": "add"},
    "alpha": {"src_factor": "one", "dst_factor": "one-minus-src-alpha", "operation": "add"},
  }

  pipeline = Pipeline(shader, target_format, depth_stencil=None, blend=blend)

  # Registra os TextureSets
  shader.add_texture_set(ts_space)
  shader.add_texture_set(ts_sun)
  shader.add_texture_set(ts_mercury)
  shader.add_texture_set(ts_earth)
  shader.add_texture_set(ts_moon)

  # O fundo é colocado primeiro para ser desenhado atrás
  root = Node(pipeline, nodes=[node_bg, node_sun, node_mercury_orbit, node_earth_orbit])

  global scene
  scene = Scene(root)
  scene.add_engine(SolarEngine(
    trf_mercury_orbit, trf_mercury_spin,
    trf_earth_orbit, trf_earth_spin, trf_moon_orbit,
))


def update(dt: float) -> None:
  scene.update(dt)


def draw() -> None:
  global last_t
  t = time.perf_counter()
  update(t - last_t)
  last_t = t

  target_texture = context.get_current_texture()
  renderer.render(target_texture, scene, camera)


def on_key(event: Any) -> None:
  if event["key"] == "q":
    canvas.close()


def main() -> None:
  global canvas, device, context, renderer, last_t

  canvas = RenderCanvas(size=(700, 700), title="Mini-sistema solar 2D", update_mode="continuous", max_fps=60)
  adapter = wgpu.gpu.request_adapter_sync()
  device = adapter.request_device_sync()
  context = canvas.get_context("wgpu")
  target_format = context.get_preferred_format(device.adapter)
  context.configure(device=device, format=target_format)

  renderer = Renderer(device, clear_value=(0.0, 0.0, 0.0, 1.0))

  initialize(device, target_format)

  canvas.add_event_handler(on_key, "key_down")
  last_t = time.perf_counter()
  canvas.request_draw(draw)
  loop.run()


if __name__ == "__main__":
  main()