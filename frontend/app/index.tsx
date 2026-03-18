import { useEffect, useRef } from 'react';
import { useRouter } from 'expo-router';
import {
  View, Text, StyleSheet, TouchableOpacity, ScrollView,
  Dimensions, Animated, ActivityIndicator, Platform, Image,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../src/context/AuthContext';
import { useTheme } from '../src/context/ThemeContext';

const { width: W } = Dimensions.get('window');

// ── App screenshots from existing landing (unchanged URLs) ──
const SCREENSHOTS = {
  dashboard: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/9hzxt4al_Screenshot_20260226-200549~2.png',
  ai: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/grp9sgzv_Screenshot_20260226-201400.png',
  emi: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/04v9zk8l_Screenshot_20260226-201222.png',
  goals: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/f3gfcnw1_Screenshot_20260226-201152.png',
  invest1: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/voih10w7_Screenshot_20260226-201000.png',
  insights: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/wmw07vga_Screenshot_20260226-155347.png',
  creditCard: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/9k87r733_Screenshot_20260226-201755.png',
  tax: 'https://customer-assets.emergentagent.com/job_personal-money-visor/artifacts/yg8e7myr_Screenshot_20260226-201433.png',
};

// ── 8-dimension health score descriptions ──
const HEALTH_DIMS = [
  { icon: 'piggy-bank', color: '#10B981', label: 'Savings Rate' },
  { icon: 'chart-line', color: '#3B82F6', label: 'Investments' },
  { icon: 'shield-check', color: '#8B5CF6', label: 'Emergency Fund' },
  { icon: 'credit-card-off', color: '#EC4899', label: 'Debt Control' },
  { icon: 'target', color: '#F59E0B', label: 'Goal Progress' },
  { icon: 'cash', color: '#06B6D4', label: 'Spending' },
  { icon: 'trending-up', color: '#10B981', label: 'Income' },
  { icon: 'umbrella', color: '#F97316', label: 'Insurance' },
];

// ── Core feature list ──
const FEATURES = [
  { icon: 'star-four-points' as const, color: '#10B981', bg: 'rgba(16,185,129,0.12)', title: 'Health Score', desc: '0–1000 point score across 8 financial dimensions. Know exactly where you stand.' },
  { icon: 'robot' as const, color: '#3B82F6', bg: 'rgba(59,130,246,0.12)', title: 'Visor AI', desc: 'Context-aware AI that reads your real data and gives personalized, benchmark-based advice.' },
  { icon: 'target' as const, color: '#F59E0B', bg: 'rgba(245,158,11,0.12)', title: 'Jar Goals', desc: 'Set financial goals. Watch them fill up like money jars — visual, motivating, real.' },
  { icon: 'repeat' as const, color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)', title: 'SIP Tracking', desc: 'Track SIPs, link them to goals, see wealth projections at 8%, 12% and 15% CAGR.' },
  { icon: 'home-city' as const, color: '#EC4899', bg: 'rgba(236,72,153,0.12)', title: 'EMI Analytics', desc: 'Principal vs Interest breakdown. Prepayment calculator. Know true cost of debt.' },
  { icon: 'credit-card-multiple' as const, color: '#06B6D4', bg: 'rgba(6,182,212,0.12)', title: 'Credit Cards', desc: 'Due dates, interest calculator, rewards tracker, best card recommender for each spend.' },
  { icon: 'calendar-clock' as const, color: '#F97316', bg: 'rgba(249,115,22,0.12)', title: 'Upcoming Dues', desc: 'Consolidated view of all CC bills and loan EMIs. Never miss a payment again.' },
  { icon: 'chart-pie' as const, color: '#10B981', bg: 'rgba(16,185,129,0.12)', title: 'Net Worth', desc: 'Real-time net worth = assets − liabilities. See your true financial picture.' },
  { icon: 'receipt' as const, color: '#3B82F6', bg: 'rgba(59,130,246,0.12)', title: 'Smart Alerts', desc: 'Actionable insights that navigate you to the right screen. No more ignored notifications.' },
  { icon: 'file-chart' as const, color: '#8B5CF6', bg: 'rgba(139,92,246,0.12)', title: 'Tax Screen', desc: 'Old vs New regime comparison. Auto-detect deductible transactions. Advance tax alerts.' },
  { icon: 'bank-transfer' as const, color: '#EC4899', bg: 'rgba(236,72,153,0.12)', title: 'Bank Import', desc: 'Upload PDF/CSV bank statements. Auto-parse and categorise transactions instantly.' },
  { icon: 'shield-lock' as const, color: '#10B981', bg: 'rgba(16,185,129,0.12)', title: 'Secure', desc: 'AES-256 encryption, 4-digit PIN, and biometric lock. Your data is yours alone.' },
];

const AI_EXAMPLES = [
  '"Your savings rate is 28% — that\'s strong. But your emergency fund is only 0.8 months. Priority: build ₹2.1L buffer first."',
  '"At ₹5K/month SIP, you\'ll reach your ₹20L goal in 3.2 years at 12% CAGR — you\'re 6 months ahead of schedule."',
  '"Switching to New Tax Regime saves you ₹46,800/year at your income level. Current deductions don\'t offset the benefit."',
];

export default function IntroScreen() {
  const { user, loading } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(24)).current;

  useEffect(() => {
    if (!loading && user) router.replace('/(tabs)');
  }, [loading, user]);

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 700, useNativeDriver: true }),
    ]).start();
  }, []);

  if (loading) {
    return (
      <View style={[s.center, { backgroundColor: '#0F172A' }]}>
        <ActivityIndicator size="large" color="#10B981" />
      </View>
    );
  }
  if (user) return null;

  return (
    <SafeAreaView style={[s.safe, { backgroundColor: isDark ? '#0F172A' : '#F8FAFC' }]}>
      {/* ── Nav Bar ── */}
      <View style={[s.nav, { borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)', backgroundColor: isDark ? 'rgba(15,23,42,0.98)' : 'rgba(248,250,252,0.98)' }]}>
        <View style={s.navLogo}>
          <LinearGradient colors={['#10B981', '#059669']} style={s.logoMini}>
            <MaterialCommunityIcons name="shield-check" size={16} color="#fff" />
          </LinearGradient>
          <Text style={[s.navLogoText, { color: colors.textPrimary }]}>Visor</Text>
          <View style={s.badge}><Text style={s.badgeText}>BETA</Text></View>
        </View>
        <View style={s.navBtns}>
          <TouchableOpacity data-testid="intro-login-btn" style={[s.loginBtn, { borderColor: isDark ? 'rgba(255,255,255,0.14)' : 'rgba(0,0,0,0.1)' }]} onPress={() => router.push('/(auth)/login')}>
            <Text style={[s.loginBtnText, { color: colors.textPrimary }]}>Log In</Text>
          </TouchableOpacity>
          <TouchableOpacity data-testid="intro-signup-btn" onPress={() => router.push('/(auth)/register')}>
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={s.signupBtn}>
              <Text style={s.signupBtnText}>Sign Up</Text>
            </LinearGradient>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={s.scroll}>

        {/* ── HERO ── */}
        <Animated.View style={[s.hero, { opacity: fadeAnim, transform: [{ translateY: slideAnim }] }]}>
          {/* Pill badges */}
          <View style={s.heroBadges}>
            {['🇮🇳 India-Focused', 'AI-Powered', '100% Free'].map((b, i) => (
              <View key={i} style={[s.heroPill, { backgroundColor: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(16,185,129,0.08)', borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.2)' }]}>
                <Text style={[s.heroPillText, { color: '#10B981' }]}>{b}</Text>
              </View>
            ))}
          </View>

          <Text style={[s.heroTitle, { color: colors.textPrimary }]}>
            Your Money.{'\n'}Understood.{'\n'}Finally.
          </Text>
          <Text style={[s.heroSub, { color: colors.textSecondary }]}>
            Visor is India's smartest AI-powered personal finance tracker. Track spending, grow investments, plan taxes — all in one beautifully simple app.
          </Text>

          <TouchableOpacity data-testid="hero-get-started-btn" style={s.heroCTA} onPress={() => router.push('/(auth)/register')}>
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={s.heroCTAInner}>
              <Text style={s.heroCTAText}>Get Started Free</Text>
              <MaterialCommunityIcons name="arrow-right" size={20} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
          <TouchableOpacity style={[s.heroSecondary, { borderColor: isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)' }]} onPress={() => router.push('/(auth)/login')}>
            <Text style={[s.heroSecondaryText, { color: colors.textSecondary }]}>Already have an account?  <Text style={{ color: '#10B981', fontWeight: '700' }}>Log In</Text></Text>
          </TouchableOpacity>

          {/* Dashboard screenshot */}
          <View style={s.heroImgWrap}>
            <Image source={{ uri: SCREENSHOTS.dashboard }} style={s.heroImg} resizeMode="cover" />
            <LinearGradient colors={['transparent', isDark ? '#0F172A' : '#F8FAFC']} style={s.heroImgFade} />
          </View>
        </Animated.View>

        {/* ── STATS BAR ── */}
        <View style={[s.statsBar, { backgroundColor: isDark ? 'rgba(16,185,129,0.06)' : 'rgba(16,185,129,0.04)', borderColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.12)' }]}>
          {[
            { num: '12+', label: 'Features' },
            { num: '1000', label: 'Health Points' },
            { num: 'AI', label: 'Advisor' },
            { num: '8', label: 'Screens' },
          ].map((s2, i) => (
            <View key={i} style={st.statItem}>
              <Text style={[st.statNum, { color: '#10B981' }]}>{s2.num}</Text>
              <Text style={[st.statLabel, { color: colors.textSecondary }]}>{s2.label}</Text>
            </View>
          ))}
        </View>

        {/* ── FINANCIAL HEALTH SCORE ── */}
        <View style={s.section}>
          <View style={s.sectionTag}>
            <MaterialCommunityIcons name="star-four-points" size={14} color="#10B981" />
            <Text style={s.sectionTagText}>SIGNATURE FEATURE</Text>
          </View>
          <Text style={[s.sectionTitle, { color: colors.textPrimary }]}>
            One Score.{'\n'}Eight Dimensions.
          </Text>
          <Text style={[s.sectionSub, { color: colors.textSecondary }]}>
            Visor calculates a 0–1000 Financial Health Score across 8 key dimensions. Know exactly where you shine — and where to improve.
          </Text>

          <View style={[s.scoreCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : '#fff', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
            {/* Score number */}
            <View style={s.scoreNumRow}>
              <LinearGradient colors={['#10B981', '#059669']} style={s.scoreCircle}>
                <Text style={s.scoreNum}>748</Text>
                <Text style={s.scoreLabel}>/ 1000</Text>
              </LinearGradient>
              <View style={{ flex: 1, marginLeft: 16 }}>
                <Text style={[s.scoreGrade, { color: '#10B981' }]}>Good</Text>
                <Text style={[s.scoreDesc, { color: colors.textSecondary }]}>Your finances are on a strong foundation. A few tweaks to reach Excellent.</Text>
              </View>
            </View>
            {/* 8 dimensions grid */}
            <View style={s.dimsGrid}>
              {HEALTH_DIMS.map((d, i) => (
                <View key={i} style={[s.dimItem, { backgroundColor: d.color + '12' }]}>
                  <MaterialCommunityIcons name={d.icon as any} size={18} color={d.color} />
                  <Text style={[s.dimLabel, { color: colors.textPrimary }]}>{d.label}</Text>
                </View>
              ))}
            </View>
          </View>
        </View>

        {/* ── FEATURES GRID ── */}
        <View style={s.section}>
          <View style={s.sectionTag}>
            <MaterialCommunityIcons name="view-grid" size={14} color="#3B82F6" />
            <Text style={[s.sectionTagText, { color: '#3B82F6' }]}>EVERYTHING YOU NEED</Text>
          </View>
          <Text style={[s.sectionTitle, { color: colors.textPrimary }]}>Built for your entire{'\n'}financial life</Text>

          <View style={s.featureGrid}>
            {FEATURES.map((f, i) => (
              <View key={i} style={[s.featureCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : '#fff', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                <View style={[s.featureIcon, { backgroundColor: f.bg }]}>
                  <MaterialCommunityIcons name={f.icon} size={22} color={f.color} />
                </View>
                <Text style={[s.featureTitle, { color: colors.textPrimary }]}>{f.title}</Text>
                <Text style={[s.featureDesc, { color: colors.textSecondary }]}>{f.desc}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ── VISOR AI SECTION ── */}
        <View style={[s.aiSection, { backgroundColor: isDark ? 'rgba(59,130,246,0.06)' : 'rgba(59,130,246,0.04)', borderColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.12)' }]}>
          <View style={s.sectionTag}>
            <MaterialCommunityIcons name="robot" size={14} color="#3B82F6" />
            <Text style={[s.sectionTagText, { color: '#3B82F6' }]}>VISOR AI</Text>
          </View>
          <Text style={[s.sectionTitle, { color: colors.textPrimary }]}>
            An AI that actually{'\n'}knows your numbers
          </Text>
          <Text style={[s.sectionSub, { color: colors.textSecondary }]}>
            Unlike generic chatbots, Visor AI reads your real financial data and responds with exact amounts, benchmark comparisons, and step-by-step actions.
          </Text>

          {AI_EXAMPLES.map((ex, i) => (
            <View key={i} style={[s.aiExample, { backgroundColor: isDark ? 'rgba(59,130,246,0.08)' : 'rgba(59,130,246,0.06)', borderColor: isDark ? 'rgba(59,130,246,0.2)' : 'rgba(59,130,246,0.15)' }]}>
              <MaterialCommunityIcons name="robot" size={16} color="#3B82F6" style={{ marginTop: 2 }} />
              <Text style={[s.aiExampleText, { color: colors.textPrimary }]}>{ex}</Text>
            </View>
          ))}

          <View style={s.aiScreenRow}>
            <Image source={{ uri: SCREENSHOTS.ai }} style={s.aiScreen} resizeMode="cover" />
          </View>
        </View>

        {/* ── JAR GOALS SECTION ── */}
        <View style={s.section}>
          <View style={s.sectionTag}>
            <MaterialCommunityIcons name="target" size={14} color="#F59E0B" />
            <Text style={[s.sectionTagText, { color: '#F59E0B' }]}>FINANCIAL GOALS</Text>
          </View>
          <Text style={[s.sectionTitle, { color: colors.textPrimary }]}>
            Goals that fill up{'\n'}like money jars
          </Text>
          <Text style={[s.sectionSub, { color: colors.textSecondary }]}>
            Every goal gets its own money jar. As you save, the jar fills up with a liquid animation. Visual, motivating, and oddly satisfying.
          </Text>

          <View style={[s.goalsShowcase, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : '#fff', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
            {[
              { title: 'Emergency Fund', pct: 62, color: '#10B981', saved: '₹1.9L', target: '₹3.0L' },
              { title: 'Goa Trip', pct: 64, color: '#3B82F6', saved: '₹32K', target: '₹50K' },
              { title: 'New Laptop', pct: 56, color: '#F59E0B', saved: '₹28K', target: '₹50K' },
            ].map((goal, i) => (
              <View key={i} style={[s.goalPreview, { borderColor: goal.color + '25' }]}>
                {/* Simplified jar graphic using rectangles */}
                <View style={[s.jarContainer, { borderColor: goal.color + '50' }]}>
                  <View style={[s.jarFill, { height: `${goal.pct}%` as any, backgroundColor: goal.color + 'AA' }]} />
                  <Text style={[s.jarPct, { color: goal.pct > 55 ? '#fff' : goal.color }]}>{goal.pct}%</Text>
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={[s.goalPreviewTitle, { color: colors.textPrimary }]}>{goal.title}</Text>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 }}>
                    <Text style={[s.goalPreviewAmt, { color: goal.color }]}>{goal.saved}</Text>
                    <Text style={[s.goalPreviewAmt, { color: colors.textSecondary }]}>{goal.target}</Text>
                  </View>
                </View>
              </View>
            ))}
          </View>
        </View>

        {/* ── APP SCREENSHOTS ROW ── */}
        <View style={s.section}>
          <View style={s.sectionTag}>
            <MaterialCommunityIcons name="cellphone" size={14} color="#8B5CF6" />
            <Text style={[s.sectionTagText, { color: '#8B5CF6' }]}>THE FULL PICTURE</Text>
          </View>
          <Text style={[s.sectionTitle, { color: colors.textPrimary }]}>One app.{'\n'}Complete financial clarity.</Text>

          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.screenshotRow}>
            {[SCREENSHOTS.insights, SCREENSHOTS.invest1, SCREENSHOTS.emi, SCREENSHOTS.creditCard, SCREENSHOTS.tax].map((uri, i) => (
              <Image key={i} source={{ uri }} style={s.screenshot} resizeMode="cover" />
            ))}
          </ScrollView>
        </View>

        {/* ── SECURITY SECTION ── */}
        <View style={[s.securitySection, { backgroundColor: isDark ? 'rgba(16,185,129,0.05)' : 'rgba(16,185,129,0.03)', borderColor: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(16,185,129,0.1)' }]}>
          <MaterialCommunityIcons name="shield-check" size={36} color="#10B981" style={{ marginBottom: 12 }} />
          <Text style={[s.sectionTitle, { color: colors.textPrimary, textAlign: 'center' }]}>Your data. Your control.</Text>
          <Text style={[s.sectionSub, { color: colors.textSecondary, textAlign: 'center' }]}>
            Your financial data is protected with industry-leading security. No sharing, no selling, no compromises.
          </Text>
          <View style={s.securityItems}>
            {[
              { icon: 'lock', label: 'AES-256 Encryption' },
              { icon: 'fingerprint', label: 'Biometric Lock' },
              { icon: 'dialpad', label: '4-Digit PIN' },
              { icon: 'eye-off', label: 'Private by Default' },
            ].map((sec, i) => (
              <View key={i} style={[s.secItem, { backgroundColor: isDark ? 'rgba(16,185,129,0.08)' : 'rgba(16,185,129,0.06)' }]}>
                <MaterialCommunityIcons name={sec.icon as any} size={20} color="#10B981" />
                <Text style={[s.secLabel, { color: colors.textPrimary }]}>{sec.label}</Text>
              </View>
            ))}
          </View>
        </View>

        {/* ── FINAL CTA ── */}
        <View style={s.finalCTA}>
          <Text style={[s.finalTitle, { color: colors.textPrimary }]}>
            Take control of your{'\n'}financial story.
          </Text>
          <Text style={[s.finalSub, { color: colors.textSecondary }]}>
            Smart tracking. Intelligent insights. Real clarity.{'\n'}Your journey starts here — and it's free.
          </Text>
          <TouchableOpacity data-testid="bottom-get-started-btn" style={s.heroCTA} onPress={() => router.push('/(auth)/register')}>
            <LinearGradient colors={['#10B981', '#059669']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={s.heroCTAInner}>
              <Text style={s.heroCTAText}>Create Free Account</Text>
              <MaterialCommunityIcons name="arrow-right" size={20} color="#fff" />
            </LinearGradient>
          </TouchableOpacity>
          <View style={s.finalBadges}>
            {['No credit card required', 'Free forever', 'Cancel anytime'].map((b, i) => (
              <View key={i} style={s.finalBadge}>
                <MaterialCommunityIcons name="check-circle" size={13} color="#10B981" />
                <Text style={[s.finalBadgeText, { color: colors.textSecondary }]}>{b}</Text>
              </View>
            ))}
          </View>
        </View>

        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

// ── Named alias for stats bar styles (avoid collision with shadow 's') ──
const st = StyleSheet.create({
  statItem: { alignItems: 'center' },
  statNum: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '800' },
  statLabel: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 2 },
});

const s = StyleSheet.create({
  safe: { flex: 1 },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  scroll: { paddingBottom: 20 },

  // Nav
  nav: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 16, paddingVertical: 10, borderBottomWidth: 1 },
  navLogo: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  logoMini: { width: 28, height: 28, borderRadius: 9, justifyContent: 'center', alignItems: 'center' },
  navLogoText: { fontSize: 19, fontFamily: 'DM Sans', fontWeight: '800' },
  badge: { backgroundColor: 'rgba(16,185,129,0.15)', borderRadius: 4, paddingHorizontal: 5, paddingVertical: 1 },
  badgeText: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '700', color: '#10B981', letterSpacing: 0.5 },
  navBtns: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  loginBtn: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 9, borderWidth: 1.5 },
  loginBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  signupBtn: { paddingHorizontal: 14, paddingVertical: 7, borderRadius: 9 },
  signupBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },

  // Hero
  hero: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 36, paddingBottom: 0 },
  heroBadges: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, justifyContent: 'center', marginBottom: 24 },
  heroPill: { paddingHorizontal: 12, paddingVertical: 5, borderRadius: 20, borderWidth: 1 },
  heroPillText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' },
  heroTitle: { fontSize: 38, fontFamily: 'DM Sans', fontWeight: '800', textAlign: 'center', letterSpacing: -1, lineHeight: 46, marginBottom: 16 },
  heroSub: { fontSize: 15, fontFamily: 'DM Sans', textAlign: 'center', lineHeight: 23, marginBottom: 28, paddingHorizontal: 8 },
  heroCTA: { width: '100%', borderRadius: 14, overflow: 'hidden', marginBottom: 12 },
  heroCTAInner: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, height: 52 },
  heroCTAText: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  heroSecondary: { paddingVertical: 12, paddingHorizontal: 20, borderRadius: 12, borderWidth: 1, marginBottom: 28 },
  heroSecondaryText: { fontSize: 14, fontFamily: 'DM Sans' },
  heroImgWrap: { width: '100%', height: 200, borderRadius: 20, overflow: 'hidden', marginBottom: 0 },
  heroImg: { width: '100%', height: '100%' },
  heroImgFade: { position: 'absolute', bottom: 0, left: 0, right: 0, height: 80 },

  // Stats bar
  statsBar: { flexDirection: 'row', justifyContent: 'space-around', marginHorizontal: 20, marginVertical: 20, paddingVertical: 16, borderRadius: 16, borderWidth: 1 },

  // Section common
  section: { paddingHorizontal: 20, paddingTop: 32, paddingBottom: 8 },
  sectionTag: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 10 },
  sectionTagText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', color: '#10B981', letterSpacing: 1 },
  sectionTitle: { fontSize: 26, fontFamily: 'DM Sans', fontWeight: '800', letterSpacing: -0.5, lineHeight: 33, marginBottom: 10 },
  sectionSub: { fontSize: 14, fontFamily: 'DM Sans', lineHeight: 22, marginBottom: 20 },

  // Health Score
  scoreCard: { borderRadius: 18, borderWidth: 1, padding: 20 },
  scoreNumRow: { flexDirection: 'row', alignItems: 'center', marginBottom: 20 },
  scoreCircle: { width: 80, height: 80, borderRadius: 40, justifyContent: 'center', alignItems: 'center' },
  scoreNum: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '800', color: '#fff' },
  scoreLabel: { fontSize: 10, color: 'rgba(255,255,255,0.7)', fontFamily: 'DM Sans' },
  scoreGrade: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '800', marginBottom: 6 },
  scoreDesc: { fontSize: 13, fontFamily: 'DM Sans', lineHeight: 19 },
  dimsGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  dimItem: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10 },
  dimLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '500' },

  // Features Grid
  featureGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  featureCard: { width: (W - 50) / 2, padding: 16, borderRadius: 16, borderWidth: 1 },
  featureIcon: { width: 42, height: 42, borderRadius: 12, justifyContent: 'center', alignItems: 'center', marginBottom: 10 },
  featureTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 4 },
  featureDesc: { fontSize: 12, fontFamily: 'DM Sans', lineHeight: 17 },

  // AI Section
  aiSection: { marginHorizontal: 20, marginVertical: 12, borderRadius: 20, padding: 20, borderWidth: 1 },
  aiExample: { flexDirection: 'row', gap: 10, padding: 14, borderRadius: 12, borderWidth: 1, marginBottom: 10, alignItems: 'flex-start' },
  aiExampleText: { flex: 1, fontSize: 13, fontFamily: 'DM Sans', lineHeight: 20, fontStyle: 'italic' },
  aiScreenRow: { marginTop: 16, borderRadius: 16, overflow: 'hidden', height: 180 },
  aiScreen: { width: '100%', height: '100%' },

  // Goals Showcase
  goalsShowcase: { borderRadius: 18, borderWidth: 1, padding: 16, gap: 10 },
  goalPreview: { flexDirection: 'row', alignItems: 'center', gap: 14, borderWidth: 1, borderRadius: 12, padding: 12 },
  jarContainer: { width: 48, height: 64, borderRadius: 8, borderWidth: 2, overflow: 'hidden', justifyContent: 'flex-end', position: 'relative', backgroundColor: 'rgba(255,255,255,0.04)' },
  jarFill: { width: '100%', borderRadius: 4 },
  jarPct: { position: 'absolute', width: '100%', textAlign: 'center', top: '45%', fontSize: 10, fontFamily: 'DM Sans', fontWeight: '800' },
  goalPreviewTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' },
  goalPreviewAmt: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },

  // Screenshots row
  screenshotRow: { gap: 12, paddingVertical: 8 },
  screenshot: { width: W * 0.45, height: 200, borderRadius: 16 },

  // Security
  securitySection: { marginHorizontal: 20, marginVertical: 12, borderRadius: 20, padding: 24, borderWidth: 1, alignItems: 'center' },
  securityItems: { flexDirection: 'row', flexWrap: 'wrap', gap: 10, justifyContent: 'center', marginTop: 16 },
  secItem: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20 },
  secLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' },

  // Final CTA
  finalCTA: { alignItems: 'center', paddingHorizontal: 24, paddingTop: 36, paddingBottom: 8 },
  finalTitle: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '800', textAlign: 'center', letterSpacing: -0.5, lineHeight: 36, marginBottom: 12 },
  finalSub: { fontSize: 14, fontFamily: 'DM Sans', textAlign: 'center', lineHeight: 22, marginBottom: 28 },
  finalBadges: { flexDirection: 'row', flexWrap: 'wrap', gap: 16, justifyContent: 'center', marginTop: 16 },
  finalBadge: { flexDirection: 'row', alignItems: 'center', gap: 5 },
  finalBadgeText: { fontSize: 12, fontFamily: 'DM Sans' },
});
