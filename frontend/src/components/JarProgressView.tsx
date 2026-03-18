/**
 * JarProgressView — Old-school money collection jar with liquid fill
 * Uses SVG ClipPath for smooth percentage-based fill visualization
 */
import React from 'react';
import Svg, { Path, Rect, Defs, ClipPath, Text as SvgText, G } from 'react-native-svg';

type Props = {
  percentage: number;
  color: string;
  uid: string;
  width?: number;
  showLabel?: boolean;
  bgColor?: string;
};

// Fixed coordinate space (66 x 96)
const VB_W = 66;
const VB_H = 96;

// Jar body starts (below lid/neck shoulder) and ends (before bottom curve)
const BODY_TOP = 29;   // where body starts (after neck shoulder)
const BODY_BOTTOM = 91; // where liquid fill maxes out

// Jar path in fixed coordinates:
// Lid (cap) at top, narrow neck, wide body, rounded bottom
const JAR_PATH = `M 10,1 H 56 Q 60,1 60,5 V 9 Q 60,13 56,13 H 50 C 50,20 62,23 62,29 V 82 Q 62,95 33,95 Q 4,95 4,82 V 29 C 4,23 16,20 16,13 H 10 Q 6,13 6,9 V 5 Q 6,1 10,1 Z`;

// Lid outline only (for contrasting lid cap)
const LID_PATH = `M 10,1 H 56 Q 60,1 60,5 V 9 Q 60,13 56,13 H 10 Q 6,13 6,9 V 5 Q 6,1 10,1 Z`;

export const JarProgressView: React.FC<Props> = ({
  percentage,
  color,
  uid,
  width = 56,
  showLabel = true,
  bgColor,
}) => {
  const height = Math.round(width * (VB_H / VB_W));
  const pct = Math.min(100, Math.max(0, percentage));

  // Fill calculation — fills from bottom up within body area
  const bodyHeight = BODY_BOTTOM - BODY_TOP; // 62 units
  const fillHeight = bodyHeight * (pct / 100);
  const fillY = BODY_BOTTOM - fillHeight;

  const clipId = `jar-clip-${uid}`;
  const lidClipId = `lid-clip-${uid}`;

  return (
    <Svg
      width={width}
      height={height}
      viewBox={`0 0 ${VB_W} ${VB_H}`}
    >
      <Defs>
        {/* Clip to full jar shape */}
        <ClipPath id={clipId}>
          <Path d={JAR_PATH} />
        </ClipPath>
        {/* Clip to lid only */}
        <ClipPath id={lidClipId}>
          <Path d={LID_PATH} />
        </ClipPath>
      </Defs>

      {/* Jar background (transparent glass look) */}
      <Path
        d={JAR_PATH}
        fill={bgColor || 'rgba(255,255,255,0.04)'}
        stroke={color}
        strokeWidth={1.8}
        strokeOpacity={0.45}
      />

      {/* Liquid fill - rises from bottom */}
      {pct > 0 && (
        <G clipPath={`url(#${clipId})`}>
          {/* Main fill body */}
          <Rect
            x={0}
            y={fillY}
            width={VB_W}
            height={fillHeight + 6}
            fill={color}
            opacity={0.55}
          />
          {/* Shine highlight on liquid surface */}
          {fillHeight > 8 && (
            <Rect
              x={12}
              y={fillY + 2}
              width={10}
              height={Math.min(18, fillHeight - 6)}
              rx={4}
              fill="rgba(255,255,255,0.18)"
            />
          )}
          {/* Subtle bubbles effect for full jar */}
          {pct > 80 && (
            <>
              <Rect x={20} y={fillY + 4} width={5} height={5} rx={2.5} fill="rgba(255,255,255,0.12)" />
              <Rect x={40} y={fillY + 8} width={4} height={4} rx={2} fill="rgba(255,255,255,0.1)" />
            </>
          )}
        </G>
      )}

      {/* Lid cap tint (slightly lighter to look like a real jar lid) */}
      <Path
        d={LID_PATH}
        fill={color}
        opacity={0.2}
        stroke={color}
        strokeWidth={1.5}
        strokeOpacity={0.6}
      />

      {/* Percentage label in the body */}
      {showLabel && (
        <SvgText
          x={VB_W / 2}
          y={BODY_TOP + (BODY_BOTTOM - BODY_TOP) * 0.58}
          textAnchor="middle"
          fontSize={11}
          fontWeight="bold"
          fill={pct > 55 ? 'rgba(255,255,255,0.9)' : color}
          fillOpacity={0.95}
        >
          {`${Math.round(pct)}%`}
        </SvgText>
      )}
    </Svg>
  );
};
