import React, { useState } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator, ScrollView } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';

type Props = { token: string; isDark: boolean; colors: any };

const CATEGORIES = ['Shopping', 'Travel', 'Food & Dining', 'Fuel', 'Entertainment', 'Utilities', 'Healthcare', 'Education', 'Subscriptions', 'Other'];

export const CardRecommender = ({ token, isDark, colors }: Props) => {
  const [category, setCategory] = useState('Shopping');
  const [amount, setAmount] = useState('5000');
  const [merchant, setMerchant] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const getRecommendation = async () => {
    setLoading(true);
    try {
      const res = await apiRequest('/credit-cards/recommend', {
        token,
        method: 'POST',
        body: { category, amount: parseFloat(amount) || 0, merchant },
      });
      setResult(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  };

  return (
    <View testID="cc-recommender">
      <View style={[s.header, { backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(16,185,129,0.04)' }]}>
        <MaterialCommunityIcons name="brain" size={20} color="#10B981" />
        <Text style={[s.headerText, { color: colors.textPrimary }]}>Smart Card Recommender</Text>
      </View>

      <Text style={[s.desc, { color: colors.textSecondary }]}>
        Tell us about your transaction and we'll recommend the best card to maximize your rewards.
      </Text>

      {/* Category Pills */}
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={s.pillScroll}>
        {CATEGORIES.map(cat => (
          <TouchableOpacity
            key={cat}
            style={[s.pill, {
              backgroundColor: category === cat ? '#10B98120' : isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
              borderColor: category === cat ? '#10B981' : 'transparent',
            }]}
            onPress={() => setCategory(cat)}
          >
            <Text style={[s.pillText, { color: category === cat ? '#10B981' : colors.textSecondary }]}>{cat}</Text>
          </TouchableOpacity>
        ))}
      </ScrollView>

      <View style={s.inputRow}>
        <View style={[s.inputBox, { flex: 1, backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Amount (Rs)</Text>
          <TextInput style={[s.input, { color: colors.textPrimary }]} value={amount} onChangeText={setAmount} keyboardType="numeric" placeholder="5000" placeholderTextColor={colors.textSecondary} />
        </View>
        <View style={[s.inputBox, { flex: 1, backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)', borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Merchant</Text>
          <TextInput style={[s.input, { color: colors.textPrimary }]} value={merchant} onChangeText={setMerchant} placeholder="MakeMyTrip" placeholderTextColor={colors.textSecondary} />
        </View>
      </View>

      <TouchableOpacity testID="recommend-btn" style={s.recBtn} onPress={getRecommendation} disabled={loading}>
        {loading ? <ActivityIndicator size="small" color="#fff" /> : (
          <>
            <MaterialCommunityIcons name="magic-staff" size={18} color="#fff" />
            <Text style={s.recBtnText}>Get Recommendation</Text>
          </>
        )}
      </TouchableOpacity>

      {result && (
        <View>
          {/* AI Recommendation */}
          {result.ai_recommendation && (
            <View style={[s.aiBox, { backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(16,185,129,0.04)', borderColor: isDark ? 'rgba(16,185,129,0.25)' : 'rgba(16,185,129,0.15)' }]}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                <MaterialCommunityIcons name="robot-outline" size={16} color="#10B981" />
                <Text style={[s.aiLabel, { color: '#10B981' }]}>Visor AI Says</Text>
              </View>
              <Text style={[s.aiText, { color: isDark ? '#E2E8F0' : '#1E293B' }]}>{result.ai_recommendation}</Text>
            </View>
          )}

          {/* Card Rankings */}
          {result.recommendations?.map((rec: any, idx: number) => (
            <View key={rec.card_id} style={[s.recCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#fff', borderColor: idx === 0 ? '#10B981' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
              <View style={s.recTop}>
                {idx === 0 && (
                  <View style={s.bestBadge}>
                    <MaterialCommunityIcons name="crown" size={12} color="#F59E0B" />
                    <Text style={s.bestText}>BEST</Text>
                  </View>
                )}
                <Text style={[s.recCardName, { color: colors.textPrimary }]}>{rec.card_name}</Text>
                <Text style={[s.recFour, { color: colors.textSecondary }]}>*{rec.last_four}</Text>
              </View>
              <View style={s.recStats}>
                <View style={s.recStat}>
                  <Text style={[s.recStatLabel, { color: colors.textSecondary }]}>Points</Text>
                  <Text style={[s.recStatVal, { color: '#8B5CF6' }]}>{rec.points_earned}</Text>
                </View>
                <View style={s.recStat}>
                  <Text style={[s.recStatLabel, { color: colors.textSecondary }]}>Value</Text>
                  <Text style={[s.recStatVal, { color: '#10B981' }]}>Rs {rec.value_earned}</Text>
                </View>
                <View style={s.recStat}>
                  <Text style={[s.recStatLabel, { color: colors.textSecondary }]}>Utilization</Text>
                  <Text style={[s.recStatVal, { color: rec.utilization_after > 50 ? '#EF4444' : colors.textPrimary }]}>{rec.utilization_after}%</Text>
                </View>
              </View>
              <Text style={[s.recNote, { color: colors.textSecondary }]}>{rec.reward_note}</Text>
            </View>
          ))}
        </View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 14, borderRadius: 14, marginBottom: 8 },
  headerText: { fontSize: 16, fontWeight: '700' },
  desc: { fontSize: 13, lineHeight: 19, marginBottom: 14, paddingHorizontal: 2 },
  pillScroll: { marginBottom: 14 },
  pill: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, marginRight: 8, borderWidth: 1.5 },
  pillText: { fontSize: 12, fontWeight: '600' },
  inputRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  inputBox: { borderWidth: 1, borderRadius: 12, padding: 12 },
  inputLabel: { fontSize: 10, fontWeight: '600', marginBottom: 4 },
  input: { fontSize: 16, fontWeight: '700' },
  recBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#10B981', paddingVertical: 14, borderRadius: 14, marginBottom: 16 },
  recBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  aiBox: { borderRadius: 14, borderWidth: 1, padding: 14, marginBottom: 12 },
  aiLabel: { fontSize: 13, fontWeight: '700' },
  aiText: { fontSize: 14, lineHeight: 21 },
  recCard: { borderRadius: 14, borderWidth: 1.5, padding: 14, marginBottom: 8 },
  recTop: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 10 },
  bestBadge: { flexDirection: 'row', alignItems: 'center', gap: 3, backgroundColor: '#F59E0B20', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  bestText: { fontSize: 10, fontWeight: '800', color: '#F59E0B' },
  recCardName: { fontSize: 14, fontWeight: '700', flex: 1 },
  recFour: { fontSize: 12 },
  recStats: { flexDirection: 'row', gap: 10, marginBottom: 8 },
  recStat: { flex: 1 },
  recStatLabel: { fontSize: 10, fontWeight: '500', marginBottom: 2 },
  recStatVal: { fontSize: 15, fontWeight: '700' },
  recNote: { fontSize: 11, fontStyle: 'italic' },
});
