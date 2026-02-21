import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../../utils/theme';
import { formatINR, formatINRShort } from '../../utils/formatters';

interface Goal {
  id: string;
  title: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  category: string;
}

interface GoalsSectionProps {
  goals: Goal[];
  colors: any;
  isDark: boolean;
  onAddGoal: () => void;
  onEditGoal: (goal: Goal) => void;
  onDeleteGoal: (id: string, title: string) => void;
}

const getCategoryIcon = (category: string): any => {
  const icons: Record<string, any> = {
    'Safety': 'shield-check',
    'Travel': 'airplane',
    'Purchase': 'cart',
    'Property': 'home',
    'Education': 'school',
    'Retirement': 'beach',
    'Wedding': 'heart',
    'Other': 'star',
  };
  return icons[category] || 'target';
};

const getCategoryColor = (category: string): string => {
  const colors: Record<string, string> = {
    'Safety': Accent.emerald,
    'Travel': Accent.sapphire,
    'Purchase': Accent.amber,
    'Property': '#78716C',
    'Education': Accent.amethyst,
    'Retirement': '#14B8A6',
    'Wedding': '#EC4899',
    'Other': '#6B7280',
  };
  return colors[category] || Accent.sapphire;
};

export const GoalsSection: React.FC<GoalsSectionProps> = ({
  goals,
  colors,
  isDark,
  onAddGoal,
  onEditGoal,
  onDeleteGoal,
}) => {
  const getDaysRemaining = (deadline: string) => {
    const days = Math.ceil((new Date(deadline).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
    if (days < 0) return 'Overdue';
    if (days === 0) return 'Due today';
    if (days === 1) return '1 day left';
    if (days <= 30) return `${days} days left`;
    if (days <= 365) return `${Math.ceil(days / 30)} months left`;
    return `${(days / 365).toFixed(1)} years`;
  };

  return (
    <View data-testid="goals-section" style={styles.section}>
      <View style={styles.sectionHeader}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <View style={[styles.sectionIconWrap, { backgroundColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}>
            <MaterialCommunityIcons name="target" size={18} color={Accent.emerald} />
          </View>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Financial Goals</Text>
        </View>
        <TouchableOpacity
          data-testid="add-goal-btn"
          style={[styles.addBtn, { backgroundColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}
          onPress={onAddGoal}
        >
          <MaterialCommunityIcons name="plus" size={20} color={Accent.emerald} />
        </TouchableOpacity>
      </View>

      {goals.length === 0 ? (
        <View style={[styles.emptyCard, {
          backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
        }]}>
          <MaterialCommunityIcons name="target" size={40} color={colors.textSecondary} />
          <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>No goals yet</Text>
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            Set financial goals to track your progress
          </Text>
        </View>
      ) : (
        <View style={{ gap: 10 }}>
          {goals.map((goal) => {
            const pct = Math.min((goal.current_amount / goal.target_amount) * 100, 100);
            const catColor = getCategoryColor(goal.category);
            const remaining = goal.target_amount - goal.current_amount;

            return (
              <View
                key={goal.id}
                data-testid={`goal-card-${goal.id}`}
                style={[styles.goalCard, {
                  backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.85)',
                  borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                }]}
              >
                <View style={styles.goalHeader}>
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, flex: 1 }}>
                    <View style={[styles.goalIconWrap, { backgroundColor: `${catColor}20` }]}>
                      <MaterialCommunityIcons name={getCategoryIcon(goal.category)} size={18} color={catColor} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.goalTitle, { color: colors.textPrimary }]} numberOfLines={1}>
                        {goal.title}
                      </Text>
                      <Text style={[styles.goalDeadline, { color: colors.textSecondary }]}>
                        {getDaysRemaining(goal.deadline)}
                      </Text>
                    </View>
                  </View>
                  <View style={{ flexDirection: 'row', gap: 6 }}>
                    <TouchableOpacity
                      data-testid={`edit-goal-${goal.id}`}
                      style={[styles.actionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]}
                      onPress={() => onEditGoal(goal)}
                    >
                      <MaterialCommunityIcons name="pencil" size={14} color={colors.textSecondary} />
                    </TouchableOpacity>
                    <TouchableOpacity
                      data-testid={`delete-goal-${goal.id}`}
                      style={[styles.actionBtn, { backgroundColor: 'rgba(239,68,68,0.1)' }]}
                      onPress={() => onDeleteGoal(goal.id, goal.title)}
                    >
                      <MaterialCommunityIcons name="trash-can-outline" size={14} color={Accent.ruby} />
                    </TouchableOpacity>
                  </View>
                </View>

                {/* Progress bar */}
                <View style={[styles.progressBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                  <View style={[styles.progressFill, { width: `${pct}%`, backgroundColor: catColor }]} />
                </View>

                <View style={styles.goalFooter}>
                  <View>
                    <Text style={[styles.goalAmount, { color: catColor }]}>
                      {formatINRShort(goal.current_amount)}
                    </Text>
                    <Text style={[styles.goalLabel, { color: colors.textSecondary }]}>saved</Text>
                  </View>
                  <View style={{ alignItems: 'center' }}>
                    <Text style={[styles.goalPercent, { color: pct >= 100 ? Accent.emerald : colors.textPrimary }]}>
                      {pct.toFixed(0)}%
                    </Text>
                    <Text style={[styles.goalLabel, { color: colors.textSecondary }]}>complete</Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' }}>
                    <Text style={[styles.goalAmount, { color: colors.textPrimary }]}>
                      {formatINRShort(goal.target_amount)}
                    </Text>
                    <Text style={[styles.goalLabel, { color: colors.textSecondary }]}>target</Text>
                  </View>
                </View>
              </View>
            );
          })}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  section: {
    marginBottom: 20,
  },
  sectionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
    paddingHorizontal: 16,
  },
  sectionIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  sectionTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  addBtn: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  emptyCard: {
    marginHorizontal: 16,
    borderRadius: 16,
    padding: 24,
    borderWidth: 1,
    alignItems: 'center',
    gap: 8,
  },
  emptyTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans',
    fontWeight: '600',
    marginTop: 4,
  },
  emptyText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    textAlign: 'center',
  },
  goalCard: {
    marginHorizontal: 16,
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
  },
  goalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  goalIconWrap: {
    width: 36,
    height: 36,
    borderRadius: 10,
    justifyContent: 'center',
    alignItems: 'center',
  },
  goalTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  goalDeadline: {
    fontSize: 11,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
  actionBtn: {
    width: 28,
    height: 28,
    borderRadius: 7,
    justifyContent: 'center',
    alignItems: 'center',
  },
  progressBg: {
    height: 6,
    borderRadius: 3,
    overflow: 'hidden',
    marginBottom: 10,
  },
  progressFill: {
    height: '100%',
    borderRadius: 3,
  },
  goalFooter: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-end',
  },
  goalAmount: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '700',
  },
  goalPercent: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '800',
  },
  goalLabel: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },
});
