import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
  TextInput, KeyboardAvoidingView, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { LinearGradient } from 'expo-linear-gradient';
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
import TaxDeductionsModal from '../../src/components/TaxDeductionsModal';
import { TaxDeduction } from '../../src/data/taxDeductions';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

// ── Investment asset categories for allocation pie chart ──
const ASSET_CATEGORIES: Record<string, { label: string; color: string }> = {
  'Stocks': { label: 'Stocks', color: Accent.sapphire },
  'Mutual Funds': { label: 'Mutual Funds', color: Accent.amethyst },
  'SIP': { label: 'SIP', color: '#6366F1' },
  'FD': { label: 'Fixed Deposits', color: '#0891B2' },
  'Fixed Deposit': { label: 'Fixed Deposits', color: '#0891B2' },
  'PPF': { label: 'PPF', color: '#14B8A6' },
  'Gold': { label: 'Gold', color: '#EAB308' },
  'Sovereign Gold Bond': { label: 'Gold', color: '#CA8A04' },
  'Silver': { label: 'Silver', color: '#94A3B8' },
  'NPS': { label: 'NPS', color: Accent.emerald },
  'EPF': { label: 'EPF', color: '#14B8A6' },
  'Crypto': { label: 'Crypto', color: '#F59E0B' },
  'ETFs': { label: 'ETFs', color: '#2563EB' },
  'Bonds': { label: 'Bonds', color: '#0284C7' },
  'Real Estate': { label: 'Real Estate', color: '#78716C' },
  'ULIP': { label: 'ULIP', color: '#7C3AED' },
};

// ── Goal categories ──
const GOAL_CATS = ['Safety', 'Travel', 'Purchase', 'Property', 'Education', 'Retirement', 'Wedding', 'Other'];

// ── Types ──
type MarketItem = {
  key: string; name: string; price: number; change: number;
  change_percent: number; prev_close: number; icon: string; last_updated: string;
};
type Goal = {
  id: string; title: string; target_amount: number; current_amount: number;
  deadline: string; category: string;
};
type DashboardStats = {
  total_income: number; total_expenses: number; total_investments: number;
  invest_breakdown: Record<string, number>;
};

type PortfolioData = {
  total_invested: number;
  total_current_value: number;
  total_gain_loss: number;
  total_gain_loss_pct: number;
  categories: Array<{
    category: string; invested: number; current_value: number;
    gain_loss: number; gain_loss_pct: number; transactions: number;
  }>;
};

type Holding = {
  id: string; name: string; ticker: string; isin: string; category: string;
  quantity: number; buy_price: number; buy_date: string; source: string;
  current_price: number; invested_value: number; current_value: number;
  gain_loss: number; gain_loss_pct: number;
};
type HoldingsData = {
  holdings: Holding[];
  summary: { total_invested: number; total_current: number; total_gain_loss: number; total_gain_loss_pct: number; count: number };
};

