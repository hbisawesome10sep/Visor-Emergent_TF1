import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import Svg, { Path, Defs, LinearGradient, Stop, Line, Text as SvgText, Rect } from 'react-native-svg';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type DataPoint = {
  label: string;
  income: number;
  expenses: number;
};

type Props = {
  data: DataPoint[];
  width?: number;
  height?: number;
  colors: any;
  isDark: boolean;
};

function createPath(points: { x: number; y: number }[], smooth: boolean = true): string {
  if (points.length < 2) return '';

  if (!smooth) {
    return points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ');
  }

  let path = `M ${points[0].x} ${points[0].y}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const curr = points[i];
    const cpx = (prev.x + curr.x) / 2;
    path += ` Q ${prev.x + (curr.x - prev.x) / 4} ${prev.y}, ${cpx} ${(prev.y + curr.y) / 2}`;
    path += ` Q ${curr.x - (curr.x - prev.x) / 4} ${curr.y}, ${curr.x} ${curr.y}`;
  }
  return path;
}

export default function TrendChart({
  data,
  width = SCREEN_WIDTH - 72,
  height = 180,
  colors,
  isDark,
}: Props) {
  const padding = { top: 20, right: 20, bottom: 30, left: 50 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  if (data.length === 0) {
    return (
      <View style={[styles.emptyContainer, { height }]}>
        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>No data available</Text>
      </View>
    );
  }

  const allValues = data.flatMap((d) => [d.income, d.expenses]);
  const maxValue = Math.max(...allValues, 1);
  const minValue = 0;

  const getX = (index: number) => padding.left + (index / (data.length - 1 || 1)) * chartWidth;
  const getY = (value: number) =>
    padding.top + chartHeight - ((value - minValue) / (maxValue - minValue || 1)) * chartHeight;

  const incomePoints = data.map((d, i) => ({ x: getX(i), y: getY(d.income) }));
  const expensePoints = data.map((d, i) => ({ x: getX(i), y: getY(d.expenses) }));

  const incomePath = createPath(incomePoints);
  const expensePath = createPath(expensePoints);

  // Create area paths
  const incomeAreaPath =
    incomePath +
    ` L ${incomePoints[incomePoints.length - 1].x} ${padding.top + chartHeight}` +
    ` L ${incomePoints[0].x} ${padding.top + chartHeight} Z`;
  const expenseAreaPath =
    expensePath +
    ` L ${expensePoints[expensePoints.length - 1].x} ${padding.top + chartHeight}` +
    ` L ${expensePoints[0].x} ${padding.top + chartHeight} Z`;

  // Y-axis labels
  const yLabels = [0, maxValue * 0.25, maxValue * 0.5, maxValue * 0.75, maxValue];

  const formatYLabel = (val: number) => {
    if (val >= 100000) return `₹${(val / 100000).toFixed(0)}L`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(0)}K`;
    return `₹${val.toFixed(0)}`;
  };

  return (
    <View style={styles.container}>
      <Svg width={width} height={height}>
        <Defs>
          <LinearGradient id="incomeGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#10B981" stopOpacity="0.3" />
            <Stop offset="1" stopColor="#10B981" stopOpacity="0.02" />
          </LinearGradient>
          <LinearGradient id="expenseGrad" x1="0" y1="0" x2="0" y2="1">
            <Stop offset="0" stopColor="#EF4444" stopOpacity="0.25" />
            <Stop offset="1" stopColor="#EF4444" stopOpacity="0.02" />
          </LinearGradient>
        </Defs>

        {/* Grid lines */}
        {yLabels.map((val, i) => (
          <Line
            key={`grid-${i}`}
            x1={padding.left}
            y1={getY(val)}
            x2={width - padding.right}
            y2={getY(val)}
            stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'}
            strokeWidth={1}
          />
        ))}

        {/* Y-axis labels */}
        {yLabels.map((val, i) => (
          <SvgText
            key={`ylabel-${i}`}
            x={padding.left - 8}
            y={getY(val) + 4}
            fontSize={10}
            fill={isDark ? '#94A3B8' : '#64748B'}
            textAnchor="end"
          >
            {formatYLabel(val)}
          </SvgText>
        ))}

        {/* X-axis labels */}
        {data.map((d, i) => (
          <SvgText
            key={`xlabel-${i}`}
            x={getX(i)}
            y={height - 8}
            fontSize={10}
            fill={isDark ? '#94A3B8' : '#64748B'}
            textAnchor="middle"
          >
            {d.label}
          </SvgText>
        ))}

        {/* Area fills */}
        <Path d={incomeAreaPath} fill="url(#incomeGrad)" />
        <Path d={expenseAreaPath} fill="url(#expenseGrad)" />

        {/* Lines */}
        <Path d={incomePath} stroke="#10B981" strokeWidth={2.5} fill="none" />
        <Path d={expensePath} stroke="#EF4444" strokeWidth={2.5} fill="none" />

        {/* Data points */}
        {incomePoints.map((p, i) => (
          <React.Fragment key={`inc-point-${i}`}>
            <Rect
              x={p.x - 4}
              y={p.y - 4}
              width={8}
              height={8}
              rx={2}
              fill="#10B981"
            />
          </React.Fragment>
        ))}
        {expensePoints.map((p, i) => (
          <React.Fragment key={`exp-point-${i}`}>
            <Rect
              x={p.x - 4}
              y={p.y - 4}
              width={8}
              height={8}
              rx={2}
              fill="#EF4444"
            />
          </React.Fragment>
        ))}
      </Svg>

      {/* Legend */}
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#10B981' }]} />
          <Text style={[styles.legendText, { color: colors.textSecondary }]}>Income</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: '#EF4444' }]} />
          <Text style={[styles.legendText, { color: colors.textSecondary }]}>Expenses</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
  },
  emptyContainer: {
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    fontFamily: 'Outfit', fontWeight: '500' as any,
  },
  legend: {
    flexDirection: 'row',
    gap: 20,
    marginTop: 8,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendText: {
    fontSize: 12,
    fontFamily: 'Outfit', fontWeight: '500' as any,
  },
});
