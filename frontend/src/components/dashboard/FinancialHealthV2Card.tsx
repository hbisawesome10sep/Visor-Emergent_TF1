import React, { useState, useEffect, useCallback, useRef } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Animated, Dimensions, ActivityIndicator, Modal, Platform, Alert, ScrollView } from 'react-native';
import Svg, { Circle, Defs, LinearGradient as SvgGradient, Stop, G } from 'react-native-svg';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import ViewShot, { captureRef } from 'react-native-view-shot';
import * as Sharing from 'expo-sharing';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';
import { ShareScoreCard } from './ShareScoreCard';

const SCREEN_WIDTH = Dimensions.get('window').width;

type Dimension = { score: number; raw_value: number };
type HealthData = {
  composite_score: number;
  grade: string;
  has_data: boolean;
  score_change: number;
  biggest_drag: string;
  improvement_tip: string;
  dimensions: {
    savings_rate: Dimension;
    debt_load: Dimension;
    investment_rate: Dimension;
    emergency_fund: Dimension;
    cc_utilization: Dimension;
    goal_progress: Dimension;
    insurance_cover: Dimension;
    net_worth_growth: Dimension;
  };
};

type Props = { 
  token: string; 
  isDark: boolean; 
  colors: any; 
  frequency?: 'Month' | 'Quarter' | 'Year' | 'Custom';
};

const DIM_CONFIG: Record<string, { label: string; icon: string; color: string }> = {
  savings_rate: { label: 'Savings Rate', icon: 'piggy-bank-outline', color: '#10B981' },
  debt_load: { label: 'Debt Load', icon: 'scale-balance', color: '#F59E0B' },
  investment_rate: { label: 'Investment Rate', icon: 'trending-up', color: '#3B82F6' },
  emergency_fund: { label: 'Emergency Fund', icon: 'shield-check-outline', color: '#06B6D4' },
  cc_utilization: { label: 'CC Utilization', icon: 'credit-card-outline', color: '#8B5CF6' },
  goal_progress: { label: 'Goal Progress', icon: 'flag-checkered', color: '#EC4899' },
  insurance_cover: { label: 'Insurance Cover', icon: 'heart-pulse', color: '#EF4444' },
  net_worth_growth: { label: 'Net Worth Growth', icon: 'chart-timeline-variant', color: '#14B8A6' },
};

const getGradeConfig = (score: number, hasData: boolean) => {
  if (!hasData) return { gradient: ['#64748B', '#475569'] as const, glow: '#64748B' };
  if (score >= 800) return { gradient: ['#10B981', '#059669'] as const, glow: '#10B981' };
  if (score >= 650) return { gradient: ['#14B8A6', '#0D9488'] as const, glow: '#14B8A6' };
  if (score >= 450) return { gradient: ['#F59E0B', '#D97706'] as const, glow: '#F59E0B' };
  if (score >= 250) return { gradient: ['#F97316', '#EA580C'] as const, glow: '#F97316' };
  return { gradient: ['#EF4444', '#DC2626'] as const, glow: '#EF4444' };
};

