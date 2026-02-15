import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Svg, { G, Path, Circle } from 'react-native-svg';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type DataItem = {
  category: string;
  amount: number;
  color: string;
};

type Props = {
  data: DataItem[];
  size?: number;
  colors: any;
  isDark: boolean;
};

function polarToCartesian(cx: number, cy: number, r: number, angle: number) {
  const rad = ((angle - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(rad),
    y: cy + r * Math.sin(rad),
  };
}

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number) {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;

  return [
    'M', start.x, start.y,
    'A', r, r, 0, largeArcFlag, 0, end.x, end.y,
    'L', cx, cy,
    'Z',
  ].join(' ');
}

export default function PieChart({ data, size = 180, colors, isDark }: Props) {
  const total = data.reduce((sum, item) => sum + item.amount, 0) || 1;
  const cx = size / 2;
  const cy = size / 2;
  const radius = size / 2 - 10;
  const innerRadius = radius * 0.55;

  let currentAngle = 0;
  const slices = data.map((item) => {
    const angle = (item.amount / total) * 360;
    const startAngle = currentAngle;
    const endAngle = currentAngle + angle;
    currentAngle = endAngle;

    return {
      ...item,
      startAngle,
      endAngle,
      percentage: ((item.amount / total) * 100).toFixed(1),
    };
  });

  return (
    <View style={styles.container}>
      <Svg width={size} height={size}>
        <G>
          {slices.map((slice, index) => {
            if (slice.amount === 0) return null;
            const path = describeArc(cx, cy, radius, slice.startAngle, slice.endAngle - 0.5);
            return (
              <Path
                key={`${slice.category}-${index}`}
                d={path}
                fill={slice.color}
                strokeWidth={2}
                stroke={isDark ? 'rgba(15, 23, 42, 0.8)' : 'rgba(255,255,255,0.8)'}
              />
            );
          })}
          {/* Inner circle for donut effect */}
          <Circle
            cx={cx}
            cy={cy}
            r={innerRadius}
            fill={isDark ? 'rgba(30, 41, 59, 0.95)' : 'rgba(255,255,255,0.95)'}
          />
        </G>
      </Svg>

      {/* Center text */}
      <View style={[styles.centerText, { top: cy - 20, left: cx - 40 }]}>
        <Text style={[styles.totalLabel, { color: colors.textSecondary }]}>Total</Text>
        <Text style={[styles.totalAmount, { color: colors.textPrimary }]}>
          ₹{total >= 100000 ? `${(total / 100000).toFixed(1)}L` : `${(total / 1000).toFixed(0)}K`}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'relative',
    alignItems: 'center',
    justifyContent: 'center',
  },
  centerText: {
    position: 'absolute',
    width: 80,
    alignItems: 'center',
  },
  totalLabel: {
    fontSize: 11,
    fontWeight: '500',
  },
  totalAmount: {
    fontSize: 16,
    fontWeight: '800',
    marginTop: 2,
  },
});
