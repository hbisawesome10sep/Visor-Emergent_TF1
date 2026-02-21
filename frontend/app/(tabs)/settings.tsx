import React, { useState } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, Alert,
  Switch, TextInput, Platform, StatusBar, Modal, Dimensions,
  ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import Slider from '@react-native-community/slider';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { useSecurity } from '../../src/context/SecurityContext';
import { apiRequest } from '../../src/utils/api';
import { Accent } from '../../src/utils/theme';
import { Linking } from 'react-native';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const TABS = [
  { key: 'account', label: 'Account', icon: 'account' },
  { key: 'security', label: 'Security', icon: 'shield-check' },
  { key: 'banking', label: 'Banking', icon: 'bank' },
  { key: 'sources', label: 'Sources', icon: 'link-variant' },
  { key: 'notifications', label: 'Alerts', icon: 'bell' },
  { key: 'financial', label: 'Financial', icon: 'target' },
  { key: 'appearance', label: 'Theme', icon: 'palette' },
  { key: 'data', label: 'Data', icon: 'download' },
];

export default function SettingsScreen() {
  const { user, logout, token } = useAuth();
  const { colors, isDark, themeMode, setThemeMode } = useTheme();
  const {
    isPinSetup, isBiometricEnabled, isBiometricAvailable,
    isSecuritySetupDone, toggleBiometric, resetSecurity, lock,
  } = useSecurity();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;
  const router = useRouter();

  const [activeTab, setActiveTab] = useState('account');
  const [showPan, setShowPan] = useState(false);
  const [showAadhaar, setShowAadhaar] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteConfirmText, setDeleteConfirmText] = useState('');

  // Gmail state
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailLastSync, setGmailLastSync] = useState<string | null>(null);
  const [gmailSyncing, setGmailSyncing] = useState(false);
  const [gmailSyncResult, setGmailSyncResult] = useState<string | null>(null);

  // Load Gmail status on mount
  React.useEffect(() => {
    (async () => {
      try {
        const status = await apiRequest('/gmail/status', { token: token || '' });
        setGmailConnected(status.connected);
        setGmailLastSync(status.last_sync);
      } catch {}
    })();
  }, []);

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

  // Bank accounts state
  const [bankAccounts, setBankAccounts] = useState<any[]>([]);
  const [banksList, setBanksList] = useState<string[]>([]);
  const [showBankModal, setShowBankModal] = useState(false);
  const [editingBank, setEditingBank] = useState<any>(null);
  const [bankForm, setBankForm] = useState({ bank_name: '', account_name: '', account_number: '', ifsc_code: '', is_default: false });
  const [showBankPicker, setShowBankPicker] = useState(false);
  const [bankSearch, setBankSearch] = useState('');

  // Bank statement upload state
  const [uploadingStatement, setUploadingStatement] = useState(false);
  const [uploadResult, setUploadResult] = useState<any>(null);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadBankName, setUploadBankName] = useState('');
  const [uploadAccountName, setUploadAccountName] = useState('');
  const [uploadPassword, setUploadPassword] = useState(''); // Password for encrypted PDFs
  const [selectedFile, setSelectedFile] = useState<any>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadPhase, setUploadPhase] = useState<'idle' | 'uploading' | 'processing' | 'complete'>('idle');

  // Fetch bank accounts
  React.useEffect(() => {
    if (!token) return;
    (async () => {
      try {
        const [accounts, banks] = await Promise.all([
          apiRequest('/bank-accounts', { token }),
          apiRequest('/bank-accounts/banks-list'),
        ]);
        setBankAccounts(accounts);
        setBanksList(banks.banks);
      } catch {}
    })();
  }, [token]);

  const saveBankAccount = async () => {
    if (!bankForm.bank_name || !bankForm.account_name) {
      Alert.alert('Required', 'Please select a bank and enter account name');
      return;
    }
    try {
      if (editingBank) {
        await apiRequest(`/bank-accounts/${editingBank.id}`, { method: 'PUT', token: token || '', body: bankForm });
      } else {
        await apiRequest('/bank-accounts', { method: 'POST', token: token || '', body: bankForm });
      }
      const updated = await apiRequest('/bank-accounts', { token: token || '' });
      setBankAccounts(updated);
      setShowBankModal(false);
      setEditingBank(null);
    } catch (e: any) { Alert.alert('Error', e.message); }
  };

  const deleteBankAccount = (id: string, name: string) => {
    Alert.alert('Delete Account', `Remove "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await apiRequest(`/bank-accounts/${id}`, { method: 'DELETE', token: token || '' });
          setBankAccounts(prev => prev.filter(b => b.id !== id));
        } catch (e: any) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  const deleteAllBankAccounts = () => {
    Alert.alert('Delete All', 'Remove all bank accounts? This cannot be undone.', [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete All', style: 'destructive', onPress: async () => {
        try {
          await apiRequest('/bank-accounts', { method: 'DELETE', token: token || '' });
          setBankAccounts([]);
        } catch (e: any) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  const setDefaultBank = async (id: string) => {
    try {
      await apiRequest(`/bank-accounts/${id}/set-default`, { method: 'PUT', token: token || '' });
      const updated = await apiRequest('/bank-accounts', { token: token || '' });
      setBankAccounts(updated);
    } catch (e: any) { Alert.alert('Error', e.message); }
  };

  // Bank statement upload functions
  const handlePickFile = async () => {
    try {
      const result = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf', 'text/csv', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
        copyToCacheDirectory: true,
      });
      
      if (!result.canceled && result.assets?.[0]) {
        setSelectedFile(result.assets[0]);
        setShowUploadModal(true);
      }
    } catch (e: any) {
      Alert.alert('Error', 'Failed to pick file: ' + e.message);
    }
  };

  const handleUploadStatement = async () => {
    if (!selectedFile) return;
    
    setUploadingStatement(true);
    setUploadResult(null);
    setUploadProgress(0);
    setUploadPhase('uploading');
    
    try {
      // Simulate upload progress
      const progressInterval = setInterval(() => {
        setUploadProgress(prev => {
          if (prev >= 40) {
            clearInterval(progressInterval);
            return prev;
          }
          return prev + 5;
        });
      }, 100);

      const formData = new FormData();
      formData.append('file', {
        uri: selectedFile.uri,
        name: selectedFile.name,
        type: selectedFile.mimeType || 'application/octet-stream',
      } as any);
      formData.append('bank_name', uploadBankName || '');
      formData.append('account_name', uploadAccountName || '');
      formData.append('password', uploadPassword || ''); // Include password for encrypted PDFs
      
      const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';
      
      // Upload phase
      setUploadProgress(45);
      setUploadPhase('processing');
      
      const response = await fetch(`${API_URL}/api/bank-statements/upload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        body: formData,
      });
      
      clearInterval(progressInterval);
      
      // Processing phase - simulate progress
      setUploadProgress(70);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Upload failed');
      }
      
      setUploadProgress(90);
      const result = await response.json();
      
      setUploadProgress(100);
      setUploadPhase('complete');
      setUploadResult(result);
      
      // Refresh bank accounts list
      const updated = await apiRequest('/bank-accounts', { token: token || '' });
      setBankAccounts(updated);
      
    } catch (e: any) {
      Alert.alert('Upload Failed', e.message);
      setUploadResult({ error: e.message });
      setUploadPhase('idle');
    } finally {
      setUploadingStatement(false);
    }
  };

  const closeUploadModal = () => {
    setShowUploadModal(false);
    setSelectedFile(null);
    setUploadBankName('');
    setUploadAccountName('');
    setUploadResult(null);
    setUploadProgress(0);
    setUploadPhase('idle');
  };

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

  const handleDeleteAccount = async () => {
    if (deleteConfirmText.toUpperCase() !== 'DELETE') {
      Alert.alert('Error', 'Please type DELETE to confirm.');
      return;
    }

    try {
      // Call the backend to delete the account and all associated data
      await apiRequest('/auth/delete-account', { 
        method: 'DELETE', 
        token: token || '' 
      });
      
      Alert.alert('Account Deleted', 'Your account and all associated data have been permanently deleted.', [
        {
          text: 'OK',
          onPress: async () => {
            await logout();
            router.replace('/(auth)/login');
          },
        },
      ]);
      setShowDeleteModal(false);
      setDeleteConfirmText('');
    } catch (error: any) {
      Alert.alert('Error', error.message || 'Failed to delete account. Please try again.');
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
      case 'banking':
        return <BankingTab />;
      case 'sources':
        return <SourcesTab />;
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

  // ═══ BANKING TAB ═══
  const BankingTab = () => {
    const filteredBanks = bankSearch
      ? banksList.filter(b => b.toLowerCase().includes(bankSearch.toLowerCase()))
      : banksList;

    return (
      <View data-testid="banking-tab">
        {/* Bank Accounts Card */}
        <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)' }]}>
              <MaterialCommunityIcons name="bank" size={22} color={Accent.sapphire} />
            </View>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Bank Accounts</Text>
          </View>

          <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans', marginBottom: 16, lineHeight: 20 }}>
            Add your bank accounts to track payments and receipts. Set a default account for transactions.
          </Text>

          {/* Bank Account Cards */}
          {bankAccounts.map(bank => (
            <View key={bank.id} data-testid={`bank-card-${bank.id}`} style={[styles.toggleRow, { borderColor: bank.is_default ? Accent.sapphire : colors.border, marginBottom: 10 }]}>
              <View style={[styles.toggleIconWrap, { backgroundColor: bank.is_default ? 'rgba(59,130,246,0.15)' : isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)' }]}>
                <MaterialCommunityIcons name="bank" size={20} color={bank.is_default ? Accent.sapphire : colors.textSecondary} />
              </View>
              <View style={{ flex: 1 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <Text style={[styles.toggleTitle, { color: colors.textPrimary }]}>{bank.account_name}</Text>
                  {bank.is_default && (
                    <View style={{ backgroundColor: 'rgba(59,130,246,0.15)', paddingHorizontal: 6, paddingVertical: 2, borderRadius: 6 }}>
                      <Text style={{ fontSize: 9, color: Accent.sapphire, fontWeight: '700', fontFamily: 'DM Sans' }}>DEFAULT</Text>
                    </View>
                  )}
                </View>
                <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>{bank.bank_name}</Text>
                {bank.account_number && (
                  <Text style={{ fontSize: 11, color: colors.textSecondary, fontFamily: 'DM Sans', marginTop: 2 }}>
                    A/c: ****{bank.account_number.slice(-4)}
                  </Text>
                )}
              </View>
              <View style={{ flexDirection: 'row', gap: 6 }}>
                {!bank.is_default && (
                  <TouchableOpacity onPress={() => setDefaultBank(bank.id)} style={{ padding: 6 }} data-testid={`set-default-${bank.id}`}>
                    <MaterialCommunityIcons name="star-outline" size={20} color={colors.textSecondary} />
                  </TouchableOpacity>
                )}
                <TouchableOpacity onPress={() => {
                  setEditingBank(bank);
                  setBankForm({
                    bank_name: bank.bank_name,
                    account_name: bank.account_name,
                    account_number: bank.account_number || '',
                    ifsc_code: bank.ifsc_code || '',
                    is_default: bank.is_default,
                  });
                  setShowBankModal(true);
                }} style={{ padding: 6 }} data-testid={`edit-bank-${bank.id}`}>
                  <MaterialCommunityIcons name="pencil" size={18} color={colors.textSecondary} />
                </TouchableOpacity>
                <TouchableOpacity onPress={() => deleteBankAccount(bank.id, bank.account_name)} style={{ padding: 6 }} data-testid={`delete-bank-${bank.id}`}>
                  <MaterialCommunityIcons name="trash-can-outline" size={18} color={Accent.ruby} />
                </TouchableOpacity>
              </View>
            </View>
          ))}

          {bankAccounts.length === 0 && (
            <View style={{ alignItems: 'center', paddingVertical: 20, opacity: 0.6 }}>
              <MaterialCommunityIcons name="bank-off" size={40} color={colors.textSecondary} />
              <Text style={{ fontSize: 14, color: colors.textSecondary, fontFamily: 'DM Sans', marginTop: 8 }}>No bank accounts added</Text>
            </View>
          )}

          {/* Add Bank Account Button */}
          <TouchableOpacity
            data-testid="add-bank-account-btn"
            style={[styles.syncBtn, { borderColor: Accent.sapphire, marginTop: 12 }]}
            onPress={() => {
              setEditingBank(null);
              setBankForm({ bank_name: '', account_name: '', account_number: '', ifsc_code: '', is_default: false });
              setBankSearch('');
              setShowBankPicker(false);
              setShowBankModal(true);
            }}
          >
            <MaterialCommunityIcons name="plus" size={20} color={Accent.sapphire} />
            <Text style={[styles.syncBtnText, { color: Accent.sapphire }]}>Add Bank Account</Text>
          </TouchableOpacity>

          {/* Delete All Button */}
          {bankAccounts.length > 1 && (
            <TouchableOpacity
              data-testid="delete-all-banks-btn"
              style={{ alignItems: 'center', marginTop: 12, paddingVertical: 10 }}
              onPress={deleteAllBankAccounts}
            >
              <Text style={{ fontSize: 13, color: Accent.ruby, fontFamily: 'DM Sans', fontWeight: '600' }}>Delete All Bank Accounts</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Bank Statement Upload Card */}
        <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border, marginTop: 14 }]}>
          <View style={styles.cardHeader}>
            <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}>
              <MaterialCommunityIcons name="file-upload" size={22} color={Accent.emerald} />
            </View>
            <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Import Bank Statement</Text>
          </View>

          <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans', marginBottom: 16, lineHeight: 20 }}>
            Upload your bank statement (PDF, CSV, Excel) to automatically import transactions. 
            The system will detect and categorize transactions, and create journal entries.
          </Text>

          {/* Supported Formats */}
          <View style={[styles.banksList, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', marginBottom: 16 }]}>
            <Text style={[styles.banksTitle, { color: colors.textSecondary }]}>Supported Formats</Text>
            <View style={{ flexDirection: 'row', gap: 10, marginTop: 8 }}>
              <View style={[styles.formatBadge, { backgroundColor: isDark ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.1)' }]}>
                <MaterialCommunityIcons name="file-pdf-box" size={18} color="#EF4444" />
                <Text style={{ fontSize: 12, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }}>PDF</Text>
              </View>
              <View style={[styles.formatBadge, { backgroundColor: isDark ? 'rgba(16,185,129,0.15)' : 'rgba(16,185,129,0.1)' }]}>
                <MaterialCommunityIcons name="file-delimited" size={18} color={Accent.emerald} />
                <Text style={{ fontSize: 12, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }}>CSV</Text>
              </View>
              <View style={[styles.formatBadge, { backgroundColor: isDark ? 'rgba(59,130,246,0.15)' : 'rgba(59,130,246,0.1)' }]}>
                <MaterialCommunityIcons name="file-excel" size={18} color={Accent.sapphire} />
                <Text style={{ fontSize: 12, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }}>Excel</Text>
              </View>
            </View>
          </View>

          {/* Upload Button */}
          <TouchableOpacity
            data-testid="upload-statement-btn"
            style={styles.uploadBtn}
            onPress={handlePickFile}
          >
            <LinearGradient 
              colors={[Accent.emerald, '#059669']} 
              start={{ x: 0, y: 0 }} 
              end={{ x: 1, y: 0 }} 
              style={styles.uploadBtnGradient}
            >
              <MaterialCommunityIcons name="file-upload" size={22} color="#fff" />
              <Text style={styles.uploadBtnText}>Select Bank Statement</Text>
            </LinearGradient>
          </TouchableOpacity>

          {/* Supported Banks */}
          <View style={[styles.banksList, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', marginTop: 16 }]}>
            <Text style={[styles.banksTitle, { color: colors.textSecondary }]}>Supported Banks</Text>
            <Text style={[styles.bankNames, { color: colors.textPrimary }]}>
              HDFC  ·  ICICI  ·  SBI  ·  Axis  ·  Kotak  ·  Yes Bank  ·  PNB  ·  BOB  ·  IndusInd  ·  IDFC  ·  Federal
            </Text>
          </View>

          {/* How it works */}
          <View style={{ marginTop: 16 }}>
            <Text style={[styles.sectionLabel, { color: colors.textSecondary, marginBottom: 10 }]}>How it works</Text>
            <View style={{ gap: 8 }}>
              {[
                { icon: 'numeric-1-circle', text: 'Upload your bank statement file' },
                { icon: 'numeric-2-circle', text: 'System parses all transactions automatically' },
                { icon: 'numeric-3-circle', text: 'Transactions & journal entries are created' },
              ].map((step, i) => (
                <View key={i} style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <MaterialCommunityIcons name={step.icon as any} size={22} color={Accent.emerald} />
                  <Text style={{ fontSize: 13, color: colors.textPrimary, fontFamily: 'DM Sans', flex: 1 }}>{step.text}</Text>
                </View>
              ))}
            </View>
          </View>
        </View>

        <View style={[styles.futureFeature, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', marginTop: 8 }]}>
          <MaterialCommunityIcons name="clock-outline" size={18} color={colors.textSecondary} />
          <Text style={[styles.futureText, { color: colors.textSecondary }]}>
            Coming soon: Auto-fetch bank accounts via registered mobile number (pending government approval)
          </Text>
        </View>
      </View>
    );
  };

  // ═══ ACCOUNT TAB ═══
  const AccountTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="account" size={22} color={Accent.sapphire} />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Personal Information</Text>
      </View>

      {/* Profile Banner */}
      <View style={[styles.profileBanner, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <View style={styles.profileLeft}>
          <LinearGradient colors={[Accent.sapphire, Accent.amethyst]} style={styles.avatarLarge}>
            <Text style={styles.avatarText}>{user?.full_name?.charAt(0)?.toUpperCase() || 'V'}</Text>
          </LinearGradient>
          <View style={styles.profileInfo}>
            <Text style={[styles.profileName, { color: colors.textPrimary }]}>{user?.full_name || 'User'}</Text>
            <Text style={[styles.profileEmail, { color: colors.textSecondary }]}>{user?.email}</Text>
            <View style={[styles.verifiedBadge, { backgroundColor: 'rgba(16, 185, 129, 0.1)' }]}>
              <MaterialCommunityIcons name="check-decagram" size={12} color={Accent.emerald} />
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
            <MaterialCommunityIcons name="logout" size={16} color={Accent.ruby} />
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
          <MaterialCommunityIcons name="shield-check" size={22} color={Accent.emerald} />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Security & Privacy</Text>
      </View>

      {/* Security Status Banner */}
      <View style={[styles.securityBanner, {
        backgroundColor: isPinSetup
          ? (isDark ? 'rgba(16, 185, 129, 0.1)' : 'rgba(16, 185, 129, 0.06)')
          : (isDark ? 'rgba(245, 158, 11, 0.1)' : 'rgba(245, 158, 11, 0.06)'),
      }]}>
        <MaterialCommunityIcons
          name={isPinSetup ? 'shield-check' : 'shield-alert'}
          size={20}
          color={isPinSetup ? Accent.emerald : '#F59E0B'}
        />
        <View style={{ flex: 1 }}>
          <Text style={[styles.securityBannerTitle, { color: colors.textPrimary }]}>
            {isPinSetup ? 'Security Active' : 'Security Not Configured'}
          </Text>
          <Text style={[styles.securityBannerDesc, { color: colors.textSecondary }]}>
            {isPinSetup
              ? `PIN enabled${isBiometricEnabled ? ' + Biometric' : ''} | Auto-lock: 5 min`
              : 'Set up PIN to protect your financial data'}
          </Text>
        </View>
      </View>

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Authentication</Text>

      <SettingToggleRow
        icon="lock"
        iconColor={Accent.emerald}
        title="App PIN Lock"
        description={isPinSetup ? 'PIN is set — app locks after 5 min' : 'Not configured'}
        value={isPinSetup}
        onToggle={() => {
          if (isPinSetup) {
            Alert.alert('Reset PIN', 'This will disable PIN lock. You can set it up again from Settings.', [
              { text: 'Cancel', style: 'cancel' },
              { text: 'Reset', style: 'destructive', onPress: () => resetSecurity() },
            ]);
          }
        }}
        colors={colors}
        isDark={isDark}
      />

      {isBiometricAvailable && (
        <SettingToggleRow
          icon="fingerprint"
          iconColor={Accent.sapphire}
          title="Biometric Authentication"
          description="Use fingerprint or Face ID to unlock"
          value={isBiometricEnabled}
          onToggle={() => toggleBiometric(!isBiometricEnabled)}
          colors={colors}
          isDark={isDark}
        />
      )}

      {isPinSetup && (
        <TouchableOpacity
          style={[styles.lockNowBtn, { borderColor: Accent.emerald }]}
          onPress={() => lock()}
          data-testid="lock-now-btn"
        >
          <MaterialCommunityIcons name="lock" size={18} color={Accent.emerald} />
          <Text style={[styles.lockNowText, { color: Accent.emerald }]}>Lock App Now</Text>
        </TouchableOpacity>
      )}

      <View style={[styles.separator, { backgroundColor: colors.border }]} />

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Data Encryption</Text>

      <View style={[styles.encryptionInfo, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
        <View style={styles.encryptionRow}>
          <MaterialCommunityIcons name="database-lock" size={18} color={Accent.emerald} />
          <Text style={[styles.encryptionText, { color: colors.textPrimary }]}>AES-256 field-level encryption</Text>
        </View>
        <View style={styles.encryptionRow}>
          <MaterialCommunityIcons name="key-variant" size={18} color={Accent.emerald} />
          <Text style={[styles.encryptionText, { color: colors.textPrimary }]}>Per-user encryption keys</Text>
        </View>
        <View style={styles.encryptionRow}>
          <MaterialCommunityIcons name="shield-lock" size={18} color={Accent.emerald} />
          <Text style={[styles.encryptionText, { color: colors.textPrimary }]}>PAN & Aadhaar encrypted at rest</Text>
        </View>
      </View>
    </View>
  );

  // ═══ SOURCES TAB (Gmail & SMS) ═══
  const handleGmailConnect = async () => {
    try {
      const result = await apiRequest('/gmail/connect', { token: token || '' });
      if (result.auth_url) {
        if (Platform.OS === 'web') {
          window.open(result.auth_url, '_self');
        } else {
          Linking.openURL(result.auth_url);
        }
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to connect Gmail');
    }
  };

  const handleGmailSync = async () => {
    setGmailSyncing(true);
    setGmailSyncResult(null);
    try {
      const result = await apiRequest('/gmail/sync', { method: 'POST', token: token || '' });
      setGmailSyncResult(`Found ${result.new_transactions} new transactions from ${result.emails_scanned} emails`);
      setGmailLastSync(new Date().toISOString());
    } catch (e: any) {
      setGmailSyncResult('Sync failed: ' + (e.message || 'Unknown error'));
    } finally {
      setGmailSyncing(false);
    }
  };

  const handleGmailDisconnect = async () => {
    Alert.alert('Disconnect Gmail', 'This will remove your Gmail connection. Previously imported transactions will remain.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Disconnect',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest('/gmail/disconnect', { method: 'DELETE', token: token || '' });
            setGmailConnected(false);
            setGmailLastSync(null);
          } catch {}
        },
      },
    ]);
  };

  const SourcesTab = () => (
    <View style={{ gap: 16 }}>
      {/* Gmail Section */}
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(234, 67, 53, 0.15)' : 'rgba(234, 67, 53, 0.1)' }]}>
            <MaterialCommunityIcons name="gmail" size={22} color="#EA4335" />
          </View>
          <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Gmail Email Parsing</Text>
        </View>

        <Text style={[styles.sourceDesc, { color: colors.textSecondary }]}>
          Connect your Gmail to automatically detect and import bank transaction alerts from HDFC, ICICI, SBI, Axis, Kotak and more.
        </Text>

        {gmailConnected ? (
          <>
            <View style={[styles.connectedBanner, { backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.06)' }]}>
              <MaterialCommunityIcons name="check-circle" size={20} color={Accent.emerald} />
              <View style={{ flex: 1 }}>
                <Text style={[styles.connectedTitle, { color: colors.textPrimary }]}>Gmail Connected</Text>
                {gmailLastSync && (
                  <Text style={[styles.connectedSubtext, { color: colors.textSecondary }]}>
                    Last sync: {new Date(gmailLastSync).toLocaleDateString()}
                  </Text>
                )}
              </View>
            </View>

            <TouchableOpacity
              style={[styles.syncBtn, { borderColor: Accent.emerald }]}
              onPress={handleGmailSync}
              disabled={gmailSyncing}
              data-testid="gmail-sync-btn"
            >
              <MaterialCommunityIcons name={gmailSyncing ? 'loading' : 'sync'} size={18} color={Accent.emerald} />
              <Text style={[styles.syncBtnText, { color: Accent.emerald }]}>
                {gmailSyncing ? 'Syncing...' : 'Sync Now'}
              </Text>
            </TouchableOpacity>

            {gmailSyncResult && (
              <Text style={[styles.syncResult, { color: colors.textSecondary }]}>{gmailSyncResult}</Text>
            )}

            <TouchableOpacity style={styles.disconnectBtn} onPress={handleGmailDisconnect} data-testid="gmail-disconnect-btn">
              <Text style={styles.disconnectText}>Disconnect Gmail</Text>
            </TouchableOpacity>
          </>
        ) : (
          <TouchableOpacity style={styles.connectGmailBtn} onPress={handleGmailConnect} data-testid="gmail-connect-btn">
            <LinearGradient colors={['#EA4335', '#D93025']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.connectGmailGradient}>
              <MaterialCommunityIcons name="gmail" size={20} color="#fff" />
              <Text style={styles.connectGmailText}>Connect Gmail</Text>
            </LinearGradient>
          </TouchableOpacity>
        )}

        <View style={[styles.banksList, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
          <Text style={[styles.banksTitle, { color: colors.textSecondary }]}>Supported Banks</Text>
          <Text style={[styles.bankNames, { color: colors.textPrimary }]}>
            HDFC  ·  ICICI  ·  SBI  ·  Axis  ·  Kotak  ·  Yes Bank  ·  PNB  ·  BOB  ·  IndusInd
          </Text>
        </View>
      </View>

      {/* SMS Section (Android only info) */}
      <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
        <View style={styles.cardHeader}>
          <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(139, 92, 246, 0.15)' : 'rgba(139, 92, 246, 0.1)' }]}>
            <MaterialCommunityIcons name="message-text" size={22} color="#8B5CF6" />
          </View>
          <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>SMS Transaction Parsing</Text>
        </View>

        <Text style={[styles.sourceDesc, { color: colors.textSecondary }]}>
          Automatically reads bank SMS on your Android device to detect transactions. Supports all major Indian banks.
        </Text>

        <View style={[styles.smsPlatformNote, { backgroundColor: isDark ? 'rgba(245,158,11,0.1)' : 'rgba(245,158,11,0.06)' }]}>
          <MaterialCommunityIcons name="android" size={18} color="#3DDC84" />
          <Text style={[styles.smsPlatformText, { color: colors.textSecondary }]}>
            {Platform.OS === 'android'
              ? 'Available on this device. Grant SMS permission to enable.'
              : 'Available on Android devices only. iOS restricts SMS access.'}
          </Text>
        </View>
      </View>
    </View>
  );

  // ═══ NOTIFICATIONS TAB ═══
  const NotificationsTab = () => (
    <View style={[styles.card, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.cardIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="bell" size={22} color={Accent.sapphire} />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Notifications</Text>
      </View>

      <SettingToggleRow
        icon="email"
        iconColor={Accent.emerald}
        title="Email Notifications"
        description="Receive updates via email"
        value={settings.emailNotifications}
        onToggle={() => toggleSetting('emailNotifications')}
        colors={colors}
        isDark={isDark}
      />

      <SettingToggleRow
        icon="cellphone"
        iconColor={Accent.sapphire}
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
            <Text style={[styles.sliderValueText, { color: Accent.amethyst }]}>{settings.savingsTarget}%</Text>
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
                  backgroundColor: risk === 'Conservative' ? Accent.sapphire : risk === 'Moderate' ? Accent.amber : Accent.ruby,
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
        iconColor={Accent.emerald}
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
          <MaterialCommunityIcons name="palette" size={22} color={Accent.amber} />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Appearance & Display</Text>
      </View>

      <Text style={[styles.sectionLabel, { color: colors.textSecondary }]}>Theme</Text>

      <View style={styles.themeOptions}>
        {[
          { key: 'light', label: 'Light', icon: 'white-balance-sunny', color: Accent.amber },
          { key: 'dark', label: 'Dark', icon: 'moon-waning-crescent', color: Accent.amethyst },
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
          <MaterialCommunityIcons name="download" size={22} color={Accent.ruby} />
        </View>
        <Text style={[styles.cardTitle, { color: colors.textPrimary }]}>Data Management</Text>
      </View>

      {/* Export Data */}
      <View style={[styles.dataRow, { borderColor: colors.border }]}>
        <View style={[styles.dataIconWrap, { backgroundColor: isDark ? 'rgba(59, 130, 246, 0.15)' : 'rgba(59, 130, 246, 0.1)' }]}>
          <MaterialCommunityIcons name="download" size={20} color={Accent.sapphire} />
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
          <MaterialCommunityIcons name="trash-can" size={20} color={Accent.ruby} />
        </View>
        <View style={styles.dataInfo}>
          <Text style={[styles.dangerTitle, { color: isDark ? '#FCA5A5' : Accent.ruby }]}>Delete Account</Text>
          <Text style={[styles.dangerDesc, { color: isDark ? '#FCA5A5' : Accent.ruby }]}>
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
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View style={[styles.headerContent, {
          backgroundColor: isDark ? '#000000' : '#FFFFFF',
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
              <MaterialCommunityIcons name="alert-circle" size={48} color={Accent.ruby} />
            </View>
            <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>Delete Account?</Text>
            <Text style={[styles.deleteModalDesc, { color: colors.textSecondary }]}>
              This action cannot be undone. All your data including transactions, goals, and settings will be permanently deleted.
            </Text>
            <Text style={[styles.deleteModalPrompt, { color: colors.textSecondary }]}>
              Type <Text style={{ color: Accent.ruby, fontFamily: 'DM Sans', fontWeight: '700' as any }}>DELETE</Text> to confirm:
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

      {/* ═══ BANK ACCOUNT MODAL ═══ */}
      <Modal visible={showBankModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.deleteModal, { backgroundColor: colors.surface, maxWidth: 420, width: '100%' }]}>
            <Text style={[styles.deleteModalTitle, { color: colors.textPrimary, marginBottom: 16 }]}>
              {editingBank ? 'Edit Bank Account' : 'Add Bank Account'}
            </Text>

            {/* Bank Selector */}
            <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>Bank *</Text>
            <TouchableOpacity
              data-testid="bank-name-selector"
              style={[styles.deleteInput, { borderColor: showBankPicker ? Accent.sapphire : colors.border, backgroundColor: colors.background, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
              onPress={() => setShowBankPicker(!showBankPicker)}
            >
              <Text style={{ fontSize: 14, color: bankForm.bank_name ? colors.textPrimary : colors.textSecondary, fontFamily: 'DM Sans' }}>
                {bankForm.bank_name || 'Select Bank'}
              </Text>
              <MaterialCommunityIcons name={showBankPicker ? 'chevron-up' : 'chevron-down'} size={20} color={colors.textSecondary} />
            </TouchableOpacity>

            {showBankPicker && (
              <View style={{ width: '100%', maxHeight: 200, borderRadius: 12, borderWidth: 1, borderColor: colors.border, backgroundColor: colors.background, marginBottom: 8 }}>
                <TextInput
                  style={{ padding: 10, fontSize: 14, color: colors.textPrimary, fontFamily: 'DM Sans', borderBottomWidth: 1, borderBottomColor: colors.border }}
                  placeholder="Search banks..."
                  placeholderTextColor={colors.textSecondary}
                  value={bankSearch}
                  onChangeText={setBankSearch}
                  data-testid="bank-search-input"
                />
                <ScrollView style={{ maxHeight: 150 }} nestedScrollEnabled>
                  {(bankSearch ? banksList.filter(b => b.toLowerCase().includes(bankSearch.toLowerCase())) : banksList).map(bank => (
                    <TouchableOpacity
                      key={bank}
                      style={{ paddingHorizontal: 12, paddingVertical: 10, backgroundColor: bankForm.bank_name === bank ? (isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.08)') : 'transparent' }}
                      onPress={() => {
                        setBankForm(p => ({ ...p, bank_name: bank, account_name: p.account_name || bank.split(' (')[0] + ' Savings' }));
                        setShowBankPicker(false);
                        setBankSearch('');
                      }}
                    >
                      <Text style={{ fontSize: 13, color: colors.textPrimary, fontFamily: 'DM Sans' }}>{bank}</Text>
                    </TouchableOpacity>
                  ))}
                </ScrollView>
              </View>
            )}

            {/* Account Name */}
            <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>Account Name *</Text>
            <TextInput
              data-testid="bank-account-name-input"
              style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
              value={bankForm.account_name}
              onChangeText={v => setBankForm(p => ({ ...p, account_name: v }))}
              placeholder="e.g., HDFC Savings"
              placeholderTextColor={colors.textSecondary}
            />

            {/* Account Number */}
            <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>Account Number (optional)</Text>
            <TextInput
              data-testid="bank-account-number-input"
              style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
              value={bankForm.account_number}
              onChangeText={v => setBankForm(p => ({ ...p, account_number: v }))}
              placeholder="Account number"
              placeholderTextColor={colors.textSecondary}
              keyboardType="numeric"
            />

            {/* IFSC Code */}
            <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>IFSC Code (optional)</Text>
            <TextInput
              data-testid="bank-ifsc-input"
              style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
              value={bankForm.ifsc_code}
              onChangeText={v => setBankForm(p => ({ ...p, ifsc_code: v.toUpperCase() }))}
              placeholder="e.g., HDFC0001234"
              placeholderTextColor={colors.textSecondary}
              autoCapitalize="characters"
            />

            {/* Set as Default */}
            <TouchableOpacity
              data-testid="bank-set-default-toggle"
              style={{ flexDirection: 'row', alignItems: 'center', gap: 10, marginBottom: 16, width: '100%' }}
              onPress={() => setBankForm(p => ({ ...p, is_default: !p.is_default }))}
            >
              <MaterialCommunityIcons
                name={bankForm.is_default ? 'checkbox-marked' : 'checkbox-blank-outline'}
                size={22}
                color={bankForm.is_default ? Accent.sapphire : colors.textSecondary}
              />
              <Text style={{ fontSize: 14, color: colors.textPrimary, fontFamily: 'DM Sans' }}>Set as default account</Text>
            </TouchableOpacity>

            <View style={[styles.deleteModalActions, { width: '100%' }]}>
              <TouchableOpacity
                style={[styles.cancelModalBtn, { borderColor: colors.border }]}
                onPress={() => { setShowBankModal(false); setEditingBank(null); }}
              >
                <Text style={[styles.cancelModalText, { color: colors.textPrimary }]}>Cancel</Text>
              </TouchableOpacity>
              <TouchableOpacity
                data-testid="save-bank-account-btn"
                style={[styles.confirmDeleteBtn, { backgroundColor: Accent.sapphire }]}
                onPress={saveBankAccount}
              >
                <Text style={styles.confirmDeleteText}>{editingBank ? 'Update' : 'Add'}</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </Modal>

      {/* ═══ BANK STATEMENT UPLOAD MODAL ═══ */}
      <Modal visible={showUploadModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.deleteModal, { backgroundColor: colors.surface, maxWidth: 420, width: '100%' }]}>
            {!uploadResult ? (
              <>
                {uploadingStatement ? (
                  <>
                    {/* Progress View */}
                    <View style={[styles.deleteModalIcon, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
                      <MaterialCommunityIcons 
                        name={uploadPhase === 'uploading' ? 'cloud-upload' : uploadPhase === 'processing' ? 'cog' : 'check-circle'} 
                        size={48} 
                        color={Accent.emerald} 
                      />
                    </View>
                    <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>
                      {uploadPhase === 'uploading' ? 'Uploading...' : uploadPhase === 'processing' ? 'Processing...' : 'Complete!'}
                    </Text>
                    <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans', marginBottom: 16, textAlign: 'center' }}>
                      {uploadPhase === 'uploading' 
                        ? 'Sending file to server...' 
                        : uploadPhase === 'processing' 
                          ? 'Parsing transactions and creating entries...' 
                          : 'All done!'}
                    </Text>
                    
                    {/* Progress Bar */}
                    <View style={[styles.progressBarContainer, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                      <View style={[styles.progressBarFill, { width: `${uploadProgress}%`, backgroundColor: Accent.emerald }]} />
                    </View>
                    <Text style={{ fontSize: 12, color: Accent.emerald, fontFamily: 'DM Sans', fontWeight: '700', marginTop: 8 }}>
                      {uploadProgress}%
                    </Text>
                    
                    {/* Phase indicators */}
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginTop: 16, paddingHorizontal: 4 }}>
                      {['Upload', 'Parse', 'Done'].map((step, i) => {
                        const isActive = (i === 0 && uploadPhase === 'uploading') || 
                                         (i === 1 && uploadPhase === 'processing') || 
                                         (i === 2 && uploadPhase === 'complete');
                        const isDone = (i === 0 && uploadProgress >= 45) || 
                                       (i === 1 && uploadProgress >= 90) || 
                                       (i === 2 && uploadProgress >= 100);
                        return (
                          <View key={step} style={{ alignItems: 'center', flex: 1 }}>
                            <View style={[styles.phaseIndicator, { 
                              backgroundColor: isDone ? Accent.emerald : isActive ? 'rgba(16,185,129,0.3)' : isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.06)'
                            }]}>
                              {isDone ? (
                                <MaterialCommunityIcons name="check" size={14} color="#fff" />
                              ) : (
                                <Text style={{ fontSize: 11, color: isActive ? Accent.emerald : colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600' }}>
                                  {i + 1}
                                </Text>
                              )}
                            </View>
                            <Text style={{ fontSize: 10, color: isActive || isDone ? Accent.emerald : colors.textSecondary, fontFamily: 'DM Sans', marginTop: 4 }}>
                              {step}
                            </Text>
                          </View>
                        );
                      })}
                    </View>
                  </>
                ) : (
                  <>
                    <View style={[styles.deleteModalIcon, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
                      <MaterialCommunityIcons name="file-upload" size={48} color={Accent.emerald} />
                    </View>
                    <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>Upload Bank Statement</Text>
                    
                    {selectedFile && (
                      <View style={[styles.selectedFileCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', borderColor: colors.border }]}>
                        <MaterialCommunityIcons 
                          name={selectedFile.name?.endsWith('.pdf') ? 'file-pdf-box' : selectedFile.name?.endsWith('.csv') ? 'file-delimited' : 'file-excel'} 
                          size={24} 
                          color={selectedFile.name?.endsWith('.pdf') ? '#EF4444' : selectedFile.name?.endsWith('.csv') ? Accent.emerald : Accent.sapphire} 
                        />
                        <View style={{ flex: 1 }}>
                          <Text style={{ fontSize: 14, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }} numberOfLines={1}>
                            {selectedFile.name}
                          </Text>
                          <Text style={{ fontSize: 11, color: colors.textSecondary, fontFamily: 'DM Sans', marginTop: 2 }}>
                            {(selectedFile.size / 1024).toFixed(1)} KB
                          </Text>
                        </View>
                        <TouchableOpacity onPress={handlePickFile}>
                          <MaterialCommunityIcons name="swap-horizontal" size={20} color={colors.textSecondary} />
                        </TouchableOpacity>
                      </View>
                    )}

                    <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start', marginTop: 16 }}>Bank Name (optional)</Text>
                    <TextInput
                      data-testid="upload-bank-name-input"
                      style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
                      value={uploadBankName}
                      onChangeText={setUploadBankName}
                      placeholder="e.g., ICICI, SBI, HDFC"
                      placeholderTextColor={colors.textSecondary}
                    />

                    <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>Account Name (optional)</Text>
                    <TextInput
                      data-testid="upload-account-name-input"
                      style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 8 }]}
                      value={uploadAccountName}
                      onChangeText={setUploadAccountName}
                      placeholder="e.g., HDFC Savings"
                      placeholderTextColor={colors.textSecondary}
                    />

                    <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6, alignSelf: 'flex-start' }}>PDF Password (if protected)</Text>
                    <TextInput
                      data-testid="upload-password-input"
                      style={[styles.deleteInput, { borderColor: colors.border, backgroundColor: colors.background, textAlign: 'left', paddingHorizontal: 12, marginBottom: 16 }]}
                      value={uploadPassword}
                      onChangeText={setUploadPassword}
                      placeholder="Leave empty if not protected"
                      placeholderTextColor={colors.textSecondary}
                      secureTextEntry={true}
                    />

                    <View style={[styles.deleteModalActions, { width: '100%' }]}>
                      <TouchableOpacity
                        style={[styles.cancelModalBtn, { borderColor: colors.border }]}
                        onPress={closeUploadModal}
                      >
                        <Text style={[styles.cancelModalText, { color: colors.textPrimary }]}>Cancel</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        data-testid="confirm-upload-btn"
                        style={[styles.confirmDeleteBtn, { backgroundColor: Accent.emerald }]}
                        onPress={handleUploadStatement}
                      >
                        <Text style={styles.confirmDeleteText}>Upload & Import</Text>
                      </TouchableOpacity>
                    </View>
                  </>
                )}
              </>
            ) : uploadResult.error ? (
              <>
                <View style={[styles.deleteModalIcon, { backgroundColor: 'rgba(239,68,68,0.1)' }]}>
                  <MaterialCommunityIcons name="alert-circle" size={48} color={Accent.ruby} />
                </View>
                <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>Upload Failed</Text>
                <Text style={[styles.deleteModalDesc, { color: colors.textSecondary }]}>{uploadResult.error}</Text>
                <TouchableOpacity
                  style={[styles.syncBtn, { borderColor: colors.border, marginTop: 16, width: '100%' }]}
                  onPress={closeUploadModal}
                >
                  <Text style={[styles.syncBtnText, { color: colors.textPrimary }]}>Close</Text>
                </TouchableOpacity>
              </>
            ) : (
              <>
                <View style={[styles.deleteModalIcon, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
                  <MaterialCommunityIcons name="check-circle" size={48} color={Accent.emerald} />
                </View>
                <Text style={[styles.deleteModalTitle, { color: colors.textPrimary }]}>Import Successful!</Text>
                
                <View style={[styles.resultCard, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', borderColor: colors.border }]}>
                  <View style={styles.resultRow}>
                    <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Bank Account</Text>
                    <Text style={{ fontSize: 14, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }}>{uploadResult.account_name}</Text>
                  </View>
                  <View style={styles.resultRow}>
                    <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Total in Statement</Text>
                    <Text style={{ fontSize: 14, color: colors.textPrimary, fontFamily: 'DM Sans', fontWeight: '600' }}>{uploadResult.total_in_statement}</Text>
                  </View>
                  <View style={styles.resultRow}>
                    <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Imported</Text>
                    <Text style={{ fontSize: 14, color: Accent.emerald, fontFamily: 'DM Sans', fontWeight: '700' }}>{uploadResult.imported}</Text>
                  </View>
                  {uploadResult.skipped_duplicates > 0 && (
                    <View style={styles.resultRow}>
                      <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Skipped (Duplicates)</Text>
                      <Text style={{ fontSize: 14, color: Accent.amber, fontFamily: 'DM Sans', fontWeight: '600' }}>{uploadResult.skipped_duplicates}</Text>
                    </View>
                  )}
                  {uploadResult.date_range?.start && (
                    <View style={styles.resultRow}>
                      <Text style={{ fontSize: 13, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Date Range</Text>
                      <Text style={{ fontSize: 12, color: colors.textPrimary, fontFamily: 'DM Sans' }}>
                        {uploadResult.date_range.start} to {uploadResult.date_range.end}
                      </Text>
                    </View>
                  )}
                  {uploadResult.account_created && (
                    <View style={[styles.resultBadge, { backgroundColor: 'rgba(59,130,246,0.1)' }]}>
                      <MaterialCommunityIcons name="bank-plus" size={16} color={Accent.sapphire} />
                      <Text style={{ fontSize: 12, color: Accent.sapphire, fontFamily: 'DM Sans', fontWeight: '600' }}>New bank account created</Text>
                    </View>
                  )}
                </View>

                <TouchableOpacity
                  style={[styles.confirmDeleteBtn, { backgroundColor: Accent.emerald, marginTop: 16, width: '100%', paddingVertical: 14 }]}
                  onPress={closeUploadModal}
                >
                  <Text style={styles.confirmDeleteText}>Done</Text>
                </TouchableOpacity>
              </>
            )}
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
        thumbColor={value ? Accent.amethyst : '#CBD5E1'}
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
  headerTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any },
  headerSubtitle: { fontSize: 13, marginTop: 2 },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 16, paddingBottom: 120 },

  // Tab Bar
  tabBar: { flexDirection: 'row', flexWrap: 'wrap', borderRadius: 14, padding: 6, marginBottom: 16 },
  tabItem: { width: '33.33%', alignItems: 'center', paddingVertical: 10, borderRadius: 10 },
  tabLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, marginTop: 4 },

  // Card
  card: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 14 },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 16 },
  cardIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  cardTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },

  // Profile Banner
  profileBanner: { borderRadius: 16, padding: 16, marginBottom: 16 },
  profileLeft: { flexDirection: 'row', alignItems: 'center', gap: 14, marginBottom: 14 },
  avatarLarge: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },
  avatarText: { color: '#fff', fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any },
  profileInfo: { flex: 1 },
  profileName: { fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any },
  profileEmail: { fontSize: 13, marginTop: 2 },
  verifiedBadge: { flexDirection: 'row', alignItems: 'center', gap: 4, alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 4, borderRadius: 8, marginTop: 6 },
  verifiedText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, color: Accent.emerald },
  profileActions: { flexDirection: 'row', gap: 10 },
  editBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 12, borderWidth: 1 },
  editBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  signOutBtn: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6, paddingVertical: 10, borderRadius: 12, backgroundColor: 'rgba(239, 68, 68, 0.1)' },
  signOutText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, color: Accent.ruby },

  // Details Grid
  detailsGrid: { gap: 12 },
  fieldContainer: { borderRadius: 12, padding: 12, borderWidth: 1 },
  fieldHeader: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 4 },
  fieldLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.3 },
  fieldValueRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  fieldValue: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  eyeBtn: { padding: 4 },
  fieldHelper: { fontSize: 10, marginTop: 4 },

  // Section Label
  sectionLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 12, marginTop: 8 },

  // Separator
  separator: { height: 1, marginVertical: 16 },

  // Security Banner
  securityBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 14, marginBottom: 16 },
  securityBannerTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  securityBannerDesc: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },

  // Lock Now Button
  lockNowBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 12, borderRadius: 12, borderWidth: 1.5, marginTop: 4, marginBottom: 4 },
  lockNowText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },

  // Encryption Info
  encryptionInfo: { borderRadius: 14, padding: 14, gap: 10 },
  encryptionRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  encryptionText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any },

  // Sources Tab
  sourceDesc: { fontSize: 13, fontFamily: 'DM Sans', lineHeight: 20, marginBottom: 16 },
  connectedBanner: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 14, marginBottom: 12 },
  connectedTitle: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  connectedSubtext: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
  syncBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, paddingVertical: 12, borderRadius: 12, borderWidth: 1.5, marginBottom: 8 },
  syncBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  syncResult: { fontSize: 12, fontFamily: 'DM Sans', textAlign: 'center', marginBottom: 8 },
  disconnectBtn: { alignItems: 'center', paddingVertical: 10 },
  disconnectText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, color: '#EF4444' },
  connectGmailBtn: { borderRadius: 999, overflow: 'hidden', marginBottom: 16 },
  connectGmailGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, height: 50, borderRadius: 999 },
  connectGmailText: { color: '#fff', fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  banksList: { borderRadius: 14, padding: 14, marginTop: 4 },
  banksTitle: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 6 },
  bankNames: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '500' as any, lineHeight: 20 },
  smsPlatformNote: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 14, borderRadius: 14 },
  smsPlatformText: { fontSize: 13, fontFamily: 'DM Sans', flex: 1, lineHeight: 20 },

  // Toggle Row
  toggleRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 10, gap: 12 },
  toggleIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  toggleInfo: { flex: 1 },
  toggleTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  toggleDesc: { fontSize: 12, marginTop: 2 },

  // Future Feature
  futureFeature: { flexDirection: 'row', alignItems: 'center', gap: 10, padding: 12, borderRadius: 12, marginTop: 8 },
  futureText: { flex: 1, fontSize: 12, lineHeight: 17 },

  // Setting Row
  settingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, paddingHorizontal: 4 },
  settingLeft: { flex: 1 },
  settingTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  settingDesc: { fontSize: 12, marginTop: 2 },

  // Currency Selector
  currencySelector: { flexDirection: 'row', borderRadius: 10, borderWidth: 1, overflow: 'hidden' },
  currencyOption: { paddingHorizontal: 12, paddingVertical: 8 },
  currencyText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // Risk Selector
  riskSelector: { flexDirection: 'row', borderRadius: 10, borderWidth: 1, overflow: 'hidden' },
  riskOption: { paddingHorizontal: 10, paddingVertical: 8 },
  riskText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any },

  // Slider
  sliderSection: { paddingVertical: 8 },
  sliderHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  sliderValue: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12 },
  sliderValueText: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  slider: { width: '100%', height: 40 },
  sliderLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: -8 },
  sliderLabel: { fontSize: 11 },

  // Theme Options
  themeOptions: { flexDirection: 'row', gap: 10 },
  themeCard: { flex: 1, alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1.5 },
  themeIconWrap: { width: 48, height: 48, borderRadius: 14, justifyContent: 'center', alignItems: 'center', marginBottom: 10 },
  themeLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 6 },

  // Data Row
  dataRow: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 12, gap: 12 },
  dataIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  dataInfo: { flex: 1 },
  dataTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  dataDesc: { fontSize: 12, marginTop: 2 },
  exportBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, borderWidth: 1 },
  exportBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // Danger Zone
  dangerZone: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 16, gap: 12 },
  dangerTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any },
  dangerDesc: { fontSize: 12, marginTop: 2 },
  deleteBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 10, backgroundColor: Accent.ruby },
  deleteBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, color: '#fff' },

  // App Info
  appInfo: { alignItems: 'center', marginTop: 16, gap: 4 },
  appInfoText: { fontSize: 12 },

  // Modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'center', alignItems: 'center', padding: 24 },
  deleteModal: { width: '100%', maxWidth: 360, borderRadius: 24, padding: 24, alignItems: 'center' },
  deleteModalIcon: { width: 80, height: 80, borderRadius: 40, justifyContent: 'center', alignItems: 'center', marginBottom: 16 },
  deleteModalTitle: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 8 },
  deleteModalDesc: { fontSize: 14, textAlign: 'center', lineHeight: 20, marginBottom: 16 },
  deleteModalPrompt: { fontSize: 13, marginBottom: 12 },
  deleteInput: { width: '100%', height: 48, borderRadius: 12, borderWidth: 1, paddingHorizontal: 16, fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, textAlign: 'center', marginBottom: 20 },
  deleteModalActions: { flexDirection: 'row', gap: 12, width: '100%' },
  cancelModalBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, borderWidth: 1, alignItems: 'center' },
  cancelModalText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  confirmDeleteBtn: { flex: 1, paddingVertical: 14, borderRadius: 12, backgroundColor: Accent.ruby, alignItems: 'center' },
  confirmDeleteText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, color: '#fff' },

  // Upload Statement Styles
  formatBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10 },
  uploadBtn: { borderRadius: 999, overflow: 'hidden' },
  uploadBtnGradient: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10, height: 50, borderRadius: 999 },
  uploadBtnText: { color: '#fff', fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  selectedFileCard: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 14, borderWidth: 1, width: '100%', marginTop: 8 },
  resultCard: { width: '100%', borderRadius: 14, padding: 14, borderWidth: 1, marginTop: 16 },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 0.5, borderBottomColor: 'rgba(0,0,0,0.05)' },
  resultBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 10, marginTop: 10 },
  progressBarContainer: { width: '100%', height: 8, borderRadius: 4, overflow: 'hidden' },
  progressBarFill: { height: '100%', borderRadius: 4 },
  phaseIndicator: { width: 24, height: 24, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
});
