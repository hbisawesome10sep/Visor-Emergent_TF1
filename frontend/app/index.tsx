import { useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Dimensions, Animated, ActivityIndicator, Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../src/context/AuthContext';
import { useTheme } from '../src/context/ThemeContext';

const { width: W } = Dimensions.get('window');

const FEATURES = [
  {
    icon: 'chart-timeline-variant-shimmer' as const,
    color: '#10B981',
    bg: 'rgba(16,185,129,0.1)',
    title: 'Smart Dashboard',
    desc: 'Track income, expenses & net worth with real-time charts and insights.',
  },
  {
    icon: 'swap-horizontal-bold' as const,
    color: '#3B82F6',
    bg: 'rgba(59,130,246,0.1)',
    title: 'Transaction Tracking',
    desc: 'Categorise every rupee. Split bills, recurring entries, and quick-fill descriptions.',
  },
  {
    icon: 'trending-up' as const,
    color: '#F59E0B',
    bg: 'rgba(245,158,11,0.1)',
    title: 'Live Indian Markets',
    desc: 'Nifty 50, SENSEX, Gold & Silver prices fetched live every time you open the app.',
  },
  {
    icon: 'calculator-variant' as const,
    color: '#8B5CF6',
    bg: 'rgba(139,92,246,0.1)',
    title: 'Income Tax Calculator',
    desc: 'Old vs New regime comparison. Auto-detect tax-deductible transactions.',
  },
  {
    icon: 'brain' as const,
    color: '#EC4899',
    bg: 'rgba(236,72,153,0.1)',
    title: 'AI Financial Advisor',
    desc: 'Context-aware AI that understands your screen and gives personalised advice.',
  },
  {
    icon: 'book-open-page-variant' as const,
    color: '#06B6D4',
    bg: 'rgba(6,182,212,0.1)',
    title: 'Books & Reports',
    desc: 'Ledger, P&L, Balance Sheet. Export to Excel, PDF, CSV or JSON anytime.',
  },
  {
    icon: 'shield-lock' as const,
    color: '#10B981',
    bg: 'rgba(16,185,129,0.1)',
    title: 'Bank-Grade Security',
    desc: '4-digit PIN + biometric lock. Auto-lock after 5 minutes of inactivity.',
  },
  {
    icon: 'target' as const,
    color: '#F97316',
    bg: 'rgba(249,115,22,0.1)',
    title: 'Financial Goals',
    desc: 'Set savings targets, track progress, and get AI-powered rebalancing tips.',
  },
];

export default function IntroScreen() {
  const { user, loading } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(30)).current;

  useEffect(() => {
    if (!loading && user) {
      router.replace('/(tabs)');
    }
  }, [loading, user]);

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 600, useNativeDriver: true }),
    ]).start();
  }, []);

  if (loading) {
    return (
      <View style={[styles.loadingContainer, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  // If user is logged in, the useEffect above handles redirect
  if (user) return null;

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: isDark ? '#000' : '#FAFBFC' }]}>
      {/* Top Auth Buttons */}
      <View style={[styles.topBar, { borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
        <View style={styles.topBarLogo}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.logoMini}>
            <MaterialCommunityIcons name="shield-check" size={18} color="#fff" />
          </LinearGradient>
          <Text style={[styles.logoText, { color: colors.textPrimary }]}>Visor</Text>
        </View>
        <View style={styles.topBarBtns}>
          <TouchableOpacity
            data-testid="intro-login-btn"
            style={[styles.loginBtn, { borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)' }]}
            onPress={() => router.push('/(auth)/login')}
          >
            <Text style={[styles.loginBtnText, { color: colors.textPrimary }]}>Log In</Text>
          </TouchableOpacity>
          <TouchableOpacity
            data-testid="intro-signup-btn"
            onPress={() => router.push('/(auth)/register')}
          >
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.signupBtn}>
              <Text style={styles.signupBtnText}>Sign Up</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {/* Hero Section */}
        <Animated.View style={[styles.hero, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
          <LinearGradient colors={['#10B981', '#059669']} style={styles.heroIcon}>
            <MaterialCommunityIcons name="shield-check" size={52} color="#fff" />
          </LinearGradient>
          <Text style={[styles.heroTitle, { color: colors.textPrimary }]}>
            Your Finances,{'\n'}Simplified
          </Text>
          <Text style={[styles.heroSubtitle, { color: colors.textSecondary }]}>
            Track expenses, manage investments, calculate taxes, and get AI-powered insights — all in one place.
          </Text>

          {/* CTA Buttons */}
          <TouchableOpacity
            data-testid="hero-get-started-btn"
            style={styles.heroBtn}
            onPress={() => router.push('/(auth)/register')}
          >
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.heroBtnGradient}>
              <Text style={styles.heroBtnText}>Get Started Free</Text>
              <MaterialCommunityIcons name="arrow-right" size={20} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.heroSecondaryBtn, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' }]}
            onPress={() => router.push('/(auth)/login')}
          >
            <Text style={[styles.heroSecondaryText, { color: colors.textPrimary }]}>Already have an account? Log In</Text>
          </TouchableOpacity>
        </Animated.View>

        {/* Stats Row */}
        <View style={[styles.statsRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
          {[
            { num: '100%', label: 'Free' },
            { num: 'Live', label: 'Market Data' },
            { num: 'AI', label: 'Powered' },
          ].map((s, i) => (
            <View key={i} style={styles.statItem}>
              <Text style={[styles.statNum, { color: '#10B981' }]}>{s.num}</Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>{s.label}</Text>
            </View>
          ))}
        </View>

        {/* Section Title */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Everything You Need</Text>
          <Text style={[styles.sectionSubtitle, { color: colors.textSecondary }]}>
            Powerful features to take control of your financial life
          </Text>
        </View>

        {/* Feature Cards */}
        <View style={styles.featureGrid}>
          {FEATURES.map((feature, idx) => (
            <Animated.View
              key={idx}
              style={[
                styles.featureCard,
                {
                  backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#fff',
                  borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
                  opacity: fadeAnim,
                },
              ]}
            >
              <View style={[styles.featureIconWrap, { backgroundColor: feature.bg }]}>
                <MaterialCommunityIcons name={feature.icon} size={24} color={feature.color} />
              </View>
              <Text style={[styles.featureTitle, { color: colors.textPrimary }]}>{feature.title}</Text>
              <Text style={[styles.featureDesc, { color: colors.textSecondary }]}>{feature.desc}</Text>
            </Animated.View>
          ))}
        </View>

        {/* Bottom CTA */}
        <View style={styles.bottomCTA}>
          <Text style={[styles.bottomTitle, { color: colors.textPrimary }]}>
            Ready to take control?
          </Text>
          <TouchableOpacity
            data-testid="bottom-get-started-btn"
            style={styles.heroBtn}
            onPress={() => router.push('/(auth)/register')}
          >
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.heroBtnGradient}>
              <Text style={styles.heroBtnText}>Create Your Account</Text>
              <MaterialCommunityIcons name="arrow-right" size={20} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderBottomWidth: 1,
  },
  topBarLogo: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  logoMini: { width: 30, height: 30, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  logoText: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' },
  topBarBtns: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  loginBtn: {
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 10,
    borderWidth: 1.5,
  },
  loginBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' },
  signupBtn: {
    paddingHorizontal: 18,
    paddingVertical: 8,
    borderRadius: 10,
  },
  signupBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  scrollContent: { paddingBottom: 20 },
  hero: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 36, paddingBottom: 24 },
  heroIcon: {
    width: 96, height: 96, borderRadius: 32,
    justifyContent: 'center', alignItems: 'center', marginBottom: 24,
  },
  heroTitle: {
    fontSize: 32, fontFamily: 'DM Sans', fontWeight: '800',
    textAlign: 'center', letterSpacing: -0.8, lineHeight: 40, marginBottom: 12,
  },
  heroSubtitle: {
    fontSize: 16, fontFamily: 'DM Sans', textAlign: 'center',
    lineHeight: 24, marginBottom: 28, paddingHorizontal: 12,
  },
  heroBtn: { width: '100%', borderRadius: 14, overflow: 'hidden', marginBottom: 12 },
  heroBtnGradient: {
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: 10, height: 52,
  },
  heroBtnText: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  heroSecondaryBtn: {
    paddingVertical: 12, paddingHorizontal: 24,
    borderRadius: 12, borderWidth: 1,
  },
  heroSecondaryText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '500' },
  statsRow: {
    flexDirection: 'row', justifyContent: 'space-around',
    paddingVertical: 20, marginHorizontal: 20, borderRadius: 16, marginBottom: 32,
  },
  statItem: { alignItems: 'center' },
  statNum: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '800' },
  statLabel: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
  sectionHeader: { paddingHorizontal: 24, marginBottom: 20 },
  sectionTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 6 },
  sectionSubtitle: { fontSize: 14, fontFamily: 'DM Sans', lineHeight: 20 },
  featureGrid: { paddingHorizontal: 20, gap: 12 },
  featureCard: {
    padding: 18, borderRadius: 16, borderWidth: 1,
    ...Platform.select({
      ios: { shadowColor: '#000', shadowOffset: { width: 0, height: 2 }, shadowOpacity: 0.04, shadowRadius: 8 },
      android: { elevation: 1 },
    }),
  },
  featureIconWrap: {
    width: 44, height: 44, borderRadius: 13,
    justifyContent: 'center', alignItems: 'center', marginBottom: 12,
  },
  featureTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 4 },
  featureDesc: { fontSize: 13, fontFamily: 'DM Sans', lineHeight: 19 },
  bottomCTA: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 36 },
  bottomTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 16 },
});
