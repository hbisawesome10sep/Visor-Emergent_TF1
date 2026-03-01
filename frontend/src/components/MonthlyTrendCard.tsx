import React from 'react';
import { View, Text, StyleSheet, Dimensions } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { formatINRShort } from '../utils/formatters';
import { Accent } from '../utils/theme';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type MonthData = {
  month: string;
  income: number;
  expenses: number;
  savings: number;
};

type Props = {
  data: MonthData[];
  isDark: boolean;
  colors: any;
};

export const MonthlyTrendCard = ({ data, isDark, colors }: Props) => {
  if (!data || data.length === 0) return null;

  const maxValue = Math.max(...data.flatMap(d => [d.income, d.expenses])) || 1;
  const avgSavingsRate = (() => {
    const rates = data.filter(d => d.income > 0).map(d => (d.savings / d.income) * 100);
    if (rates.length === 0) return 0;
    const raw = rates.reduce((s, r) => s + r, 0) / rates.length;
    return Math.max(-100, Math.min(raw, 100)); // Clamp between -100% and 100%
  })();
  
  // Calculate trend
  const recentSavings = data.slice(-3).reduce((s, d) => s + d.savings, 0);
  const olderSavings = data.slice(0, 3).reduce((s, d) => s + d.savings, 0);
  const trend = recentSavings > olderSavings ? 'up' : recentSavings < olderSavings ? 'down' : 'stable';

  const trendColors = {
    up: Accent.emerald,
    down: Accent.ruby,
    stable: Accent.amber,
  };

  const trendIcons = {
    up: 'trending-up',
    down: 'trending-down',
    stable: 'minus',
  };

  const trendLabels = {
    up: 'Improving',
    down: 'Declining',
    stable: 'Stable',
  };

  return (
    <View style={[styles.card, {
      backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
      borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    }]}>
      {/* Header */}
      <View style={styles.header}>
        <View style={{ flex: 1 }}>
          <Text style={[styles.title, { color: colors.textPrimary }]}>Monthly Savings Trend</Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>Last {data.length} months overview</Text>
        </View>
        <View style={[styles.trendBadge, { backgroundColor: `${trendColors[trend]}15` }]}>
          <MaterialCommunityIcons name={trendIcons[trend] as any} size={14} color={trendColors[trend]} />
          <Text style={[styles.trendText, { color: trendColors[trend] }]}>{trendLabels[trend]}</Text>
        </View>
      </View>

      {/* Summary Stats */}
      <View style={styles.statsRow}>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Avg Savings Rate</Text>
          <Text style={[styles.statValue, { color: avgSavingsRate >= 20 ? Accent.emerald : Accent.amber }]}>
            {avgSavingsRate.toFixed(1)}%
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Best Month</Text>
          <Text style={[styles.statValue, { color: Accent.emerald }]}>
            {formatINRShort(Math.max(...data.map(d => d.savings)))}
          </Text>
        </View>
        <View style={styles.statItem}>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>Total Saved</Text>
          <Text style={[styles.statValue, { color: colors.textPrimary }]}>
            {formatINRShort(data.reduce((s, d) => s + d.savings, 0))}
          </Text>
        </View>
      </View>

      {/* Chart */}
      <View style={styles.chartContainer}>
        {data.map((item, index) => {
          const incomeHeight = (item.income / maxValue) * 100;
          const expenseHeight = (item.expenses / maxValue) * 100;
          const savingsRate = item.income > 0 ? Math.max(-100, Math.min((item.savings / item.income) * 100, 100)) : 0;
          
          return (
            <View key={index} style={styles.barGroup}>
              <View style={styles.barsContainer}>
                {/* Income Bar */}
                <View style={[styles.bar, { height: `${incomeHeight}%`, backgroundColor: Accent.emerald }]}>
                  {incomeHeight > 20 && (
                    <Text style={styles.barLabel}>{formatINRShort(item.income)}</Text>
                  )}
                </View>
                {/* Expense Bar */}
                <View style={[styles.bar, { height: `${expenseHeight}%`, backgroundColor: Accent.ruby }]}>
                  {expenseHeight > 20 && (
                    <Text style={styles.barLabel}>{formatINRShort(item.expenses)}</Text>
                  )}
                </View>
              </View>
              <Text style={[styles.monthLabel, { color: colors.textSecondary }]}>{item.month}</Text>
              <Text style={[styles.savingsLabel, { 
                color: savingsRate >= 20 ? Accent.emerald : savingsRate >= 0 ? Accent.amber : Accent.ruby 
              }]}>
                {savingsRate >= 0 ? '+' : ''}{savingsRate.toFixed(0)}%
              </Text>
            </View>
          );
        })}
      </View>

      {/* Legend */}
      <View style={styles.legend}>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: Accent.emerald }]} />
          <Text style={[styles.legendText, { color: colors.textSecondary }]}>Income</Text>
        </View>
        <View style={styles.legendItem}>
          <View style={[styles.legendDot, { backgroundColor: Accent.ruby }]} />
          <Text style={[styles.legendText, { color: colors.textSecondary }]}>Expenses</Text>
        </View>
        <View style={styles.legendItem}>
          <MaterialCommunityIcons name="percent" size={12} color={colors.textSecondary} />
          <Text style={[styles.legendText, { color: colors.textSecondary }]}>Savings Rate</Text>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: { 
    borderRadius: 20, 
    borderWidth: 1, 
    padding: 20, 
    marginBottom: 16,
  },
  header: { 
    flexDirection: 'row', 
    alignItems: 'flex-start', 
    justifyContent: 'space-between', 
    marginBottom: 16,
  },
  title: { 
    fontSize: 18, 
    fontFamily: 'DM Sans', 
    fontWeight: '700' as any,
  },
  subtitle: { 
    fontSize: 12, 
    fontFamily: 'DM Sans', 
    marginTop: 2,
  },
  trendBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 12,
    gap: 4,
  },
  trendText: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(128, 128, 128, 0.15)',
  },
  statItem: {
    alignItems: 'center',
  },
  statLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginBottom: 4,
  },
  statValue: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
  },
  chartContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    alignItems: 'flex-end',
    height: 140,
    marginBottom: 16,
  },
  barGroup: {
    alignItems: 'center',
    flex: 1,
  },
  barsContainer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    height: 100,
    gap: 3,
  },
  bar: {
    width: 14,
    borderRadius: 4,
    minHeight: 4,
    justifyContent: 'flex-end',
    alignItems: 'center',
    paddingBottom: 2,
  },
  barLabel: {
    fontSize: 7,
    color: '#fff',
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    transform: [{ rotate: '-90deg' }],
    width: 40,
    textAlign: 'center',
  },
  monthLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 6,
  },
  savingsLabel: {
    fontSize: 9,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
    marginTop: 2,
  },
  legend: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 20,
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  legendDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  legendText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
  },
});
