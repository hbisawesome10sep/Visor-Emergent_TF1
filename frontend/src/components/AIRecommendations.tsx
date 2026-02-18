import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Accent } from '../utils/theme';

type Recommendation = {
  priority: string;
  icon: string;
  title: string;
  description: string;
  impact: string;
  source: string;
};

type Props = {
  recommendations: Recommendation[];
  isDark: boolean;
  colors: any;
};

export const AIRecommendations = ({ recommendations, isDark, colors }: Props) => (
  <View>
    <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>AI Insights & Recommendations</Text>
    <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>Personalized tips based on your financial data</Text>

    {recommendations.map((rec, index) => (
      <View
        key={index}
        style={[styles.card, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.9)' : 'rgba(255, 255, 255, 0.95)',
          borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          borderLeftColor: rec.priority === 'high' ? Accent.ruby : rec.priority === 'medium' ? Accent.amber : Accent.emerald,
        }]}
      >
        <View style={styles.header}>
          <View style={[styles.icon, {
            backgroundColor: rec.priority === 'high' ? 'rgba(239, 68, 68, 0.12)' : rec.priority === 'medium' ? 'rgba(245, 158, 11, 0.12)' : 'rgba(16, 185, 129, 0.12)',
          }]}>
            <MaterialCommunityIcons
              name={rec.icon as any}
              size={20}
              color={rec.priority === 'high' ? Accent.ruby : rec.priority === 'medium' ? Accent.amber : Accent.emerald}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>{rec.title}</Text>
            <Text style={[styles.desc, { color: colors.textSecondary }]}>{rec.description}</Text>
          </View>
        </View>
        <View style={styles.footer}>
          <View style={[styles.impactBadge, {
            backgroundColor: rec.priority === 'low' ? 'rgba(16, 185, 129, 0.12)' : 'rgba(245, 158, 11, 0.12)',
          }]}>
            <MaterialCommunityIcons name="lightning-bolt" size={12} color={rec.priority === 'low' ? Accent.emerald : Accent.amber} />
            <Text style={[styles.impactText, { color: rec.priority === 'low' ? Accent.emerald : Accent.amber }]}>{rec.impact}</Text>
          </View>
          <Text style={[styles.source, { color: colors.textSecondary }]}>{rec.source}</Text>
        </View>
      </View>
    ))}
  </View>
);

const styles = StyleSheet.create({
  sectionTitle: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  sectionSubtitle: { fontSize: 12, fontFamily: 'DM Sans', marginBottom: 12 },
  card: { borderRadius: 16, borderWidth: 1, borderLeftWidth: 4, padding: 16, marginBottom: 12 },
  header: { flexDirection: 'row', gap: 12, marginBottom: 10 },
  icon: { width: 40, height: 40, borderRadius: 12, alignItems: 'center', justifyContent: 'center' },
  title: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 4 },
  desc: { fontSize: 13, fontFamily: 'DM Sans', lineHeight: 18 },
  footer: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 },
  impactBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6 },
  impactText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any },
  source: { fontSize: 10, fontFamily: 'DM Sans', fontStyle: 'italic' },
});
