import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Animated } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

type InsightData = {
  insight: string;
  generated_at: string;
  data_points_used: number;
};

type Props = { token: string; isDark: boolean; colors: any };

export const AIInsightCard = ({ token, isDark, colors }: Props) => {
  const [data, setData] = useState<InsightData | null>(null);
  const [loading, setLoading] = useState(true);
  const shimmerAnim = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(shimmerAnim, { toValue: 1, duration: 1500, useNativeDriver: true }),
        Animated.timing(shimmerAnim, { toValue: 0, duration: 1500, useNativeDriver: true }),
      ])
    ).start();
  }, []);

  const fetchData = useCallback(async () => {
    try {
      const res = await apiRequest('/dashboard/ai-insight', { token });
      setData(res);
    } catch (e) {
      console.warn('AI insight fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <LinearGradient
      colors={isDark ? ['rgba(139,92,246,0.12)', 'rgba(99,102,241,0.06)'] : ['rgba(139,92,246,0.06)', 'rgba(99,102,241,0.03)']}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={[s.card, { borderColor: isDark ? 'rgba(139,92,246,0.25)' : 'rgba(139,92,246,0.15)' }]}
    >
      <View testID="ai-insight-card" style={s.headerRow}>
        <Animated.View style={[s.iconBg, { backgroundColor: isDark ? 'rgba(139,92,246,0.2)' : 'rgba(139,92,246,0.12)', opacity: shimmerAnim.interpolate({ inputRange: [0, 1], outputRange: [0.7, 1] }) }]}>
          <MaterialCommunityIcons name="brain" size={18} color="#8B5CF6" />
        </Animated.View>
        <View style={{ flex: 1 }}>
          <Text style={[s.title, { color: colors.textPrimary }]}>Visor AI Insight</Text>
          <Text style={[s.subtitle, { color: colors.textSecondary }]}>Personalized for you</Text>
        </View>
        {data && (
          <View style={[s.dataBadge, { backgroundColor: isDark ? 'rgba(139,92,246,0.15)' : 'rgba(139,92,246,0.08)' }]}>
            <MaterialCommunityIcons name="database-outline" size={10} color="#8B5CF6" />
            <Text style={[s.dataText, { color: '#8B5CF6' }]}>{data.data_points_used} pts</Text>
          </View>
        )}
      </View>

      {loading ? (
        <View style={s.loadingBox}>
          <ActivityIndicator size="small" color="#8B5CF6" />
          <Text style={[s.loadingText, { color: colors.textSecondary }]}>Analyzing your finances...</Text>
        </View>
      ) : data ? (
        <Text style={[s.insightText, { color: isDark ? '#E2E8F0' : '#1E293B' }]}>
          {data.insight}
        </Text>
      ) : (
        <Text style={[s.insightText, { color: colors.textSecondary }]}>
          Add more transactions to get personalized AI insights.
        </Text>
      )}

      <View style={[s.disclaimer, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
        <MaterialCommunityIcons name="information-outline" size={12} color={colors.textSecondary} />
        <Text style={[s.disclaimerText, { color: colors.textSecondary }]}>
          AI-generated. Not financial advice. Consult a SEBI-registered advisor.
        </Text>
      </View>
    </LinearGradient>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 18, borderWidth: 1, padding: 16, marginBottom: 16, overflow: 'hidden' },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 12 },
  iconBg: { width: 36, height: 36, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 15, fontWeight: '700' },
  subtitle: { fontSize: 11, marginTop: 1 },
  dataBadge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, paddingVertical: 3, borderRadius: 8, gap: 4 },
  dataText: { fontSize: 10, fontWeight: '600' },
  insightText: { fontSize: 14, lineHeight: 22, fontWeight: '500' },
  loadingBox: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingVertical: 12 },
  loadingText: { fontSize: 13 },
  disclaimer: { borderTopWidth: 0.5, marginTop: 12, paddingTop: 10, flexDirection: 'row', alignItems: 'center', gap: 6 },
  disclaimerText: { fontSize: 10, flex: 1 },
});
