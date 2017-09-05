/*
Comments:
	Simple ocean shader with animated bump map and geometric waves
	Based partly on "Effective Water Simulation From Physical Models", GPU Gems

11 Aug 05: heavily modified by Jeff Doyle (nfz) for Ogre
Mar 2009: Ported to Panda3D by clcheung
Aug 2017: translated to GLSL and improved by Ákos Sülyi
*/

#version 130

uniform sampler2D p3d_Texture0;
uniform sampler2D p3d_Texture1;
uniform samplerCube p3d_Texture2;

uniform vec4 param3;
uniform vec4 param4;
uniform vec4 deepColor;
uniform vec4 shallowColor;
uniform vec4 reflectionColor;
uniform int pass;

// Input from vertex shader
in vec4 texcoord0;
in vec4 eyeVector;
in vec3 binormalVector;
in vec3 tangentVector;
in vec3 normalVector;
in vec4 bumpCoord01;
in vec4 bumpCoord23;
in float z;

out vec4 colour;
out vec4 height;

void main() {
    vec4 t0 = texture(p3d_Texture1, bumpCoord01.xy) * 2.0 - 1.0;
    vec4 t1 = texture(p3d_Texture1, bumpCoord01.zw) * 2.0 - 1.0;
    vec4 t2 = texture(p3d_Texture1, bumpCoord23.xy) * 2.0 - 1.0;
    vec3 N = t0.xyz + t1.xyz + t2.xyz;

    mat3 m; // tangent to world matrix
    m[0] = binormalVector;
    m[1] = tangentVector;
    m[2] = normalVector;

    N = normalize(N * m);
    vec3 E = normalize(eyeVector.xyz);
    float reflectionAmount = param3.x;
    float waterAmount = param3.y;
    float cubemap = param3.w;
    float fresnelPower = param4.x; //5.0;
    float fresnelBias = param4.y; //0.328;
    float hdrMultiplier = param4.z; //0.471;
    float reflectionBlur = param4.w; //0.0;

    float facing = 1.0 - max((dot(-E, N)), 0.0);

    // reflection
    vec4 reflection;
    if (cubemap > 0.0) {
        vec3 R = reflect(E, N);

        reflection = textureCube(p3d_Texture2, R, reflectionBlur);
        //cheap hdr effect
        reflection.rgb *= (reflection.r + reflection.g + reflection.b) * hdrMultiplier;
    } else {
        vec4 distortion = texture(p3d_Texture1, N.xy);
        reflection = texture2DProj(p3d_Texture0, texcoord0 + distortion);

        //cheap hdr effect
        reflection.rgb *= (reflection.r + reflection.g + reflection.b) * hdrMultiplier;
        reflection.rgb *= 1.0 - facing;
    }

    float fresnel = clamp(fresnelBias + pow(facing, fresnelPower), 0.0, 1.0);
    vec4 waterColor = mix(shallowColor, deepColor, facing) * waterAmount;
    reflection = mix(waterColor,  reflection * reflectionColor, fresnel) * reflectionAmount;

    colour = waterColor + reflection;
    // colour = waterColor + reflection;

    /*	try clipping */
    float edge = pow(bumpCoord23.z - 0.5, 2.0) + pow(bumpCoord23.w - 0.5, 2.0);
    if (edge >= 0.22) {
        if (edge >= 0.25)
            colour.a = 0.0;
        else
            colour.a = (0.25 - edge) / 0.03;
    }

    height = vec4(z, 0.0, 0.0, 1.0);
}