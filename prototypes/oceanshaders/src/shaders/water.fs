#version 130

uniform sampler2D p3d_Texture0;
uniform sampler2D p3d_Texture1;
uniform sampler2D p3d_Texture2;

uniform vec4 param1;

in vec2 texcoord0;

bool inrange(vec2 v)
{
	return (v.x >=0.0 && v.x <= 1 && v.y >= 0 && v.y <= 1);
}

void main() {
  float vx = 1.0 / param1.x;
  float vy = 1.0 / param1.y;
  float fh = 10;

  vec2 psSimulationTexCoordDelta_x0y1 = vec2(-vx, 0);
  vec2 psSimulationTexCoordDelta_x2y1 = vec2(vx, 0);
  vec2 psSimulationTexCoordDelta_x1y0 = vec2(0, -vy);
  vec2 psSimulationTexCoordDelta_x1y2 = vec2(0, vy);
  float height_x1y1, height_x0y1, height_x2y1, height_x1y0, height_x1y2;
  vec2 x;
  height_x1y1 = texture(p3d_Texture0, texcoord0).x;
  height_x1y1 = (height_x1y1 -0.5) * 2;

  x = texcoord0 + psSimulationTexCoordDelta_x0y1;
  if (inrange(x)) {
    height_x0y1 = texture(p3d_Texture0, x).x;
	height_x0y1 = (height_x0y1 -0.5) * 2;
  } else {
	height_x0y1 = 0;
  }

  x = texcoord0 + psSimulationTexCoordDelta_x2y1;
  if (inrange(x)) {
	height_x2y1 = texture(p3d_Texture0, x).x;
	height_x2y1 = (height_x2y1 -0.5) * 2;
  } else {
	height_x2y1 = 0;
  }

  x = texcoord0 + psSimulationTexCoordDelta_x1y0;
  if (inrange(x)) {
	height_x1y0 = texture(p3d_Texture0, x).x;
	height_x1y0 = (height_x1y0 -0.5) * 2;
  } else {
	height_x1y0 = 0;
  }

  x = texcoord0 + psSimulationTexCoordDelta_x1y2;
  if (inrange(x)) {
	height_x1y2 = texture(p3d_Texture0, x).x;
	height_x1y2 = (height_x1y2 -0.5) * 2;
  } else {
	height_x1y2 = 0;
  }

  float previousHeight = texture(p3d_Texture1, texcoord0).x;
  previousHeight = (previousHeight -0.5) * 2;
  float damp = texture(p3d_Texture2, texcoord0).x;
  float psSimulationWaveSpeedSquared = param1.z; //30;
  float acceleration = damp * psSimulationWaveSpeedSquared * (height_x0y1 + height_x2y1 + height_x1y0 + height_x1y2 - 4.0 * height_x1y1);

  // Do Verlet integration
  vec2 psSimulationPositionWeighting = vec2(1.99,0.99);
  float psSimulationOneHalfTimesDeltaTimeSquared = 0.01;
  float newHeight = psSimulationPositionWeighting.x * height_x1y1 -
              psSimulationPositionWeighting.y * previousHeight +
              psSimulationOneHalfTimesDeltaTimeSquared * acceleration;
  newHeight *= clamp(damp + 0.5, 0.0, 1.0) * param1.w; // 0.99
  newHeight = clamp(newHeight / 2 + 0.5, 0.0, 1.0);

  gl_FragColor.x = newHeight;
  gl_FragColor.y = clamp((height_x2y1 - height_x1y1)/4 + 0.5, 0.0, 1.0);
  gl_FragColor.z = clamp((height_x1y2 - height_x1y1)/4 + 0.5, 0.0, 1.0);
  gl_FragColor.w = 1.0;
}
