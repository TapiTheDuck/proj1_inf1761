from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np
import wgpu
from shape import Shape

if TYPE_CHECKING:
    from state import State


class Disk(Shape):
    """Disco 2D aproximado por triângulos em torno da origem (0, 0)."""

    def __init__(self, device: wgpu.GPUDevice, radius: float = 1.0, slices: int = 64) -> None:
        super().__init__()
        self.slices = slices
        self.vertex_count = slices * 3

        positions = []
        texcoords = []

        angles = np.linspace(0, 2 * np.pi, slices, endpoint=False)
        step = 2 * np.pi / slices

        for theta in angles:
            theta_next = theta + step

            # Vértice 0: centro do disco
            p0 = [0.0, 0.0]
            uv0 = [0.5, 0.5]

            # Vértice 1: borda no ângulo atual
            p1 = [radius * np.cos(theta), radius * np.sin(theta)]
            uv1 = [0.5 + 0.5 * np.cos(theta), 0.5 - 0.5 * np.sin(theta)]   # <- sinal trocado no V

            # Vértice 2: borda no próximo ângulo
            p2 = [radius * np.cos(theta_next), radius * np.sin(theta_next)]
            uv2 = [0.5 + 0.5 * np.cos(theta_next), 0.5 - 0.5 * np.sin(theta_next)]   # <- idem
            positions.extend([p0, p1, p2])
            texcoords.extend([uv0, uv1, uv2])

        pos_data = np.array(positions, dtype="float32")
        uv_data = np.array(texcoords, dtype="float32")

        self.vbo_pos: wgpu.GPUBuffer = device.create_buffer_with_data(
            data=pos_data, usage=wgpu.BufferUsage.VERTEX
        )
        self.vbo_uv: wgpu.GPUBuffer = device.create_buffer_with_data(
            data=uv_data, usage=wgpu.BufferUsage.VERTEX
        )

    def draw(self, st: State) -> None:
        first_instance = st.get_shader().commit_matrix(st)
        st.render_pass.set_vertex_buffer(0, self.vbo_pos)
        st.render_pass.set_vertex_buffer(1, self.vbo_uv)
        st.render_pass.draw(self.vertex_count, 1, 0, first_instance)