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

export default function RegisterScreen() {
  const { register } = useAuth();
  const { colors } = useTheme();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', dob: '', pan: '', aadhaar: '' });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const update = (key: string, val: string) => setForm(p => ({ ...p, [key]: val }));

  const handleRegister = async () => {
    const { full_name, email, password, dob, pan, aadhaar } = form;
    if (!full_name || !email || !password || !dob || !pan || !aadhaar) {
      Alert.alert('Error', 'All fields are required');
      return;
    }
    if (pan.length !== 10) { Alert.alert('Error', 'PAN must be 10 characters (e.g., ABCDE1234F)'); return; }
    const cleanAadhaar = aadhaar.replace(/[\s-]/g, '');
    if (cleanAadhaar.length !== 12) { Alert.alert('Error', 'Aadhaar must be 12 digits'); return; }
    if (password.length < 6) { Alert.alert('Error', 'Password must be at least 6 characters'); return; }

    setLoading(true);
    try {
      await register({ ...form, aadhaar: cleanAadhaar });
      router.replace('/(tabs)');
    } catch (e: any) {
      Alert.alert('Registration Failed', e.message || 'Please try again');
    } finally {
      setLoading(false);
    }
  };

  const fields = [
    { key: 'full_name', label: 'Full Name', icon: 'account-outline' as const, placeholder: 'Your full name', keyboard: 'default' as const },
    { key: 'email', label: 'Email', icon: 'email-outline' as const, placeholder: 'your@email.com', keyboard: 'email-address' as const },
    { key: 'password', label: 'Password', icon: 'lock-outline' as const, placeholder: 'Min 6 characters', keyboard: 'default' as const, secure: true },
    { key: 'dob', label: 'Date of Birth', icon: 'calendar' as const, placeholder: 'YYYY-MM-DD', keyboard: 'default' as const },
    { key: 'pan', label: 'PAN Number', icon: 'card-account-details-outline' as const, placeholder: 'ABCDE1234F', keyboard: 'default' as const },
    { key: 'aadhaar', label: 'Aadhaar Number', icon: 'fingerprint' as const, placeholder: '1234 5678 9012', keyboard: 'number-pad' as const },
  ];

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <TouchableOpacity testID="back-to-login-btn" onPress={() => router.back()} style={styles.backBtn}>
            <MaterialCommunityIcons name="arrow-left" size={24} color={colors.textPrimary} />
          </TouchableOpacity>

          <View style={styles.header}>
            <Text style={[styles.title, { color: colors.textPrimary }]}>Create Account</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Secure your finances with Visor
            </Text>
          </View>

          <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            {fields.map((f) => (
              <View key={f.key} style={styles.inputGroup}>
                <Text style={[styles.label, { color: colors.textSecondary }]}>{f.label}</Text>
                <View style={[styles.inputWrapper, { borderColor: colors.border, backgroundColor: colors.background }]}>
                  <MaterialCommunityIcons name={f.icon} size={20} color={colors.textSecondary} />
                  <TextInput
                    testID={`register-${f.key}-input`}
                    style={[styles.input, { color: colors.textPrimary }]}
                    value={(form as any)[f.key]}
                    onChangeText={(v) => update(f.key, f.key === 'pan' ? v.toUpperCase() : v)}
                    placeholder={f.placeholder}
                    placeholderTextColor={colors.textSecondary}
                    keyboardType={f.keyboard}
                    autoCapitalize={f.key === 'email' ? 'none' : f.key === 'pan' ? 'characters' : 'words'}
                    secureTextEntry={f.secure && !showPassword}
                  />
                  {f.secure && (
                    <TouchableOpacity onPress={() => setShowPassword(!showPassword)}>
                      <MaterialCommunityIcons name={showPassword ? 'eye-off' : 'eye'} size={20} color={colors.textSecondary} />
                    </TouchableOpacity>
                  )}
                </View>
              </View>
            ))}

            <TouchableOpacity
              testID="register-submit-btn"
              style={[styles.primaryBtn, { backgroundColor: colors.primary }]}
              onPress={handleRegister}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.primaryBtnText}>Create Account</Text>
              )}
            </TouchableOpacity>
          </View>

          <TouchableOpacity testID="goto-login-btn" onPress={() => router.back()} style={styles.linkBtn}>
            <Text style={[styles.linkText, { color: colors.textSecondary }]}>
              Already have an account? <Text style={{ color: colors.primary, fontWeight: '600' }}>Sign In</Text>
            </Text>
          </TouchableOpacity>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, paddingHorizontal: 24, paddingTop: 16, paddingBottom: 40 },
  backBtn: { width: 44, height: 44, justifyContent: 'center' },
  header: { marginBottom: 24 },
  title: { fontSize: 28, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5 },
  subtitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 4 },
  card: { borderRadius: 24, padding: 24, borderWidth: 1, marginBottom: 16 },
  inputGroup: { marginBottom: 14 },
  label: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 4, textTransform: 'uppercase', letterSpacing: 0.5 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 14, paddingHorizontal: 14, height: 48, gap: 10 },
  input: { flex: 1, fontSize: 15, fontFamily: 'DM Sans', fontWeight: '400' as any, height: '100%' },
  primaryBtn: { height: 56, borderRadius: 999, justifyContent: 'center', alignItems: 'center', marginTop: 8 },
  primaryBtnText: { color: '#fff', fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any },
  linkBtn: { marginTop: 12, alignItems: 'center' },
  linkText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '500' as any },
});