const HOLDING_CATS = ['Stock', 'Mutual Fund', 'ETF', 'Gold', 'Silver', 'Bond', 'Other'];
const SIP_CATS = ['SIP', 'PPF', 'NPS', 'EPF', 'ELSS', 'Insurance', 'FD', 'Gold', 'Other'];
const SIP_FREQUENCIES = ['monthly', 'weekly', 'quarterly', 'yearly'];
const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// ── Recurring Transaction Types ──
type RecurringTransaction = {
  id: string;
  name: string;
  amount: number;
  frequency: string;
  category: string;
  start_date: string;
  end_date: string | null;
  day_of_month: number;
  notes: string | null;
  is_active: boolean;
  next_execution: string;
  total_invested: number;
  execution_count: number;
  upcoming: Array<{ date: string; amount: number; status: string }>;
};
type RecurringData = {
  recurring: RecurringTransaction[];
  summary: {
    total_count: number;
    active_count: number;
    monthly_commitment: number;
    categories: string[];
  };
};

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
  const [casPassword, setCasPassword] = useState('');
  const [taxData, setTaxData] = useState<any>(null);
  const [capitalGainsData, setCapitalGainsData] = useState<any>(null);
  const [rebalanceData, setRebalanceData] = useState<any>(null);
  const [recurringData, setRecurringData] = useState<RecurringData | null>(null);
  const [showSipModal, setShowSipModal] = useState(false);
  const [editSip, setEditSip] = useState<RecurringTransaction | null>(null);
  const [sipForm, setSipForm] = useState({ name: '', amount: '', frequency: 'monthly', category: 'SIP', start_date: '', day_of_month: '5', notes: '' });
  const [showTaxDeductionsModal, setShowTaxDeductionsModal] = useState(false);
  const [userDeductions, setUserDeductions] = useState<string[]>([]);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Set screen context for AI awareness
  useEffect(() => {
    setCurrentScreen('investments');
  }, [setCurrentScreen]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const [statsData, goalsData, mktData, portfolioData, holdingsLive, savedRisk, taxSummary, rebalancing, recurringTxns, capGains] = await Promise.all([
        apiRequest('/dashboard/stats', { token }),
        apiRequest('/goals', { token }),
        apiRequest('/market-data', {}),
        apiRequest('/portfolio-overview', { token }),
        apiRequest('/holdings/live', { token }),
        apiRequest('/risk-profile', { token }),
        apiRequest('/tax-summary', { token }),
        apiRequest('/portfolio-rebalancing', { token }),
        apiRequest('/recurring', { token }),
        apiRequest('/capital-gains', { token }),
      ]);
      setStats(statsData);
      setGoals(goalsData);
      setMarketData(mktData || []);
      setPortfolio(portfolioData);
      setHoldingsData(holdingsLive);
      setTaxData(taxSummary);
      setRebalanceData(rebalancing);
      setRecurringData(recurringTxns);
      setCapitalGainsData(capGains);
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

  const onRefresh = () => { setRefreshing(true); fetchData(); };

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

  // ── Risk assessment (12 behavioral finance questions) ──
  const RISK_QUESTIONS = [
    { id: 1, category: 'horizon', question: 'What is your primary investment time horizon?', options: [
      { label: '< 1 year', value: 1 }, { label: '1-3 years', value: 2 }, { label: '3-7 years', value: 3 }, { label: '7-15 years', value: 4 }, { label: '15+ years', value: 5 }
    ]},
    { id: 2, category: 'loss_tolerance', question: 'If your portfolio dropped 25% in a month, what would you do?', options: [
      { label: 'Sell everything immediately', value: 1 }, { label: 'Sell half to limit damage', value: 2 }, { label: 'Hold and wait for recovery', value: 3 }, { label: 'Buy more at lower prices', value: 5 }
    ]},
    { id: 3, category: 'experience', question: 'How much investment experience do you have?', options: [
      { label: 'None — I\'m new to investing', value: 1 }, { label: 'Beginner (FDs, PPF only)', value: 2 }, { label: 'Intermediate (MFs, SIPs)', value: 3 }, { label: 'Advanced (Stocks, F&O, crypto)', value: 5 }
    ]},
    { id: 4, category: 'income_stability', question: 'How stable is your primary source of income?', options: [
      { label: 'Unstable / Freelance', value: 1 }, { label: 'Somewhat stable', value: 2 }, { label: 'Stable salaried job', value: 4 }, { label: 'Multiple income streams', value: 5 }
    ]},
    { id: 5, category: 'emergency_fund', question: 'How many months of expenses do you have as an emergency fund?', options: [
      { label: 'None', value: 1 }, { label: '1-3 months', value: 2 }, { label: '3-6 months', value: 3 }, { label: '6-12 months', value: 4 }, { label: '12+ months', value: 5 }
    ]},
    { id: 6, category: 'return_expectation', question: 'What annual return do you expect from your investments?', options: [
      { label: '6-8% (FD-like safety)', value: 1 }, { label: '8-12% (Balanced growth)', value: 2 }, { label: '12-18% (Equity-like returns)', value: 4 }, { label: '18%+ (High growth, high risk)', value: 5 }
    ]},
    { id: 7, category: 'loss_tolerance', question: 'What is the maximum portfolio loss you can stomach in a year?', options: [
      { label: '0% — I can\'t afford any loss', value: 1 }, { label: 'Up to 10%', value: 2 }, { label: 'Up to 20%', value: 3 }, { label: 'Up to 30%', value: 4 }, { label: '30%+ if long-term gains are high', value: 5 }
    ]},
    { id: 8, category: 'concentration', question: 'How comfortable are you putting 50%+ of your portfolio in equities?', options: [
      { label: 'Very uncomfortable', value: 1 }, { label: 'Slightly uncomfortable', value: 2 }, { label: 'Neutral', value: 3 }, { label: 'Comfortable', value: 4 }, { label: 'Very comfortable', value: 5 }
    ]},
    { id: 9, category: 'behavior', question: 'When markets are at all-time highs, what do you typically do?', options: [
      { label: 'Sell and book profits', value: 2 }, { label: 'Stop investing and wait', value: 1 }, { label: 'Continue my SIPs normally', value: 3 }, { label: 'Invest more aggressively', value: 5 }
    ]},
    { id: 10, category: 'goal_priority', question: 'What matters more to you in investing?', options: [
      { label: 'Capital preservation above all', value: 1 }, { label: 'Steady income with low risk', value: 2 }, { label: 'Balance of growth and safety', value: 3 }, { label: 'Maximum growth, even with volatility', value: 5 }
    ]},
    { id: 11, category: 'behavior', question: 'A friend recommends a "hot stock tip". What do you do?', options: [
      { label: 'Ignore it completely', value: 3 }, { label: 'Research before acting', value: 4 }, { label: 'Invest a small amount to test', value: 2 }, { label: 'Go all-in if it sounds good', value: 1 }
    ]},
    { id: 12, category: 'age_capacity', question: 'What is your age group?', options: [
      { label: '18-25', value: 5 }, { label: '26-35', value: 4 }, { label: '36-45', value: 3 }, { label: '46-55', value: 2 }, { label: '55+', value: 1 }
    ]},
  ];

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
        
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.detail || 'Upload failed');
        
        const summary = data.summary ? `\n\nTotal Invested: ₹${data.summary.total_invested?.toLocaleString('en-IN')}\nCurrent Value: ₹${data.summary.total_current?.toLocaleString('en-IN')}\nGain/Loss: ${data.summary.gain_loss_pct >= 0 ? '+' : ''}${data.summary.gain_loss_pct?.toFixed(2)}%` : '';
        Alert.alert('Success', `${data.message || `Imported ${data.holdings?.length || 0} holdings`}${summary}`);
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

  // Build allocation data for pie chart - prefer portfolio categories if available
  const pieData = portfolio?.categories?.length
    ? portfolio.categories.map(cat => ({
        category: ASSET_CATEGORIES[cat.category]?.label || cat.category,
        amount: cat.invested,
        color: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8',
      }))
    : Object.entries(allocation).filter(([_, amt]) => amt > 0).map(([cat, amt]) => ({
        category: ASSET_CATEGORIES[cat]?.label || cat,
        amount: amt,
        color: ASSET_CATEGORIES[cat]?.color || '#94A3B8',
      }));

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

  // Tax saving — now from backend
  const taxSections = taxData?.sections || [];

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

        {portfolio && portfolio.total_invested > 0 && (
          <View data-testid="portfolio-card" style={[styles.portfolioCard, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            <View style={styles.portfolioSummaryRow}>
              <View style={{ flex: 1 }}>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Invested</Text>
                <Text data-testid="portfolio-invested-value" style={[styles.portfolioMainNum, { color: colors.textPrimary }]}>
                  {formatINR(portfolio.total_invested)}
                </Text>
              </View>
              <View style={[styles.portfolioDivider, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
              <View style={{ flex: 1, alignItems: 'flex-end' }}>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Current Value</Text>
                <Text data-testid="portfolio-current-value" style={[styles.portfolioMainNum, { color: colors.textPrimary }]}>
                  {formatINR(portfolio.total_current_value)}
                </Text>
              </View>
            </View>
            <View style={[styles.gainLossBadge, {
              backgroundColor: portfolio.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
            }]}>
              <MaterialCommunityIcons
                name={portfolio.total_gain_loss >= 0 ? 'trending-up' : 'trending-down'}
                size={16}
                color={portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby}
              />
              <Text data-testid="portfolio-gain-loss" style={[styles.gainLossText, {
                color: portfolio.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
              }]}>
                {portfolio.total_gain_loss >= 0 ? '+' : ''}{formatINR(portfolio.total_gain_loss)} ({portfolio.total_gain_loss >= 0 ? '+' : ''}{portfolio.total_gain_loss_pct.toFixed(2)}%)
              </Text>
            </View>
            <View style={[styles.categoryBreakdownHeader, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, flex: 1 }]}>Category</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Invested</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 80, textAlign: 'right' as any }]}>Current</Text>
              <Text style={[styles.breakdownHeaderText, { color: colors.textSecondary, width: 70, textAlign: 'right' as any }]}>Return</Text>
            </View>
            {portfolio.categories.map((cat, idx) => (
              <View key={cat.category} data-testid={`portfolio-cat-${cat.category}`} style={[styles.categoryRow, idx < portfolio.categories.length - 1 && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}>
                <View style={{ flex: 1, flexDirection: 'row' as any, alignItems: 'center' as any, gap: 8 }}>
                  <View style={[styles.catDot, { backgroundColor: ASSET_CATEGORIES[cat.category]?.color || '#94A3B8' }]} />
                  <View>
                    <Text style={[styles.catName, { color: colors.textPrimary }]}>{cat.category}</Text>
                    <Text style={[styles.catTxnCount, { color: colors.textSecondary }]}>{cat.transactions} txn{cat.transactions > 1 ? 's' : ''}</Text>
                  </View>
                </View>
                <Text style={[styles.catNum, { color: colors.textSecondary, width: 80 }]}>{formatINRShort(cat.invested)}</Text>
                <Text style={[styles.catNum, { color: colors.textPrimary, width: 80 }]}>{formatINRShort(cat.current_value)}</Text>
                <Text style={[styles.catReturn, { color: cat.gain_loss >= 0 ? Accent.emerald : Accent.ruby, width: 70 }]}>
                  {cat.gain_loss >= 0 ? '+' : ''}{cat.gain_loss_pct.toFixed(1)}%
                </Text>
              </View>
            ))}
          </View>
        )}

        {(!portfolio || portfolio.total_invested === 0) && (
          <View style={[styles.emptyPortfolio, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
            <MaterialCommunityIcons name="wallet-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No investments yet</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Add investment transactions to track your portfolio</Text>
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 2.5: MY HOLDINGS (Manual + CAS)
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.sectionHeader}>
          <Text data-testid="holdings-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>My Holdings</Text>
          <View style={{ flexDirection: 'row' as any, gap: 8 }}>
            <TouchableOpacity data-testid="clear-holdings-quick-btn" style={[styles.casBtn, { borderColor: Accent.ruby }]} onPress={handleClearHoldings}>
              <MaterialCommunityIcons name="delete-outline" size={14} color={Accent.ruby} />
              <Text style={[styles.casBtnText, { color: Accent.ruby }]}>Clear</Text>
            </TouchableOpacity>
            <TouchableOpacity data-testid="upload-cas-btn" style={[styles.casBtn, { borderColor: '#F97316' }]} onPress={() => setShowCasModal(true)}>
              <MaterialCommunityIcons name="file-upload-outline" size={14} color="#F97316" />
              <Text style={[styles.casBtnText, { color: '#F97316' }]}>CAS</Text>
            </TouchableOpacity>
            <TouchableOpacity data-testid="add-holding-btn" style={[styles.addGoalBtn, { backgroundColor: '#F97316' }]} onPress={openAddHolding}>
              <MaterialCommunityIcons name="plus" size={14} color="#fff" />
              <Text style={styles.addGoalText}>Add</Text>
            </TouchableOpacity>
          </View>
        </View>

        {holdingsData && holdingsData.holdings.length > 0 ? (
          <View data-testid="holdings-card" style={[styles.holdingsCard, {
            backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            {/* Holdings summary */}
            <View style={styles.holdingsSummaryRow}>
              <View>
                <Text style={[styles.portfolioSmallLabel, { color: colors.textSecondary }]}>Holdings Value</Text>
                <Text style={[styles.holdingsSummaryNum, { color: colors.textPrimary }]}>{formatINR(holdingsData.summary.total_current)}</Text>
              </View>
              <View style={[styles.gainLossBadge, {
                backgroundColor: holdingsData.summary.total_gain_loss >= 0 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)',
                marginHorizontal: 0, marginBottom: 0,
              }]}>
                <Text style={[styles.gainLossText, {
                  color: holdingsData.summary.total_gain_loss >= 0 ? Accent.emerald : Accent.ruby,
                }]}>
                  {holdingsData.summary.total_gain_loss >= 0 ? '+' : ''}{holdingsData.summary.total_gain_loss_pct.toFixed(2)}%
                </Text>
              </View>
            </View>

            {/* Holdings list */}
            {holdingsData.holdings.map((h, idx) => {
              const isGain = h.gain_loss >= 0;
              const isLast = idx === holdingsData.holdings.length - 1;
              return (
                <TouchableOpacity key={h.id} data-testid={`holding-row-${h.id}`}
                  style={[styles.holdingRow, !isLast && { borderBottomWidth: 1, borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.03)' }]}
                  onLongPress={() => handleDeleteHolding(h.id, h.name)}>
                  <View style={{ flex: 1 }}>
                    <Text style={[styles.holdingName, { color: colors.textPrimary }]} numberOfLines={1}>{h.name}</Text>
                    <Text style={[styles.holdingSub, { color: colors.textSecondary }]}>
                      {h.quantity} {h.category === 'Mutual Fund' ? 'units' : 'shares'} @ {fmtPrice(Math.round(h.buy_price))}
                    </Text>
                  </View>
                  <View style={{ alignItems: 'flex-end' as any }}>
                    <Text style={[styles.holdingValue, { color: colors.textPrimary }]}>{formatINRShort(h.current_value)}</Text>
                    <Text style={[styles.holdingGain, { color: isGain ? Accent.emerald : Accent.ruby }]}>
                      {isGain ? '+' : ''}{h.gain_loss_pct.toFixed(1)}%
                    </Text>
                  </View>
                </TouchableOpacity>
              );
            })}
          </View>
        ) : (
          <View style={[styles.emptyPortfolio, { backgroundColor: isDark ? 'rgba(10,10,11,0.9)' : '#FFFFFF', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
            <MaterialCommunityIcons name="briefcase-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No holdings added</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Add stocks and mutual funds manually or upload your CAS statement</Text>
          </View>
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
                  const pct = totalInvested > 0 ? ((item.amount / totalInvested) * 100).toFixed(1) : '0';
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
        <View data-testid="risk-card" style={[styles.riskCard, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <View style={styles.riskHeader}>
            <View style={[styles.riskBadge, {
              backgroundColor: riskProfile === 'Conservative' ? 'rgba(59,130,246,0.15)' : riskProfile === 'Moderate' ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)',
            }]}>
              <MaterialCommunityIcons
                name={riskProfile === 'Conservative' ? 'shield-check' : riskProfile === 'Moderate' ? 'scale-balance' : 'rocket-launch'}
                size={20}
                color={riskProfile === 'Conservative' ? Accent.sapphire : riskProfile === 'Moderate' ? Accent.amber : Accent.ruby}
              />
              <Text data-testid="risk-profile-label" style={[styles.riskBadgeText, { color: riskProfile === 'Conservative' ? Accent.sapphire : riskProfile === 'Moderate' ? Accent.amber : Accent.ruby }]}>
                {riskProfile}
              </Text>
              {riskSaved && riskScore > 0 && (
                <Text style={[styles.riskScoreText, { color: colors.textSecondary }]}>
                  {riskScore.toFixed(1)}/5
                </Text>
              )}
            </View>
            <TouchableOpacity data-testid="risk-retake-btn" style={[styles.retakeBtn, { borderColor: colors.border }]} onPress={() => { setShowRiskModal(true); setRiskStep(0); setRiskAnswers([]); setShowRiskResult(false); }}>
              <Text style={[styles.retakeBtnText, { color: colors.textSecondary }]}>{riskSaved ? 'Retake' : 'Take Assessment'}</Text>
            </TouchableOpacity>
          </View>

          {/* Score breakdown bars */}
          {riskSaved && Object.keys(riskBreakdown).length > 0 && (
            <View style={styles.breakdownSection}>
              {Object.entries(riskBreakdown).map(([cat, val]) => {
                const labels: Record<string, string> = {
                  horizon: 'Time Horizon', loss_tolerance: 'Loss Tolerance', experience: 'Experience',
                  income_stability: 'Income Stability', emergency_fund: 'Emergency Fund',
                  return_expectation: 'Return Expectation', concentration: 'Equity Comfort',
                  behavior: 'Behavioral Discipline', goal_priority: 'Goal Priority', age_capacity: 'Age Capacity',
                };
                const pct = (val / 5) * 100;
                const barColor = val <= 2 ? Accent.sapphire : val <= 3.5 ? Accent.amber : Accent.ruby;
                return (
                  <View key={cat} data-testid={`risk-breakdown-${cat}`} style={styles.breakdownRow}>
                    <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>{labels[cat] || cat}</Text>
                    <View style={[styles.breakdownBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                      <View style={[styles.breakdownBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                    </View>
                    <Text style={[styles.breakdownVal, { color: colors.textPrimary }]}>{val.toFixed(1)}</Text>
                  </View>
                );
              })}
            </View>
          )}

          <Text style={[styles.strategyName, { color: colors.textPrimary }]}>{currentStrategy.name} Strategy</Text>
          <View style={styles.strategyBar}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={[styles.strategySegment, { width: `${item.p}%`, backgroundColor: item.c }]}>
                {item.p >= 15 && <Text style={styles.strategySegmentText}>{item.p}%</Text>}
              </View>
            ))}
          </View>
          <View style={styles.strategyLegend}>
            {currentStrategy.allocation.map((item, i) => (
              <View key={i} style={styles.strategyLegendItem}>
                <View style={[styles.strategyLegendDot, { backgroundColor: item.c }]} />
                <Text style={[styles.strategyLegendText, { color: colors.textSecondary }]}>{item.name} ({item.p}%)</Text>
              </View>
            ))}
          </View>
        </View>

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
             SECTION 5.7: RECURRING INVESTMENTS (SIPs)
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.sectionHeader}>
          <Text data-testid="sip-section-title" style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Recurring Investments</Text>
          <TouchableOpacity data-testid="add-sip-btn" style={[styles.addGoalBtn, { backgroundColor: '#6366F1' }]} onPress={openAddSip}>
            <MaterialCommunityIcons name="plus" size={16} color="#fff" />
            <Text style={styles.addGoalText}>Add SIP</Text>
          </TouchableOpacity>
        </View>

        {/* SIP Summary Card */}
        {recurringData && recurringData.recurring.length > 0 && (
          <View data-testid="sip-summary-card" style={[styles.sipSummaryCard, {
            backgroundColor: isDark ? 'rgba(99,102,241,0.1)' : 'rgba(99,102,241,0.06)',
            borderColor: isDark ? 'rgba(99,102,241,0.25)' : 'rgba(99,102,241,0.15)',
          }]}>
            <View style={styles.sipSummaryRow}>
              <View>
                <Text style={[styles.sipSummaryLabel, { color: colors.textSecondary }]}>Monthly Commitment</Text>
                <Text data-testid="sip-monthly-commitment" style={[styles.sipSummaryAmount, { color: '#6366F1' }]}>
                  {formatINR(recurringData.summary.monthly_commitment)}/mo
                </Text>
              </View>
              <View style={styles.sipCountBadge}>
                <Text style={styles.sipCountText}>{recurringData.summary.active_count} Active</Text>
              </View>
            </View>
          </View>
        )}

        {/* Empty State */}
        {(!recurringData || recurringData.recurring.length === 0) && (
          <View style={[styles.emptyGoals, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}>
            <MaterialCommunityIcons name="calendar-sync-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No recurring investments</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Set up SIPs to automate your investments</Text>
          </View>
        )}

        {/* SIP Cards */}
        {recurringData && recurringData.recurring.length > 0 && (
          <View style={styles.sipList}>
            {recurringData.recurring.map(sip => {
              const catColor = ASSET_CATEGORIES[sip.category]?.color || '#6366F1';
              const freqLabel = sip.frequency.charAt(0).toUpperCase() + sip.frequency.slice(1);
              const nextDate = sip.next_execution ? new Date(sip.next_execution).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }) : '-';
              return (
                <View key={sip.id} data-testid={`sip-card-${sip.id}`} style={[styles.sipCard, {
                  backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : '#FFFFFF',
                  borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  opacity: sip.is_active ? 1 : 0.6,
                }]}>
                  {/* SIP Header */}
                  <View style={styles.sipCardHeader}>
                    <View style={[styles.sipIconWrap, { backgroundColor: catColor + '20' }]}>
                      <MaterialCommunityIcons name="calendar-sync" size={18} color={catColor} />
                    </View>
                    <View style={{ flex: 1 }}>
                      <Text style={[styles.sipName, { color: colors.textPrimary }]} numberOfLines={1}>{sip.name}</Text>
                      <Text style={[styles.sipCategory, { color: colors.textSecondary }]}>{sip.category} • {freqLabel}</Text>
                    </View>
                    <View style={{ alignItems: 'flex-end' }}>
                      <Text style={[styles.sipAmount, { color: colors.textPrimary }]}>{formatINR(sip.amount)}</Text>
                      {!sip.is_active && (
                        <View style={[styles.sipPausedBadge, { backgroundColor: '#F59E0B20' }]}>
                          <Text style={[styles.sipPausedText, { color: '#F59E0B' }]}>Paused</Text>
                        </View>
                      )}
                    </View>
                  </View>

                  {/* Next Execution & Stats */}
                  <View style={[styles.sipStatsRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}>
                    <View style={styles.sipStat}>
                      <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Next</Text>
                      <Text style={[styles.sipStatValue, { color: colors.textPrimary }]}>{nextDate}</Text>
                    </View>
                    <View style={styles.sipStatDivider} />
                    <View style={styles.sipStat}>
                      <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Invested</Text>
                      <Text style={[styles.sipStatValue, { color: Accent.emerald }]}>{formatINRShort(sip.total_invested)}</Text>
                    </View>
                    <View style={styles.sipStatDivider} />
                    <View style={styles.sipStat}>
                      <Text style={[styles.sipStatLabel, { color: colors.textSecondary }]}>Count</Text>
                      <Text style={[styles.sipStatValue, { color: colors.textPrimary }]}>{sip.execution_count}</Text>
                    </View>
                  </View>

                  {/* Action Buttons */}
                  <View style={styles.sipActions}>
                    <TouchableOpacity
                      data-testid={`sip-execute-${sip.id}`}
                      style={[styles.sipActionBtn, { backgroundColor: Accent.emerald + '15', borderColor: Accent.emerald + '30' }]}
                      onPress={() => handleExecuteSip(sip)}
                      disabled={!sip.is_active}
                    >
                      <MaterialCommunityIcons name="check-circle-outline" size={16} color={Accent.emerald} />
                      <Text style={[styles.sipActionText, { color: Accent.emerald }]}>Execute</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      data-testid={`sip-pause-${sip.id}`}
                      style={[styles.sipActionBtn, { backgroundColor: '#F59E0B15', borderColor: '#F59E0B30' }]}
                      onPress={() => handlePauseSip(sip)}
                    >
                      <MaterialCommunityIcons name={sip.is_active ? 'pause-circle-outline' : 'play-circle-outline'} size={16} color="#F59E0B" />
                      <Text style={[styles.sipActionText, { color: '#F59E0B' }]}>{sip.is_active ? 'Pause' : 'Resume'}</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      data-testid={`sip-edit-${sip.id}`}
                      style={[styles.sipActionBtn, { backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)', borderColor: colors.border }]}
                      onPress={() => openEditSip(sip)}
                    >
                      <MaterialCommunityIcons name="pencil-outline" size={16} color={colors.textSecondary} />
                    </TouchableOpacity>
                    <TouchableOpacity
                      data-testid={`sip-delete-${sip.id}`}
                      style={[styles.sipActionBtn, { backgroundColor: Accent.ruby + '10', borderColor: Accent.ruby + '20' }]}
                      onPress={() => handleDeleteSip(sip.id, sip.name)}
                    >
                      <MaterialCommunityIcons name="delete-outline" size={16} color={Accent.ruby} />
                    </TouchableOpacity>
                  </View>
                </View>
              );
            })}
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.9: TAX PLANNING
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.taxPlanningHeader}>
          <View>
            <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Tax Planning</Text>
            <Text data-testid="tax-fy-label" style={[styles.taxFyLabel, { color: colors.textSecondary, marginTop: 2 }]}>FY {taxData?.fy || '2025-26'}</Text>
          </View>
          <TouchableOpacity
            data-testid="add-deduction-btn"
            style={[styles.addDeductionBtn, { backgroundColor: isDark ? 'rgba(249,115,22,0.15)' : 'rgba(249,115,22,0.1)' }]}
            onPress={() => setShowTaxDeductionsModal(true)}
            activeOpacity={0.7}
          >
            <MaterialCommunityIcons name="plus" size={20} color="#F97316" />
          </TouchableOpacity>
        </View>

        {taxData?.tax_saved_30_slab > 0 && (
          <View data-testid="tax-saved-badge" style={[styles.taxSavedBadge, { backgroundColor: 'rgba(16,185,129,0.1)' }]}>
            <MaterialCommunityIcons name="cash-check" size={16} color={Accent.emerald} />
            <Text style={[styles.taxSavedText, { color: Accent.emerald }]}>
              Est. tax saved: {formatINR(taxData.tax_saved_30_slab)} (30% slab) / {formatINR(taxData.tax_saved_20_slab)} (20% slab)
            </Text>
          </View>
        )}

        {taxSections.map((sec: any) => {
          const pct = sec.limit > 0 ? Math.min((sec.used / sec.limit) * 100, 100) : 0;
          const isFull = sec.limit > 0 && sec.used >= sec.limit;
          const barColor = isFull ? Accent.emerald : '#F97316';
          return (
            <View key={sec.section} data-testid={`tax-section-${sec.section}`} style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
              marginBottom: 12,
            }]}>
              <View style={styles.taxHeader}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                  <View style={[styles.taxIconWrap, { backgroundColor: isFull ? 'rgba(16,185,129,0.12)' : 'rgba(249,115,22,0.12)' }]}>
                    <MaterialCommunityIcons name={sec.icon || 'file-document-outline'} size={18} color={isFull ? Accent.emerald : '#F97316'} />
                  </View>
                  <View>
                    <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>{sec.label}</Text>
                    <Text style={[styles.taxUsed, { color: colors.textSecondary }]}>
                      {formatINRShort(sec.used)} {sec.limit > 0 ? `/ ${formatINRShort(sec.limit)}` : '(no limit)'}
                    </Text>
                  </View>
                </View>
                {sec.limit > 0 && (
                  <View style={[styles.taxPercentBadge, { backgroundColor: isFull ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)' }]}>
                    <Text style={[styles.taxPercentText, { color: isFull ? Accent.emerald : Accent.amber }]}>
                      {pct.toFixed(0)}%
                    </Text>
                  </View>
                )}
              </View>
              {sec.limit > 0 && (
                <View style={[styles.taxBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                  <View style={[styles.taxBarFill, { width: `${pct}%`, backgroundColor: barColor }]} />
                </View>
              )}
              {sec.items && sec.items.length > 0 && (
                <View style={styles.taxItemsList}>
                  {sec.items.map((item: any, idx: number) => (
                    <View key={idx} style={styles.taxItemRow}>
                      <Text style={[styles.taxItemName, { color: colors.textSecondary }]}>{item.name}</Text>
                      <Text style={[styles.taxItemAmt, { color: colors.textPrimary }]}>{formatINR(item.amount)}</Text>
                    </View>
                  ))}
                </View>
              )}
              {sec.remaining > 0 && (
                <Text style={[styles.taxRemaining, { color: colors.textSecondary }]}>
                  {formatINRShort(sec.remaining)} remaining
                </Text>
              )}
            </View>
          );
        })}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 5.10: CAPITAL GAINS
           ═══════════════════════════════════════════════════════════ */}
        {capitalGainsData && (capitalGainsData.gains?.length > 0 || capitalGainsData.summary?.total_estimated_tax > 0) && (
          <View data-testid="capital-gains-section">
            <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginTop: 8 }]}>Capital Gains Tax</Text>
            
            {/* Summary Card */}
            <View style={[styles.glassCard, {
              backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
              borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
              marginBottom: 12,
            }]}>
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', marginBottom: 12 }}>
                <View style={{ flex: 1 }}>
                  <Text style={[styles.taxUsed, { color: colors.textSecondary, marginBottom: 4 }]}>Short Term (STCG)</Text>
                  <Text style={[styles.taxTitle, { color: Accent.ruby }]}>{formatINR(capitalGainsData.summary?.total_stcg || 0)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>Tax: {formatINR(capitalGainsData.summary?.estimated_stcg_tax || 0)}</Text>
                </View>
                <View style={{ flex: 1, alignItems: 'flex-end' }}>
                  <Text style={[styles.taxUsed, { color: colors.textSecondary, marginBottom: 4 }]}>Long Term (LTCG)</Text>
                  <Text style={[styles.taxTitle, { color: Accent.sapphire }]}>{formatINR(capitalGainsData.summary?.total_ltcg || 0)}</Text>
                  <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 2 }}>Tax: {formatINR(capitalGainsData.summary?.estimated_ltcg_tax || 0)}</Text>
                </View>
              </View>
              
              {capitalGainsData.summary?.ltcg_exemption > 0 && capitalGainsData.summary?.total_ltcg > 0 && (
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8, borderRadius: 8, backgroundColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.06)', marginBottom: 10 }}>
                  <MaterialCommunityIcons name="information" size={14} color={Accent.sapphire} />
                  <Text style={{ fontSize: 11, color: colors.textSecondary, flex: 1 }}>
                    LTCG exemption: {formatINR(capitalGainsData.summary.ltcg_exemption)} (Taxable: {formatINR(capitalGainsData.summary.ltcg_taxable)})
                  </Text>
                </View>
              )}

              <View style={[{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: 10, borderTopWidth: 1, borderTopColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
                <Text style={[styles.taxTitle, { color: colors.textPrimary }]}>Total Estimated Tax</Text>
                <Text style={[styles.taxTitle, { color: Accent.ruby, fontSize: 16 }]}>{formatINR(capitalGainsData.summary?.total_estimated_tax || 0)}</Text>
              </View>
            </View>

            {/* Individual Gains */}
            {capitalGainsData.gains?.length > 0 && capitalGainsData.gains.map((gain: any, idx: number) => (
              <View key={idx} data-testid={`capital-gain-item-${idx}`} style={[styles.glassCard, {
                backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.85)',
                borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                marginBottom: 8, padding: 14,
              }]}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <Text style={[styles.taxTitle, { color: colors.textPrimary, flex: 1 }]} numberOfLines={1}>{gain.description}</Text>
                  <View style={[styles.taxPercentBadge, { backgroundColor: gain.is_long_term ? 'rgba(59,130,246,0.1)' : 'rgba(239,68,68,0.1)' }]}>
                    <Text style={[styles.taxPercentText, { color: gain.is_long_term ? Accent.sapphire : Accent.ruby, fontSize: 10 }]}>
                      {gain.is_long_term ? 'LTCG' : 'STCG'}
                    </Text>
                  </View>
                </View>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <Text style={{ fontSize: 12, color: colors.textSecondary }}>
                    Sold: {formatINR(gain.sell_amount)} · Cost: {formatINR(gain.cost_basis)}
                  </Text>
                  <Text style={{ fontSize: 13, fontWeight: '700' as any, color: gain.gain_loss >= 0 ? Accent.emerald : Accent.ruby }}>
                    {gain.gain_loss >= 0 ? '+' : ''}{formatINR(gain.gain_loss)}
                  </Text>
                </View>
                <Text style={{ fontSize: 11, color: colors.textSecondary, marginTop: 4 }}>
                  {gain.holding_days} days · Tax: {formatINR(gain.tax_liability)} @ {(gain.tax_rate * 100).toFixed(1)}%
                </Text>
              </View>
            ))}

            {/* Tax Notes */}
            {capitalGainsData.notes?.length > 0 && (
              <View style={{ marginBottom: 16, paddingHorizontal: 4 }}>
                {capitalGainsData.notes.map((note: string, idx: number) => (
                  <Text key={idx} style={{ fontSize: 11, color: colors.textSecondary, marginBottom: 2 }}>• {note}</Text>
                ))}
              </View>
            )}
          </View>
        )}

        {/* ═══════════════════════════════════════════════════════════
             SECTION 6: FINANCIAL GOALS
           ═══════════════════════════════════════════════════════════ */}
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: colors.textPrimary, marginBottom: 0 }]}>Financial Goals</Text>
          <TouchableOpacity data-testid="add-goal-btn" style={[styles.addGoalBtn, { backgroundColor: Accent.emerald }]} onPress={openAddGoal}>
            <MaterialCommunityIcons name="plus" size={16} color="#fff" />
            <Text style={styles.addGoalText}>Add</Text>
          </TouchableOpacity>
        </View>

        {goals.length === 0 ? (
          <View style={[styles.emptyGoals, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)', borderColor: colors.border }]}>
            <MaterialCommunityIcons name="flag-variant-outline" size={36} color={colors.textSecondary} />
            <Text style={[styles.emptyGoalsTitle, { color: colors.textPrimary }]}>No goals yet</Text>
            <Text style={[styles.emptyGoalsSubtitle, { color: colors.textSecondary }]}>Set financial goals to track your progress</Text>
          </View>
        ) : (
          <>
            {goals.length > 0 && (
              <View style={[styles.goalsOverviewCard, {
                backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.06)',
                borderColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.15)',
              }]}>
                <View style={styles.goalsOverviewRow}>
                  <View>
                    <Text style={[styles.goalsOverviewLabel, { color: colors.textSecondary }]}>Overall Progress</Text>
                    <Text style={[styles.goalsOverviewAmount, { color: colors.textPrimary }]}>{formatINRShort(totalGoalCurrent)} / {formatINRShort(totalGoalTarget)}</Text>
                  </View>
                  <View style={[styles.goalsPercentBadge, { backgroundColor: overallGoalProgress >= 50 ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)' }]}>
                    <Text style={[styles.goalsPercentText, { color: overallGoalProgress >= 50 ? Accent.emerald : Accent.amber }]}>{overallGoalProgress.toFixed(0)}%</Text>
                  </View>
                </View>
                <View style={[styles.goalsProgressBar, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                  <View style={[styles.goalsProgressFill, { width: `${Math.min(overallGoalProgress, 100)}%`, backgroundColor: Accent.emerald }]} />
                </View>
              </View>
            )}
            <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.goalsScroll}>
              {goals.map(goal => {
                const progress = goal.target_amount > 0 ? (goal.current_amount / goal.target_amount) * 100 : 0;
                const progressColor = progress >= 75 ? Accent.emerald : progress >= 40 ? Accent.amber : Accent.ruby;
                return (
                  <TouchableOpacity key={goal.id} data-testid={`goal-card-${goal.id}`} style={[styles.goalCard, {
                    backgroundColor: isDark ? 'rgba(10,10,11,0.85)' : 'rgba(255,255,255,0.9)',
                    borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  }]} onPress={() => openEditGoal(goal)} onLongPress={() => handleDeleteGoal(goal.id, goal.title)}>
                    <View style={styles.goalCardHeader}>
                      <View style={[styles.goalIconWrap, { backgroundColor: `${getCategoryColor(goal.category, isDark)}20` }]}>
                        <MaterialCommunityIcons name={getCategoryIcon(goal.category) as any} size={16} color={getCategoryColor(goal.category, isDark)} />
                      </View>
                      <Text style={[styles.goalPercent, { color: progressColor }]}>{progress.toFixed(0)}%</Text>
                    </View>
                    <Text style={[styles.goalTitle, { color: colors.textPrimary }]} numberOfLines={1}>{goal.title}</Text>
                    <View style={[styles.goalBarBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}>
                      <View style={[styles.goalBarFill, { width: `${Math.min(progress, 100)}%`, backgroundColor: progressColor }]} />
                    </View>
                    <Text style={[styles.goalAmounts, { color: colors.textSecondary }]}>{formatINRShort(goal.current_amount)} / {formatINRShort(goal.target_amount)}</Text>
                  </TouchableOpacity>
                );
              })}
            </ScrollView>
          </>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>

      {/* ═══ ADD GOAL FAB ═══ */}
      <TouchableOpacity data-testid="goal-fab" style={styles.fab} onPress={openAddGoal}>
        <LinearGradient colors={[Accent.emerald, Accent.teal]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }} style={styles.fabGradient}>
          <MaterialCommunityIcons name="plus" size={28} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>

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
              <TextInput data-testid="goal-deadline-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={goalForm.deadline} onChangeText={v => setGoalForm(p => ({ ...p, deadline: v }))} placeholder="Deadline (YYYY-MM-DD)" placeholderTextColor={colors.textSecondary} />
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
                      const labels: Record<string, string> = {
                        horizon: 'Time Horizon', loss_tolerance: 'Loss Tolerance', experience: 'Experience',
                        income_stability: 'Income Stability', emergency_fund: 'Emergency Fund',
                        return_expectation: 'Return Expectation', concentration: 'Equity Comfort',
                        behavior: 'Behavioral Discipline', goal_priority: 'Goal Priority', age_capacity: 'Age Capacity',
                      };
                      const pct = (val / 5) * 100;
                      const barColor = val <= 2 ? Accent.sapphire : val <= 3.5 ? Accent.amber : Accent.ruby;
                      return (
                        <View key={cat} style={styles.breakdownRow}>
                          <Text style={[styles.breakdownLabel, { color: colors.textSecondary }]}>{labels[cat] || cat}</Text>
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
                    {({ horizon: 'Investment Horizon', loss_tolerance: 'Risk Tolerance', experience: 'Experience', income_stability: 'Financial Stability', emergency_fund: 'Safety Net', return_expectation: 'Expectations', concentration: 'Portfolio Comfort', behavior: 'Behavioral Finance', goal_priority: 'Goal Alignment', age_capacity: 'Demographics' } as Record<string, string>)[RISK_QUESTIONS[riskStep].category] || ''}
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
              <TextInput data-testid="holding-date-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                value={holdingForm.buy_date} onChangeText={v => setHoldingForm(p => ({ ...p, buy_date: v }))} placeholder="Buy Date (YYYY-MM-DD)" placeholderTextColor={colors.textSecondary} />
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
          <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
            <View style={styles.modalHandle} />
            <View style={styles.modalHeader}>
              <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>Upload CAS Statement</Text>
              <TouchableOpacity data-testid="cas-modal-close" onPress={() => setShowCasModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
            <Text style={[styles.casDesc, { color: colors.textSecondary }]}>
              Upload your NSDL/CDSL Consolidated Account Statement (CAS) PDF. Existing CAS holdings will be automatically replaced.
            </Text>
            <TextInput data-testid="cas-password-input" style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
              value={casPassword} onChangeText={setCasPassword} placeholder="PDF Password (if any)" placeholderTextColor={colors.textSecondary} secureTextEntry />
            
            <TouchableOpacity data-testid="cas-upload-btn" style={styles.saveBtn} onPress={handleCasUpload} disabled={saving}>
              <LinearGradient colors={['#EA580C', Accent.ruby]} start={{ x: 0, y: 0 }} end={{ x: 1, y: 0 }} style={styles.saveBtnGradient}>
                {saving ? <ActivityIndicator color="#fff" /> : (
                  <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
                    <MaterialCommunityIcons name="file-upload-outline" size={20} color="#fff" />
                    <Text style={styles.saveBtnText}>Choose PDF & Upload</Text>
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
                  <TextInput
                    data-testid="sip-start-input"
                    style={[styles.input, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                    value={sipForm.start_date}
                    onChangeText={(v) => setSipForm({ ...sipForm, start_date: v })}
                    placeholder="YYYY-MM-DD"
                    placeholderTextColor={colors.textSecondary}
                  />
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
  taxFyLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, marginBottom: 12, marginTop: -10 },
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
});
