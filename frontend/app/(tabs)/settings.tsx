import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert,
  Switch, TextInput, Platform, StatusBar, Modal, Dimensions,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import Slider from '@react-native-community/slider';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const TABS = [
  { key: 'account', label: 'Account', icon: 'account' },
  { key: 'security', label: 'Security', icon: 'shield-check' },
  { key: 'notifications', label: 'Alerts', icon: 'bell' },
  { key: 'financial', label: 'Financial', icon: 'target' },
  { key: 'appearance', label: 'Theme', icon: 'palette' },
  { key: 'data', label: 'Data', icon: 'download' },
];

export default function SettingsScreen() {
  const { user, logout } = useAuth();
  const { colors, isDark, themeMode, setThemeMode } = useTheme();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('account');
  const [showPan, setShowPan] = useState(false);
  const [showAadhaar, setShowAadhaar] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  // Settings state
  const [settings, setSettings] = useState({
    biometric: true,
    twoFactor: false,
    smsParsing: true,
    emailNotifications: true,
    pushNotifications: true,
    currency: 'INR',
    savingsTarget: 30,
    riskTolerance: 'Moderate',
    autoInvestment: false,
  });

  const handleLogout = () => {
    Alert.alert('Sign Out', 'Are you sure you want to sign out?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign Out',
        style: 'destructive',
        onPress: async () => {
          await logout();
          router.replace('/(auth)/login');
        },
      },
    ]);
  };

  const handleDeleteAccount = () => {
    if (deleteConfirmText.toUpperCase() === 'DELETE') {
      Alert.alert('Account Deleted', 'Your account has been permanently deleted.', [
        {
          text: 'OK',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]);
      setShowDeleteModal(false);
    } else {
      Alert.alert('Error', 'Please type DELETE to confirm.');
    }
  };

  const handleExportData = () => {
    Alert.alert('Export Data', 'Your financial data has been prepared for download.', [
      { text: 'Download CSV', onPress: () => Alert.alert('Success', 'Data exported successfully!') },
      { text: 'Cancel', style: 'cancel' },
    ]);
  };

  const toggleSetting = (key: keyof typeof settings) => {
    setSettings(prev => ({ ...prev, [key]: !prev[key] }));
    // Show toast feedback
  };

  // Mask sensitive data
  const maskPan = (pan: string) => showPan ? pan : '••••••••••';
  const maskAadhaar = (aadhaar: string) => showAadhaar ? `${aadhaar.slice(0, 4)} ${aadhaar.slice(4, 8)} ${aadhaar.slice(8)}` : '•••• •••• ••••';

  const renderTabContent = () => {
    switch (activeTab) {
      case 'account':
        return <AccountTab />;
      case 'security':
        return <SecurityTab />;
      case 'notifications':
        return <NotificationsTab />;
      case 'financial':
        return <FinancialTab />;
      case 'appearance':
        return <AppearanceTab />;
      case 'data':
        return <DataTab />;
      default:
        return null;
    }
  };

  // ═══ ACCOUNT TAB ═══
  const AccountTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="account" size={22} color="#3B82F6" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Personal Information</Text>
      </View>

      {/* Profile Banner */}
      <View style={[styles.profileBanner, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <View style={styles.profileLeft}>
          <LinearGradient colors={['#3B82F6', '#8B5CF6']} style={styles.avatarLarge}>
            <Text style={styles.avatarText}>{user?.full_name?.charAt(0)?.toUpperCase() || 'V'}</Text>
          </LinearGradient>
          <View style={styles.profileInfo}>
            <Text style={[styles.profileName, { color: colors.textPrimary }]}>{user?.full_name || 'User'}</Text>
            <Text style={[styles.profileEmail, { color: colors.textSecondary }]}>{user?.email}</Text>
            <View style={[styles.verifiedBadge, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
              <MaterialCommunityIcons name="check-decagram" size={12} color="#10B981" />
              <Text style={styles.verifiedText}>Verified</Text>
            </View>
          </View>
        </View>
        <View style={styles.profileActions}>
          <TouchableOpacity style={[styles.editBtn, { borderColor: colors.border }]}>
            <MaterialCommunityIcons name="pencil" size={16} color={colors.textSecondary} />
            <Text style={[styles.editBtnText, { color: colors.textSecondary }]}>Edit</Text>
          </TouchableOpacity>
          <TouchableOpacity style={styles.signOutBtn} onPress={handleLogout}>
            <MaterialCommunityIcons name="logout" size={16} color="#EF4444" />
            <Text style={styles.signOutText}>Sign Out</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Personal Details Grid */}
      <View style={styles.detailsGrid}>
        <SettingField label="Full Name" value={user?.full_name || 'N/A'} icon="account" colors={colors} isDark={isDark} />
        <SettingField label="Email Address" value={user?.email || 'N/A'} icon="email" colors={colors} isDark={isDark} />
        <SettingField label="Mobile Number" value={user?.phone || '+91 XXXXXXXXXX'} icon="phone" colors={colors} isDark={isDark} />
        <SettingField
          label="PAN Number"
          value={maskPan(user?.pan || 'XXXXX0000X')}
          icon="card-account-details"
          colors={colors}
          isDark={isDark}
          showToggle
          isVisible={showPan}
          onToggle={() => setShowPan(!showPan)}
          helper="Used for fetching account details and compliance"
        />
        <SettingField
          label="Aadhaar Number"
          value={maskAadhaar(user?.aadhaar || '000000000000')}
          icon="fingerprint"
          colors={colors}
          isDark={isDark}
          showToggle
          isVisible={showAadhaar}
          onToggle={() => setShowAadhaar(!showAadhaar)}
          helper="Used for date of birth verification"
        />
        <SettingField label="Date of Birth" value={user?.dob || '01/01/1990'} icon="calendar" colors={colors} isDark={isDark} />
      </View>
    </View>
  );

  // ═══ SECURITY TAB ═══
  const SecurityTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)' }]}>
          <MaterialCommunityIcons name="shield-check" size={22} color="#10B981" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Security & Privacy</Text>
      </View>

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Authentication Methods</Text>

      <SettingToggleRow
        icon="fingerprint"
        iconColor="#3B82F6"
        title="Biometric Authentication"
        description="Use fingerprint or face ID"
        value={settings.biometric}
        onToggle={() => toggleSetting('biometric')}
        colors={colors}
        isDark={isDark}
      />

      <SettingToggleRow
        icon="lock"
        iconColor="#10B981"
        title="Two-Factor Authentication"
        description="Extra security for your account"
        value={settings.twoFactor}
        onToggle={() => toggleSetting('twoFactor')}
        colors={colors}
        isDark={isDark}
      />

      <View style={[styles.separator, { backgroundColor: colors.border }]} />

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Data Collection</Text>

      <SettingToggleRow
        icon="message-text"
        iconColor="#8B5CF6"
        title="SMS Transaction Parsing"
        description="Automatically detect bank transactions from SMS"
        value={settings.smsParsing}
        onToggle={() => toggleSetting('smsParsing')}
        colors={colors}
        isDark={isDark}
      />
    </View>
  );

  // ═══ NOTIFICATIONS TAB ═══
  const NotificationsTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="bell" size={22} color="#3B82F6" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Notifications</Text>
      </View>

      <SettingToggleRow
        icon="email"
        iconColor="#10B981"
        title="Email Notifications"
        description="Receive updates via email"
        value={settings.emailNotifications}
        onToggle={() => toggleSetting('emailNotifications')}
        colors={colors}
        isDark={isDark}
      />

      <SettingToggleRow
        icon="cellphone"
        iconColor="#3B82F6"
        title="Push Notifications"
        description="Real-time app notifications"
        value={settings.pushNotifications}
        onToggle={() => toggleSetting('pushNotifications')}
        colors={colors}
        isDark={isDark}
      />

      <View style={[styles.separator, { backgroundColor: colors.border }]} />

      <View style={[styles.futureFeature, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <MaterialCommunityIcons name="clock-outline" size={18} color={colors.textSecondary} />
        <Text style={[styles.futureText, { color: colors.textSecondary }]}>
          More notification options coming soon: Transaction alerts, Weekly summaries, Goal milestones
        </Text>
      </View>
    </View>
  );

  // ═══ FINANCIAL TAB ═══
  const FinancialTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="target" size={22} color="#8B5CF6" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Financial Preferences</Text>
      </View>

      {/* Currency */}
      <View style={[styles.settingRow, { borderColor: colors.border }]}>
        <View style={styles.settingLeft}>
          <Text style={[styles.settingTitle, { color: colors.textPrimary }]}>Default Currency</Text>
          <Text style={[styles.settingDesc, { color: colors.textSecondary }]}>Currency for all transactions</Text>
        </View>
        <View style={[styles.currencySelector, { borderColor: colors.border, backgroundColor: colors.background }]}>
          {['₹ INR', '$ USD', '€ EUR'].map(cur => (
            <TouchableOpacity
              key={cur}
              style={[
                styles.currencyOption,
                settings.currency === cur.split(' ')[1] && { backgroundColor: colors.primary },
              ]}
              onPress={() => setSettings(prev => ({ ...prev, currency: cur.split(' ')[1] }))}
            >
              <Text style={[
                styles.currencyText,
                { color: settings.currency === cur.split(' ')[1] ? '#fff' : colors.textSecondary },
              ]}>
                {cur}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <View style={[styles.separator, { backgroundColor: colors.border }]} />

      {/* Savings Target */}
      <View style={styles.sliderSection}>
        <View style={styles.sliderHeader}>
          <View>
            <Text style={[styles.settingTitle, { color: colors.textPrimary }]}>Savings Target</Text>
            <Text style={[styles.settingDesc, { color: colors.textSecondary }]}>Monthly savings goal percentage</Text>
          </View>
          <View style={[styles.sliderValue, { backgroundColor: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)' }]}>
            <Text style={[styles.sliderValueText, { color: '#8B5CF6' }]}>{settings.savingsTarget}%</Text>
          </View>
        </View>
        <Slider
          style={styles.slider}
          minimumValue={5}
          maximumValue={50}
          step={5}
          value={settings.savingsTarget}
          onValueChange={val => setSettings(prev => ({ ...prev, savingsTarget: val }))}
          minimumTrackTintColor="#8B5CF6"
          maximumTrackTintColor={isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)'}
          thumbTintColor="#8B5CF6"
        />
        <View style={styles.sliderLabels}>
          <Text style={[styles.sliderLabel, { color: colors.textSecondary }]}>5%</Text>
          <Text style={[styles.sliderLabel, { color: colors.textSecondary }]}>50%</Text>
        </View>
      </View>

      <View style={[styles.separator, { backgroundColor: colors.border }]} />

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Investment Preferences</Text>

      {/* Risk Tolerance */}
      <View style={[styles.settingRow, { borderColor: colors.border }]}>
        <View style={styles.settingLeft}>
          <Text style={[styles.settingTitle, { color: colors.textPrimary }]}>Risk Tolerance</Text>
          <Text style={[styles.settingDesc, { color: colors.textSecondary }]}>Your investment risk appetite</Text>
        </View>
        <View style={[styles.riskSelector, { borderColor: colors.border }]}>
          {['Conservative', 'Moderate', 'Aggressive'].map(risk => (
            <TouchableOpacity
              key={risk}
              style={[
                styles.riskOption,
                settings.riskTolerance === risk && {
                  backgroundColor: risk === 'Conservative' ? '#3B82F6' : risk === 'Moderate' ? '#F59E0B' : '#EF4444',
                },
              ]}
              onPress={() => setSettings(prev => ({ ...prev, riskTolerance: risk }))}
            >
              <Text style={[
                styles.riskText,
                { color: settings.riskTolerance === risk ? '#fff' : colors.textSecondary },
              ]}>
                {risk.slice(0, 3)}
              </Text>
            </TouchableOpacity>
          ))}
        </View>
      </View>

      <SettingToggleRow
        icon="trending-up"
        iconColor="#10B981"
        title="Auto-Investment"
        description="Automatically invest surplus funds"
        value={settings.autoInvestment}
        onToggle={() => toggleSetting('autoInvestment')}
        colors={colors}
        isDark={isDark}
      />
    </View>
  );

  // ═══ APPEARANCE TAB ═══
  const AppearanceTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.1)' }]}>
          <MaterialCommunityIcons name="palette" size={22} color="#F59E0B" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Appearance & Display</Text>
      </View>

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Theme</Text>

      <View style={styles.themeOptions}>
        {[
          { key: 'light', label: 'Light', icon: 'white-balance-sunny', color: '#F59E0B' },
          { key: 'dark', label: 'Dark', icon: 'moon-waning-crescent', color: '#6366F1' },
          { key: 'system', label: 'System', icon: 'cellphone', color: '#64748B' },
        ].map(theme => (
          <TouchableOpacity
            key={theme.key}
            style={[
              styles.themeCard,
              {
                backgroundColor: themeMode === theme.key
                  ? isDark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.1)'
                  : isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                borderColor: themeMode === theme.key ? colors.primary : colors.border,
              },
            ]}
            onPress={() => setThemeMode(theme.key as 'light' | 'dark' | 'system')}
          >
            <View style={[styles.themeIconWrap, { backgroundColor: `${theme.color}20` }]}>
              <MaterialCommunityIcons name={theme.icon as any} size={24} color={theme.color} />
            </View>
            <Text style={[styles.themeLabel, { color: colors.textPrimary }]}>{theme.label}</Text>
            {themeMode === theme.key && (
              <MaterialCommunityIcons name="check-circle" size={20} color={colors.primary} />
            )}
          </TouchableOpacity>
        ))}
      </View>

      <View style={[styles.futureFeature, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <MaterialCommunityIcons name="clock-outline" size={18} color={colors.textSecondary} />
        <Text style={[styles.futureText, { color: colors.textSecondary }]}>
          Coming soon: Font size, Compact mode, Accent color picker
        </Text>
      </View>
    </View>
  );

  // ═══ DATA TAB ═══
  const DataTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.1)' }]}>
          <MaterialCommunityIcons name="download" size={22} color="#EF4444" />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Data Management</Text>
      </View>

      {/* Export Data */}
      <View style={[styles.dataRow, { borderColor: colors.border }]}>
        <View style={[styles.dataIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="download" size={20} color="#3B82F6" />
        </View>
        <View style={styles.dataInfo}>
          <Text style={[styles.dataTitle, { color: colors.textPrimary }]}>Export Data</Text>
          <Text style={[styles.dataDesc, { color: colors.textSecondary }]}>Download your financial data</Text>
        </View>
        <TouchableOpacity style={[styles.exportBtn, { borderColor: colors.border }]} onPress={handleExportData}>
          <Text style={[styles.exportBtnText, { color: colors.primary }]}>Export CSV</Text>
        </TouchableOpacity>
      </View>

      {/* Delete Account */}
      <View style={[styles.dangerZone, {
        backgroundColor: isDark ? 'rgba(239, 68, 68, 0.08)' : 'rgba(239, 68, 68, 0.05)',
        borderColor: isDark ? 'rgba(239, 68, 68, 0.3)' : 'rgba(239, 68, 68, 0.2)',
      }]}>
        <View style={[styles.dataIconWrap, { backgroundColor: 'rgba(239, 68, 68, 0.15)' }]}>
          <MaterialCommunityIcons name="trash-can" size={20} color="#EF4444" />
        </View>
        <View style={styles.dataInfo}>
          <Text style={[styles.dangerTitle, { color: isDark ? '#FCA5A5' : '#DC2626' }]}>Delete Account</Text>
          <Text style={[styles.dangerDesc, { color: isDark ? '#FCA5A5' : '#EF4444' }]}>
            Permanently delete your account and data
          </Text>
        </View>
        <TouchableOpacity
          style={styles.deleteBtn}
          onPress={() => setShowDeleteModal(true)}
        >
          <Text style={styles.deleteBtnText}>Delete</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.appInfo}>
        <Text style={[styles.appInfoText, { color: colors.textSecondary }]}>Visor Finance v1.0.0</Text>
        <Text style={[styles.appInfoText, { color: colors.textSecondary }]}>Built with AI · Made in India</Text>
      </View>
    </View>
  );

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* ═══ HEADER ═══ */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#0F172A' : '#FFFFFF' }]}>
        <View style={[styles.headerContent, {
          backgroundColor: isDark ? '#0F172A' : '#FFFFFF',
          borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
        }]}>
          <View style={styles.headerLeft}>
            <Text style={[styles.headerTitle, { color: '#64748B' }]}>Settings</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
              Account, security & preferences
            </Text>
          </View>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 8 }]}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ TAB BAR ═══ */}
        <View style={[styles.tabBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)' }]}>
          {TABS.map(tab => (
            <TouchableOpacity
              key={tab.key}
              style={[
                styles.tabItem,
                activeTab === tab.key && {
                  backgroundColor: isDark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.1)',
                },
              ]}
              onPress={() => setActiveTab(tab.key)}
            >
              <MaterialCommunityIcons
                name={tab.icon as any}
                size={20}
                color={activeTab === tab.key ? colors.primary : colors.textSecondary}
              />
              <Text style={[
                styles.tabLabel,
                { color: activeTab === tab.key ? colors.primary : colors.textSecondary },
              ]}>
                {tab.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* ═══ TAB CONTENT ═══ */}
        {renderTabContent()}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ DELETE CONFIRMATION MODAL ═══ */}
      <Modal visible={showDeleteModal} animationType="fade" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.deleteModal, { backgroundColor: colors.surface }]}>
            <View style={[styles.deleteModalIcon, { backgroundColor: 'rgba(239, 68, 68, 0.1)' }]}>
              <MaterialCommunityIcons name="alert-circle" size={48} color="#EF4444" />
            </View>
            <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>Delete Account?</Text>
            <Text style={[styles.deleteModalDesc, { color: colors.textSecondary }]}>
              This action cannot be undone. All your data including transactions, goals, and settings will be permanently deleted.
            </Text>
            <Text style={[styles.deleteModalPrompt, { color: colors.textSecondary }]}>
              Type <Text style={{ color: '#EF4444', fontWeight: '700' }}>DELETE</Text> to confirm:
            </Text>
            <TextInput
              style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
              value={deleteConfirmText}
              onChangeText={setDeleteConfirmText}
              placeholder="DELETE"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="characters"
            />
            <View style={styles.deleteModalActions}>
              <TouchableOpacity
                style={[styles.cancelModalBtn, { borderColor: colors.border }]}
                onPress={() => { setShowDeleteModal(false); setDeleteConfirmText(''); }}
              >
                <Text style={[styles.cancelModalText, { color: colors.textPrimary }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.confirmDeleteBtn} onPress={handleDeleteAccount}>
                <Text style={styles.confirmDeleteText}>Delete Account</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>
    </View>
  );
}

