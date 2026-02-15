import React from 'react';
import { View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { colors, isDark, themeMode, setThemeMode } = useTheme();
  const router = useRouter();

  const handleLogout = () => {
    Alert.alert('Logout', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Sign Out', style: 'destructive', onPress: async () => {
        await logout();
        router.replace('/(auth)/login');
      }},
    ]);
  };

  const themes: Array<{ key: 'light' | 'dark' | 'system'; label: string; icon: any }> = [
    { key: 'light', label: 'Light', icon: 'white-balance-sunny' },
    { key: 'dark', label: 'Dark', icon: 'moon-waning-crescent' },
    { key: 'system', label: 'System', icon: 'cellphone' },
  ];

  return (
    <SafeAreaView style={[styles.safe, { backgroundColor: colors.background }]}>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: colors.textPrimary }]}>Settings</Text>

        {/* Profile Card */}
        <View style={[styles.profileCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <View style={[styles.avatarLarge, { backgroundColor: colors.primary }]}>
            <Text style={styles.avatarText}>{user?.full_name?.charAt(0)?.toUpperCase() || 'V'}</Text>
          </View>
          <Text style={[styles.profileName, { color: colors.textPrimary }]}>{user?.full_name || 'User'}</Text>
          <Text style={[styles.profileEmail, { color: colors.textSecondary }]}>{user?.email}</Text>
          <View style={[styles.profileDivider, { backgroundColor: colors.border }]} />
          <View style={styles.profileDetails}>
            <ProfileDetail icon="calendar" label="DOB" value={user?.dob || 'N/A'} colors={colors} />
            <ProfileDetail icon="card-account-details" label="PAN" value={user?.pan || 'N/A'} colors={colors} />
            <ProfileDetail icon="fingerprint" label="Aadhaar" value={user?.aadhaar_last4 ? `XXXX XXXX ${user.aadhaar_last4}` : 'N/A'} colors={colors} />
          </View>
        </View>

        {/* Theme Section */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Appearance</Text>
        <View style={[styles.themeCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          {themes.map(t => (
            <TouchableOpacity
              key={t.key}
              testID={`theme-${t.key}-btn`}
              style={[styles.themeOption, {
                backgroundColor: themeMode === t.key ? (isDark ? colors.primaryLight : '#D1FAE5') : 'transparent',
                borderColor: themeMode === t.key ? colors.primary : colors.border,
              }]}
              onPress={() => setThemeMode(t.key)}
            >
              <MaterialCommunityIcons name={t.icon} size={24} color={themeMode === t.key ? colors.primary : colors.textSecondary} />
              <Text style={[styles.themeLabel, { color: themeMode === t.key ? colors.primary : colors.textPrimary }]}>{t.label}</Text>
              {themeMode === t.key && (
                <MaterialCommunityIcons name="check-circle" size={20} color={colors.primary} />
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* App Info */}
        <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>About</Text>
        <View style={[styles.infoCard, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <InfoRow icon="shield-check" label="App Version" value="1.0.0" colors={colors} />
          <InfoRow icon="robot" label="AI Model" value="GPT-5.2" colors={colors} />
          <InfoRow icon="database" label="Data Storage" value="Secure Cloud" colors={colors} />
          <InfoRow icon="currency-inr" label="Currency" value="Indian Rupee (₹)" colors={colors} />
        </View>

        {/* Logout */}
        <TouchableOpacity
          testID="logout-btn"
          style={[styles.logoutBtn, { borderColor: colors.error }]}
          onPress={handleLogout}
        >
          <MaterialCommunityIcons name="logout" size={20} color={colors.error} />
          <Text style={[styles.logoutText, { color: colors.error }]}>Sign Out</Text>
        </TouchableOpacity>

        <Text style={[styles.footer, { color: colors.textSecondary }]}>
          Visor Finance · Built with AI
        </Text>
        <View style={{ height: 40 }} />
      </ScrollView>
    </SafeAreaView>
  );
}

function ProfileDetail({ icon, label, value, colors }: { icon: any; label: string; value: string; colors: any }) {
  return (
    <View style={styles.detailRow}>
      <MaterialCommunityIcons name={icon} size={18} color={colors.textSecondary} />
      <Text style={[styles.detailLabel, { color: colors.textSecondary }]}>{label}</Text>
      <Text style={[styles.detailValue, { color: colors.textPrimary }]}>{value}</Text>
    </View>
  );
}

function InfoRow({ icon, label, value, colors }: { icon: any; label: string; value: string; colors: any }) {
  return (
    <View style={[styles.infoRow, { borderBottomColor: colors.border }]}>
      <MaterialCommunityIcons name={icon} size={20} color={colors.primary} />
      <Text style={[styles.infoLabel, { color: colors.textPrimary }]}>{label}</Text>
      <Text style={[styles.infoValue, { color: colors.textSecondary }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1 },
  scroll: { paddingHorizontal: 20, paddingTop: 20 },
  title: { fontSize: 28, fontWeight: '800', letterSpacing: -0.5, marginBottom: 20 },

  profileCard: { borderRadius: 24, padding: 24, borderWidth: 1, alignItems: 'center', marginBottom: 24 },
  avatarLarge: { width: 72, height: 72, borderRadius: 36, justifyContent: 'center', alignItems: 'center', marginBottom: 12 },
  avatarText: { color: '#fff', fontSize: 28, fontWeight: '800' },
  profileName: { fontSize: 20, fontWeight: '700' },
  profileEmail: { fontSize: 14, marginTop: 4 },
  profileDivider: { width: '100%', height: 1, marginVertical: 16 },
  profileDetails: { width: '100%', gap: 12 },
  detailRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  detailLabel: { fontSize: 13, width: 60 },
  detailValue: { fontSize: 14, fontWeight: '600', flex: 1 },

  sectionTitle: { fontSize: 17, fontWeight: '700', marginBottom: 12 },
  themeCard: { borderRadius: 20, borderWidth: 1, overflow: 'hidden', marginBottom: 24 },
  themeOption: { flexDirection: 'row', alignItems: 'center', paddingVertical: 16, paddingHorizontal: 20, gap: 14, borderWidth: 1, borderColor: 'transparent' },
  themeLabel: { flex: 1, fontSize: 15, fontWeight: '600' },

  infoCard: { borderRadius: 20, borderWidth: 1, overflow: 'hidden', marginBottom: 24 },
  infoRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 14, paddingHorizontal: 20, gap: 14, borderBottomWidth: 0.5 },
  infoLabel: { flex: 1, fontSize: 14, fontWeight: '500' },
  infoValue: { fontSize: 14 },

  logoutBtn: { flexDirection: 'row', justifyContent: 'center', alignItems: 'center', gap: 8, paddingVertical: 16, borderRadius: 20, borderWidth: 1.5 },
  logoutText: { fontSize: 16, fontWeight: '700' },

  footer: { textAlign: 'center', fontSize: 12, marginTop: 24 },
});
