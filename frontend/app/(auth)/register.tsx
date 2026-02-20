import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, ScrollView,
  KeyboardAvoidingView, Platform, ActivityIndicator, Alert, Modal,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';

export default function RegisterScreen() {
  const { register } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();
  const [form, setForm] = useState({ full_name: '', email: '', password: '', dob: '', pan: '', aadhaar: '' });
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // DOB picker state
  const [showDobPicker, setShowDobPicker] = useState(false);
  const [dobDate, setDobDate] = useState(new Date(2000, 0, 1));

  const update = (key: string, val: string) => setForm(p => ({ ...p, [key]: val }));

  const openDobPicker = () => {
    if (form.dob) {
      const d = new Date(form.dob);
      if (!isNaN(d.getTime())) setDobDate(d);
    }
    setShowDobPicker(true);
  };

  const handleDobChange = (event: any, date?: Date) => {
    if (Platform.OS === 'android') setShowDobPicker(false);
    if (date) {
      setDobDate(date);
      if (Platform.OS === 'android') {
        update('dob', date.toISOString().split('T')[0]);
      }
    }
  };

  const confirmIosDob = () => {
    update('dob', dobDate.toISOString().split('T')[0]);
    setShowDobPicker(false);
  };

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

  const textFields = [
    { key: 'full_name', label: 'Full Name', icon: 'account-outline' as const, placeholder: 'Your full name', keyboard: 'default' as const },
    { key: 'email', label: 'Email', icon: 'email-outline' as const, placeholder: 'your@email.com', keyboard: 'email-address' as const },
    { key: 'password', label: 'Password', icon: 'lock-outline' as const, placeholder: 'Min 6 characters', keyboard: 'default' as const, secure: true },
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
            {/* Full Name, Email, Password */}
            {textFields.slice(0, 3).map((f) => (
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
                    autoCapitalize={f.key === 'email' ? 'none' : 'words'}
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

            {/* Date of Birth — Calendar Picker */}
            <View style={styles.inputGroup}>
              <Text style={[styles.label, { color: colors.textSecondary }]}>Date of Birth</Text>
              <TouchableOpacity
                testID="register-dob-picker"
                style={[styles.inputWrapper, { borderColor: colors.border, backgroundColor: colors.background }]}
                onPress={openDobPicker}
                activeOpacity={0.7}
              >
                <MaterialCommunityIcons name="calendar" size={20} color={colors.textSecondary} />
                <Text style={[styles.input, { color: form.dob ? colors.textPrimary : colors.textSecondary, lineHeight: 48 }]}>
                  {form.dob
                    ? new Date(form.dob).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })
                    : 'Select your date of birth'}
                </Text>
                <MaterialCommunityIcons name="chevron-down" size={20} color={colors.textSecondary} />
              </TouchableOpacity>

              {/* Inline iOS DOB picker */}
              {showDobPicker && Platform.OS === 'ios' && (
                <View style={[styles.iosPickerWrap, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                  <View style={[styles.iosPickerHeader, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }]}>
                    <TouchableOpacity onPress={() => setShowDobPicker(false)}>
                      <Text style={{ fontSize: 14, color: '#EF4444', fontFamily: 'DM Sans', fontWeight: '600' }}>Cancel</Text>
                    </TouchableOpacity>
                    <Text style={{ fontSize: 13, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '700' }}>Date of Birth</Text>
                    <TouchableOpacity onPress={confirmIosDob}>
                      <Text style={{ fontSize: 14, color: colors.primary, fontFamily: 'DM Sans', fontWeight: '700' }}>Done</Text>
                    </TouchableOpacity>
                  </View>
                  <DateTimePicker
                    value={dobDate}
                    mode="date"
                    display="spinner"
                    themeVariant={isDark ? 'dark' : 'light'}
                    maximumDate={new Date()}
                    minimumDate={new Date(1940, 0, 1)}
                    onChange={(e: any, d?: Date) => { if (d) setDobDate(d); }}
                    style={{ height: 150 }}
                  />
                </View>
              )}
            </View>

            {/* PAN, Aadhaar */}
            {textFields.slice(3).map((f) => (
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
                    autoCapitalize={f.key === 'pan' ? 'characters' : 'none'}
                  />
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

      {/* Android DOB picker (native dialog) */}
      {showDobPicker && Platform.OS === 'android' && (
        <DateTimePicker
          value={dobDate}
          mode="date"
          display="default"
          maximumDate={new Date()}
          minimumDate={new Date(1940, 0, 1)}
          onChange={handleDobChange}
        />
      )}
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
  iosPickerWrap: { borderWidth: 1, borderRadius: 12, overflow: 'hidden', marginTop: 6 },
  iosPickerHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8 },
});
