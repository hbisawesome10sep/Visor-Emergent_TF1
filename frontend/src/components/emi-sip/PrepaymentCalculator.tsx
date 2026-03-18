import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort, formatINR } from '../../utils/formatters';

type Loan = { id: string; name: string; outstanding: number; emi_amount: number; interest_rate: number; remaining_emis: number };
type Props = { token: string; isDark: boolean; colors: any };

export const PrepaymentCalculator = ({ token, isDark, colors }: Props) => {
  const [loans, setLoans] = useState<Loan[]>([]);
  const [selectedLoan, setSelectedLoan] = useState('');
  const [amount, setAmount] = useState('');
  const [reduceType, setReduceType] = useState<'tenure' | 'emi'>('tenure');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [calculating, setCalculating] = useState(false);

  const fetchLoans = useCallback(async () => {
    try {
      const res = await apiRequest('/emi-analytics/overview', { token });
      setLoans(res.loans || []);
      if (res.loans?.length > 0) setSelectedLoan(res.loans[0].id);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token]);

  useEffect(() => { fetchLoans(); }, [fetchLoans]);

  const calculate = async () => {
    if (!selectedLoan || !amount) return;
    setCalculating(true);
    try {
      const res = await apiRequest('/emi-analytics/prepayment', {
        token, method: 'POST',
        body: { loan_id: selectedLoan, prepayment_amount: parseFloat(amount), reduce_type: reduceType },
      });
      setResult(res);
    } catch (e) { console.warn(e); }
    finally { setCalculating(false); }
  };

  if (loading) return <ActivityIndicator color={colors.primary} style={{ padding: 24 }} />;
  if (loans.length === 0) {
    return (
      <View style={s.empty} data-testid="prepayment-empty">
        <MaterialCommunityIcons name="calculator-variant-outline" size={40} color={colors.textSecondary} />
        <Text style={[s.emptyText, { color: colors.textSecondary }]}>No loans to calculate prepayment</Text>
      </View>
    );
  }

  return (
    <View data-testid="prepayment-calculator">
      <View style={[s.hdr, { backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(16,185,129,0.04)' }]}>
        <MaterialCommunityIcons name="calculator" size={20} color="#10B981" />
        <Text style={[s.hdrText, { color: colors.textPrimary }]}>Prepayment Calculator</Text>
      </View>

      <Text style={[s.desc, { color: colors.textSecondary }]}>
        See how much you can save by making a lump-sum prepayment on your loan.
      </Text>

      {/* Loan selector */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.scroll}>
        {loans.map(l => (
          <TouchableOpacity
            key={l.id}
            style={[s.chip, {
              backgroundColor: selectedLoan === l.id ? '#10B98120' : isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
              borderColor: selectedLoan === l.id ? '#10B981' : 'transparent',
            }]}
            onPress={() => { setSelectedLoan(l.id); setResult(null); }}
            data-testid={`loan-select-${l.id}`}
          >
            <Text style={[s.chipText, { color: selectedLoan === l.id ? '#10B981' : colors.textSecondary }]}>
              {l.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      {/* Amount input */}
      <View style={[s.inputBox, {
        backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)',
        borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
      }]}>
        <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Prepayment Amount (Rs)</Text>
        <TextInput
          style={[s.input, { color: colors.textPrimary }]}
          value={amount}
          onChangeText={(v) => { setAmount(v); setResult(null); }}
          keyboardType="numeric"
          placeholder="500000"
          placeholderTextColor={colors.textSecondary}
          data-testid="prepayment-amount-input"
        />
      </View>

      {/* Reduce type toggle */}
      <View style={s.toggleRow}>
        <TouchableOpacity
          style={[s.toggle, {
            backgroundColor: reduceType === 'tenure' ? '#10B98118' : isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
            borderColor: reduceType === 'tenure' ? '#10B981' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          }]}
          onPress={() => { setReduceType('tenure'); setResult(null); }}
          data-testid="reduce-tenure-btn"
        >
          <MaterialCommunityIcons name="calendar-minus" size={16} color={reduceType === 'tenure' ? '#10B981' : colors.textSecondary} />
          <Text style={[s.toggleText, { color: reduceType === 'tenure' ? '#10B981' : colors.textSecondary }]}>Reduce Tenure</Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[s.toggle, {
            backgroundColor: reduceType === 'emi' ? '#3B82F618' : isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
            borderColor: reduceType === 'emi' ? '#3B82F6' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          }]}
          onPress={() => { setReduceType('emi'); setResult(null); }}
          data-testid="reduce-emi-btn"
        >
          <MaterialCommunityIcons name="currency-inr" size={16} color={reduceType === 'emi' ? '#3B82F6' : colors.textSecondary} />
          <Text style={[s.toggleText, { color: reduceType === 'emi' ? '#3B82F6' : colors.textSecondary }]}>Reduce EMI</Text>
        </TouchableOpacity>
      </View>

      {/* Calculate button */}
      <TouchableOpacity
        style={[s.btn, { opacity: (!amount || calculating) ? 0.5 : 1 }]}
        onPress={calculate}
        disabled={!amount || calculating}
        data-testid="calculate-prepayment-btn"
      >
        {calculating ? <ActivityIndicator color="#fff" size="small" /> : (
          <Text style={s.btnText}>Calculate Savings</Text>
        )}
      </TouchableOpacity>

      {/* Results */}
      {result && (
        <View style={[s.resultCard, {
          backgroundColor: isDark ? 'rgba(16,185,129,0.06)' : 'rgba(16,185,129,0.03)',
          borderColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.12)',
        }]} data-testid="prepayment-result">
          <Text style={[s.resultTitle, { color: colors.textPrimary }]}>
            {result.loan_name} - Prepayment Impact
          </Text>

          {/* Savings highlight */}
          <View style={[s.savingsBox, { backgroundColor: '#10B98115' }]}>
            <MaterialCommunityIcons name="piggy-bank" size={24} color="#10B981" />
            <View>
              <Text style={[s.savingsLabel, { color: colors.textSecondary }]}>Interest Saved</Text>
              <Text style={s.savingsAmount}>{formatINRShort(result.interest_saved)}</Text>
            </View>
            {result.tenure_saved_months > 0 && (
              <View style={{ marginLeft: 'auto', alignItems: 'flex-end' }}>
                <Text style={[s.savingsLabel, { color: colors.textSecondary }]}>Tenure Saved</Text>
                <Text style={s.tenureSaved}>{result.tenure_saved_months} months</Text>
              </View>
            )}
          </View>

          {/* Comparison table */}
          <View style={s.compRow}>
            <Text style={[s.compHeader, { color: colors.textSecondary, flex: 1.5 }]}></Text>
            <Text style={[s.compHeader, { color: colors.textSecondary }]}>Before</Text>
            <Text style={[s.compHeader, { color: '#10B981' }]}>After</Text>
          </View>
          {[
            { label: 'EMI', before: formatINRShort(result.original_emi), after: formatINRShort(result.new_emi) },
            { label: 'Tenure', before: `${result.original_tenure_months} mo`, after: `${result.new_tenure_months} mo` },
            { label: 'Total Interest', before: formatINRShort(result.original_total_interest), after: formatINRShort(result.new_total_interest) },
            { label: 'Total Paid', before: formatINRShort(result.original_total_paid), after: formatINRShort(result.new_total_paid) },
          ].map((row, i) => (
            <View key={i} style={[s.compRow, { borderTopWidth: 1, borderTopColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' }]}>
              <Text style={[s.compLabel, { color: colors.textSecondary }]}>{row.label}</Text>
              <Text style={[s.compVal, { color: colors.textSecondary }]}>{row.before}</Text>
              <Text style={[s.compVal, { color: '#10B981', fontWeight: '700' }]}>{row.after}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  empty: { alignItems: 'center', padding: 32, gap: 8 },
  emptyText: { fontSize: 15, fontWeight: '600' },
  hdr: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, marginBottom: 8 },
  hdrText: { fontSize: 15, fontWeight: '700' },
  desc: { fontSize: 13, marginBottom: 12, paddingHorizontal: 4 },
  scroll: { marginBottom: 12 },
  chip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, borderWidth: 1, marginRight: 8 },
  chipText: { fontSize: 12, fontWeight: '600' },
  inputBox: { borderWidth: 1, borderRadius: 10, padding: 12, marginBottom: 12 },
  inputLabel: { fontSize: 11, marginBottom: 4 },
  input: { fontSize: 18, fontWeight: '600', padding: 0 },
  toggleRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  toggle: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: 6, paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10, borderWidth: 1 },
  toggleText: { fontSize: 13, fontWeight: '600' },
  btn: { backgroundColor: '#10B981', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 16 },
  btnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  resultCard: { borderRadius: 12, borderWidth: 1, padding: 16 },
  resultTitle: { fontSize: 14, fontWeight: '700', marginBottom: 12 },
  savingsBox: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 10, marginBottom: 14 },
  savingsLabel: { fontSize: 11 },
  savingsAmount: { fontSize: 20, fontWeight: '800', color: '#10B981' },
  tenureSaved: { fontSize: 16, fontWeight: '700', color: '#3B82F6' },
  compRow: { flexDirection: 'row', paddingVertical: 8 },
  compHeader: { flex: 1, fontSize: 11, fontWeight: '600', textAlign: 'center' },
  compLabel: { flex: 1.5, fontSize: 12 },
  compVal: { flex: 1, fontSize: 13, fontWeight: '600', textAlign: 'center' },
});
