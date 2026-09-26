struct Matrix {
    projection: mat4x4<f32>,
};

@group(0) @binding(0) var<storage, read> matrix: array<Matrix>;

@group(1) @binding(0) var tex: texture_2d<f32>;
@group(1) @binding(1) var smp: sampler;

struct VertexOutput {
    @builtin(position) clip_position: vec4f,
    @location(0) uv: vec2f,
};

@vertex
fn vs_main(
    @builtin(instance_index) instance_idx: u32,
    @location(0) pos: vec2f,
    @location(1) uv: vec2f
) -> VertexOutput {
    var out: VertexOutput;
    out.uv = uv;
    out.clip_position = matrix[instance_idx].projection * vec4f(pos, 0.0, 1.0);
    return out;
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4f {
    return textureSample(tex, smp, in.uv);
}