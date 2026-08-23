// Fragment shader for the selected-wallpaper shimmer border.
//
// The rounded-rect border, the perimeter position of each fragment and the
// travelling gaussian glow band are all computed analytically per pixel, so
// the whole effect runs on the GPU. The CPU only updates the u_head uniform
// once per animation tick (no QPainter repaints, no software shadowBlur).
//
// Vulkan-style GLSL. Compile to the .qsb package consumed by ShaderEffect
// with the qsb tool (qt6-shadertools), or simply run:
//     ./scripts/build_shaders.sh

#version 440

layout(location = 0) in vec2 qt_TexCoord0;
layout(location = 0) out vec4 fragColor;

// The default vertex shader expects qt_Matrix at offset 0 and qt_Opacity at
// offset 64; custom uniforms must follow them (std140 layout).
layout(std140, binding = 0) uniform buf {
    mat4 qt_Matrix;
    float qt_Opacity;
    float u_head;          // head position along the perimeter, 0..1 (loops)
    float u_radius;        // corner radius in px
    float u_bandFraction;  // band width as a fraction of the perimeter
    float u_bandSharpness; // gaussian peak of the band
    float u_coreWidth;     // core line width in px
    float u_coreOpacity;   // peak opacity of the core stroke
    float u_glowBlur;      // gaussian sigma of the glow in px
    float u_lightCount;    // number of bands travelling the loop
    float u_inset;         // border inset from the effect edges in px
    vec2 u_size;           // effect size in px
    vec4 u_color;          // glow color (premultiplied, alpha = 1.0)
};

const float PI = 3.141592653589793;

void main() {
    // Top-left origin pixel coordinates (scene graph textures are top-left).
    vec2 p = qt_TexCoord0 * u_size;

    float w = u_size.x - u_inset * 2.0;
    float h = u_size.y - u_inset * 2.0;
    float r = u_radius;

    // Rounded-rect SDF: negative inside, positive outside, 0 on the border.
    vec2 q = abs(p - u_size * 0.5) - (vec2(w, h) * 0.5 - r);
    float sd = length(max(q, 0.0)) + min(max(q.x, q.y), 0.0) - r;

    // Early-out: nothing to draw far from the border.
    if (abs(sd) > u_glowBlur * 3.0 + u_coreWidth) {
        fragColor = vec4(0.0);
        return;
    }

    float topLen = max(w - 2.0 * r, 0.0);
    float sideLen = max(h - 2.0 * r, 0.0);
    float corner = PI * r * 0.5;
    float perimeter = 2.0 * topLen + 2.0 * sideLen + 4.0 * corner;
    if (perimeter <= 0.0) {
        fragColor = vec4(0.0);
        return;
    }

    // Arc length along the rounded-rect boundary (0..perimeter), starting at
    // the top-left and going clockwise. Straight edges are linear, corners
    // are arc lengths via atan(y, x).
    float d;
    if (p.y <= u_inset + r) {
        if (p.x <= u_inset + r) {
            // Top-left corner.
            d = 2.0 * topLen + 2.0 * sideLen + 3.0 * corner
                + (atan(p.y - (u_inset + r), p.x - (u_inset + r)) + PI) * r;
        } else if (p.x >= u_inset + w - r) {
            // Top-right corner.
            d = topLen + (atan(p.y - (u_inset + r), p.x - (u_inset + w - r)) + PI * 0.5) * r;
        } else {
            // Top edge.
            d = p.x - (u_inset + r);
        }
    } else if (p.y >= u_inset + h - r) {
        if (p.x <= u_inset + r) {
            // Bottom-left corner.
            d = 2.0 * topLen + 2.0 * sideLen + 3.0 * corner
                + (atan(p.y - (u_inset + h - r), p.x - (u_inset + r)) - PI * 0.5) * r;
        } else if (p.x >= u_inset + w - r) {
            // Bottom-right corner.
            d = topLen + corner + sideLen
                + atan(p.y - (u_inset + h - r), p.x - (u_inset + w - r)) * r;
        } else {
            // Bottom edge (travels right to left).
            d = topLen + 2.0 * corner + sideLen + (u_inset + w - r - p.x);
        }
    } else if (p.x >= u_inset + w - r) {
        // Right edge.
        d = topLen + corner + (p.y - (u_inset + r));
    } else {
        // Left edge (travels bottom to top).
        d = 2.0 * topLen + 2.0 * corner + sideLen + (u_inset + h - r - p.y);
    }

    // Gaussian band weight: max over all travelling lights, evenly spaced
    // around the loop. The modulo wrap keeps the loop perfectly continuous.
    float bandLen = perimeter * u_bandFraction;
    float band = 0.0;
    for (int n = 0; n < 8; n++) {
        if (float(n) >= u_lightCount) break;
        float center = fract(u_head + float(n) / u_lightCount) * perimeter;
        float delta = d - center;
        delta -= perimeter * floor(delta / perimeter + 0.5);
        float t = delta / bandLen + 0.5;
        if (t < 0.0 || t > 1.0) continue;
        float x = (t - 0.5) * 2.0 * u_bandSharpness;
        band = max(band, exp(-x * x));
    }

    // Core line + soft gaussian glow (replaces the old software shadowBlur).
    float core = smoothstep(u_coreWidth * 0.5, 0.0, abs(sd)) * u_coreOpacity;
    float glow = exp(-(sd * sd) / (2.0 * u_glowBlur * u_glowBlur)) * 0.85;

    float alpha = band * (core + glow) * u_color.a;
    // Premultiplied output, as required by ShaderEffect.
    fragColor = vec4(u_color.rgb * alpha, alpha) * qt_Opacity;
}
