import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';

type Props = { token: string; isDark: boolean; colors: any; cards: any[] };

const fmtINR = (n: number) => n >= 100000 ? `Rs ${(n / 100000).toFixed(2)}L` : `Rs ${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;

export const InterestCalculator = ({ token, isDark, colors, cards }: Props) => {
  const [amount, setAmount] = useState('50000');
  const [rate, setRate] = useState('3.49');
  const [selectedCard, setSelectedCard] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const calculate = async () => {
    setLoading(true);
    try {
      const res = await apiRequest('/credit-cards/interest-calculator', {
        token,
        method: 'POST',
        body: {
          outstanding: parseFloat(amount) || 0,
          monthly_rate: parseFloat(rate) || 3.49,
          card_id: selectedCard,
        },
      });
      setResult(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  };

  return (
    <View testID="cc-interest-calculator">
      <View style={[s.header, { backgroundColor: isDark ? 'rgba(245,158,11,0.08)' : 'rgba(245,158,11,0.04)' }]}>
        <MaterialCommunityIcons name="calculator-variant" size={20} color="#F59E0B" />
        <Text style={[s.headerText, { color: colors.textPrimary }]}>Interest Calculator</Text>
      </View>

      <Text style={[s.desc, { color: colors.textSecondary }]}>
        See how much interest you'd pay if you only pay the minimum due amount each month.
      </Text>

      {/* Card Selection */}
      {cards.length > 0 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.cardScroll}>
          {cards.map(c => (
            <TouchableOpacity
              key={c.id}
              style={[s.cardChip, {
                backgroundColor: selectedCard === c.id ? '#F59E0B20' : isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                borderColor: selectedCard === c.id ? '#F59E0B' : 'transparent',
              }]}
              onPress={() => setSelectedCard(selectedCard === c.id ? '' : c.id)}
            >
              <Text style={[s.cardChipText, { color: selectedCard === c.id ? '#F59E0B' : colors.textSecondary }]}>
                {c.card_name} ({c.last_four})
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      )}

      <View style={s.inputRow}>
        <View style={[s.inputBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Outstanding (Rs)</Text>
          <TextInput
            style={[s.input, { color: colors.textPrimary }]}
            value={amount}
            onChangeText={setAmount}
            keyboardType="numeric"
            placeholder="50000"
            placeholderTextColor={colors.textSecondary}
          />
        </View>
        <View style={[s.inputBox, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Monthly Rate (%)</Text>
          <TextInput
            style={[s.input, { color: colors.textPrimary }]}
            value={rate}
            onChangeText={setRate}
            keyboardType="numeric"
            placeholder="3.49"
            placeholderTextColor={colors.textSecondary}
          />
        </View>
      </View>

      <TouchableOpacity testID="calc-interest-btn" style={s.calcBtn} onPress={calculate} disabled={loading}>
        {loading ? <ActivityIndicator size="small" color="#fff" /> : (
          <>
            <MaterialCommunityIcons name="calculator" size={18} color="#fff" />
            <Text style={s.calcBtnText}>Calculate</Text>
          </>
        )}
      </TouchableOpacity>

      {result?.summary && (
        <View style={[s.resultCard, { backgroundColor: isDark ? 'rgba(239,68,68,0.08)' : 'rgba(239,68,68,0.04)', borderColor: isDark ? 'rgba(239,68,68,0.2)' : 'rgba(239,68,68,0.1)' }]}>
          <Text style={[s.resultTitle, { color: '#EF4444' }]}>
            <MaterialCommunityIcons name="alert-circle" size={16} /> Minimum Payment Trap
          </Text>

          <View style={s.resultGrid}>
            <View style={s.resultItem}>
              <Text style={[s.resultLabel, { color: colors.textSecondary }]}>Original Amount</Text>
              <Text style={[s.resultVal, { color: colors.textPrimary }]}>{fmtINR(result.summary.original_amount)}</Text>
            </View>
            <View style={s.resultItem}>
              <Text style={[s.resultLabel, { color: colors.textSecondary }]}>Total Interest</Text>
              <Text style={[s.resultVal, { color: '#EF4444' }]}>{fmtINR(result.summary.total_interest)}</Text>
            </View>
            <View style={s.resultItem}>
              <Text style={[s.resultLabel, { color: colors.textSecondary }]}>Total You'll Pay</Text>
              <Text style={[s.resultVal, { color: '#EF4444' }]}>{fmtINR(result.summary.total_paid)}</Text>
            </View>
            <View style={s.resultItem}>
              <Text style={[s.resultLabel, { color: colors.textSecondary }]}>Time to Clear</Text>
              <Text style={[s.resultVal, { color: '#F59E0B' }]}>{result.summary.months_to_clear} months</Text>
            </View>
          </View>

          <View style={[s.warnBox, { backgroundColor: isDark ? 'rgba(245,158,11,0.12)' : 'rgba(245,158,11,0.06)' }]}>
            <MaterialCommunityIcons name="lightbulb-on-outline" size={16} color="#F59E0B" />
            <Text style={[s.warnText, { color: isDark ? '#FCD34D' : '#92400E' }]}>
              You'd pay {result.summary.interest_pct_of_principal.toFixed(0)}% extra in interest! Always pay the full bill to avoid this trap.
            </Text>
          </View>
        </View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14, borderRadius: 14, marginBottom: 8 },
  headerText: { fontSize: 16, fontWeight: '700' },
  desc: { fontSize: 13, lineHeight: 19, marginBottom: 14, paddingHorizontal: 2 },
  cardScroll: { marginBottom: 14 },
  cardChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, marginRight: 8, borderWidth: 1.5 },
  cardChipText: { fontSize: 12, fontWeight: '600' },
  inputRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  inputBox: { flex: 1, borderWidth: 1, borderRadius: 12, padding: 12 },
  inputLabel: { fontSize: 10, fontWeight: '600', marginBottom: 4 },
  input: { fontSize: 18, fontWeight: '700' },
  calcBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#F59E0B', paddingVertical: 14, borderRadius: 14, marginBottom: 16 },
  calcBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  resultCard: { borderRadius: 16, borderWidth: 1, padding: 16 },
  resultTitle: { fontSize: 15, fontWeight: '700', marginBottom: 14 },
  resultGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, marginBottom: 14 },
  resultItem: { width: '47%' },
  resultLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  resultVal: { fontSize: 18, fontWeight: '800' },
  warnBox: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, padding: 12, borderRadius: 12 },
  warnText: { flex: 1, fontSize: 12, lineHeight: 18, fontWeight: '500' },
});