// ═══ HELPER COMPONENTS ═══

function SettingField({ label, value, icon, colors, isDark, showToggle, isVisible, onToggle, helper }: any) {
  return (
    <View style={[styles.fieldContainer, { borderColor: colors.border }]}>
      <View style={styles.fieldHeader}>
        <MaterialCommunityIcons name={icon} size={16} color={colors.textSecondary} />
        <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>{label}</Text>
      </View>
      <View style={styles.fieldValueRow}>
        <Text style={[styles.fieldValue, { color: colors.textPrimary }]}>{value}</Text>
        {showToggle && (
          <TouchableOpacity onPress={onToggle} style={styles.eyeBtn}>
            <MaterialCommunityIcons name={isVisible ? 'eye-off' : 'eye'} size={18} color={colors.textSecondary} />
          </TouchableOpacity>
        )}
      </View>
      {helper && <Text style={[styles.fieldHelper, { color: colors.textSecondary }]}>{helper}</Text>}
    </View>
  );
}

function SettingToggleRow({ icon, iconColor, title, description, value, onToggle, colors, isDark }: any) {
  return (
    <View style={[styles.toggleRow, { borderColor: colors.border }]}>
      <View style={[styles.toggleIconWrap, { backgroundColor: `${iconColor}15` }]}>
        <MaterialCommunityIcons name={icon} size={20} color={iconColor} />
      </View>
      <View style={styles.toggleInfo}>
        <Text style={[styles.toggleTitle, { color: colors.textPrimary }]}>{title}</Text>
        <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>{description}</Text>
      </View>
      <Switch
        value={value}
        onValueChange={onToggle}
        trackColor={{ false: colors.border, true: 'rgba(99, 102, 241, 0.5)' }}
        thumbColor={value ? '#6366F1' : '#CBD5E1'}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  // Header
  stickyHeader: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 100 },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerLeft: { flex: 1 },
  headerTitle: { fontSize: 22, fontWeight: '800' },
  headerSubtitle: { fontSize: 13, marginTop: 2 },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 120 },

  // Tab Bar
  tabBar: { flexDirection: 'row', flexWrap: 'wrap', borderRadius: 14, padding: 6, marginBottom: 16 },
  tabItem: { width: '33.33%', alignItems: 'center', paddingVertical: 10, borderRadius: 10 },
  tabLabel: { fontSize: 11, fontWeight: '600', marginTop: 4 },

  // Card
  card: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 14 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  cardIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  cardTitle: { fontSize: 16, fontWeight: '700' },

  // Profile Banner
  profileBanner: { borderRadius: 16, padding: 16, marginBottom: 20 },
  profileLeft: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 14 },
  avatarLarge: { width: 60, height: 60, borderRadius: 30, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontSize: 24, fontWeight: '800' },
  profileInfo: { flex: 1 },
  profileName: { fontSize: 18, fontWeight: '700' },
  profileEmail: { fontSize: 13, marginTop: 2 },
  verifiedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginTop: 6 },
  verifiedText: { fontSize: 11, fontWeight: '600', color: '#10B981' },
  profileActions: { flexDirection: 'row', gap: 10 },
  editBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 12, borderWidth: 1 },
  editBtnText: { fontSize: 13, fontWeight: '600' },
  signOutBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 12, backgroundColor: 'rgba(239, 68, 68, 0.1)' },
  signOutText: { fontSize: 13, fontWeight: '600', color: '#EF4444' },

  // Details Grid
  detailsGrid: { gap: 12 },
  fieldContainer: { borderRadius: 12, padding: 12, borderWidth: 1 },
  fieldHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  fieldLabel: { fontSize: 11, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 0.3 },
  fieldValueRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fieldValue: { fontSize: 15, fontWeight: '600' },
  eyeBtn: { padding: 4 },
  fieldHelper: { fontSize: 10, marginTop: 4 },

  // Section Label
  sectionLabel: { fontSize: 12, fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12, marginTop: 8 },

  // Separator
  separator: { height: 1, marginVertical: 16 },

  // Toggle Row
  toggleRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 10, gap: 12 },
  toggleIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  toggleInfo: { flex: 1 },
  toggleTitle: { fontSize: 15, fontWeight: '600' },
  toggleDesc: { fontSize: 12, marginTop: 2 },

  // Future Feature
  futureFeature: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 12, marginTop: 8 },
  futureText: { flex: 1, fontSize: 12, lineHeight: 17 },

  // Setting Row
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, paddingHorizontal: 4 },
  settingLeft: { flex: 1 },
  settingTitle: { fontSize: 15, fontWeight: '600' },
  settingDesc: { fontSize: 12, marginTop: 2 },

  // Currency Selector
  currencySelector: { flexDirection: 'row', borderRadius: 10, borderWidth: 1, overflow: 'hidden' },
  currencyOption: { paddingHorizontal: 12, paddingVertical: 8 },
  currencyText: { fontSize: 12, fontWeight: '600' },

  // Risk Selector
  riskSelector: { flexDirection: 'row', borderRadius: 10, borderWidth: 1, overflow: 'hidden' },
  riskOption: { paddingHorizontal: 10, paddingVertical: 8 },
  riskText: { fontSize: 11, fontWeight: '700' },

  // Slider
  sliderSection: { paddingVertical: 8 },
  sliderHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sliderValue: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12 },
  sliderValueText: { fontSize: 16, fontWeight: '800' },
  slider: { width: '100%', height: 40 },
  sliderLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: -8 },
  sliderLabel: { fontSize: 11 },

  // Theme Options
  themeOptions: { flexDirection: 'row', gap: 10 },
  themeCard: { flex: 1, alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1.5 },
  themeIconWrap: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginBottom: 10 },
  themeLabel: { fontSize: 13, fontWeight: '600', marginBottom: 6 },

  // Data Row
  dataRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 12, gap: 12 },
  dataIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  dataInfo: { flex: 1 },
  dataTitle: { fontSize: 15, fontWeight: '600' },
  dataDesc: { fontSize: 12, marginTop: 2 },
  exportBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, borderWidth: 1 },
  exportBtnText: { fontSize: 13, fontWeight: '600' },

  // Danger Zone
  dangerZone: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 16, gap: 12 },
  dangerTitle: { fontSize: 15, fontWeight: '700' },
  dangerDesc: { fontSize: 12, marginTop: 2 },
  deleteBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, backgroundColor: '#EF4444' },
  deleteBtnText: { fontSize: 13, fontWeight: '700', color: '#fff' },

  // App Info
  appInfo: { alignItems: 'center', marginTop: 16, gap: 4 },
  appInfoText: { fontSize: 12 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  deleteModal: { width: '100%', maxWidth: 360, borderRadius: 24, padding: 24, alignItems: 'center' },
  deleteModalIcon: { width: 80, height: 80, borderRadius: 40, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  deleteModalTitle: { fontSize: 22, fontWeight: '800', marginBottom: 8 },
  deleteModalDesc: { fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 16 },
  deleteModalPrompt: { fontSize: 13, marginBottom: 12 },
  deleteInput: { width: '100%', height: 48, borderRadius: 12, borderWidth: 1, paddingHorizontal: 16, fontSize: 16, fontWeight: '700', textAlign: 'center', marginBottom: 20 },
  deleteModalActions: { flexDirection: 'row', gap: 12, width: '100%' },
  cancelModalBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, borderWidth: 1, alignItems: 'center' },
  cancelModalText: { fontSize: 15, fontWeight: '600' },
  confirmDeleteBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, backgroundColor: '#EF4444', alignItems: 'center' },
  confirmDeleteText: { fontSize: 15, fontWeight: '700', color: '#fff' },
});
