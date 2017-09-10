/*
Comments:
	Simple ocean shader with animated bump map and geometric waves
	Based partly on "Effective Water Simulation From Physical Models", GPU Gems
	and
	A vertex texture shader, based on Vertex Texture Fetch Water demo in NVIDIA SDK 9.5

11 Aug 05: heavily modified by Jeff Doyle (nfz) for Ogre
Mar 2009: Ported to Panda3D by clcheung
Aug 2017: translated to GLSL and improved by Ákos Sülyi
*/

#version 130

struct Wave {
  float freq;  // 2 * PI / wavelength
  float amp;   // amplitude
  float phase; // speed * 2 * PI / wavelength
  vec2 dir;
};

// Vertex inputs
in vec4 p3d_Vertex;
in vec2 p3d_MultiTexCoord1;
in vec2 p3d_MultiTexCoord4;

// Uniform inputs
uniform mat4 p3d_ModelViewProjectionMatrix;

uniform sampler2D vtftex;

uniform float time;
uniform vec4 waveInfo;
uniform vec4 param2;
uniform vec4 speed;
uniform vec4 eyePosition;
uniform vec4 gridRatio;

// Output to fragment shader
out vec4 texcoord0;
out vec4 eyeVector;
out vec3 binormal;
out vec3 tangent;
out vec3 normal;
out vec4 bumpCoord01;
out vec4 bumpCoord23;
out float z;

void main() {
    #define NWAVES 2
	Wave wave[NWAVES] = Wave[NWAVES](
		Wave(1.0, 1.0, 0.5, vec2(-2, 0)),
		Wave(2.0, 0.5, 1.7, vec2(-0.7, 0.7))
	);
    wave[0].freq = waveInfo.x;
    wave[0].amp = waveInfo.y;
	wave[0].dir = speed.xy;

    wave[1].freq = waveInfo.x * 1.33;
    wave[1].amp = waveInfo.y * 0.75;
	wave[1].dir = speed.zw;

    vec4 position = p3d_Vertex;

    // applying texture deformation
    vec4 simulationSample = texture(vtftex, p3d_MultiTexCoord4);
	position.z = (simulationSample.x - 0.5) * gridRatio.w;
    vec3 dzdx = vec3(gridRatio.x, 0.0,  (simulationSample.y - 0.5) * 4.0 * gridRatio.z);
    vec3 dzdy = vec3(0.0, gridRatio.y, (simulationSample.z - 0.5) * 4.0 * gridRatio.z);
    vec3 dd = normalize(cross(dzdx, dzdy));
    vec3 cc = vec3(1.0, 1.0, 0.0);

	// sum waves
	vec3 displacement = vec3(0.0, 0.0, 0.0);
	float q = waveInfo.w / float(NWAVES);
	vec2 dir;
	float angle, sin_a, cos_a, qi, wa;
	float ci, ki;

    for(int i = 0; i < NWAVES; i++)
	{
	    dir = normalize(wave[i].dir);
	    angle = dot(dir, position.xy) * wave[i].freq + time * wave[i].phase * length(wave[i].dir);
		sin_a = sin(angle);
		cos_a = cos(angle);

		// calculate derivate of wave function
        wa = wave[i].freq * wave[i].amp;
	    qi = q / wa;
		ci = q * sin_a;
		ki = wa * cos_a;

		cc -= vec3(ci * dir.x * dir.x, ci * dir.y * dir.y, ci * dir.x * dir.y);
		dd -= vec3(ki * dir.x, ki * dir.y, ci);

        // calculate wave function
        displacement.x += qi * wave[i].amp *  dir.x * cos_a;
        displacement.y += qi * wave[i].amp *  dir.y * cos_a;
		displacement.z += wave[i].amp * sin_a;
	}
	
	position.xyz += displacement;
	z = position.z / (2.0 * 1.75 * waveInfo.y + 0.2) + 0.5;

	float BumpScale = waveInfo.z;
	binormal.xyz = BumpScale * normalize(vec3(cc.x, cc.z, -dd.y)); // Binormal
	tangent.xyz = BumpScale * normalize(vec3(cc.z, cc.y, -dd.x)); // Tangent
	normal.xyz = normalize(dd); // Normal

    vec2 bumpSpeed = param2.xy;
	vec2 textureScale = param2.zw;

	// calculate texture coordinates for normal map lookup
	bumpCoord01.xy = p3d_MultiTexCoord1.xy * textureScale + time * bumpSpeed;
	bumpCoord01.zw = p3d_MultiTexCoord1.xy * textureScale * 2.0 + time * bumpSpeed * 4.0;
	bumpCoord23.xy = p3d_MultiTexCoord1.xy * textureScale * 4.0 + time * bumpSpeed * 8.0;
	bumpCoord23.zw = p3d_MultiTexCoord1.xy;

	// transform vertex position by combined view projection matrix
    gl_Position = p3d_ModelViewProjectionMatrix * position;

    eyeVector = position - eyePosition;

    // projective matrix (MR)
    mat4 scaleMatrix = mat4(1.0f, 0.0f, 0.0f, 0.0f,
   	                        0.0f, 1.0f, 0.0f, 0.0f,
   	                        0.0f, 0.0f, 1.0f, 0.0f,
   	                        1.0f, 1.0f, 1.0f, 2.0f );
   	mat4 matMR = scaleMatrix * p3d_ModelViewProjectionMatrix;
	texcoord0 =  matMR * position;
}