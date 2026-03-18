import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, ScrollView, TouchableOpacity } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';

type LoanSplit = {
  id: string; name: string; loan_type: string; lender: string;
  principal_amount: number; interest_rate: number; emi_amount: number;
  principal_paid: number; interest_paid: number; outstanding: number;
  total_interest_lifetime: number; total_cost: number; progress_pct: number;
  remaining_emis: number; tenure_months: number;
};

type Props = { token: string; isDark: boolean; colors: any };

const LOAN_COLORS: Record<string, string> = {
  Home: '#3B82F6', Car: '#10B981', Personal: '#F59E0B',
  Education: '#8B5CF6', 'Credit Card EMI': '#EF4444', Other: '#6B7280',
};

export const PrincipalInterestSplit = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);

  const fetch = useCallback(async () => {
    try {
      const res = await apiRequest('/emi-analytics/overview', { token });
      setData(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetch(); }, [fetch]);

  if (loading) return <ActivityIndicator color={colors.primary} style={{ padding: 24 }} />;
  if (!data || data.loans.length === 0) {
    return (
      <View style={s.empty} data-testid="pi-split-empty">
        <MaterialCommunityIcons name="bank-off" size={40} color={colors.textSecondary} />
        <Text style={[s.emptyText, { color: colors.textSecondary }]}>No active loans found</Text>
        <Text style={[s.emptyHint, { color: colors.textSecondary }]}>Add a loan in Investments to see the split</Text>
      </View>
    );
  }

  const totalPaid = data.total_principal_paid + data.total_interest_paid;
  const principalPct = totalPaid > 0 ? (data.total_principal_paid / totalPaid * 100) : 0;
  const interestPct = totalPaid > 0 ? (data.total_interest_paid / totalPaid * 100) : 0;

  return (
    <View data-testid="pi-split-section">
      {/* Header */}
      <View style={[s.hdr, { backgroundColor: isDark ? 'rgba(59,130,246,0.08)' : 'rgba(59,130,246,0.04)' }]}>
        <MaterialCommunityIcons name="chart-donut" size={20} color="#3B82F6" />
        <Text style={[s.hdrText, { color: colors.textPrimary }]}>Principal vs Interest</Text>
      </View>

      {/* Overall split bar */}
      <View style={s.splitSection}>
        <View style={s.splitRow}>
          <View style={s.splitLabel}>
            <View style={[s.dot, { backgroundColor: '#10B981' }]} />
            <Text style={[s.splitLabelText, { color: colors.textSecondary }]}>Principal</Text>
          </View>
          <Text style={[s.splitAmount, { color: '#10B981' }]}>{formatINRShort(data.total_principal_paid)}</Text>
        </View>
        <View style={s.splitRow}>
          <View style={s.splitLabel}>
            <View style={[s.dot, { backgroundColor: '#EF4444' }]} />
            <Text style={[s.splitLabelText, { color: colors.textSecondary }]}>Interest</Text>
          </View>
          <Text style={[s.splitAmount, { color: '#EF4444' }]}>{formatINRShort(data.total_interest_paid)}</Text>
        </View>

        {/* Stacked bar */}
        <View style={[s.bar, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
          <View style={[s.barPrincipal, { width: `${principalPct}%` }]} />
          <View style={[s.barInterest, { width: `${interestPct}%` }]} />
        </View>
        <View style={s.pctRow}>
          <Text style={[s.pctText, { color: '#10B981' }]}>{principalPct.toFixed(0)}%</Text>
          <Text style={[s.pctText, { color: '#EF4444' }]}>{interestPct.toFixed(0)}%</Text>
        </View>
      </View>

      {/* Summary stats */}
      <View style={[s.statsRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
        <View style={s.stat}>
          <Text style={[s.statLabel, { color: colors.textSecondary }]}>Monthly EMI</Text>
          <Text style={[s.statVal, { color: colors.textPrimary }]}>{formatINRShort(data.total_emi_per_month)}</Text>
        </View>
        <View style={s.stat}>
          <Text style={[s.statLabel, { color: colors.textSecondary }]}>Outstanding</Text>
          <Text style={[s.statVal, { color: '#EF4444' }]}>{formatINRShort(data.total_outstanding)}</Text>
        </View>
        <View style={s.stat}>
          <Text style={[s.statLabel, { color: colors.textSecondary }]}>I:P Ratio</Text>
          <Text style={[s.statVal, { color: '#F59E0B' }]}>{data.interest_to_principal_ratio}x</Text>
        </View>
      </View>

      {/* Per-loan breakdown */}
      <Text style={[s.subhead, { color: colors.textPrimary }]}>Loan Breakdown</Text>
      {data.loans.map((loan: LoanSplit) => {
        const loanColor = LOAN_COLORS[loan.loan_type] || '#6B7280';
        const isExpanded = expanded === loan.id;
        const loanTotalPaid = loan.principal_paid + loan.interest_paid;
        const lPrinPct = loanTotalPaid > 0 ? (loan.principal_paid / loanTotalPaid * 100) : 0;

        return (
          <TouchableOpacity
            key={loan.id}
            onPress={() => setExpanded(isExpanded ? null : loan.id)}
            style={[s.loanCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
            }]}
            data-testid={`loan-card-${loan.id}`}
          >
            <View style={s.loanTop}>
              <View style={[s.loanIcon, { backgroundColor: loanColor + '18' }]}>
                <MaterialCommunityIcons
                  name={loan.loan_type === 'Home' ? 'home' : loan.loan_type === 'Car' ? 'car' : 'cash'}
                  size={18} color={loanColor}
                />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={[s.loanName, { color: colors.textPrimary }]}>{loan.name}</Text>
                <Text style={[s.loanSub, { color: colors.textSecondary }]}>
                  {loan.lender} | {loan.interest_rate}% | {loan.remaining_emis} EMIs left
                </Text>
              </View>
              <Text style={[s.loanEmi, { color: colors.textPrimary }]}>{formatINRShort(loan.emi_amount)}/mo</Text>
            </View>

            {/* Progress bar */}
            <View style={[s.loanBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
              <View style={[s.loanProgress, { width: `${loan.progress_pct}%`, backgroundColor: loanColor }]} />
            </View>
            <Text style={[s.loanPct, { color: colors.textSecondary }]}>{loan.progress_pct}% completed</Text>

            {isExpanded && (
              <View style={[s.expandedSection, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
                <View style={s.expandRow}>
                  <Text style={[s.expandLabel, { color: colors.textSecondary }]}>Principal Paid</Text>
                  <Text style={[s.expandVal, { color: '#10B981' }]}>{formatINRShort(loan.principal_paid)}</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expandLabel, { color: colors.textSecondary }]}>Interest Paid</Text>
                  <Text style={[s.expandVal, { color: '#EF4444' }]}>{formatINRShort(loan.interest_paid)}</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expandLabel, { color: colors.textSecondary }]}>Total Cost (Lifetime)</Text>
                  <Text style={[s.expandVal, { color: colors.textPrimary }]}>{formatINRShort(loan.total_cost)}</Text>
                </View>
                <View style={s.expandRow}>
                  <Text style={[s.expandLabel, { color: colors.textSecondary }]}>Lifetime Interest</Text>
                  <Text style={[s.expandVal, { color: '#EF4444' }]}>{formatINRShort(loan.total_interest_lifetime)}</Text>
                </View>
                {/* Mini P vs I bar for this loan */}
                <View style={[s.bar, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)', marginTop: 8 }]}>
                  <View style={[s.barPrincipal, { width: `${lPrinPct}%` }]} />
                  <View style={[s.barInterest, { width: `${100 - lPrinPct}%` }]} />
                </View>
              </View>
            )}
          </TouchableOpacity>
        );
      })}
    </View>
  );
};

const s = StyleSheet.create({
  empty: { alignItems: 'center', padding: 32, gap: 8 },
  emptyText: { fontSize: 15, fontWeight: '600' },
  emptyHint: { fontSize: 13, textAlign: 'center' },
  hdr: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, marginBottom: 12 },
  hdrText: { fontSize: 15, fontWeight: '700' },
  splitSection: { paddingHorizontal: 4, marginBottom: 16 },
  splitRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 },
  splitLabel: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  splitLabelText: { fontSize: 13, fontWeight: '500' },
  splitAmount: { fontSize: 15, fontWeight: '700' },
  bar: { height: 12, borderRadius: 6, flexDirection: 'row', overflow: 'hidden', marginTop: 8 },
  barPrincipal: { height: '100%', backgroundColor: '#10B981', borderTopLeftRadius: 6, borderBottomLeftRadius: 6 },
  barInterest: { height: '100%', backgroundColor: '#EF4444', borderTopRightRadius: 6, borderBottomRightRadius: 6 },
  pctRow: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  pctText: { fontSize: 11, fontWeight: '600' },
  statsRow: { flexDirection: 'row', justifyContent: 'space-around', borderTopWidth: 1, paddingTop: 14, marginBottom: 16 },
  stat: { alignItems: 'center' },
  statLabel: { fontSize: 11, marginBottom: 4 },
  statVal: { fontSize: 15, fontWeight: '700' },
  subhead: { fontSize: 14, fontWeight: '700', marginBottom: 10, marginTop: 4 },
  loanCard: { borderRadius: 12, borderWidth: 1, padding: 14, marginBottom: 10 },
  loanTop: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  loanIcon: { width: 36, height: 36, borderRadius: 10, alignItems: 'center', justifyContent: 'center' },
  loanName: { fontSize: 14, fontWeight: '600' },
  loanSub: { fontSize: 11, marginTop: 2 },
  loanEmi: { fontSize: 14, fontWeight: '700' },
  loanBar: { height: 6, borderRadius: 3, overflow: 'hidden', marginTop: 10 },
  loanProgress: { height: '100%', borderRadius: 3 },
  loanPct: { fontSize: 11, marginTop: 4 },
  expandedSection: { borderTopWidth: 1, marginTop: 10, paddingTop: 10 },
  expandRow: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 6 },
  expandLabel: { fontSize: 12 },
  expandVal: { fontSize: 13, fontWeight: '600' },
});