const DimensionBar = ({ dimKey, dim, isDark }: { dimKey: string; dim: Dimension; isDark: boolean }) => {
  const config = DIM_CONFIG[dimKey];
  const animWidth = React.useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(animWidth, { toValue: dim.score, duration: 1000, useNativeDriver: false }).start();
  }, [dim.score]);

  return (
    <View style={s.dimRow}>
      <View style={s.dimLabelRow}>
        <View style={[s.dimIconBg, { backgroundColor: `${config.color}20` }]}>
          <MaterialCommunityIcons name={config.icon as any} size={13} color={config.color} />
        </View>
        <Text style={[s.dimLabel, { color: isDark ? '#CBD5E1' : '#334155' }]}>{config.label}</Text>
        <Text style={[s.dimScore, { color: config.color }]}>{dim.score}</Text>
      </View>
      <View style={[s.dimTrack, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
        <Animated.View style={[s.dimFill, { backgroundColor: config.color, width: animWidth.interpolate({ inputRange: [0, 100], outputRange: ['0%', '100%'] }) }]} />
      </View>
    </View>
  );
};

export const FinancialHealthV2Card = ({ token, isDark, colors, frequency = 'Month' }: Props) => {
  const [data, setData] = useState<HealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [flipped, setFlipped] = useState(false);
  const [showShareModal, setShowShareModal] = useState(false);
  const [sharing, setSharing] = useState(false);
  const shareRef = useRef<View>(null);

  const fetchData = useCallback(async () => {
    try {
      const res = await apiRequest('/dashboard/financial-health-v2', { token });
      setData(res);
    } catch (e) {
      console.warn('Health V2 fetch error:', e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleShare = async () => {
    if (!data || !shareRef.current) return;
    setSharing(true);
    try {
      const uri = await captureRef(shareRef, { format: 'png', quality: 0.95 });
      const isAvailable = await Sharing.isAvailableAsync();
      if (isAvailable) {
        await Sharing.shareAsync(uri, {
          mimeType: 'image/png',
          dialogTitle: 'Share your Financial Health Score',
        });
      } else {
        Alert.alert('Sharing not available', 'Sharing is not supported on this device.');
      }
    } catch (e: any) {
      console.warn('Share error:', e);
      Alert.alert('Share Failed', e?.message || 'Could not share the score card.');
    } finally {
      setSharing(false);
    }
  };

  if (loading) {
    return (
      <View style={[s.card, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : 'rgba(255,255,255,0.95)', borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
        <ActivityIndicator size="small" color={colors.primary} style={{ padding: 40 }} />
      </View>
    );
  }

  if (!data || !data.has_data) {
    return (
      <View testID="financial-health-v2-empty" style={[s.card, { backgroundColor: isDark ? 'rgba(100,116,139,0.15)' : '#F8FAFC', borderColor: isDark ? 'rgba(100,116,139,0.3)' : '#E2E8F0' }]}>
        <View style={s.emptyState}>
          <View style={[s.emptyIcon, { backgroundColor: isDark ? 'rgba(100,116,139,0.3)' : 'rgba(100,116,139,0.1)' }]}>
            <MaterialCommunityIcons name="chart-donut" size={32} color="#64748B" />
          </View>
          <Text style={[s.emptyTitle, { color: colors.textPrimary }]}>Financial Health Score</Text>
          <Text style={[s.emptyDesc, { color: colors.textSecondary }]}>Add transactions to see your 8-dimension score (0-1000)</Text>
        </View>
      </View>
    );
  }

  const cfg = getGradeConfig(data.composite_score, data.has_data);
  const scoreRatio = Math.min(1, data.composite_score / 1000);
  const circleSize = 120;
  const strokeW = 10;
  const radius = (circleSize - strokeW) / 2;
  const circumference = 2 * Math.PI * radius;
  const dashOffset = circumference * (1 - scoreRatio);

  return (
    <TouchableOpacity
      testID="financial-health-v2-card"
      activeOpacity={0.98}
      onPress={() => setFlipped(!flipped)}
    >
      <LinearGradient
        colors={isDark ? [`${cfg.gradient[0]}18`, `${cfg.gradient[1]}0A`] : [`${cfg.gradient[0]}12`, `${cfg.gradient[1]}06`]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[s.card, { borderColor: isDark ? `${cfg.gradient[0]}40` : `${cfg.gradient[0]}30` }]}
      >
        {!flipped ? (
          <>
            {/* FRONT: Score + Overview */}
            <View style={s.header}>
              <View style={[s.badge, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}>
                <MaterialCommunityIcons name="shield-check" size={14} color={cfg.gradient[0]} />
                <Text style={[s.badgeText, { color: colors.textSecondary }]}>Financial Health</Text>
              </View>
              <TouchableOpacity style={[s.flipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]} onPress={() => setFlipped(true)}>
                <MaterialCommunityIcons name="rotate-3d-variant" size={16} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <View style={s.mainContent}>
              {/* Score Ring */}
              <View style={{ alignItems: 'center', justifyContent: 'center', width: circleSize, height: circleSize }}>
                <Svg width={circleSize} height={circleSize}>
                  <Defs>
                    <SvgGradient id="healthGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                      <Stop offset="0%" stopColor={cfg.gradient[0]} />
                      <Stop offset="100%" stopColor={cfg.gradient[1]} />
                    </SvgGradient>
                  </Defs>
                  <G rotation="-90" origin={`${circleSize / 2}, ${circleSize / 2}`}>
                    <Circle cx={circleSize / 2} cy={circleSize / 2} r={radius} stroke={isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)'} strokeWidth={strokeW} fill="transparent" />
                    <Circle cx={circleSize / 2} cy={circleSize / 2} r={radius} stroke="url(#healthGrad)" strokeWidth={strokeW} fill="transparent" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={dashOffset} />
                  </G>
                </Svg>
                <View style={{ position: 'absolute', alignItems: 'center' }}>
                  <Text style={[s.scoreNum, { color: cfg.gradient[0] }]}>{data.composite_score}</Text>
                  <Text style={[s.scoreMax, { color: colors.textSecondary }]}>/ 1000</Text>
                </View>
              </View>

              {/* Score Info */}
              <View style={{ flex: 1, marginLeft: 16 }}>
                <LinearGradient colors={[cfg.gradient[0], cfg.gradient[1]]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={s.gradeBadge}>
                  <Text style={s.gradeText}>{data.grade}</Text>
                </LinearGradient>
                <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 6 }}>
                  <MaterialCommunityIcons name={data.score_change >= 0 ? 'arrow-up' : 'arrow-down'} size={14} color={data.score_change >= 0 ? Accent.emerald : Accent.ruby} />
                  <Text style={[s.changeText, { color: data.score_change >= 0 ? Accent.emerald : Accent.ruby }]}>
                    {Math.abs(data.score_change)} pts this {frequency === 'Year' ? 'year' : frequency === 'Quarter' ? 'quarter' : frequency === 'Custom' ? 'period' : 'month'}
                  </Text>
                </View>
                <Text style={[s.tipSmall, { color: colors.textSecondary }]} numberOfLines={2}>
                  Drag: {data.biggest_drag}
                </Text>

                {/* Quick dimension preview */}
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 4, marginTop: 8 }}>
                  {Object.entries(data.dimensions).slice(0, 4).map(([key, dim]) => {
                    const c = DIM_CONFIG[key];
                    return (
                      <View key={key} style={[s.miniPill, { backgroundColor: isDark ? `${c.color}18` : `${c.color}12` }]}>
                        <MaterialCommunityIcons name={c.icon as any} size={10} color={c.color} />
                        <Text style={[s.miniPillText, { color: c.color }]}>{dim.score}</Text>
                      </View>
                    );
                  })}
                </View>
              </View>
            </View>

            {/* Share My Score Button */}
            <TouchableOpacity
              testID="share-score-btn"
              style={[s.shareBtn, { backgroundColor: isDark ? `${cfg.gradient[0]}18` : `${cfg.gradient[0]}10` }]}
              onPress={(e) => { e.stopPropagation(); setShowShareModal(true); }}
              activeOpacity={0.8}
            >
              <MaterialCommunityIcons name="share-variant-outline" size={15} color={cfg.gradient[0]} />
              <Text style={[s.shareBtnText, { color: cfg.gradient[0] }]}>Share My Score</Text>
            </TouchableOpacity>
          </>
        ) : (
          <>
            {/* BACK: All 8 Dimensions */}
            <View style={s.header}>
              <View style={[s.badge, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]}>
                <MaterialCommunityIcons name="view-dashboard-outline" size={14} color={cfg.gradient[0]} />
                <Text style={[s.badgeText, { color: colors.textSecondary }]}>8 Dimensions</Text>
              </View>
              <TouchableOpacity style={[s.flipBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.04)' }]} onPress={() => setFlipped(false)}>
                <MaterialCommunityIcons name="rotate-3d-variant" size={16} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            <View style={{ gap: 6 }}>
              {Object.entries(data.dimensions).map(([key, dim]) => (
                <DimensionBar key={key} dimKey={key} dim={dim} isDark={isDark} />
              ))}
            </View>

            {/* Tip */}
            <View style={[s.tipBox, { backgroundColor: isDark ? `${cfg.gradient[0]}15` : `${cfg.gradient[0]}0A` }]}>
              <MaterialCommunityIcons name="lightbulb-on-outline" size={16} color={cfg.gradient[0]} />
              <Text style={[s.tipText, { color: isDark ? `${cfg.gradient[0]}` : cfg.gradient[1] }]} numberOfLines={3}>
                {data.improvement_tip}
              </Text>
            </View>
          </>
        )}
      </LinearGradient>

      {/* Share Modal */}
      {showShareModal && data && (
        <Modal
          visible={showShareModal}
          transparent
          animationType="fade"
          onRequestClose={() => setShowShareModal(false)}
        >
          <View style={s.modalOverlay}>
            <View style={[s.modalContent, { backgroundColor: isDark ? '#1E293B' : '#FFFFFF' }]}>
              <View style={s.modalHeader}>
                <Text style={[s.modalTitle, { color: isDark ? '#F8FAFC' : '#0F172A' }]}>Share Your Score</Text>
                <TouchableOpacity onPress={() => setShowShareModal(false)}>
                  <MaterialCommunityIcons name="close" size={22} color={isDark ? '#94A3B8' : '#64748B'} />
                </TouchableOpacity>
              </View>

              {/* Scrollable content so share button is never cut off */}
              <ScrollView showsVerticalScrollIndicator={false} bounces={false}>
                {/* The capturable share card */}
                <View style={s.shareCardWrapper}>
                  <ShareScoreCard
                    ref={shareRef}
                    composite_score={data.composite_score}
                    dimensions={data.dimensions}
                    score_change={data.score_change}
                    frequency={frequency}
                  />
                </View>

                <TouchableOpacity
                  testID="share-score-action-btn"
                  style={[s.shareActionBtn, { backgroundColor: cfg.gradient[0] }]}
                  onPress={handleShare}
                  activeOpacity={0.85}
                  disabled={sharing}
                >
                  {sharing ? (
                    <ActivityIndicator size="small" color="#fff" />
                  ) : (
                    <>
                      <MaterialCommunityIcons name="share-variant" size={18} color="#fff" />
                      <Text style={s.shareActionText}>Share to WhatsApp / Instagram</Text>
                    </>
                  )}
                </TouchableOpacity>
              </ScrollView>
            </View>
          </View>
        </Modal>
      )}
    </TouchableOpacity>
  );
};

const s = StyleSheet.create({
  card: { borderRadius: 20, borderWidth: 1.5, padding: 16, marginBottom: 16, overflow: 'hidden' },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  badge: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20, gap: 6 },
  badgeText: { fontSize: 12, fontWeight: '600' },
  flipBtn: { width: 28, height: 28, borderRadius: 14, alignItems: 'center', justifyContent: 'center' },
  mainContent: { flexDirection: 'row', alignItems: 'center' },
  scoreNum: { fontSize: 36, fontWeight: '800' },
  scoreMax: { fontSize: 11, fontWeight: '500', marginTop: -4 },
  gradeBadge: { paddingHorizontal: 14, paddingVertical: 5, borderRadius: 12, alignSelf: 'flex-start' },
  gradeText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  changeText: { fontSize: 12, fontWeight: '600', marginLeft: 2 },
  tipSmall: { fontSize: 11, marginTop: 4 },
  miniPill: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6, gap: 3 },
  miniPillText: { fontSize: 10, fontWeight: '700' },
  dimRow: { marginBottom: 2 },
  dimLabelRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  dimIconBg: { width: 22, height: 22, borderRadius: 6, alignItems: 'center', justifyContent: 'center', marginRight: 6 },
  dimLabel: { flex: 1, fontSize: 12, fontWeight: '500' },
  dimScore: { fontSize: 13, fontWeight: '700', minWidth: 28, textAlign: 'right' },
  dimTrack: { height: 6, borderRadius: 3, overflow: 'hidden' },
  dimFill: { height: '100%', borderRadius: 3 },
  tipBox: { flexDirection: 'row', alignItems: 'flex-start', padding: 12, borderRadius: 12, marginTop: 12, gap: 8 },
  tipText: { flex: 1, fontSize: 12, lineHeight: 17 },
  emptyState: { alignItems: 'center', paddingVertical: 24 },
  emptyIcon: { width: 56, height: 56, borderRadius: 28, alignItems: 'center', justifyContent: 'center', marginBottom: 12 },
  emptyTitle: { fontSize: 16, fontWeight: '700', marginBottom: 4 },
  emptyDesc: { fontSize: 13, textAlign: 'center', paddingHorizontal: 20 },
  shareBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 12, marginTop: 14 },
  shareBtnText: { fontSize: 13, fontWeight: '700' },
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', justifyContent: 'center', alignItems: 'center', padding: 20 },
  modalContent: { borderRadius: 24, padding: 20, width: '100%', maxWidth: 400, maxHeight: '90%' },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  modalTitle: { fontSize: 18, fontWeight: '700' },
  shareCardWrapper: { alignItems: 'center', marginBottom: 16 },
  shareActionBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 14, borderRadius: 14 },
  shareActionText: { color: '#fff', fontSize: 15, fontWeight: '700' },
});
