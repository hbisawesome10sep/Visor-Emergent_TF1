import React, { useEffect, useState, useCallback, useRef } from 'react';
import { useFocusEffect } from 'expo-router';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
  TextInput, KeyboardAvoidingView, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
import DateTimePicker from '@react-native-community/datetimepicker';
import Svg, { Circle, G } from 'react-native-svg';
import * as DocumentPicker from 'expo-document-picker';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { useScreenContext } from '../../src/context/ScreenContext';
import { Accent } from '../../src/utils/theme';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';
import PieChart from '../../src/components/PieChart';
import { WhatIfSimulator } from '../../src/components/WhatIfSimulator';
import { 
  MarketTickerBar, 
  GoalsSection, 
  PortfolioOverviewCard, 
  HoldingsSection, 
  RiskProfileCard, 
  RecurringInvestmentsSection,
  StockHoldingsCard,
  MutualFundHoldingsCard,
  UploadDropdown,
} from '../../src/components/investments';
import EMITrackerModal from '../../src/components/EMITrackerModal';
import { PrincipalInterestSplit } from '../../src/components/emi-sip/PrincipalInterestSplit';
import { PrepaymentCalculator } from '../../src/components/emi-sip/PrepaymentCalculator';
import { WealthProjector } from '../../src/components/emi-sip/WealthProjector';
import { GoalMapper } from '../../src/components/emi-sip/GoalMapper';
import {
  type MarketItem, type Goal, type DashboardStats, type PortfolioData,
  type Holding, type HoldingsData, type RecurringTransaction, type RecurringData,
  ASSET_CATEGORIES, GOAL_CATS, HOLDING_CATS, SIP_CATS, SIP_FREQUENCIES,
  RISK_QUESTIONS, RISK_CATEGORY_LABELS, RISK_CATEGORY_DISPLAY,
} from '../../src/components/investments/types';

const { width: SCREEN_WIDTH } = Dimensions.get('window');
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

