import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';

export default function LoginScreen() {
  const { login } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert('Error', 'Please fill in all fields');
      return;
    }
    setLoading(true);
    try {
      await login(email.trim(), password);
      router.replace('/(tabs)');
    } catch (e: any) {
      Alert.alert('Login Failed', e.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  const fillDemo = (num: number) => {
    if (num === 1) { setEmail('rajesh@visor.demo'); setPassword('Demo@123'); }
    else { setEmail('priya@visor.demo'); setPassword('Demo@456'); }
  };

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          {/* Logo */}
          <View style={styles.logoContainer}>
            <View style={[styles.logoCircle, { backgroundColor: colors.primary }]}>
              <MaterialCommunityIcons name="shield-check" size={40} color="#fff" />
            </View>
            <Text style={[styles.appName, { color: colors.textPrimary }]}>Visor</Text>
            <Text style={[styles.tagline, { color: colors.textSecondary }]}>
              AI-Powered Finance Manager
            </Text>
          </View>

          {/* Form Card */}
          <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Welcome Back</Text>

            <View style={styles.inputGroup}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Email</Text>
              <View style={[styles.inputWrapper, { borderColor: colors.border, backgroundColor: colors.background }]}>
                <MaterialCommunityIcons name="email-outline" size={20} color={colors.textSecondary} />
                <TextInput
                  testID="login-email-input"
                  style={[styles.input, { color: colors.textPrimary }]}
                  value={email}
                  onChangeText={setEmail}
                  placeholder="your@email.com"
                  placeholderTextColor={colors.textSecondary}
                  keyboardType="email-address"
                  autoCapitalize="none"
                />
              </View>
            </View>

            <View style={styles.inputGroup}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Password</Text>
              <View style={[styles.inputWrapper, { borderColor: colors.border, backgroundColor: colors.background }]}>
                <MaterialCommunityIcons name="lock-outline" size={20} color={colors.textSecondary} />
                <TextInput
                  testID="login-password-input"
                  style={[styles.input, { color: colors.textPrimary }]}
                  value={password}
                  onChangeText={setPassword}
                  placeholder="Enter password"
                  placeholderTextColor={colors.textSecondary}
                  secureTextEntry={!showPassword}
                />
                <TouchableOpacity testID="toggle-password-btn" onPress={() => setShowPassword(!showPassword)}>
                  <MaterialCommunityIcons
                    name={showPassword ? 'eye-off' : 'eye'}
                    size={20}
                    color={colors.textSecondary}
                  />
                </TouchableOpacity>
              </View>
            </View>

            <TouchableOpacity
              testID="login-submit-btn"
              style={[styles.primaryBtn, { backgroundColor: colors.primary }]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>Sign In</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity testID="goto-register-btn" onPress={() => router.push('/(auth)/register')} style={styles.linkBtn}>
              <Text style={[styles.linkText, { color: colors.textSecondary }]}>
                Don't have an account? <Text style={{ color: colors.primary, fontWeight: '600' }}>Sign Up</Text>
              </Text>
            </TouchableOpacity>
          </View>

          {/* Demo Accounts */}
          <View style={[styles.demoCard, { backgroundColor: isDark ? colors.primaryLight : '#ECFDF5', borderColor: colors.primary }]}>
            <Text style={[styles.demoTitle, { color: colors.primary }]}>
              <MaterialCommunityIcons name="test-tube" size={16} color={colors.primary} /> Demo Accounts
            </Text>
            <TouchableOpacity testID="demo-account-1-btn" style={[styles.demoBtn, { borderColor: colors.border }]} onPress={() => fillDemo(1)}>
              <View>
                <Text style={[styles.demoName, { color: colors.textPrimary }]}>Rajesh Kumar</Text>
                <Text style={[styles.demoEmail, { color: colors.textSecondary }]}>rajesh@visor.demo / Demo@123</Text>
              </View>
              <MaterialCommunityIcons name="arrow-right" size={20} color={colors.primary} />
            </TouchableOpacity>
            <TouchableOpacity testID="demo-account-2-btn" style={[styles.demoBtn, { borderColor: colors.border }]} onPress={() => fillDemo(2)}>
              <View>
                <Text style={[styles.demoName, { color: colors.textPrimary }]}>Priya Sharma</Text>
                <Text style={[styles.demoEmail, { color: colors.textSecondary }]}>priya@visor.demo / Demo@456</Text>
              </View>
              <MaterialCommunityIcons name="arrow-right" size={20} color={colors.primary} />
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 40, paddingBottom: 40 },
  logoContainer: { alignItems: 'center', marginBottom: 32 },
  logoCircle: { width: 80, height: 80, borderRadius: 40, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  appName: { fontSize: 32, fontFamily: 'Space Grotesk', fontWeight: '700' as any, letterSpacing: -1 },
  tagline: { fontSize: 15, fontFamily: 'Outfit', fontWeight: '500' as any, marginTop: 4 },
  card: { borderRadius: 24, padding: 24, borderWidth: 1, marginBottom: 24 },
  cardTitle: { fontSize: 22, fontFamily: 'Space Grotesk', fontWeight: '700' as any, marginBottom: 24, textAlign: 'center' },
  inputGroup: { marginBottom: 16 },
  label: { fontSize: 13, fontFamily: 'Outfit', fontWeight: '600' as any, marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 16, paddingHorizontal: 16, height: 52, gap: 12 },
  input: { flex: 1, fontSize: 16, fontFamily: 'Outfit', fontWeight: '400' as any, height: '100%' },
  primaryBtn: { height: 56, borderRadius: 999, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  primaryBtnText: { color: '#fff', fontSize: 17, fontFamily: 'Space Grotesk', fontWeight: '700' as any },
  linkBtn: { marginTop: 16, alignItems: 'center' },
  linkText: { fontSize: 14, fontFamily: 'Outfit', fontWeight: '500' as any },
  demoCard: { borderRadius: 20, padding: 20, borderWidth: 1, borderStyle: 'dashed' },
  demoTitle: { fontSize: 14, fontFamily: 'Outfit', fontWeight: '600' as any, marginBottom: 12 },
  demoBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderBottomWidth: 0.5 },
  demoName: { fontSize: 15, fontFamily: 'Outfit', fontWeight: '600' as any },
  demoEmail: { fontSize: 12, fontFamily: 'Outfit', fontWeight: '400' as any, marginTop: 2 },
});