export default function InvestmentsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const { setCurrentScreen } = useScreenContext();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;

  const [marketData, setMarketData] = useState<MarketItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showRiskModal, setShowRiskModal] = useState(false);
  const [showGoalModal, setShowGoalModal] = useState(false);
  const [editGoal, setEditGoal] = useState<Goal | null>(null);
  const [riskStep, setRiskStep] = useState(0);
  const [riskAnswers, setRiskAnswers] = useState<{question_id: number; value: number; category: string}[]>([]);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Moderate' | 'Aggressive'>('Moderate');
  const [riskScore, setRiskScore] = useState(0);
  const [riskBreakdown, setRiskBreakdown] = useState<Record<string, number>>({});
  const [riskSaved, setRiskSaved] = useState(false);
  const [showRiskResult, setShowRiskResult] = useState(false);
  const [goalForm, setGoalForm] = useState({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
  const [saving, setSaving] = useState(false);
  const [holdingsData, setHoldingsData] = useState<HoldingsData | null>(null);
  const [showHoldingModal, setShowHoldingModal] = useState(false);
  const [showCasModal, setShowCasModal] = useState(false);
  const [holdingForm, setHoldingForm] = useState({ name: '', ticker: '', isin: '', category: 'Stock', quantity: '', buy_price: '', buy_date: '' });
  // Native date picker state
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [datePickerTarget, setDatePickerTarget] = useState<'goal_deadline' | 'holding_buy_date' | 'sip_start_date'>('goal_deadline');
  const [datePickerValue, setDatePickerValue] = useState(new Date());
  const [casPassword, setCasPassword] = useState('');
  const [rebalanceData, setRebalanceData] = useState<any>(null);
  const [recurringData, setRecurringData] = useState<RecurringData | null>(null);
  const [showSipModal, setShowSipModal] = useState(false);
  const [showEMITracker, setShowEMITracker] = useState(false);
  const [editSip, setEditSip] = useState<RecurringTransaction | null>(null);
  const [sipForm, setSipForm] = useState({ name: '', amount: '', frequency: 'monthly', category: 'SIP', start_date: '', day_of_month: '5', notes: '' });
  const [sipSuggestions, setSipSuggestions] = useState<Array<{ id: string; fund_name: string; isin: string }>>([]);

  const [uploadingStatement, setUploadingStatement] = useState(false);
  const [refreshingPrices, setRefreshingPrices] = useState(false);

  const handleRefreshPrices = async () => {
    setRefreshingPrices(true);
    try {
      const resp = await apiRequest('/holdings/refresh-prices', { method: 'POST', token });
      if (resp?.updated > 0) {
        Alert.alert('Prices Updated', `Updated ${resp.updated} of ${resp.total} holdings with live prices.`);
        fetchData();
      } else {
        Alert.alert('No Updates', resp?.message || 'Prices are already up to date.');
      }
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to refresh prices');
    } finally {
      setRefreshingPrices(false);
    }
  };

  const isPickingRef = useRef(false);

  // Safely open document picker — catches iOS "picking in progress" and retries once
  const safePickDocument = async (options: Parameters<typeof DocumentPicker.getDocumentAsync>[0]) => {
    try {
      return await DocumentPicker.getDocumentAsync(options);
    } catch (e: any) {
      const msg: string = e?.message || '';
      if (msg.toLowerCase().includes('picking in progress') || msg.toLowerCase().includes('another picker')) {
        await new Promise(r => setTimeout(r, 800));
        return await DocumentPicker.getDocumentAsync(options);
      }
      throw e;
    }
  };

  const handleStatementUpload = async (type: 'stock_statement' | 'mf_statement' | 'ecas') => {
    if (type === 'ecas') {
      setShowCasModal(true);
      return;
    }
    if (isPickingRef.current) return;
    isPickingRef.current = true;
    try {
      const result = await safePickDocument({
        type: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/vnd.ms-excel'],
        copyToCacheDirectory: true,
      });
      if (result.canceled || !result.assets?.length) return;
      const file = result.assets[0];
      setUploadingStatement(true);
      const formData = new FormData();
      formData.append('file', { uri: file.uri, name: file.name, type: file.mimeType || 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' } as any);
      formData.append('statement_type', type);
      const resp = await apiRequest('/upload-statement', { token, method: 'POST', body: formData, isFormData: true });
      setUploadingStatement(false);
      if (resp?.status === 'success') {
        const sipMsg = resp.sip_suggestions_created > 0 ? `\n${resp.sip_suggestions_created} SIP suggestion(s) added for your review.` : '';
        Alert.alert('Import Successful', `${resp.saved} holdings imported, ${resp.duplicates} updated.\nSource: ${resp.metadata?.source || 'Unknown'}${sipMsg}`);
        fetchData();
      } else if (resp?.status === 'no_holdings') {
        Alert.alert('No Holdings Found', resp.message || 'Please check the file format.');
      } else {
        Alert.alert('Import Failed', resp?.detail || resp?.message || 'Unknown error');
      }
    } catch (e: any) {
      setUploadingStatement(false);
      Alert.alert('Upload Error', e.message || 'Failed to upload statement');
    } finally {
      isPickingRef.current = false;
    }
  };

  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Set screen context for AI awareness
  useEffect(() => {
    setCurrentScreen('investments');
  }, [setCurrentScreen]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [statsData, goalsData, mktData, portfolioData, holdingsLive, savedRisk, rebalancing, recurringTxns, sipSuggestionsData] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/goals', { token }),
        apiRequest('/market-data?force=true', {}),
        apiRequest('/portfolio-overview', { token }),
        apiRequest('/holdings/live', { token }),
        apiRequest('/risk-profile', { token }),
        apiRequest('/portfolio-rebalancing', { token }),
        apiRequest('/recurring', { token }),
        apiRequest('/sip-suggestions', { token }),
      ]);
      setStats(statsData);
      setGoals(goalsData);
      setMarketData(mktData || []);
      setPortfolio(portfolioData);
      setHoldingsData(holdingsLive);
      setRebalanceData(rebalancing);
      setRecurringData(recurringTxns);
      setSipSuggestions(sipSuggestionsData?.suggestions || []);
      if (savedRisk && savedRisk.profile) {
        setRiskProfile(savedRisk.profile);
        setRiskScore(savedRisk.score || 0);
        setRiskBreakdown(savedRisk.breakdown || {});
        setRiskSaved(true);
      }
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }).start();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token]);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Re-fetch when tab comes back into focus (e.g., after approving a SIP in Transactions)
  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [fetchData])
  );

  const onRefresh = () => { setRefreshing(true); fetchData(); };

  // ── Date picker helpers ──
  const openInvestDatePicker = (target: 'goal_deadline' | 'holding_buy_date' | 'sip_start_date') => {
    let current = new Date();
    if (target === 'goal_deadline' && goalForm.deadline) {
      const d = new Date(goalForm.deadline);
      if (!isNaN(d.getTime())) current = d;
    } else if (target === 'holding_buy_date' && holdingForm.buy_date) {
      const d = new Date(holdingForm.buy_date);
      if (!isNaN(d.getTime())) current = d;
    } else if (target === 'sip_start_date' && sipForm.start_date) {
      const d = new Date(sipForm.start_date);
      if (!isNaN(d.getTime())) current = d;
    }
    setDatePickerValue(current);
    setIosPickerDate(current);
    setDatePickerTarget(target);
    setShowDatePicker(true);
  };

  const handleInvestDateChange = (event: any, selectedDate?: Date) => {
    setShowDatePicker(false);
    if (event.type === 'dismissed' || !selectedDate) return;
    const formatted = selectedDate.toISOString().split('T')[0];
    if (datePickerTarget === 'goal_deadline') {
      setGoalForm(f => ({ ...f, deadline: formatted }));
    } else if (datePickerTarget === 'holding_buy_date') {
      setHoldingForm(f => ({ ...f, buy_date: formatted }));
    } else if (datePickerTarget === 'sip_start_date') {
      setSipForm(f => ({ ...f, start_date: formatted }));
    }
  };

  // iOS date picker: updates state live (no dismiss event)
  const [iosPickerDate, setIosPickerDate] = useState(new Date());

  // ── Goal handlers ──
  const openAddGoal = () => {
    setEditGoal(null);
    setGoalForm({ title: '', target_amount: '', current_amount: '0', deadline: '', category: 'Safety' });
    setShowGoalModal(true);
  };
  const openEditGoal = (g: Goal) => {
    setEditGoal(g);
    setGoalForm({ title: g.title, target_amount: g.target_amount.toString(), current_amount: g.current_amount.toString(), deadline: g.deadline, category: g.category });
    setShowGoalModal(true);
  };
  const handleSaveGoal = async () => {
    if (!goalForm.title || !goalForm.target_amount || !goalForm.category) { Alert.alert('Error', 'Please fill required fields'); return; }
    setSaving(true);
    try {
      const body = { title: goalForm.title, target_amount: parseFloat(goalForm.target_amount), current_amount: parseFloat(goalForm.current_amount || '0'), deadline: goalForm.deadline || '2026-12-31', category: goalForm.category };
      if (editGoal) { await apiRequest(`/goals/${editGoal.id}`, { method: 'PUT', token, body }); }
      else { await apiRequest('/goals', { method: 'POST', token, body }); }
      setShowGoalModal(false);
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };
  const handleDeleteGoal = (id: string, title: string) => {
    Alert.alert('Delete Goal', `Delete "${title}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { await apiRequest(`/goals/${id}`, { method: 'DELETE', token }); fetchData(); } },
    ]);
  };

  // ── SIP/Recurring handlers ──
  const openAddSip = () => {
    setEditSip(null);
    const today = new Date().toISOString().split('T')[0];
    setSipForm({ name: '', amount: '', frequency: 'monthly', category: 'SIP', start_date: today, day_of_month: '5', notes: '' });
    setShowSipModal(true);
  };
  const openEditSip = (sip: RecurringTransaction) => {
    setEditSip(sip);
    setSipForm({
      name: sip.name,
      amount: sip.amount.toString(),
      frequency: sip.frequency,
      category: sip.category,
      start_date: sip.start_date,
      day_of_month: sip.day_of_month.toString(),
      notes: sip.notes || '',
    });
    setShowSipModal(true);
  };
  const handleSaveSip = async () => {
    if (!sipForm.name || !sipForm.amount || !sipForm.category) {
      Alert.alert('Error', 'Please fill required fields');
      return;
    }
    setSaving(true);
    try {
      const body = {
        name: sipForm.name,
        amount: parseFloat(sipForm.amount),
        frequency: sipForm.frequency,
        category: sipForm.category,
        start_date: sipForm.start_date || new Date().toISOString().split('T')[0],
        day_of_month: parseInt(sipForm.day_of_month) || 5,
        notes: sipForm.notes || null,
        is_active: true,
      };
      if (editSip) {
        await apiRequest(`/recurring/${editSip.id}`, { method: 'PUT', token, body });
      } else {
        await apiRequest('/recurring', { method: 'POST', token, body });
      }
      setShowSipModal(false);
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    } finally {
      setSaving(false);
    }
  };
  const handleDeleteSip = (id: string, name: string) => {
    Alert.alert('Delete SIP', `Delete "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        await apiRequest(`/recurring/${id}`, { method: 'DELETE', token });
        fetchData();
      }},
    ]);
  };
  const handlePauseSip = async (sip: RecurringTransaction) => {
    try {
      await apiRequest(`/recurring/${sip.id}/pause`, { method: 'POST', token });
      fetchData();
    } catch (e: any) {
      Alert.alert('Error', e.message);
    }
  };
  const handleExecuteSip = async (sip: RecurringTransaction) => {
    Alert.alert(
      'Execute SIP',
      `Record investment of ${formatINR(sip.amount)} for ${sip.name}?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Execute', onPress: async () => {
          try {
            await apiRequest(`/recurring/${sip.id}/execute`, { method: 'POST', token });
            Alert.alert('Success', 'SIP executed successfully!');
            fetchData();
          } catch (e: any) {
            Alert.alert('Error', e.message);
          }
        }},
      ]
    );
  };


  const handleRiskAnswer = async (value: number) => {
    const q = RISK_QUESTIONS[riskStep];
    const newAnswers = [...riskAnswers, { question_id: q.id, value, category: q.category }];
    setRiskAnswers(newAnswers);
    if (riskStep < RISK_QUESTIONS.length - 1) {
      setRiskStep(riskStep + 1);
    } else {
      // Calculate score and breakdown
      const catScores: Record<string, number[]> = {};
      newAnswers.forEach(a => {
        if (!catScores[a.category]) catScores[a.category] = [];
        catScores[a.category].push(a.value);
      });
      const breakdown: Record<string, number> = {};
      Object.entries(catScores).forEach(([cat, vals]) => {
        breakdown[cat] = parseFloat((vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(2));
      });
      const avgScore = parseFloat((newAnswers.reduce((s, a) => s + a.value, 0) / newAnswers.length).toFixed(2));
      const profile: 'Conservative' | 'Moderate' | 'Aggressive' = avgScore <= 2.0 ? 'Conservative' : avgScore <= 3.5 ? 'Moderate' : 'Aggressive';

      setRiskScore(avgScore);
      setRiskBreakdown(breakdown);
      setRiskProfile(profile);
      setShowRiskResult(true);

      // Save to backend
      try {
        await apiRequest('/risk-profile', { method: 'POST', token, body: {
          answers: newAnswers, score: avgScore, profile, breakdown,
        }});
        setRiskSaved(true);
      } catch (e) { console.error('Failed to save risk profile', e); }
    }
  };

  const closeRiskModal = () => {
    setShowRiskModal(false);
    setShowRiskResult(false);
    setRiskStep(0);
    setRiskAnswers([]);
  };

  // ── Holdings handlers ──
  const openAddHolding = () => {
    setHoldingForm({ name: '', ticker: '', isin: '', category: 'Stock', quantity: '', buy_price: '', buy_date: '' });
    setShowHoldingModal(true);
  };
  const handleSaveHolding = async () => {
    if (!holdingForm.name || !holdingForm.quantity || !holdingForm.buy_price) { Alert.alert('Error', 'Name, Quantity, and Buy Price are required'); return; }
    setSaving(true);
    try {
      await apiRequest('/holdings', { method: 'POST', token, body: {
        name: holdingForm.name, ticker: holdingForm.ticker, isin: holdingForm.isin,
        category: holdingForm.category, quantity: parseFloat(holdingForm.quantity),
        buy_price: parseFloat(holdingForm.buy_price), buy_date: holdingForm.buy_date,
      }});
      setShowHoldingModal(false);
      fetchData();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };
  const handleDeleteHolding = (id: string, name: string) => {
    Alert.alert('Delete Holding', `Remove "${name}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => { await apiRequest(`/holdings/${id}`, { method: 'DELETE', token }); fetchData(); } },
    ]);
  };
  const handleCasUpload = async () => {
    if (isPickingRef.current) return;
    isPickingRef.current = true;
    try {
      // Use expo-document-picker for cross-platform file selection
      const result = await DocumentPicker.getDocumentAsync({
        type: 'application/pdf',
        copyToCacheDirectory: true,
      });
      
      if (result.canceled || !result.assets || result.assets.length === 0) {
        return; // User cancelled
      }
      
      const file = result.assets[0];
      setSaving(true);
      
      try {
        const formData = new FormData();
        
        // Handle file data for both web and native
        if (Platform.OS === 'web') {
          // For web, fetch the file and convert to blob
          const response = await fetch(file.uri);
          const blob = await response.blob();
          formData.append('file', blob, file.name || 'cas.pdf');
        } else {
          // For native (Android/iOS)
          formData.append('file', {
            uri: file.uri,
            name: file.name || 'cas.pdf',
            type: 'application/pdf',
          } as any);
        }
        
        formData.append('password', casPassword || '');
        
        const resp = await fetch(`${BACKEND_URL}/api/holdings/upload-cas`, {
          method: 'POST',
          headers: { 
            'Authorization': `Bearer ${token}`,
          },
          body: formData,
        });
        
        let data: any = {};
        try {
          const text = await resp.text();
          data = JSON.parse(text);
        } catch {
          throw new Error('Server returned an unexpected response. Please try again.');
        }
        
        if (!resp.ok) {
          throw new Error(data.detail || data.message || `Upload failed (${resp.status})`);
        }
        
        const sipMsg = data.sip_count > 0 ? `\n\nDetected ${data.sip_count} SIP${data.sip_count > 1 ? 's' : ''} — see suggestions below in the SIP section.` : '';
        Alert.alert('Success', `${data.message || `Imported ${data.imported || 0} holdings`}${sipMsg}`);
        setShowCasModal(false);
        setCasPassword('');
        fetchData();
      } catch (err: any) {
        console.error('CAS Upload Error:', err);
        Alert.alert('Upload Error', err.message || 'Failed to parse CAS. Please check the file and password.');
      } finally { 
        setSaving(false); 
      }
    } catch (e: any) { 
      console.error('File picker error:', e);
      Alert.alert('Error', 'Could not open file picker. Please try again.'); 
    } finally {
      isPickingRef.current = false;
    }
  };

  const handleClearHoldings = async () => {
    Alert.alert(
      'Clear All Holdings',
      'Are you sure you want to delete all your holdings? This action cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clear All',
          style: 'destructive',
          onPress: async () => {
            try {
              setSaving(true);
              const resp = await fetch(`${BACKEND_URL}/api/holdings/clear-all`, {
                method: 'DELETE',
                headers: { 'Authorization': `Bearer ${token}` },
              });
              const data = await resp.json();
              if (!resp.ok) throw new Error(data.detail || 'Failed to clear');
              Alert.alert('Success', data.message || 'Holdings cleared');
              fetchData();
            } catch (err: any) {
              Alert.alert('Error', err.message || 'Failed to clear holdings');
            } finally {
              setSaving(false);
            }
          },
        },
      ]
    );
  };

  // ── Computed values ──
  const totalInvested = portfolio?.total_invested || stats?.total_investments || 0;
  const allocation = stats?.invest_breakdown || {};

  // Build allocation data for pie chart - use current_value from portfolio categories (holdings-based)
  const pieData = portfolio?.categories?.length
    ? portfolio.categories.map(cat => ({
        category: ASSET_CATEGORIES[cat.category]?.label || cat.category,
        amount: cat.current_value,
        color: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8',
      }))
    : [];

  const totalAllocValue = pieData.reduce((s, d) => s + d.amount, 0);

  // Strategy based on risk
  const strategies = {
    Conservative: { name: 'Safe Harbor', allocation: [{ name: 'Debt', p: 60, c: Accent.emerald }, { name: 'Equity', p: 25, c: Accent.sapphire }, { name: 'Gold', p: 15, c: Accent.amber }] },
    Moderate: { name: 'Balanced Growth', allocation: [{ name: 'Equity', p: 40, c: Accent.sapphire }, { name: 'Debt', p: 30, c: Accent.emerald }, { name: 'Gold', p: 15, c: Accent.amber }, { name: 'Alt', p: 15, c: Accent.amethyst }] },
    Aggressive: { name: 'High Growth', allocation: [{ name: 'Equity', p: 70, c: Accent.sapphire }, { name: 'Alt', p: 15, c: Accent.amethyst }, { name: 'Debt', p: 10, c: Accent.emerald }, { name: 'Gold', p: 5, c: Accent.amber }] },
  };
  const currentStrategy = strategies[riskProfile];

  // Market data last updated
  const lastUpdatedStr = marketData.length > 0 ? (() => {
    const d = new Date(marketData[0].last_updated);
    const istOffset = 5.5 * 60 * 60 * 1000;
    const ist = new Date(d.getTime() + istOffset);
    return ist.toLocaleString('en-IN', { hour: '2-digit', minute: '2-digit', day: 'numeric', month: 'short' });
  })() : '';

  // Goals summary
  const totalGoalTarget = goals.reduce((s, g) => s + g.target_amount, 0);
  const totalGoalCurrent = goals.reduce((s, g) => s + g.current_amount, 0);
  const overallGoalProgress = totalGoalTarget > 0 ? (totalGoalCurrent / totalGoalTarget) * 100 : 0;

  // ── Helper: format price for markets (Indian comma system) ──
  const fmtPrice = (p: number) => {
    const num = Math.round(p);
    const str = num.toString();
    const digits = str.split('').reverse();
    let formatted = '';
    for (let i = 0; i < digits.length; i++) {
      if (i === 3 || (i > 3 && (i - 3) % 2 === 0)) formatted = ',' + formatted;
      formatted = digits[i] + formatted;
    }
    return formatted;
  };

  if (loading) {
    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#F97316" />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>Loading investments...</Text>
        </View>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* ═══ HEADER ═══ */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View style={[styles.headerContent, { backgroundColor: isDark ? '#000000' : '#FFFFFF', borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)' }]}>
          <View style={styles.headerLeft}>
            <Text data-testid="invest-header-title" style={[styles.headerTitle, { color: isDark ? Accent.amber : '#D97706' }]}>Invest</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>Markets & Portfolio</Text>
          </View>
          <TouchableOpacity data-testid="invest-refresh-btn" style={[styles.refreshBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)' }]} onPress={onRefresh}>
            <MaterialCommunityIcons name="refresh" size={20} color="#F97316" />
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + 12 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor="#F97316" />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══════════════════════════════════════════════════════════
             SECTION 1: INDIAN MARKETS (TOP)
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.marketSection}>
          <View style={styles.marketSectionHeader}>
            <Text data-testid="markets-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Indian Markets</Text>
            {lastUpdatedStr ? (
              <Text style={[styles.updatedAt, { color: colors.textSecondary }]}>Live  {lastUpdatedStr}</Text>
            ) : null}
          </View>

          <View data-testid="market-cards-grid" style={[styles.marketTable, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            {marketData.map((item, idx) => {
              const isUp = item.change_percent >= 0;
              const isLast = idx === marketData.length - 1;
              const isIndex = !item.key.includes('gold') && !item.key.includes('silver');
              return (
                <View key={item.key} data-testid={`market-card-${item.key}`} style={[styles.marketRow, !isLast && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                  <View style={styles.marketRowLeft}>
                    <View style={[styles.marketDot, { backgroundColor: isUp ? Accent.emerald : Accent.ruby }]} />
                    <View>
                      <Text style={[styles.marketRowName, { color: colors.textPrimary }]}>{item.name}</Text>
                      <Text style={[styles.marketRowSub, { color: colors.textSecondary }]}>
                        {isIndex ? 'Index' : item.key.includes('gold') ? '24K / 10g' : '999 / 1Kg'}
                      </Text>
                    </View>
                  </View>
                  <View style={styles.marketRowRight}>
                    <Text data-testid={`market-price-${item.key}`} style={[styles.marketRowPrice, { color: colors.textPrimary }]}>
                      {isIndex ? '' : '₹'}{fmtPrice(item.price)}
                    </Text>
                    <View style={styles.marketRowChangeWrap}>
                      <MaterialCommunityIcons name={isUp ? 'triangle' : 'triangle-down'} size={10} color={isUp ? Accent.emerald : Accent.ruby} />
                      <Text style={[styles.marketRowChange, { color: isUp ? Accent.emerald : Accent.ruby }]}>
                        {fmtPrice(Math.abs(Math.round(item.change)))} ({Math.abs(item.change_percent).toFixed(2)}%)
                      </Text>
                    </View>
                  </View>
                </View>
              );
            })}
          </View>
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 2: PORTFOLIO OVERVIEW
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="portfolio-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 28 }]}>Portfolio Overview</Text>

        <PortfolioOverviewCard
          portfolio={portfolio}
          colors={colors}
          isDark={isDark}
        />

        {/* ═══════════════════════════════════════════════════════════
             SECTION 2.5: MY HOLDINGS HEADER
           ═══════════════════════════════════════════════════════════ */}
        <View style={{ marginTop: 24, marginBottom: 14 }}>
          {/* Title row */}
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <Text data-testid="holdings-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0, marginTop: 0 }]}>My Holdings</Text>
            {/* Live Prices — icon-only compact button */}
            {holdingsData?.holdings && holdingsData.holdings.length > 0 && (
              <TouchableOpacity
                data-testid="refresh-prices-btn"
                style={{
                  flexDirection: 'row', alignItems: 'center', gap: 5,
                  paddingHorizontal: 10, paddingVertical: 5, borderRadius: 20,
                  backgroundColor: isDark ? 'rgba(16,185,129,0.12)' : 'rgba(16,185,129,0.08)',
                  borderWidth: 1, borderColor: isDark ? 'rgba(16,185,129,0.3)' : 'rgba(16,185,129,0.2)',
                }}
                onPress={handleRefreshPrices}
                disabled={refreshingPrices}
              >
                {refreshingPrices ? (
                  <ActivityIndicator size="small" color="#10B981" />
                ) : (
                  <MaterialCommunityIcons name="refresh" size={13} color="#10B981" />
                )}
                <Text style={{ fontSize: 11, fontWeight: '600' as any, color: '#10B981', fontFamily: 'DM Sans' }}>
                  {refreshingPrices ? 'Updating...' : 'Live Prices'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
          {/* Import Statement full-width button row */}
          <UploadDropdown
            colors={colors}
            isDark={isDark}
            onSelect={handleStatementUpload}
          />
        </View>

        {/* Stock Holdings */}
        {holdingsData?.holdings && holdingsData.holdings.filter(h => h.category === 'Stock').length > 0 && (
          <StockHoldingsCard
            holdings={holdingsData.holdings
              .filter(h => h.category === 'Stock')
              .map(h => ({
                id: h.id,
                name: h.name,
                ticker: h.ticker,
                quantity: h.quantity,
                buy_price: h.buy_price,
                current_value: h.current_value,
                invested_value: h.invested_value,
                gain_loss: h.gain_loss,
                gain_loss_pct: h.gain_loss_pct,
              }))}
            colors={colors}
            isDark={isDark}
          />
        )}

        {/* Mutual Fund Holdings */}
        {holdingsData?.holdings && holdingsData.holdings.filter(h => h.category === 'Mutual Fund').length > 0 && (
          <MutualFundHoldingsCard
            holdings={holdingsData.holdings
              .filter(h => h.category === 'Mutual Fund')
              .map(h => ({
                id: h.id,
                name: h.name,
                isin: h.isin,
                quantity: h.quantity,
                buy_price: h.buy_price,
                current_value: h.current_value,
                invested_value: h.invested_value,
                gain_loss: h.gain_loss,
                gain_loss_pct: h.gain_loss_pct,
                xirr: (h as any).xirr ?? null,
              }))}
            xirr={portfolio?.total_gain_loss_pct ? portfolio.total_gain_loss_pct : null}
            colors={colors}
            isDark={isDark}
          />
        )}

        {/* Empty state when no holdings */}
        {(!holdingsData?.holdings || holdingsData.holdings.length === 0) && (
          <View data-testid="empty-holdings" style={[styles.glassCard, {
            backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
            borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            alignItems: 'center', paddingVertical: 40,
          }]}>
            <MaterialCommunityIcons name="chart-timeline-variant-shimmer" size={40} color={colors.textSecondary} style={{ opacity: 0.5, marginBottom: 12 }} />
            <Text style={{ fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700', color: colors.textPrimary, marginBottom: 6 }}>No Holdings Yet</Text>
            <Text style={{ fontSize: 12, fontFamily: 'DM Sans', color: colors.textSecondary, textAlign: 'center', paddingHorizontal: 30, lineHeight: 18 }}>
              Upload your eCAS, stock, or mutual fund statement to see your real portfolio.
            </Text>
            <TouchableOpacity
              data-testid="add-holding-empty-btn"
              style={{ marginTop: 16, flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 16, paddingVertical: 9, borderRadius: 10, backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.08)' }}
              onPress={() => setShowHoldingModal(true)}
            >
              <MaterialCommunityIcons name="plus" size={16} color="#F97316" />
              <Text style={{ fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', color: '#F97316' }}>Add Manually</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Clear All Holdings Button - visible when user has holdings */}
        {holdingsData?.holdings && holdingsData.holdings.length > 0 && (
          <TouchableOpacity 
            data-testid="clear-holdings-main-btn" 
            style={{
              flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8,
              padding: 14, borderRadius: 12, borderWidth: 1,
              borderColor: Accent.ruby, marginBottom: 16, marginTop: 4,
            }} 
            onPress={handleClearHoldings}
          >
            <MaterialCommunityIcons name="delete-outline" size={18} color={Accent.ruby} />
            <Text style={{ fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600', color: Accent.ruby }}>Clear All Holdings</Text>
          </TouchableOpacity>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 3: ASSET ALLOCATION (Pie Chart)
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="allocation-section-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>Asset Allocation</Text>
        <View data-testid="allocation-card" style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          {pieData.length > 0 ? (
            <>
              <View style={styles.pieContainer}>
                <PieChart data={pieData} size={170} colors={colors} isDark={isDark} />
              </View>
              <View style={styles.legendGrid}>
                {pieData.map((item, idx) => {
                  const pct = totalAllocValue > 0 ? ((item.amount / totalAllocValue) * 100).toFixed(1) : '0';
                  return (
                    <View key={idx} data-testid={`allocation-legend-${item.category}`} style={styles.legendItem}>
                      <View style={[styles.legendDot, { backgroundColor: item.color }]} />
                      <Text style={[styles.legendName, { color: colors.textPrimary }]}>{item.category}</Text>
                      <Text style={[styles.legendPercent, { color: colors.textSecondary }]}>{pct}%</Text>
                      <Text style={[styles.legendAmount, { color: colors.textSecondary }]}>{formatINRShort(item.amount)}</Text>
                    </View>
                  );
                })}
              </View>
            </>
          ) : (
            <View style={styles.emptyPie}>
              <MaterialCommunityIcons name="chart-pie" size={40} color={colors.textSecondary} />
              <Text style={[styles.emptyPieText, { color: colors.textSecondary }]}>Add investment transactions to see allocation</Text>
            </View>
          )}
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 4: RISK PROFILE & STRATEGY
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="risk-section-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>Risk Profile & Strategy</Text>
        <RiskProfileCard
          riskProfile={riskProfile}
          riskScore={riskScore}
          riskBreakdown={riskBreakdown}
          riskSaved={riskSaved}
          colors={colors}
          isDark={isDark}
          onRetake={() => { setShowRiskModal(true); setRiskStep(0); setRiskAnswers([]); setShowRiskResult(false); }}
        />

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5: PORTFOLIO REBALANCING
           ═══════════════════════════════════════════════════════════ */}
        {rebalanceData && rebalanceData.total > 0 && rebalanceData.actions?.length > 0 && (
          <>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary }]}>Rebalancing Actions</Text>
            <View data-testid="rebalance-card" style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            }]}>
              <View style={styles.rebalanceHeader}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                  <MaterialCommunityIcons name="swap-horizontal-bold" size={18} color="#F97316" />
                  <Text style={[styles.rebalanceTitle, { color: colors.textPrimary }]}>{rebalanceData.strategy_name}</Text>
                </View>
                <Text style={[styles.rebalanceProfile, { color: colors.textSecondary }]}>{rebalanceData.profile}</Text>
              </View>

              {/* Actual vs Target comparison bars */}
              <View style={styles.rebalanceBars}>
                {Object.keys(rebalanceData.target).map((bucket: string) => {
                  const target = rebalanceData.target[bucket] || 0;
                  const actual = rebalanceData.actual[bucket] || 0;
                  const bucketColors: Record<string, string> = { Equity: Accent.sapphire, Debt: Accent.emerald, Gold: Accent.amber, Alt: Accent.amethyst };
                  const bc = bucketColors[bucket] || Accent.sapphire;
                  return (
                    <View key={bucket} data-testid={`rebalance-bar-${bucket}`} style={styles.rebalanceBarRow}>
                      <Text style={[styles.rebalanceBarLabel, { color: colors.textSecondary }]}>{bucket}</Text>
                      <View style={styles.rebalanceBarGroup}>
                        <View style={[styles.rebalanceBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
                          <View style={[styles.rebalanceBarActual, { width: `${Math.min(actual, 100)}%`, backgroundColor: bc }]} />
                        </View>
                        <View style={[styles.rebalanceBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)', marginTop: 3 }]}>
                          <View style={[styles.rebalanceBarTarget, { width: `${Math.min(target, 100)}%`, backgroundColor: bc, opacity: 0.35 }]} />
                        </View>
                      </View>
                      <View style={{ alignItems: 'flex-end', minWidth: 45 }}>
                        <Text style={[styles.rebalanceBarVal, { color: colors.textPrimary }]}>{actual.toFixed(0)}%</Text>
                        <Text style={[styles.rebalanceBarTarget2, { color: colors.textSecondary }]}>{target}%</Text>
                      </View>
                    </View>
                  );
                })}
              </View>
              <View style={{ flexDirection: 'row', gap: 12, marginBottom: 14 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 10, height: 4, borderRadius: 2, backgroundColor: Accent.sapphire }} />
                  <Text style={[{ fontSize: 10, color: colors.textSecondary }]}>Actual</Text>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
                  <View style={{ width: 10, height: 4, borderRadius: 2, backgroundColor: Accent.sapphire, opacity: 0.35 }} />
                  <Text style={[{ fontSize: 10, color: colors.textSecondary }]}>Target</Text>
                </View>
              </View>

              {/* Action items */}
              {rebalanceData.actions.map((action: any, idx: number) => (
                <View key={idx} data-testid={`rebalance-action-${idx}`} style={[styles.rebalanceActionRow, {
                  backgroundColor: action.action === 'reduce' ? 'rgba(239,68,68,0.06)' : 'rgba(16,185,129,0.06)',
                  borderColor: action.action === 'reduce' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)',
                }]}>
                  <MaterialCommunityIcons
                    name={action.action === 'reduce' ? 'arrow-down-circle' : 'arrow-up-circle'}
                    size={20}
                    color={action.action === 'reduce' ? Accent.ruby : Accent.emerald}
                  />
                  <Text style={[styles.rebalanceActionText, { color: colors.textPrimary }]}>{action.suggestion}</Text>
                </View>
              ))}
            </View>
          </>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.6: WHAT-IF SIMULATOR
           ═══════════════════════════════════════════════════════════ */}
        <WhatIfSimulator
          totalPortfolio={rebalanceData?.total || 100000}
          initialAlloc={rebalanceData?.target ? {
            Equity: rebalanceData.target.Equity || 40,
            Debt: rebalanceData.target.Debt || 30,
            Gold: rebalanceData.target.Gold || 15,
            Alt: rebalanceData.target.Alt || 15,
          } : undefined}
          isDark={isDark}
          colors={colors}
        />

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.6b: SIP SUGGESTIONS FROM eCAS
           ═══════════════════════════════════════════════════════════ */}
        {sipSuggestions.length > 0 && (
          <View style={{ marginBottom: 8 }}>
            <View style={[styles.sectionHeader, { marginBottom: 10 }]}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                <View style={{ backgroundColor: 'rgba(99,102,241,0.15)', borderRadius: 8, padding: 6 }}>
                  <MaterialCommunityIcons name="file-document-check-outline" size={16} color="#6366F1" />
                </View>
                <View>
                  <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0, fontSize: 14 }]}>
                    SIPs Detected from eCAS
                  </Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary }}>
                    {sipSuggestions.length} fund{sipSuggestions.length > 1 ? 's' : ''} identified as active SIPs
                  </Text>
                </View>
              </View>
            </View>
            {sipSuggestions.map(sug => (
              <View key={sug.id} style={[{
                backgroundColor: isDark ? '#161616' : '#FFFFFF',
                borderRadius: 14,
                padding: 14,
                marginBottom: 10,
                borderWidth: 1,
                borderColor: isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.15)',
                flexDirection: 'row',
                alignItems: 'center',
                gap: 12,
              }]}>
                <View style={{ flex: 1 }}>
                  <Text style={{ fontSize: 13, fontWeight: '600', color: colors.textPrimary, marginBottom: 2 }} numberOfLines={2}>
                    {sug.fund_name}
                  </Text>
                  {sug.isin ? (
                    <Text style={{ fontSize: 11, color: colors.textSecondary }}>ISIN: {sug.isin}</Text>
                  ) : null}
                </View>
                <View style={{ flexDirection: 'row', gap: 8 }}>
                  <TouchableOpacity
                    data-testid={`sip-suggest-approve-${sug.id}`}
                    style={{ backgroundColor: '#6366F1', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 7 }}
                    onPress={async () => {
                      try {
                        await apiRequest(`/sip-suggestions/${sug.id}/approve`, { method: 'POST', token });
                        setSipSuggestions(prev => prev.filter(s => s.id !== sug.id));
                        setSipForm(f => ({ ...f, name: sug.fund_name, category: 'SIP' }));
                        setEditSip(null);
                        setShowSipModal(true);
                      } catch {}
                    }}
                  >
                    <Text style={{ color: '#fff', fontSize: 12, fontWeight: '600' }}>Approve</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    data-testid={`sip-suggest-decline-${sug.id}`}
                    style={{ backgroundColor: isDark ? 'rgba(239,68,68,0.15)' : 'rgba(239,68,68,0.08)', borderRadius: 20, paddingHorizontal: 14, paddingVertical: 7, borderWidth: 1, borderColor: 'rgba(239,68,68,0.3)' }}
                    onPress={async () => {
                      try {
                        await apiRequest(`/sip-suggestions/${sug.id}`, { method: 'DELETE', token });
                        setSipSuggestions(prev => prev.filter(s => s.id !== sug.id));
                      } catch {}
                    }}
                  >
                    <Text style={{ color: '#EF4444', fontSize: 12, fontWeight: '600' }}>Decline</Text>
                  </TouchableOpacity>
                </View>
              </View>
            ))}
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.7: RECURRING INVESTMENTS (SIPs)
           ═══════════════════════════════════════════════════════════ */}
        <RecurringInvestmentsSection
          recurringData={recurringData}
          colors={colors}
          isDark={isDark}
          onAddSip={openAddSip}
          onEditSip={openEditSip}
          onDeleteSip={handleDeleteSip}
          onPauseSip={handlePauseSip}
          onExecuteSip={handleExecuteSip}
        />

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9: EMI TRACKER
           ═══════════════════════════════════════════════════════════ */}
        <TouchableOpacity
          testID="emi-tracker-card"
          activeOpacity={0.85}
          onPress={() => setShowEMITracker(true)}
          style={[styles.emiTrackerCard, {
            backgroundColor: isDark ? 'rgba(245, 158, 11, 0.08)' : 'rgba(245, 158, 11, 0.06)',
            borderColor: isDark ? 'rgba(245, 158, 11, 0.25)' : 'rgba(245, 158, 11, 0.2)',
          }]}
        >
          <View style={[styles.emiTrackerIcon, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.2)' : 'rgba(245, 158, 11, 0.15)' }]}>
            <MaterialCommunityIcons name="calendar-clock" size={26} color={Accent.amber} />
          </View>
          <View style={styles.emiTrackerInfo}>
            <Text style={[styles.emiTrackerTitle, { color: colors.textPrimary }]}>EMI Tracker</Text>
            <Text style={[styles.emiTrackerSubtitle, { color: colors.textSecondary }]}>
              View active loans, upcoming payments & repayment progress
            </Text>
          </View>
          <MaterialCommunityIcons name="chevron-right" size={22} color={Accent.amber} />
        </TouchableOpacity>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9a: PRINCIPAL VS INTEREST SPLIT
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="emi-analytics-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>EMI Analytics</Text>
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <PrincipalInterestSplit token={token || ''} isDark={isDark} colors={colors} />
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9b: PREPAYMENT CALCULATOR
           ═══════════════════════════════════════════════════════════ */}
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          marginTop: 6,
        }]}>
          <PrepaymentCalculator token={token || ''} isDark={isDark} colors={colors} />
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9c: WEALTH PROJECTOR
           ═══════════════════════════════════════════════════════════ */}
        <Text data-testid="sip-analytics-title" style={[styles.sectionTitle, { color: colors.textPrimary }]}>SIP Analytics</Text>
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <WealthProjector token={token || ''} isDark={isDark} colors={colors} />
        </View>

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9d: GOAL MAPPING (removed from here — now at bottom)
           ═══════════════════════════════════════════════════════════ */}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 6: FINANCIAL GOALS
           ═══════════════════════════════════════════════════════════ */}
        <GoalsSection
          goals={goals}
          colors={colors}
          isDark={isDark}
          onAddGoal={openAddGoal}
          onEditGoal={openEditGoal}
          onDeleteGoal={handleDeleteGoal}
        />

        {/* ═══════════════════════════════════════════════════════════
             SECTION 6.5: GOAL MAPPING (bottom of screen)
           ═══════════════════════════════════════════════════════════ */}
        <View style={[styles.glassCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
          marginTop: 6,
        }]}>
          <GoalMapper token={token || ''} isDark={isDark} colors={colors} />
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ GOAL FAB ═══ */}
      <TouchableOpacity data-testid="goal-fab" style={styles.fab} onPress={openAddGoal}>
        <LinearGradient colors={[Accent.emerald, Accent.teal]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.fabGradient}>
          <MaterialCommunityIcons name="plus" size={28} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>

      {/* ═══ EMI TRACKER MODAL ═══ */}
      <EMITrackerModal
        visible={showEMITracker}
        onClose={() => setShowEMITracker(false)}
      />

      {/* ═══ GOAL MODAL ═══ */}
      <Modal visible={showGoalModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>{editGoal ? 'Edit Goal' : 'New Goal'}</Text>
                <TouchableOpacity data-testid="goal-modal-close" onPress={() => setShowGoalModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
              <TextInput data-testid="goal-title-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.title} onChangeText={v => setGoalForm(p => ({ ...p, title: v }))} placeholder="Goal title" placeholderTextColor={colors.textSecondary} />
              <View style={styles.inputRow}>
                <TextInput data-testid="goal-target-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.target_amount} onChangeText={v => setGoalForm(p => ({ ...p, target_amount: v }))} placeholder="Target" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
                <TextInput data-testid="goal-current-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={goalForm.current_amount} onChangeText={v => setGoalForm(p => ({ ...p, current_amount: v }))} placeholder="Saved" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
              </View>
              <TextInput data-testid="goal-deadline-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary, display: 'none' }]}
                value={goalForm.deadline} onChangeText={v => setGoalForm(p => ({ ...p, deadline: v }))} placeholder="Deadline (YYYY-MM-DD)" placeholderTextColor={colors.textSecondary} />
              <TouchableOpacity
                data-testid="goal-deadline-picker"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }]}
                onPress={() => openInvestDatePicker('goal_deadline')}
                activeOpacity={0.7}
              >
                <Text style={{ color: goalForm.deadline ? colors.textPrimary : colors.textSecondary, fontSize: 15, fontFamily: 'DM Sans' }}>
                  {goalForm.deadline ? new Date(goalForm.deadline).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Select Deadline'}
                </Text>
                <MaterialCommunityIcons name="calendar" size={20} color={colors.primary} />
              </TouchableOpacity>
              {/* Inline iOS date picker for goal deadline */}
              {showDatePicker && datePickerTarget === 'goal_deadline' && Platform.OS === 'ios' && (
                <View style={{ borderWidth: 1, borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)', borderRadius: 12, overflow: 'hidden', marginBottom: 8 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }}>
                    <Text style={{ fontSize: 13, color: colors.primary, fontFamily: 'DM Sans', fontWeight: '700' }}>Select Deadline</Text>
                    <TouchableOpacity onPress={() => {
                      const formatted = iosPickerDate.toISOString().split('T')[0];
                      setGoalForm(f => ({ ...f, deadline: formatted }));
                      setShowDatePicker(false);
                    }} style={{ paddingHorizontal: 12, paddingVertical: 5, backgroundColor: colors.primary, borderRadius: 8 }}>
                      <Text style={{ fontSize: 13, color: '#fff', fontFamily: 'DM Sans', fontWeight: '700' }}>Done</Text>
                    </TouchableOpacity>
                  </View>
                  <DateTimePicker
                    value={iosPickerDate}
                    mode="date"
                    display="spinner"
                    themeVariant={isDark ? 'dark' : 'light'}
                    maximumDate={new Date(2040, 11, 31)}
                    minimumDate={new Date()}
                    onChange={(event: any, date?: Date) => { if (date) setIosPickerDate(date); }}
                    style={{ height: 150 }}
                  />
                </View>
              )}
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {GOAL_CATS.map(c => (
                  <TouchableOpacity key={c} data-testid={`goal-cat-${c}`} style={[styles.catChip, {
                    backgroundColor: goalForm.category === c ? '#F97316' : colors.background,
                    borderColor: goalForm.category === c ? '#F97316' : colors.border,
                  }]} onPress={() => setGoalForm(p => ({ ...p, category: c }))}>
                    <Text style={{ color: goalForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity data-testid="goal-save-btn" style={styles.saveBtn} onPress={handleSaveGoal} disabled={saving}>
                <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                  {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>{editGoal ? 'Update Goal' : 'Create Goal'}</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ RISK MODAL ═══ */}
      <Modal visible={showRiskModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <ScrollView style={{ maxHeight: '90%' }} contentContainerStyle={{ flexGrow: 1, justifyContent: 'flex-end' }}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  {showRiskResult ? 'Your Risk Profile' : 'Risk Assessment'}
                </Text>
                <TouchableOpacity data-testid="risk-modal-close" onPress={closeRiskModal}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              {showRiskResult ? (
                /* ── RESULTS SCREEN ── */
                <View>
                  <View style={{ alignItems: 'center', marginBottom: 20 }}>
                    <View style={[styles.riskResultIcon, {
                      backgroundColor: riskProfile === 'Conservative' ? 'rgba(59,130,246,0.15)' : riskProfile === 'Moderate' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
                    }]}>
                      <MaterialCommunityIcons
                        name={riskProfile === 'Conservative' ? 'shield-check' : riskProfile === 'Moderate' ? 'scale-balance' : 'rocket-launch'}
                        size={36}
                        color={riskProfile === 'Conservative' ? Accent.sapphire : riskProfile === 'Moderate' ? Accent.amber : Accent.ruby}
                      />
                    </View>
                    <Text data-testid="risk-result-profile" style={[styles.riskResultTitle, { color: colors.textPrimary }]}>{riskProfile}</Text>
                    <Text data-testid="risk-result-score" style={[styles.riskResultScore, { color: colors.textSecondary }]}>Score: {riskScore.toFixed(1)} / 5.0</Text>
                    <Text style={[styles.riskResultDesc, { color: colors.textSecondary }]}>
                      {riskProfile === 'Conservative' ? 'You prefer capital preservation with steady, predictable returns. Debt-heavy portfolios with FDs, PPF, and bonds suit you best.'
                        : riskProfile === 'Moderate' ? 'You seek balanced growth while managing risk. A mix of equity, debt, and gold works well for your profile.'
                        : 'You are comfortable with high volatility for potentially higher returns. Equity-heavy portfolios with growth stocks and small-caps align with your appetite.'}
                    </Text>
                  </View>

                  {/* Category breakdown */}
                  <View style={styles.breakdownSection}>
                    {Object.entries(riskBreakdown).map(([cat, val]) => {
                      const pct = (val / 5) * 100;
                      const barColor = val <= 2 ? Accent.sapphire : val <= 3.5 ? Accent.amber : Accent.ruby;
                      return (
                        <View key={cat} style={styles.breakdownRow}>
                          <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>{RISK_CATEGORY_LABELS[cat] || cat}</Text>
                          <View style={[styles.breakdownBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                            <View style={[styles.breakdownBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                          </View>
                          <Text style={[styles.breakdownVal, { color: colors.textPrimary }]}>{val.toFixed(1)}</Text>
                        </View>
                      );
                    })}
                  </View>

                  <TouchableOpacity data-testid="risk-done-btn" style={styles.saveBtn} onPress={closeRiskModal}>
                    <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                      <Text style={styles.saveBtnText}>Done</Text>
                    </LinearGradient>
                  </TouchableOpacity>
                </View>
              ) : (
                /* ── QUESTIONS SCREEN ── */
                <View>
                  <View style={styles.riskProgressHeader}>
                    <Text style={[styles.riskProgressText, { color: colors.textSecondary }]}>{riskStep + 1} of {RISK_QUESTIONS.length}</Text>
                    <View style={[styles.riskProgressBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                      <View style={[styles.riskProgressBarFill, { width: `${((riskStep + 1) / RISK_QUESTIONS.length) * 100}%` }]} />
                    </View>
                  </View>
                  <Text style={[styles.riskCategoryLabel, { color: '#F97316' }]}>
                    {RISK_CATEGORY_DISPLAY[RISK_QUESTIONS[riskStep].category] || ''}
                  </Text>
                  <Text style={[styles.questionText, { color: colors.textPrimary }]}>{RISK_QUESTIONS[riskStep].question}</Text>
                  <View style={styles.optionsContainer}>
                    {RISK_QUESTIONS[riskStep].options.map((opt, i) => (
                      <TouchableOpacity key={i} data-testid={`risk-option-${i}`} style={[styles.optionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}
                        onPress={() => handleRiskAnswer(opt.value)}>
                        <Text style={[styles.optionText, { color: colors.textPrimary }]}>{opt.label}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                </View>
              )}
            </View>
          </ScrollView>
        </View>
      </Modal>

      {/* ═══ ADD HOLDING MODAL ═══ */}
      <Modal visible={showHoldingModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Add Holding</Text>
                <TouchableOpacity data-testid="holding-modal-close" onPress={() => setShowHoldingModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>
              <TextInput data-testid="holding-name-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={holdingForm.name} onChangeText={v => setHoldingForm(p => ({ ...p, name: v }))} placeholder="Name (e.g. Reliance Industries)" placeholderTextColor={colors.textSecondary} />
              <View style={styles.inputRow}>
                <TextInput data-testid="holding-ticker-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.ticker} onChangeText={v => setHoldingForm(p => ({ ...p, ticker: v }))} placeholder="Ticker (e.g. RELIANCE.NS)" placeholderTextColor={colors.textSecondary} autoCapitalize="characters" />
                <TextInput data-testid="holding-isin-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.isin} onChangeText={v => setHoldingForm(p => ({ ...p, isin: v }))} placeholder="ISIN (optional)" placeholderTextColor={colors.textSecondary} />
              </View>
              <View style={styles.inputRow}>
                <TextInput data-testid="holding-qty-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.quantity} onChangeText={v => setHoldingForm(p => ({ ...p, quantity: v }))} placeholder="Quantity" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
                <TextInput data-testid="holding-price-input" style={[styles.input, styles.halfInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={holdingForm.buy_price} onChangeText={v => setHoldingForm(p => ({ ...p, buy_price: v }))} placeholder="Buy Price" placeholderTextColor={colors.textSecondary} keyboardType="decimal-pad" />
              </View>
              <TouchableOpacity
                data-testid="holding-date-picker"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }]}
                onPress={() => openInvestDatePicker('holding_buy_date')}
                activeOpacity={0.7}
              >
                <Text style={{ color: holdingForm.buy_date ? colors.textPrimary : colors.textSecondary, fontSize: 15, fontFamily: 'DM Sans' }}>
                  {holdingForm.buy_date ? new Date(holdingForm.buy_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Select Buy Date'}
                </Text>
                <MaterialCommunityIcons name="calendar" size={20} color={colors.primary} />
              </TouchableOpacity>
              {/* Inline iOS date picker for holding buy date */}
              {showDatePicker && datePickerTarget === 'holding_buy_date' && Platform.OS === 'ios' && (
                <View style={{ borderWidth: 1, borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)', borderRadius: 12, overflow: 'hidden', marginBottom: 8 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 14, paddingVertical: 8, backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }}>
                    <Text style={{ fontSize: 13, color: colors.primary, fontFamily: 'DM Sans', fontWeight: '700' }}>Select Buy Date</Text>
                    <TouchableOpacity onPress={() => {
                      const formatted = iosPickerDate.toISOString().split('T')[0];
                      setHoldingForm(f => ({ ...f, buy_date: formatted }));
                      setShowDatePicker(false);
                    }} style={{ paddingHorizontal: 12, paddingVertical: 5, backgroundColor: colors.primary, borderRadius: 8 }}>
                      <Text style={{ fontSize: 13, color: '#fff', fontFamily: 'DM Sans', fontWeight: '700' }}>Done</Text>
                    </TouchableOpacity>
                  </View>
                  <DateTimePicker
                    value={iosPickerDate}
                    mode="date"
                    display="spinner"
                    themeVariant={isDark ? 'dark' : 'light'}
                    maximumDate={new Date()}
                    minimumDate={new Date(2015, 0, 1)}
                    onChange={(event: any, date?: Date) => { if (date) setIosPickerDate(date); }}
                    style={{ height: 150 }}
                  />
                </View>
              )}
              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {HOLDING_CATS.map(c => (
                  <TouchableOpacity key={c} data-testid={`holding-cat-${c}`} style={[styles.catChip, {
                    backgroundColor: holdingForm.category === c ? '#F97316' : colors.background,
                    borderColor: holdingForm.category === c ? '#F97316' : colors.border,
                  }]} onPress={() => setHoldingForm(p => ({ ...p, category: c }))}>
                    <Text style={{ color: holdingForm.category === c ? '#fff' : colors.textSecondary, fontSize: 13 }}>{c}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>
              <TouchableOpacity data-testid="holding-save-btn" style={styles.saveBtn} onPress={handleSaveHolding} disabled={saving}>
                <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                  {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>Add Holding</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* ═══ CAS UPLOAD MODAL ═══ */}
      <Modal visible={showCasModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { backgroundColor: colors.card }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Import eCAS Statement</Text>
              <TouchableOpacity data-testid="cas-modal-close" onPress={() => setShowCasModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            {/* What is eCAS */}
            <View style={{ backgroundColor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.06)', borderRadius: 12, padding: 12, marginBottom: 16, borderWidth: 1, borderColor: isDark ? 'rgba(99,102,241,0.2)' : 'rgba(99,102,241,0.12)' }}>
              <Text style={{ fontSize: 12, fontWeight: '700', color: '#6366F1', marginBottom: 6, textTransform: 'uppercase', letterSpacing: 0.5 }}>What is eCAS?</Text>
              <Text style={{ fontSize: 12, color: colors.textSecondary, lineHeight: 18 }}>
                Your Consolidated Account Statement (CAS) from CAMS or NSDL lists all mutual fund holdings across all fund houses in one PDF.
              </Text>
              <Text style={{ fontSize: 12, color: colors.primary, marginTop: 6, fontWeight: '600' }}>
                Download at: camsonline.com or mfcentral.com
              </Text>
            </View>

            {/* Password field */}
            <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>PDF Password</Text>
            <TextInput
              data-testid="cas-password-input"
              style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary, marginBottom: 6 }]}
              value={casPassword}
              onChangeText={setCasPassword}
              placeholder="Enter your PAN or Date of Birth"
              placeholderTextColor={colors.textSecondary}
              secureTextEntry
              autoCapitalize="characters"
            />
            <Text style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 16, lineHeight: 16 }}>
              <Text style={{ fontWeight: '600' }}>CAMS:</Text> Usually your PAN number (e.g. ABCDE1234F){'\n'}
              <Text style={{ fontWeight: '600' }}>NSDL/MF Central:</Text> Usually DOB in DDMMYYYY format (e.g. 15081985)
            </Text>

            <TouchableOpacity data-testid="cas-upload-btn" style={styles.saveBtn} onPress={handleCasUpload} disabled={saving}>
              <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                {saving ? <ActivityIndicator color="#fff" /> : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <MaterialCommunityIcons name="file-upload-outline" size={20} color="#fff" />
                    <Text style={styles.saveBtnText}>Choose PDF & Import</Text>
                  </View>
                )}
              </LinearGradient>
            </TouchableOpacity>

            {/* Clear Holdings Button */}
            <TouchableOpacity 
              data-testid="clear-holdings-btn" 
              style={[styles.clearBtn, { borderColor: Accent.ruby }]} 
              onPress={handleClearHoldings}
              disabled={saving}
            >
              <MaterialCommunityIcons name="delete-outline" size={18} color={Accent.ruby} />
              <Text style={[styles.clearBtnText, { color: Accent.ruby }]}>Clear All Holdings</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>

      {/* ═══ SIP/Recurring Investment Modal ═══ */}
      <Modal visible={showSipModal} animationType="slide" transparent>
        <KeyboardAvoidingView style={styles.modalOverlay} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
          <View style={[styles.modalContent, styles.modalKav, { backgroundColor: colors.surface }]}>
            <View style={styles.modalHandle} />
            <ScrollView showsVerticalScrollIndicator={false}>
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>{editSip ? 'Edit SIP' : 'New SIP'}</Text>
                <TouchableOpacity data-testid="sip-modal-close" onPress={() => setShowSipModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>SIP Name *</Text>
              <TextInput
                data-testid="sip-name-input"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={sipForm.name}
                onChangeText={(v) => setSipForm({ ...sipForm, name: v })}
                placeholder="e.g., HDFC Mid-Cap Fund"
                placeholderTextColor={colors.textSecondary}
              />

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Amount (₹) *</Text>
              <TextInput
                data-testid="sip-amount-input"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={sipForm.amount}
                onChangeText={(v) => setSipForm({ ...sipForm, amount: v.replace(/[^0-9.]/g, '') })}
                placeholder="5000"
                placeholderTextColor={colors.textSecondary}
                keyboardType="numeric"
              />

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {SIP_CATS.map(cat => (
                  <TouchableOpacity
                    key={cat}
                    data-testid={`sip-cat-${cat}`}
                    style={[styles.catChip, {
                      backgroundColor: sipForm.category === cat ? '#6366F1' : 'transparent',
                      borderColor: sipForm.category === cat ? '#6366F1' : colors.border,
                    }]}
                    onPress={() => setSipForm({ ...sipForm, category: cat })}
                  >
                    <Text style={{ color: sipForm.category === cat ? '#fff' : colors.textPrimary, fontWeight: '600' as any, fontSize: 13 }}>{cat}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Frequency</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.catScroll}>
                {SIP_FREQUENCIES.map(freq => (
                  <TouchableOpacity
                    key={freq}
                    data-testid={`sip-freq-${freq}`}
                    style={[styles.catChip, {
                      backgroundColor: sipForm.frequency === freq ? '#6366F1' : 'transparent',
                      borderColor: sipForm.frequency === freq ? '#6366F1' : colors.border,
                    }]}
                    onPress={() => setSipForm({ ...sipForm, frequency: freq })}
                  >
                    <Text style={{ color: sipForm.frequency === freq ? '#fff' : colors.textPrimary, fontWeight: '600' as any, fontSize: 13, textTransform: 'capitalize' }}>{freq}</Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              <View style={styles.inputRow}>
                <View style={styles.halfInput}>
                  <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Start Date</Text>
                  <TouchableOpacity
                    data-testid="sip-start-picker"
                    style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }]}
                    onPress={() => openInvestDatePicker('sip_start_date')}
                    activeOpacity={0.7}
                  >
                    <Text style={{ color: sipForm.start_date ? colors.textPrimary : colors.textSecondary, fontSize: 13, fontFamily: 'DM Sans' }}>
                      {sipForm.start_date ? new Date(sipForm.start_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : 'Select Date'}
                    </Text>
                    <MaterialCommunityIcons name="calendar" size={18} color={colors.primary} />
                  </TouchableOpacity>
                  {/* Inline iOS date picker for SIP start date */}
                  {showDatePicker && datePickerTarget === 'sip_start_date' && Platform.OS === 'ios' && (
                    <View style={{ borderWidth: 1, borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)', borderRadius: 12, overflow: 'hidden', marginTop: 4, marginBottom: 4 }}>
                      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 6, backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.02)' }}>
                        <Text style={{ fontSize: 12, color: colors.primary, fontFamily: 'DM Sans', fontWeight: '700' }}>Start Date</Text>
                        <TouchableOpacity onPress={() => {
                          const formatted = iosPickerDate.toISOString().split('T')[0];
                          setSipForm(f => ({ ...f, start_date: formatted }));
                          setShowDatePicker(false);
                        }} style={{ paddingHorizontal: 10, paddingVertical: 4, backgroundColor: colors.primary, borderRadius: 6 }}>
                          <Text style={{ fontSize: 12, color: '#fff', fontFamily: 'DM Sans', fontWeight: '700' }}>Done</Text>
                        </TouchableOpacity>
                      </View>
                      <DateTimePicker
                        value={iosPickerDate}
                        mode="date"
                        display="spinner"
                        themeVariant={isDark ? 'dark' : 'light'}
                        maximumDate={new Date(2040, 11, 31)}
                        minimumDate={new Date(2015, 0, 1)}
                        onChange={(event: any, date?: Date) => { if (date) setIosPickerDate(date); }}
                        style={{ height: 130 }}
                      />
                    </View>
                  )}
                </View>
                <View style={styles.halfInput}>
                  <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Day of Month</Text>
                  <TextInput
                    data-testid="sip-day-input"
                    style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                    value={sipForm.day_of_month}
                    onChangeText={(v) => setSipForm({ ...sipForm, day_of_month: v.replace(/[^0-9]/g, '').slice(0, 2) })}
                    placeholder="5"
                    placeholderTextColor={colors.textSecondary}
                    keyboardType="numeric"
                    maxLength={2}
                  />
                </View>
              </View>

              <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Notes (Optional)</Text>
              <TextInput
                data-testid="sip-notes-input"
                style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary, height: 80, textAlignVertical: 'top' }]}
                value={sipForm.notes}
                onChangeText={(v) => setSipForm({ ...sipForm, notes: v })}
                placeholder="Add any notes..."
                placeholderTextColor={colors.textSecondary}
                multiline
              />

              <TouchableOpacity data-testid="sip-save-btn" style={styles.saveBtn} onPress={handleSaveSip} disabled={saving}>
                <LinearGradient colors={['#6366F1', '#4F46E5']} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                  {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>{editSip ? 'Update SIP' : 'Create SIP'}</Text>}
                </LinearGradient>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* ═══ NATIVE DATE PICKER (Android only - iOS uses inline pickers) ═══ */}
      {showDatePicker && Platform.OS === 'android' && (
        <DateTimePicker
          value={datePickerValue}
          mode="date"
          display="default"
          maximumDate={datePickerTarget === 'goal_deadline' ? new Date(2040, 11, 31) : new Date()}
          minimumDate={new Date(2015, 0, 1)}
          onChange={handleInvestDateChange}
        />
      )}

    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loadingContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', gap: 12 },
  loadingText: { fontSize: 14 },

  // Header
  stickyHeader: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 100 },
  headerContent: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 12, borderBottomWidth: 1 },
  headerLeft: { flex: 1 },
  headerTitle: { fontSize: 24, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5 },
  headerSubtitle: { fontSize: 13, marginTop: 2 },
  refreshBtn: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },

  // Scroll
  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 20 },

  // Section
  sectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  sectionTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 14, letterSpacing: -0.3 },
  updatedAt: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any },

  // ── Market Section ──
  marketSection: { marginBottom: 24 },
  marketSectionHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  marketTable: { borderRadius: 18, borderWidth: 1, overflow: 'hidden' },
  marketRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 18, paddingVertical: 16 },
  marketRowLeft: { flexDirection: 'row', alignItems: 'center', gap: 12, flex: 1 },
  marketDot: { width: 8, height: 8, borderRadius: 4 },
  marketRowName: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.2 },
  marketRowSub: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 1 },
  marketRowRight: { alignItems: 'flex-end' },
  marketRowPrice: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.3 },
  marketRowChangeWrap: { flexDirection: 'row', alignItems: 'center', gap: 4, marginTop: 2 },
  marketRowChange: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // ── Portfolio ──
  portfolioCard: { borderRadius: 18, borderWidth: 1, overflow: 'hidden', marginBottom: 24 },
  portfolioSummaryRow: { flexDirection: 'row', alignItems: 'center', padding: 20, paddingBottom: 16 },
  portfolioDivider: { width: 1, height: 40, marginHorizontal: 16 },
  portfolioSmallLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5 },
  portfolioMainNum: { fontSize: 22, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5, marginTop: 4 },
  gainLossBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, marginHorizontal: 20, marginBottom: 16, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, alignSelf: 'flex-start' },
  gainLossText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  categoryBreakdownHeader: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 10, borderTopWidth: 1 },
  breakdownHeaderText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5 },
  categoryRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 20, paddingVertical: 14 },
  catDot: { width: 8, height: 8, borderRadius: 4 },
  catName: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any },
  catTxnCount: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 1 },
  catNum: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, textAlign: 'right' },
  catReturn: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, textAlign: 'right' },
  emptyPortfolio: { alignItems: 'center', padding: 28, borderRadius: 18, borderWidth: 1, marginBottom: 24 },

  // ── Glass Card ──
  glassCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 20 },

  // ── Pie Chart ──
  pieContainer: { alignItems: 'center', marginBottom: 20 },
  legendGrid: { gap: 10 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  legendDot: { width: 10, height: 10, borderRadius: 5 },
  legendName: { flex: 1, fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  legendPercent: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any, width: 40, textAlign: 'right' },
  legendAmount: { fontSize: 12, width: 60, textAlign: 'right' },
  emptyPie: { alignItems: 'center', padding: 32, gap: 10 },
  emptyPieText: { fontSize: 13, textAlign: 'center' },

  // ── Risk Profile ──
  riskCard: { borderRadius: 20, padding: 20, borderWidth: 1, marginBottom: 20 },
  riskHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 },
  riskBadge: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 14 },
  riskBadgeText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  retakeBtn: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, borderWidth: 1 },
  retakeBtnText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  riskScoreText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginLeft: 4 },
  breakdownSection: { marginBottom: 16, gap: 10 },
  breakdownRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  breakdownLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, width: 100 },
  breakdownBarBg: { flex: 1, height: 6, borderRadius: 3, overflow: 'hidden' },
  breakdownBarFill: { height: '100%', borderRadius: 3 },
  breakdownVal: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any, width: 28, textAlign: 'right' },
  riskResultIcon: { width: 72, height: 72, borderRadius: 36, justifyContent: 'center', alignItems: 'center', marginBottom: 12 },
  riskResultTitle: { fontSize: 24, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.5 },
  riskResultScore: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any, marginTop: 4 },
  riskResultDesc: { fontSize: 13, lineHeight: 20, textAlign: 'center', marginTop: 8, paddingHorizontal: 10 },
  riskProgressHeader: { marginBottom: 16 },
  riskProgressText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 6 },
  riskProgressBarBg: { height: 4, borderRadius: 2, overflow: 'hidden' },
  riskProgressBarFill: { height: '100%', borderRadius: 2, backgroundColor: '#F97316' },
  riskCategoryLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any, textTransform: 'uppercase', letterSpacing: 1, marginBottom: 6 },
  strategyName: { fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 14 },
  strategyBar: { flexDirection: 'row', height: 22, borderRadius: 11, overflow: 'hidden', marginBottom: 12 },
  strategySegment: { justifyContent: 'center', alignItems: 'center' },
  strategySegmentText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '700' as any, color: '#fff' },
  strategyLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  strategyLegendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  strategyLegendDot: { width: 8, height: 8, borderRadius: 4 },
  strategyLegendText: { fontSize: 12 },

  // ── Tax ──
  taxPlanningHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14, marginTop: 28 },
  addDeductionBtn: { width: 38, height: 38, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  taxFyLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 12, marginTop: 0 },
  taxSavedBadge: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12, marginBottom: 14 },
  taxSavedText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  taxIconWrap: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  taxHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 },
  taxTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any },
  taxUsed: { fontSize: 11, marginTop: 2 },
  taxPercentBadge: { paddingHorizontal: 10, paddingVertical: 6, borderRadius: 10 },
  taxPercentText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  taxBarBg: { height: 6, borderRadius: 3, overflow: 'hidden', marginBottom: 8 },
  taxBarFill: { height: '100%', borderRadius: 3 },
  taxItemsList: { marginTop: 4, gap: 4 },
  taxItemRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 3 },
  taxItemName: { fontSize: 12, fontFamily: 'DM Sans' },
  taxItemAmt: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  taxRemaining: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 4 },
  taxSubsectionTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, letterSpacing: 0.3 },
  deductionActionBtn: { width: 32, height: 32, borderRadius: 8, justifyContent: 'center', alignItems: 'center' },
  deductionAmountRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, marginTop: 4 },
  deductionAmountLabel: { fontSize: 12, fontFamily: 'DM Sans' },
  deductionAmountValue: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  // ── Edit Deduction Modal ──
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  editDeductionModalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 20 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  editDeductionInfo: { padding: 16, borderRadius: 14, marginBottom: 20 },
  editDeductionSection: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 4 },
  editDeductionName: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 4 },
  editDeductionLimit: { fontSize: 12, fontFamily: 'DM Sans' },
  editDeductionActions: { flexDirection: 'row', gap: 12, marginTop: 20 },
  cancelBtn: { flex: 1, height: 52, borderRadius: 14, justifyContent: 'center', alignItems: 'center' },
  cancelBtnText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '600' as any },
  saveDeductionBtn: { flex: 1, height: 52, borderRadius: 14, overflow: 'hidden' },
  saveDeductionGradient: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  saveDeductionText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, color: '#fff' },
  // ── Rebalancing ──
  rebalanceHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 },
  rebalanceTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any },
  rebalanceProfile: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  rebalanceBars: { marginBottom: 10, gap: 10 },
  rebalanceBarRow: { flexDirection: 'row', alignItems: 'center', gap: 10 },
  rebalanceBarLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, width: 48 },
  rebalanceBarGroup: { flex: 1 },
  rebalanceBarBg: { height: 5, borderRadius: 3, overflow: 'hidden' },
  rebalanceBarActual: { height: '100%', borderRadius: 3 },
  rebalanceBarTarget: { height: '100%', borderRadius: 3 },
  rebalanceBarVal: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700' as any },
  rebalanceBarTarget2: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '500' as any },
  rebalanceActionRow: { flexDirection: 'row', alignItems: 'center', gap: 10, paddingHorizontal: 14, paddingVertical: 12, borderRadius: 12, borderWidth: 1, marginBottom: 8 },
  rebalanceActionText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any, flex: 1 },
  // ── Simulator ──
  simToggle: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderRadius: 16, borderWidth: 1, marginBottom: 12 },
  simIconWrap: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  simToggleTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any },
  simToggleSub: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 1 },
  simSliderRow: { marginBottom: 16 },
  simSliderHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 2 },
  simDot: { width: 8, height: 8, borderRadius: 4 },
  simSliderLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' as any },
  simSliderVal: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800' as any },
  simSliderMeta: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: -2 },
  simTotalRow: { alignSelf: 'flex-start', paddingHorizontal: 12, paddingVertical: 5, borderRadius: 8, marginBottom: 12 },
  simTotalText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any },
  simAllocBar: { flexDirection: 'row', height: 10, borderRadius: 5, overflow: 'hidden', marginBottom: 18 },
  simAllocSegment: { justifyContent: 'center', alignItems: 'center' },
  simAllocSegText: { fontSize: 8, fontWeight: '700' as any, color: '#fff' },
  simResults: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  simResultCard: { flex: 1, padding: 12, borderRadius: 12, alignItems: 'center' },
  simResultLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 4 },
  simResultValue: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800' as any },
  simProjection: { borderTopWidth: 1, paddingTop: 14, marginBottom: 12 },
  simProjectionLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '500' as any, marginBottom: 10 },
  simProjectionRow: { flexDirection: 'row', alignItems: 'center', gap: 24 },
  simProjectionPeriod: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any },
  simProjectionVal: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '800' as any, letterSpacing: -0.5, marginTop: 2 },
  simProjectionDivider: { width: 1, height: 36 },
  simResetBtn: { flexDirection: 'row', alignItems: 'center', alignSelf: 'center', gap: 4, paddingVertical: 6 },
  simResetText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, color: '#F97316' },

  // ── Goals ──
  addGoalBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 14, paddingVertical: 8, borderRadius: 12 },
  addGoalText: { color: '#fff', fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalsOverviewCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 14 },
  goalsOverviewRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  goalsOverviewLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  goalsOverviewAmount: { fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any, marginTop: 2 },
  goalsPercentBadge: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  goalsPercentText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalsProgressBar: { height: 6, borderRadius: 3, overflow: 'hidden' },
  goalsProgressFill: { height: '100%', borderRadius: 3 },
  emptyGoals: { alignItems: 'center', padding: 28, borderRadius: 18, borderWidth: 1, marginBottom: 16 },
  emptyGoalsTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any, marginTop: 10 },
  emptyGoalsSubtitle: { fontSize: 12, marginTop: 4 },
  goalsScroll: { marginBottom: 8 },
  goalCard: { width: 155, padding: 14, borderRadius: 16, borderWidth: 1, marginRight: 10 },
  goalCardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  goalIconWrap: { width: 34, height: 34, borderRadius: 10, justifyContent: 'center', alignItems: 'center' },
  goalPercent: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  goalTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any, marginBottom: 8 },
  goalBarBg: { height: 5, borderRadius: 3, overflow: 'hidden', marginBottom: 6 },
  goalBarFill: { height: '100%', borderRadius: 3 },
  goalAmounts: { fontSize: 10 },

  // ── FAB ──
  fab: { position: 'absolute', right: 20, bottom: 90, zIndex: 99999, borderRadius: 24, shadowColor: '#EA580C', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.3, shadowRadius: 8, elevation: 6, borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)' },
  fabGradient: { width: 52, height: 52, borderRadius: 26, justifyContent: 'center', alignItems: 'center' },

  // ── Modals ──
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.5)', justifyContent: 'flex-end' },
  modalKav: { maxHeight: '90%' },
  modalContent: { borderTopLeftRadius: 28, borderTopRightRadius: 28, padding: 24, paddingBottom: 40 },
  modalHandle: { width: 40, height: 4, borderRadius: 2, backgroundColor: '#CBD5E1', alignSelf: 'center', marginBottom: 16 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  modalTitle: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any },
  input: { height: 52, borderRadius: 14, borderWidth: 1, paddingHorizontal: 16, fontSize: 15, marginBottom: 12 },
  inputRow: { flexDirection: 'row', gap: 10 },
  halfInput: { flex: 1 },
  fieldLabel: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' as any, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 8 },
  catScroll: { maxHeight: 40, marginBottom: 16 },
  catChip: { paddingHorizontal: 14, paddingVertical: 8, borderRadius: 16, borderWidth: 1, marginRight: 8 },
  saveBtn: { borderRadius: 999, overflow: 'hidden', marginTop: 8 },
  saveBtnGradient: { height: 56, justifyContent: 'center', alignItems: 'center' },
  saveBtnText: { color: '#fff', fontSize: 17, fontFamily: 'DM Sans', fontWeight: '700' as any },
  progressRow: { flexDirection: 'row', gap: 6, marginBottom: 20, justifyContent: 'center' },
  progressDot: { height: 6, borderRadius: 3 },
  questionText: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' as any, textAlign: 'center', marginBottom: 24, lineHeight: 26 },
  optionsContainer: { gap: 10 },
  optionBtn: { padding: 16, borderRadius: 14, borderWidth: 1 },
  optionText: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '500' as any, textAlign: 'center' },

  // ── Holdings ──
  holdingsCard: { borderRadius: 18, borderWidth: 1, overflow: 'hidden', marginBottom: 24 },
  holdingsSummaryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 18, paddingBottom: 14 },
  holdingsSummaryNum: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any, letterSpacing: -0.4, marginTop: 4 },
  holdingRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 18, paddingVertical: 14 },
  holdingName: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any, maxWidth: 180 },
  holdingSub: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 2 },
  holdingValue: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  holdingGain: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginTop: 2 },
  casBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 12, paddingVertical: 8, borderRadius: 12, borderWidth: 1 },
  casBtnText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '700' as any },
  casDesc: { fontSize: 13, lineHeight: 20, marginBottom: 16 },
  replaceToggle: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 14, borderRadius: 12, borderWidth: 1, marginBottom: 16 },
  toggleCheckbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 2, alignItems: 'center', justifyContent: 'center' },
  replaceToggleText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '500' as any, flex: 1 },
  clearBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 14, borderRadius: 12, borderWidth: 1, marginTop: 12 },
  clearBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // ── SIP/Recurring ──
  sipSummaryCard: { borderRadius: 16, padding: 16, borderWidth: 1, marginBottom: 16 },
  sipSummaryRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  sipSummaryLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },
  sipSummaryAmount: { fontSize: 20, fontFamily: 'DM Sans', fontWeight: '700' as any, marginTop: 4 },
  sipCountBadge: { backgroundColor: '#6366F120', paddingHorizontal: 12, paddingVertical: 6, borderRadius: 12 },
  sipCountText: { color: '#6366F1', fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipList: { gap: 12, marginBottom: 24 },
  sipCard: { borderRadius: 16, borderWidth: 1, overflow: 'hidden' },
  sipCardHeader: { flexDirection: 'row', alignItems: 'center', padding: 16, gap: 12 },
  sipNameRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 2 },
  autoDetectedBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 5,
    paddingVertical: 2,
    borderRadius: 6,
  },
  autoDetectedText: { fontSize: 9, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipIconWrap: { width: 40, height: 40, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  sipName: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipCategory: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '500' as any, marginTop: 2 },
  sipAmount: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipPausedBadge: { paddingHorizontal: 8, paddingVertical: 3, borderRadius: 6, marginTop: 4 },
  sipPausedText: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipStatsRow: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 12, borderTopWidth: 1 },
  sipStat: { flex: 1, alignItems: 'center' },
  sipStatLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '500' as any, marginBottom: 2 },
  sipStatValue: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700' as any },
  sipStatDivider: { width: 1, height: 24, backgroundColor: 'rgba(128,128,128,0.2)' },
  sipActions: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 12, paddingVertical: 10, gap: 8, borderTopWidth: 1, borderTopColor: 'rgba(128,128,128,0.1)' },
  sipActionBtn: { flexDirection: 'row', alignItems: 'center', gap: 4, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, borderWidth: 1 },
  sipActionText: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any },

  // ── EMI Tracker Card ──
  emiTrackerCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 20,
    marginBottom: 20,
    padding: 16,
    borderRadius: 16,
    borderWidth: 1,
    gap: 14,
  },
  emiTrackerIcon: {
    width: 52,
    height: 52,
    borderRadius: 14,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emiTrackerInfo: {
    flex: 1,
  },
  emiTrackerTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    marginBottom: 3,
  },
  emiTrackerSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 17,
  },
});
