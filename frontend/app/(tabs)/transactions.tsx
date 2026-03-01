import React, { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, TextInput, Modal,
  RefreshControl, ActivityIndicator, Alert, KeyboardAvoidingView, Platform,
  Switch, Animated, Dimensions, StatusBar,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { useLocalSearchParams, useRouter } from 'expo-router';
import DateTimePicker from '@react-native-community/datetimepicker';
import { useAuth } from '../../src/context/AuthContext';
import { useTheme } from '../../src/context/ThemeContext';
import { useScreenContext } from '../../src/context/ScreenContext';
import { apiRequest } from '../../src/utils/api';
import { formatINR, formatINRShort, getCategoryColor, getCategoryIcon } from '../../src/utils/formatters';
import { Accent } from '../../src/utils/theme';
import FlaggedTransactionsModal from '../../src/components/FlaggedTransactionsModal';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

const EXPENSE_CATS = [
  'Groceries', 'Rent', 'Food & Dining', 'Transport', 'Fuel', 'Shopping', 'Utilities',
  'Electricity', 'Water', 'Internet', 'Mobile Recharge', 'Entertainment', 'Health', 'Medicine',
  'Insurance', 'Education', 'EMI', 'Loan Repayment', 'Subscriptions', 'Personal Care',
  'Clothing', 'Home Maintenance', 'Travel', 'Gifts', 'Donations', 'Taxes', 'Other',
];
const INCOME_CATS = [
  'Salary', 'Business Income', 'Freelance', 'Consulting', 'Interest', 'Dividends',
  'Rental Income', 'Bonus', 'Commission', 'Capital Gains', 'Pension', 'Refund', 'Other',
];
const INVEST_CATS = [
  'Mutual Funds', 'SIP', 'Stocks', 'ETFs', 'Fixed Deposit', 'PPF', 'NPS', 'EPF',
  'Gold', 'Silver', 'Copper', 'Bonds', 'Real Estate', 'Crypto', 'ULIP',
  'Sovereign Gold Bond', 'Government Securities', 'Other',
];

const DESCRIPTION_SUGGESTIONS: Record<string, string[]> = {
  income: ['Monthly Salary', 'Freelance Project', 'Business Revenue', 'Interest Credit', 'Dividend Payout', 'Rental Income', 'Performance Bonus'],
  expense: ['Grocery Shopping', 'Monthly Rent', 'Electricity Bill', 'Fuel', 'Restaurant', 'Online Shopping', 'Medical Expenses', 'Movie/OTT'],
  investment: ['SIP - Axis Bluechip', 'SIP - HDFC Mid Cap', 'Stock Purchase', 'FD Renewal', 'PPF Contribution', 'NPS Monthly', 'Gold Purchase', 'ETF Purchase'],
};
const RECURRING_FREQ = ['Daily', 'Weekly', 'Monthly', 'Quarterly', 'Yearly'];
const DATE_PRESETS = ['This Week', 'This Month', 'Last 30 Days', 'All Time'];

type Transaction = {
  id: string; type: string; amount: number; category: string;
  description: string; date: string; created_at: string;
  is_recurring?: boolean; recurring_frequency?: string;
  is_split?: boolean; split_count?: number; notes?: string;
  payment_mode?: string; payment_account_name?: string;
};

type BankAccount = {
  id: string; bank_name: string; account_name: string;
  account_number: string; ifsc_code: string; is_default: boolean;
};

// ── Date helpers ──
function getDateLabel(dateStr: string): string {
  const today = new Date();
  const d = new Date(dateStr + 'T00:00:00');
  const todayStr = today.toISOString().split('T')[0];
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  const yesterdayStr = yesterday.toISOString().split('T')[0];

  if (dateStr === todayStr) return 'Today';
  if (dateStr === yesterdayStr) return 'Yesterday';

  const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  return `${days[d.getDay()]}, ${months[d.getMonth()]} ${d.getDate()}`;
}

function groupByDate(txns: Transaction[]): Array<{ label: string; date: string; transactions: Transaction[] }> {
  const grouped: Record<string, Transaction[]> = {};
  txns.forEach(t => {
    const key = t.date;
    if (!grouped[key]) grouped[key] = [];
    grouped[key].push(t);
  });
  return Object.entries(grouped)
    .sort(([a], [b]) => b.localeCompare(a))
    .map(([date, transactions]) => ({
      label: getDateLabel(date),
      date,
      transactions,
    }));
}

export default function TransactionsScreen() {
  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const { setCurrentScreen } = useScreenContext();
  const router = useRouter();
  const params = useLocalSearchParams<{ type?: string; action?: string }>();
  const insets = useSafeAreaInsets();
  
  // Calculate header height dynamically
  const HEADER_HEIGHT = 60 + insets.top;

  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [ccTransactions, setCCTransactions] = useState<Transaction[]>([]);
  const [creditCards, setCreditCards] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [editingTxn, setEditingTxn] = useState<Transaction | null>(null);
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([]);
  const [showPaymentDropdown, setShowPaymentDropdown] = useState(false);
  
  // Transaction Source Toggle: 'bank' or 'credit_card'
  const [txnSource, setTxnSource] = useState<'bank' | 'credit_card'>('bank');
  
  // Flagged Transactions Modal
  const [showFlaggedModal, setShowFlaggedModal] = useState(false);
  const [flaggedCount, setFlaggedCount] = useState(0);

  // Set screen context for AI awareness
  useEffect(() => {
    setCurrentScreen('transactions');
  }, [setCurrentScreen]);

  // Filters
  const [activeType, setActiveType] = useState<string>(params.type || 'all');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<string>('');
  const [showSearch, setShowSearch] = useState(false);
  const [datePreset, setDatePreset] = useState('All Time');

  // Period filter: Q=Quarter, M=Month, Y=Year, C=Custom(All)
  const [selectedPeriod, setSelectedPeriod] = useState<'Q' | 'M' | 'Y' | 'C'>('M');

  // Compute start_date/end_date from selected period
  const periodDates = useMemo(() => {
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const fmt = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    if (selectedPeriod === 'M') {
      const start = new Date(now.getFullYear(), now.getMonth(), 1);
      const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
      return { start: fmt(start), end: fmt(end) };
    } else if (selectedPeriod === 'Q') {
      const q = Math.floor(now.getMonth() / 3);
      const start = new Date(now.getFullYear(), q * 3, 1);
      const end = new Date(now.getFullYear(), q * 3 + 3, 0);
      return { start: fmt(start), end: fmt(end) };
    } else if (selectedPeriod === 'Y') {
      return { start: `${now.getFullYear()}-01-01`, end: `${now.getFullYear()}-12-31` };
    }
    return { start: null, end: null };
  }, [selectedPeriod]);

  // Human-readable period label
  const periodLabel = useMemo(() => {
    const now = new Date();
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    if (selectedPeriod === 'M') return `${monthNames[now.getMonth()]} ${now.getFullYear()}`;
    if (selectedPeriod === 'Q') return `Q${Math.floor(now.getMonth() / 3) + 1} ${now.getFullYear()}`;
    if (selectedPeriod === 'Y') return `${now.getFullYear()}`;
    return 'All Time';
  }, [selectedPeriod]);

  // Form
  const [form, setForm] = useState({
    type: 'expense', amount: '', category: '', description: '',
    date: '', notes: '', is_recurring: false, recurring_frequency: 'Monthly',
    is_split: false, split_count: '2',
    buy_sell: 'buy', units: '', price_per_unit: '',
    payment_mode: 'cash', payment_account_name: 'Cash',
  });
  const [saving, setSaving] = useState(false);
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showCategoryDropdown, setShowCategoryDropdown] = useState(false);
  const [tempDate, setTempDate] = useState(new Date());

  // Tax eligibility hint (lightweight frontend detection)
  const taxHint = useMemo(() => {
    const cat = form.category;
    const desc = (form.description + ' ' + (form.notes || '')).toLowerCase();
    // Category-based
    const catMap: Record<string, { section: string; label: string }> = {
      'PPF': { section: '80C', label: 'PPF - Section 80C' },
      'EPF': { section: '80C', label: 'EPF - Section 80C' },
      'NPS': { section: '80C', label: 'NPS - Section 80C' },
      'ELSS': { section: '80C', label: 'ELSS - Section 80C' },
      'Fixed Deposit': { section: '80C', label: 'Tax Saver FD - Section 80C' },
      'ULIP': { section: '80C', label: 'ULIP - Section 80C' },
      'Insurance': { section: '80D', label: 'Health Insurance - Section 80D' },
      'Donations': { section: '80G', label: 'Donations - Section 80G' },
      'Education': { section: '80C', label: 'Tuition Fees - Section 80C' },
    };
    if (cat && catMap[cat]) return catMap[cat];
    // Keyword-based
    const kwMap: Array<{ keywords: string[]; section: string; label: string }> = [
      { keywords: ['ppf', 'provident fund', 'pf contribution'], section: '80C', label: 'PF - Section 80C' },
      { keywords: ['health insurance', 'mediclaim', 'medical insurance'], section: '80D', label: 'Health Insurance - Section 80D' },
      { keywords: ['elss', 'tax saver', 'tax saving'], section: '80C', label: 'Tax Saver - Section 80C' },
      { keywords: ['nps', 'pension'], section: '80C', label: 'NPS - Section 80C' },
      { keywords: ['lic', 'life insurance', 'term insurance'], section: '80C', label: 'Life Insurance - Section 80C' },
      { keywords: ['education loan', 'student loan'], section: '80E', label: 'Education Loan - Section 80E' },
      { keywords: ['donation', 'charity', 'pm cares', 'ngo'], section: '80G', label: 'Donation - Section 80G' },
      { keywords: ['home loan interest', 'housing loan interest'], section: '24b', label: 'Home Loan Interest - Section 24(b)' },
    ];
    for (const entry of kwMap) {
      if (entry.keywords.some(kw => desc.includes(kw))) return { section: entry.section, label: entry.label };
    }
    return null;
  }, [form.category, form.description, form.notes]);

  // Convert the date TextInput to type="date" on web for calendar picker
  useEffect(() => {
    if (Platform.OS !== 'web' || !showModal) return;
    const timer = setTimeout(() => {
      const input = document.getElementById('visor-date-input');
      if (input && input.tagName === 'INPUT') {
        (input as HTMLInputElement).type = 'date';
        (input as HTMLInputElement).style.cursor = 'pointer';
        (input as HTMLInputElement).style.colorScheme = isDark ? 'dark' : 'light';
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [showModal, isDark]);

  // Animation
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, { toValue: 1, duration: 300, useNativeDriver: true }).start();
  }, []);

  // Summary for bank/UPI transactions
  const summary = useMemo(() => {
    const txns = txnSource === 'bank' ? transactions : ccTransactions;
    const inc = txns.filter(t => t.type === 'income').reduce((s, t) => s + t.amount, 0);
    const exp = txns.filter(t => t.type === 'expense').reduce((s, t) => s + t.amount, 0);
    const inv = txns.filter(t => t.type === 'investment').reduce((s, t) => s + t.amount, 0);
    const pay = txns.filter(t => t.type === 'payment').reduce((s, t) => s + t.amount, 0);
    const net = inc - exp - inv;
    return { income: inc, expense: exp, investment: inv, payment: pay, net, total: txns.length };
  }, [transactions, ccTransactions, txnSource]);

  const fetchTxns = useCallback(async () => {
    if (!token) return;
    try {
      // Fetch bank/UPI transactions
      const params = new URLSearchParams();
      if (activeType !== 'all') params.append('type', activeType);
      if (activeCategory) params.append('category', activeCategory);
      if (searchQuery.trim()) params.append('search', searchQuery.trim());
      if (periodDates.start) params.append('start_date', periodDates.start);
      if (periodDates.end) params.append('end_date', periodDates.end);
      const qs = params.toString() ? `?${params.toString()}` : '';
      
      // Fetch both bank transactions and credit card transactions in parallel
      const [bankData, ccData, cardsData, flaggedData] = await Promise.all([
        apiRequest(`/transactions${qs}`, { token }),
        apiRequest(`/credit-card-transactions${qs}`, { token }).catch(() => []),
        apiRequest('/credit-cards', { token }).catch(() => []),
        apiRequest('/flagged-transactions', { token }).catch(() => []),
      ]);
      
      setTransactions(bankData);
      setCCTransactions(ccData);
      setCreditCards(cardsData);
      setFlaggedCount(flaggedData?.length || 0);
    } catch (e) { console.error(e); }
    finally { setLoading(false); setRefreshing(false); }
  }, [token, activeType, activeCategory, searchQuery, periodDates]);

  useEffect(() => { fetchTxns(); }, [fetchTxns]);
  const onRefresh = () => { setRefreshing(true); fetchTxns(); };

  // Fetch bank accounts for Mode of Payment dropdown
  const fetchBankAccounts = useCallback(async () => {
    if (!token) return;
    try {
      const data = await apiRequest('/bank-accounts', { token });
      setBankAccounts(data);
    } catch {}
  }, [token]);
  useEffect(() => { fetchBankAccounts(); }, [fetchBankAccounts]);

  // Get default payment mode from bank accounts
  const getDefaultPaymentMode = useCallback(() => {
    const defaultBank = bankAccounts.find(b => b.is_default);
    if (defaultBank) return { payment_mode: 'bank', payment_account_name: defaultBank.account_name };
    return { payment_mode: 'cash', payment_account_name: 'Cash' };
  }, [bankAccounts]);

  // Auto-open add modal when navigated with action=add
  useEffect(() => {
    if (params.action === 'add' && params.type) {
      openAdd(params.type);
    }
  }, [params.action, params.type]);

  // ── Modal handlers ──
  const openAdd = (type?: string) => {
    setEditingTxn(null);
    const defaults = getDefaultPaymentMode();
    setForm({
      type: type || 'expense', amount: '', category: '', description: '',
      date: '', notes: '', is_recurring: false, recurring_frequency: 'Monthly',
      is_split: false, split_count: '2',
      buy_sell: 'buy', units: '', price_per_unit: '',
      payment_mode: defaults.payment_mode, payment_account_name: defaults.payment_account_name,
    });
    setShowPaymentDropdown(false);
    setShowModal(true);
  };

  const openEdit = (txn: Transaction) => {
    setEditingTxn(txn);
    setForm({
      type: txn.type,
      amount: String(txn.amount),
      category: txn.category,
      description: txn.description,
      date: txn.date,
      notes: txn.notes || '',
      is_recurring: txn.is_recurring || false,
      recurring_frequency: txn.recurring_frequency || 'Monthly',
      is_split: txn.is_split || false,
      split_count: String(txn.split_count || 2),
      buy_sell: (txn as any).buy_sell || 'buy',
      units: (txn as any).units ? String((txn as any).units) : '',
      price_per_unit: (txn as any).price_per_unit ? String((txn as any).price_per_unit) : '',
      payment_mode: txn.payment_mode || 'cash',
      payment_account_name: txn.payment_account_name || 'Cash',
    });
    setShowPaymentDropdown(false);
    setShowModal(true);
  };

  const handleSave = async () => {
    if (!form.amount || !form.category) {
      Alert.alert('Missing Info', 'Please fill in amount and category'); return;
    }
    setSaving(true);
    try {
      const today = new Date().toISOString().split('T')[0];
      const body: any = {
        type: form.type,
        amount: parseFloat(form.amount),
        category: form.category,
        description: form.description,
        date: form.date || today,
        notes: form.notes || null,
        is_recurring: form.is_recurring,
        recurring_frequency: form.is_recurring ? form.recurring_frequency : null,
        is_split: form.is_split,
        split_count: form.is_split ? parseInt(form.split_count) || 2 : 1,
        payment_mode: form.payment_mode || 'cash',
        payment_account_name: form.payment_account_name || 'Cash',
      };
      
      // Add investment-specific fields
      if (form.type === 'investment') {
        body.buy_sell = form.buy_sell || 'buy';
        if (form.units) body.units = parseFloat(form.units);
        if (form.price_per_unit) body.price_per_unit = parseFloat(form.price_per_unit);
      }

      if (editingTxn) {
        await apiRequest(`/transactions/${editingTxn.id}`, { method: 'PUT', token, body });
      } else {
        await apiRequest('/transactions', { method: 'POST', token, body });
      }
      setShowModal(false);
      fetchTxns();
    } catch (e: any) { Alert.alert('Error', e.message); }
    finally { setSaving(false); }
  };

  const handleDelete = (id: string, desc: string) => {
    Alert.alert('Delete Transaction', `Are you sure you want to remove "${desc}"?`, [
      { text: 'Cancel', style: 'cancel' },
      { text: 'Delete', style: 'destructive', onPress: async () => {
        try {
          await apiRequest(`/transactions/${id}`, { method: 'DELETE', token });
          setTransactions(prev => prev.filter(t => t.id !== id));
        } catch (e: any) { Alert.alert('Error', e.message); }
      }},
    ]);
  };

  const clearFilters = () => {
    setActiveType('all');
    setActiveCategory('');
    setSearchQuery('');
    setDatePreset('All Time');
  };

  const dateGroups = useMemo(() => {
    const txns = txnSource === 'bank' ? transactions : ccTransactions;
    return groupByDate(txns);
  }, [transactions, ccTransactions, txnSource]);
  
  // Categories based on transaction source
  const cats = useMemo(() => {
    if (txnSource === 'credit_card') {
      return ['Shopping', 'Food & Dining', 'EMI', 'Subscriptions', 'Travel', 'Fuel', 'Utilities', 'Entertainment', 'Health', 'Other'];
    }
    return form.type === 'income' ? INCOME_CATS : form.type === 'investment' ? INVEST_CATS : EXPENSE_CATS;
  }, [txnSource, form.type]);
  
  // Type filters based on transaction source
  const typeFilters = useMemo(() => {
    if (txnSource === 'credit_card') {
      return [
        { key: 'all', label: 'All', color: colors.primary },
        { key: 'expense', label: 'Purchases', color: colors.expense },
        { key: 'payment', label: 'Payments', color: colors.income },
      ];
    }
    return [
      { key: 'all', label: 'All', color: colors.primary },
      { key: 'income', label: 'Income', color: colors.income },
      { key: 'expense', label: 'Expense', color: colors.expense },
      { key: 'investment', label: 'Investment', color: colors.investment },
    ];
  }, [txnSource, colors]);

  const hasFilters = activeType !== 'all' || activeCategory !== '' || searchQuery !== '';

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />

      {/* Clean Header */}
      <View style={[styles.stickyHeader, { paddingTop: insets.top, backgroundColor: isDark ? '#000000' : '#FFFFFF' }]}>
        <View
          style={[
            styles.headerContent,
            {
              backgroundColor: isDark ? '#000000' : '#FFFFFF',
              borderBottomColor: isDark ? '#1F2937' : '#E5E7EB',
            },
          ]}
        >
          <View style={styles.headerLeft}>
            <Text style={[styles.headerTitle, { color: isDark ? Accent.amethyst : '#7C3AED' }]}>Transactions</Text>
            <Text style={[styles.headerSubtitle, { color: colors.textSecondary }]}>
              Track and manage your finances
            </Text>
          </View>
          <View style={styles.headerActions}>
            <TouchableOpacity
              style={[styles.headerIconBtn, {
                backgroundColor: showSearch ? 'rgba(147, 51, 234, 0.15)' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.05)',
              }]}
              onPress={() => { setShowSearch(!showSearch); if (showSearch) setSearchQuery(''); }}
            >
              <MaterialCommunityIcons
                name={showSearch ? 'close' : 'magnify'}
                size={20}
                color={showSearch ? Accent.amethyst : colors.textSecondary}
              />
            </TouchableOpacity>
          </View>
        </View>

        {/* Search Bar */}
        {showSearch && (
          <View style={[styles.searchBar, {
            backgroundColor: isDark ? '#000000' : '#FFFFFF',
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
          }]}>
            <MaterialCommunityIcons name="magnify" size={20} color={colors.textSecondary} />
            <TextInput
              style={[styles.searchInput, { color: colors.textPrimary }]}
              value={searchQuery}
              onChangeText={setSearchQuery}
              placeholder="Search transactions..."
              placeholderTextColor={colors.textSecondary}
              autoFocus
            />
            {searchQuery.length > 0 && (
              <TouchableOpacity onPress={() => setSearchQuery('')}>
                <MaterialCommunityIcons name="close-circle" size={18} color={colors.textSecondary} />
              </TouchableOpacity>
            )}
          </View>
        )}
      </View>

      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={[styles.scrollContent, { paddingTop: HEADER_HEIGHT + (showSearch ? 50 : 0) + 16 }]}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
        showsVerticalScrollIndicator={false}
      >
        {/* ═══ TRANSACTION SOURCE TOGGLE (Bank/UPI vs Credit Card) ═══ */}
        <View style={[styles.sourceToggleContainer, {
          backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          <TouchableOpacity
            data-testid="txn-source-bank"
            style={[
              styles.sourceToggleBtn,
              txnSource === 'bank' && styles.sourceToggleBtnActive,
              txnSource === 'bank' && { backgroundColor: '#10B981' },
            ]}
            onPress={() => { setTxnSource('bank'); setActiveType('all'); }}
          >
            <MaterialCommunityIcons 
              name="bank" 
              size={18} 
              color={txnSource === 'bank' ? '#fff' : colors.textSecondary} 
            />
            <Text style={[
              styles.sourceToggleText,
              { color: txnSource === 'bank' ? '#fff' : colors.textSecondary },
            ]}>Bank / UPI</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            data-testid="txn-source-cc"
            style={[
              styles.sourceToggleBtn,
              txnSource === 'credit_card' && styles.sourceToggleBtnActive,
              txnSource === 'credit_card' && { backgroundColor: '#8B5CF6' },
            ]}
            onPress={() => { setTxnSource('credit_card'); setActiveType('all'); }}
          >
            <MaterialCommunityIcons 
              name="credit-card" 
              size={18} 
              color={txnSource === 'credit_card' ? '#fff' : colors.textSecondary} 
            />
            <Text style={[
              styles.sourceToggleText,
              { color: txnSource === 'credit_card' ? '#fff' : colors.textSecondary },
            ]}>Credit Card</Text>
            {ccTransactions.length > 0 && txnSource !== 'credit_card' && (
              <View style={styles.ccBadge}>
                <Text style={styles.ccBadgeText}>{ccTransactions.length}</Text>
              </View>
            )}
          </TouchableOpacity>
        </View>

        {/* ═══ PERIOD FILTER ═══ */}
        <View style={[styles.periodFilterRow, {
          backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
          borderBottomWidth: 1,
          borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
        }]}>
          <Text style={[styles.periodFilterLabel, { color: colors.textSecondary }]}>{periodLabel}</Text>
          <View style={[styles.periodPillsGroup, {
            backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)',
          }]}>
            {(['Q', 'M', 'Y', 'C'] as const).map(p => (
              <TouchableOpacity
                key={p}
                data-testid={`txn-period-${p}`}
                style={[
                  styles.periodPill,
                  selectedPeriod === p && { backgroundColor: colors.primary },
                ]}
                onPress={() => setSelectedPeriod(p)}
              >
                <Text style={[
                  styles.periodPillText,
                  { color: selectedPeriod === p ? '#fff' : colors.textSecondary },
                ]}>
                  {p === 'C' ? 'All' : p}
                </Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* ═══ FLAGGED TRANSACTIONS ALERT BAR ═══ */}
        {flaggedCount > 0 && (
          <TouchableOpacity
            data-testid="flagged-transactions-btn"
            style={[styles.flaggedBar, {
              backgroundColor: isDark ? 'rgba(245, 158, 11, 0.12)' : 'rgba(245, 158, 11, 0.08)',
              borderColor: Accent.amber,
            }]}
            onPress={() => setShowFlaggedModal(true)}
          >
            <View style={[styles.flaggedIcon, { backgroundColor: `${Accent.amber}20` }]}>
              <MaterialCommunityIcons name="flag-checkered" size={18} color={Accent.amber} />
            </View>
            <View style={styles.flaggedContent}>
              <Text style={[styles.flaggedTitle, { color: colors.textPrimary }]}>
                {flaggedCount} transaction{flaggedCount > 1 ? 's' : ''} need review
              </Text>
              <Text style={[styles.flaggedSubtitle, { color: colors.textSecondary }]}>
                Detected as potential EMI/SIP payments
              </Text>
            </View>
            <MaterialCommunityIcons name="chevron-right" size={20} color={Accent.amber} />
          </TouchableOpacity>
        )}

        {/* ═══ TYPE FILTER PILLS ═══ */}
        <View style={styles.filterSection}>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.filterPillsRow}>
            {typeFilters.map(f => {
              const isActive = activeType === f.key;
              return (
                <TouchableOpacity
                  key={f.key}
                  style={[
                    styles.filterPill,
                    {
                      backgroundColor: isActive ? f.color : 'transparent',
                      borderColor: isActive ? f.color : isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.12)',
                    },
                  ]}
                  onPress={() => setActiveType(f.key)}
                >
                  <Text style={[styles.filterPillText, { color: isActive ? '#fff' : colors.textSecondary }]}>
                    {f.label}
                  </Text>
                </TouchableOpacity>
              );
            })}
          </ScrollView>

          {/* Category Filter Dropdown */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.categoryChipsRow}>
            {(activeType === 'all' ? ['Rent', 'Food', 'Salary', 'SIP', 'Shopping', 'Transport'] : cats.slice(0, 6)).map(cat => (
              <TouchableOpacity
                key={cat}
                style={[
                  styles.categoryChip,
                  {
                    backgroundColor: activeCategory === cat
                      ? `${getCategoryColor(cat, isDark)}20`
                      : isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)',
                    borderColor: activeCategory === cat
                      ? getCategoryColor(cat, isDark)
                      : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                  },
                ]}
                onPress={() => setActiveCategory(activeCategory === cat ? '' : cat)}
              >
                <MaterialCommunityIcons
                  name={getCategoryIcon(cat) as any}
                  size={14}
                  color={activeCategory === cat ? getCategoryColor(cat, isDark) : colors.textSecondary}
                />
                <Text style={[
                  styles.categoryChipText,
                  { color: activeCategory === cat ? getCategoryColor(cat, isDark) : colors.textSecondary },
                ]}>
                  {cat}
                </Text>
                {activeCategory === cat && (
                  <MaterialCommunityIcons name="close" size={12} color={getCategoryColor(cat, isDark)} />
                )}
              </TouchableOpacity>
            ))}
          </ScrollView>

          {/* Active Filters Badge */}
          {hasFilters && (
            <TouchableOpacity style={styles.clearFiltersBtn} onPress={clearFilters}>
              <MaterialCommunityIcons name="filter-remove" size={14} color="#9333EA" />
              <Text style={styles.clearFiltersText}>Clear Filters</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* ═══ SUMMARY BAR ═══ */}
        <View style={[styles.summaryBar, {
          backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.95)',
          borderColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
        }]}>
          {txnSource === 'bank' ? (
            <>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: colors.income }]}>+{formatINRShort(summary.income)}</Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Income</Text>
              </View>
              <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: colors.expense }]}>-{formatINRShort(summary.expense)}</Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Expenses</Text>
              </View>
              <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: summary.net >= 0 ? colors.income : colors.expense }]}>
                  {summary.net >= 0 ? '+' : ''}{formatINRShort(summary.net)}
                </Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Net</Text>
              </View>
            </>
          ) : (
            <>
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: colors.expense }]}>{formatINRShort(summary.expense)}</Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Purchases</Text>
              </View>
              <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: colors.income }]}>{formatINRShort(summary.payment)}</Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Payments</Text>
              </View>
              <View style={[styles.summaryDivider, { backgroundColor: colors.border }]} />
              <View style={styles.summaryItem}>
                <Text style={[styles.summaryAmount, { color: summary.expense - summary.payment > 0 ? colors.expense : colors.income }]}>
                  {formatINRShort(Math.abs(summary.expense - summary.payment))}
                </Text>
                <Text style={[styles.summaryLabel, { color: colors.textSecondary }]}>Outstanding</Text>
              </View>
            </>
          )}
        </View>

        {/* ═══ TRANSACTION LIST ═══ */}
        {loading ? (
          <View style={styles.loadingContainer}>
            {/* Skeleton loading */}
            {[1, 2, 3, 4, 5].map(i => (
              <View key={i} style={[styles.skeletonCard, {
                backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.03)',
              }]}>
                <View style={[styles.skeletonIcon, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
                <View style={styles.skeletonBody}>
                  <View style={[styles.skeletonLine, { width: '70%', backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
                  <View style={[styles.skeletonLine, { width: '40%', backgroundColor: isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.04)' }]} />
                </View>
                <View style={[styles.skeletonAmount, { backgroundColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]} />
              </View>
            ))}
          </View>
        ) : dateGroups.length === 0 ? (
          <View style={styles.emptyState}>
            <View style={[styles.emptyIconWrap, { backgroundColor: isDark ? 'rgba(147, 51, 234, 0.1)' : 'rgba(147, 51, 234, 0.08)' }]}>
              <MaterialCommunityIcons 
                name={txnSource === 'credit_card' ? 'credit-card-off' : 'receipt'} 
                size={56} 
                color={txnSource === 'credit_card' ? '#8B5CF6' : '#9333EA'} 
              />
            </View>
            <Text style={[styles.emptyTitle, { color: colors.textPrimary }]}>
              {hasFilters ? 'No matching transactions' : txnSource === 'credit_card' ? 'No credit card transactions' : 'No transactions yet'}
            </Text>
            <Text style={[styles.emptySubtitle, { color: colors.textSecondary }]}>
              {hasFilters
                ? 'Try adjusting your filters to see more results'
                : txnSource === 'credit_card' 
                  ? 'Add a credit card in Settings and record your expenses'
                  : 'Add your first transaction to start tracking your finances'}
            </Text>
            {hasFilters ? (
              <TouchableOpacity style={styles.clearFiltersLargeBtn} onPress={clearFilters}>
                <Text style={styles.clearFiltersLargeText}>Clear Filters</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity style={styles.emptyAddBtn} onPress={() => openAdd()}>
                <LinearGradient
                  colors={[Accent.amethyst, '#EC4899']}
                  start={{ x: 0, y: 0 }}
                  end={{ x: 1, y: 0 }}
                  style={styles.emptyAddGradient}
                >
                  <MaterialCommunityIcons name="plus" size={18} color="#fff" />
                  <Text style={styles.emptyAddText}>Add Transaction</Text>
                </LinearGradient>
              </TouchableOpacity>
            )}
          </View>
        ) : (
          <Animated.View style={{ opacity: fadeAnim }}>
            {dateGroups.map((group, groupIndex) => (
              <View key={group.date}>
                {/* Date Section Header */}
                <View style={styles.dateHeader}>
                  <Text style={[styles.dateLabel, { color: colors.textPrimary }]}>{group.label}</Text>
                  <Text style={[styles.dateCount, { color: colors.textSecondary }]}>
                    {group.transactions.length} transaction{group.transactions.length > 1 ? 's' : ''}
                  </Text>
                </View>

                {/* Transaction Cards */}
                {group.transactions.map((txn, txnIndex) => (
                  <TouchableOpacity
                    key={txn.id}
                    style={[styles.txnCard, {
                      backgroundColor: isDark ? 'rgba(10, 10, 11, 0.85)' : 'rgba(255, 255, 255, 0.9)',
                      borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)',
                    }]}
                    onPress={() => openEdit(txn)}
                    onLongPress={() => handleDelete(txn.id, txn.description)}
                    activeOpacity={0.7}
                  >
                    {/* Icon */}
                    <View style={[styles.txnIconWrap, {
                      backgroundColor: txn.type === 'income'
                        ? (isDark ? 'rgba(16, 185, 129, 0.15)' : 'rgba(16, 185, 129, 0.1)')
                        : txn.type === 'investment'
                        ? (isDark ? 'rgba(99, 102, 241, 0.15)' : 'rgba(99, 102, 241, 0.1)')
                        : (isDark ? 'rgba(239, 68, 68, 0.15)' : 'rgba(239, 68, 68, 0.1)'),
                    }]}>
                      <MaterialCommunityIcons
                        name={getCategoryIcon(txn.category) as any}
                        size={22}
                        color={txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense}
                      />
                    </View>

                    {/* Content */}
                    <View style={styles.txnContent}>
                      <Text style={[styles.txnTitle, { color: colors.textPrimary }]} numberOfLines={1}>
                        {txn.description}
                      </Text>
                      <View style={styles.txnMetaRow}>
                        <Text style={[styles.txnCategory, { color: colors.textSecondary }]}>{txn.category}</Text>
                        <Text style={[styles.txnDot, { color: colors.textSecondary }]}>·</Text>
                        <Text style={[styles.txnDate, { color: colors.textSecondary }]}>
                          {new Date(txn.date + 'T00:00:00').toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
                        </Text>
                        {txn.is_recurring && (
                          <View style={[styles.txnBadge, { backgroundColor: 'rgba(147, 51, 234, 0.1)' }]}>
                            <MaterialCommunityIcons name="repeat" size={10} color="#9333EA" />
                            <Text style={[styles.txnBadgeText, { color: Accent.amethyst }]}>Recurring</Text>
                          </View>
                        )}
                        {txn.is_split && txn.split_count && txn.split_count > 1 && (
                          <View style={[styles.txnBadge, { backgroundColor: 'rgba(245, 158, 11, 0.1)' }]}>
                            <MaterialCommunityIcons name="account-multiple" size={10} color={Accent.amber} />
                            <Text style={[styles.txnBadgeText, { color: Accent.amber }]}>Split ×{txn.split_count}</Text>
                          </View>
                        )}
                      </View>
                    </View>

                    {/* Amount */}
                    <View style={styles.txnAmountWrap}>
                      <Text style={[styles.txnAmount, {
                        color: txn.type === 'income' ? colors.income : txn.type === 'investment' ? colors.investment : colors.expense,
                      }]}>
                        {txn.type === 'income' ? '+' : txn.type === 'investment' ? '' : '-'}{formatINR(txn.amount)}
                      </Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            ))}
          </Animated.View>
        )}

        <View style={{ height: 120 }} />
      </ScrollView>

      {/* ═══ FLOATING ACTION BUTTON ═══ */}
      <TouchableOpacity
        style={styles.fab}
        onPress={() => openAdd()}
        activeOpacity={0.9}
      >
        <LinearGradient
          colors={[Accent.amethyst, '#EC4899']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.fabGradient}
        >
          <MaterialCommunityIcons name="plus" size={28} color="#fff" />
        </LinearGradient>
      </TouchableOpacity>

      {/* ═══ ADD/EDIT TRANSACTION MODAL ═══ */}
      <Modal visible={showModal} animationType="slide" transparent>
        <View style={styles.modalOverlay}>
          <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalKav}>
            <View style={[styles.modalContent, { backgroundColor: colors.surface }]}>
              <View style={styles.modalHandle} />

              {/* Modal Header */}
              <View style={styles.modalHeader}>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  {editingTxn ? 'Edit Transaction' : 'Add Transaction'}
                </Text>
                <TouchableOpacity onPress={() => setShowModal(false)}>
                  <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
                </TouchableOpacity>
              </View>

              <ScrollView showsVerticalScrollIndicator={false}>
                {/* Type Selector */}
                <View style={styles.typeSelector}>
                  {(['income', 'expense', 'investment'] as const).map(t => {
                    const isActive = form.type === t;
                    const tColor = t === 'income' ? colors.income : t === 'investment' ? colors.investment : colors.expense;
                    return (
                      <TouchableOpacity
                        key={t}
                        style={[styles.typeBtn, {
                          backgroundColor: isActive ? tColor : 'transparent',
                          borderColor: isActive ? tColor : isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
                        }]}
                        onPress={() => setForm(p => ({ ...p, type: t, category: '', description: '' }))}
                      >
                        <MaterialCommunityIcons
                          name={t === 'income' ? 'arrow-down-circle' : t === 'investment' ? 'trending-up' : 'arrow-up-circle'}
                          size={18}
                          color={isActive ? '#fff' : tColor}
                        />
                        <Text style={[styles.typeBtnText, { color: isActive ? '#fff' : colors.textPrimary }]}>
                          {t.charAt(0).toUpperCase() + t.slice(1)}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>

                {/* Category Dropdown */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Category *</Text>
                <TouchableOpacity
                  style={[styles.textInput, { borderColor: colors.border, backgroundColor: colors.background, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }]}
                  onPress={() => setShowCategoryDropdown(!showCategoryDropdown)}
                  data-testid="category-dropdown-btn"
                >
                  <Text style={{ color: form.category ? colors.textPrimary : colors.textSecondary, fontFamily: 'DM Sans', fontWeight: '500' as any, fontSize: 15 }}>
                    {form.category || 'Select category'}
                  </Text>
                  <MaterialCommunityIcons name={showCategoryDropdown ? 'chevron-up' : 'chevron-down'} size={22} color={colors.textSecondary} />
                </TouchableOpacity>
                {showCategoryDropdown && (
                  <View style={[styles.dropdownList, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                    <ScrollView nestedScrollEnabled style={{ maxHeight: 200 }} showsVerticalScrollIndicator>
                      {cats.map(cat => (
                        <TouchableOpacity
                          key={cat}
                          style={[styles.dropdownItem, { borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' }]}
                          onPress={() => { setForm(p => ({ ...p, category: cat })); setShowCategoryDropdown(false); }}
                          data-testid={`cat-option-${cat}`}
                        >
                          <MaterialCommunityIcons
                            name={getCategoryIcon(cat) as any}
                            size={18}
                            color={form.category === cat ? colors.primary : colors.textSecondary}
                          />
                          <Text style={{
                            color: form.category === cat ? colors.primary : colors.textPrimary,
                            fontFamily: 'DM Sans', fontWeight: form.category === cat ? '600' as any : '400' as any, fontSize: 15, marginLeft: 12,
                          }}>
                            {cat}
                          </Text>
                          {form.category === cat && (
                            <MaterialCommunityIcons name="check" size={18} color={colors.primary} style={{ marginLeft: 'auto' }} />
                          )}
                        </TouchableOpacity>
                      ))}
                    </ScrollView>
                  </View>
                )}

                {/* Amount Input */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Amount *</Text>
                <View style={[styles.amountInputWrap, { borderColor: colors.border, backgroundColor: colors.background }]}>
                  <Text style={[styles.rupeeSymbol, { color: colors.primary }]}>₹</Text>
                  <TextInput
                    style={[styles.amountInput, { color: colors.textPrimary }]}
                    value={form.amount}
                    onChangeText={v => setForm(p => ({ ...p, amount: v }))}
                    placeholder="0"
                    placeholderTextColor={colors.textSecondary}
                    keyboardType="decimal-pad"
                  />
                </View>

                {/* Description (optional) with suggestions */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>
                  {form.type === 'investment' ? 'Investment Name' : 'Description'} (optional)
                </Text>
                <TextInput
                  style={[styles.textInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={form.description}
                  onChangeText={v => setForm(p => ({ ...p, description: v }))}
                  placeholder={form.type === 'investment' ? 'e.g., Axis Bluechip Fund' : form.type === 'income' ? 'e.g., Monthly Salary' : 'e.g., Grocery Shopping'}
                  placeholderTextColor={colors.textSecondary}
                />
                {!form.description && (
                  <View style={styles.suggestionRow}>
                    {(DESCRIPTION_SUGGESTIONS[form.type] || []).slice(0, 4).map(s => (
                      <TouchableOpacity
                        key={s}
                        style={[styles.suggestionChip, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)' }]}
                        onPress={() => setForm(p => ({ ...p, description: s }))}
                      >
                        <Text style={{ color: colors.textSecondary, fontSize: 12, fontFamily: 'DM Sans' }}>{s}</Text>
                      </TouchableOpacity>
                    ))}
                  </View>
                )}

                {/* Buy/Sell Toggle for Investments */}
                {form.type === 'investment' && (
                  <>
                    <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Transaction Type</Text>
                    <View style={styles.buySellToggle}>
                      <TouchableOpacity
                        style={[
                          styles.buySellBtn,
                          form.buy_sell === 'buy' && styles.buySellBtnActive,
                          { borderColor: form.buy_sell === 'buy' ? colors.income : colors.border }
                        ]}
                        onPress={() => setForm(p => ({ ...p, buy_sell: 'buy' }))}
                      >
                        <MaterialCommunityIcons name="arrow-down-circle" size={18} color={form.buy_sell === 'buy' ? colors.income : colors.textSecondary} />
                        <Text style={[styles.buySellText, { color: form.buy_sell === 'buy' ? colors.income : colors.textSecondary }]}>Buy</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[
                          styles.buySellBtn,
                          form.buy_sell === 'sell' && styles.buySellBtnActive,
                          { borderColor: form.buy_sell === 'sell' ? colors.expense : colors.border }
                        ]}
                        onPress={() => setForm(p => ({ ...p, buy_sell: 'sell' }))}
                      >
                        <MaterialCommunityIcons name="arrow-up-circle" size={18} color={form.buy_sell === 'sell' ? colors.expense : colors.textSecondary} />
                        <Text style={[styles.buySellText, { color: form.buy_sell === 'sell' ? colors.expense : colors.textSecondary }]}>Sell</Text>
                      </TouchableOpacity>
                    </View>

                    <View style={styles.unitsRow}>
                      <View style={{ flex: 1 }}>
                        <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Units (optional)</Text>
                        <TextInput
                          style={[styles.textInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                          value={form.units}
                          onChangeText={v => {
                            setForm(p => ({ ...p, units: v }));
                            // Auto-calculate price per unit if amount is set
                            if (form.amount && v) {
                              const ppu = parseFloat(form.amount) / parseFloat(v);
                              if (!isNaN(ppu)) setForm(p => ({ ...p, price_per_unit: ppu.toFixed(4) }));
                            }
                          }}
                          placeholder="e.g., 100"
                          placeholderTextColor={colors.textSecondary}
                          keyboardType="decimal-pad"
                        />
                      </View>
                      <View style={{ flex: 1, marginLeft: 12 }}>
                        <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Price/Unit (auto)</Text>
                        <TextInput
                          style={[styles.textInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                          value={form.price_per_unit}
                          onChangeText={v => setForm(p => ({ ...p, price_per_unit: v }))}
                          placeholder="Auto"
                          placeholderTextColor={colors.textSecondary}
                          keyboardType="decimal-pad"
                        />
                      </View>
                    </View>
                    
                    {form.buy_sell === 'sell' && (
                      <View style={[styles.taxNote, { backgroundColor: isDark ? 'rgba(245, 158, 11, 0.1)' : 'rgba(245, 158, 11, 0.08)' }]}>
                        <MaterialCommunityIcons name="information" size={16} color={Accent.amber} />
                        <Text style={[styles.taxNoteText, { color: colors.textSecondary }]}>
                          Capital gains tax will be calculated in Tax Planning
                        </Text>
                      </View>
                    )}
                  </>
                )}

                {/* Date Picker */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Date</Text>
                <TouchableOpacity
                  style={[styles.datePickerBtn, { borderColor: colors.border, backgroundColor: colors.background }]}
                  onPress={() => {
                    const current = form.date ? new Date(form.date + 'T00:00:00') : new Date();
                    setTempDate(current);
                    setShowDatePicker(true);
                  }}
                  data-testid="date-picker-btn"
                >
                  <MaterialCommunityIcons name="calendar" size={20} color={colors.textSecondary} />
                  <Text style={[styles.datePickerText, { color: form.date ? colors.textPrimary : colors.textSecondary }]}>
                    {form.date || new Date().toISOString().split('T')[0] + ' (today)'}
                  </Text>
                </TouchableOpacity>

                {/* Android & Web: native date picker */}
                {showDatePicker && Platform.OS !== 'ios' && (
                  <DateTimePicker
                    value={form.date ? new Date(form.date + 'T00:00:00') : new Date()}
                    mode="date"
                    display="default"
                    onChange={(event, selectedDate) => {
                      setShowDatePicker(false);
                      if (selectedDate) {
                        setForm(p => ({ ...p, date: selectedDate.toISOString().split('T')[0] }));
                      }
                    }}
                  />
                )}

                {/* iOS: Modal with spinner picker + Done/Cancel */}
                {Platform.OS === 'ios' && (
                  <Modal visible={showDatePicker} transparent animationType="slide">
                    <TouchableOpacity
                      style={styles.dateModalOverlay}
                      activeOpacity={1}
                      onPress={() => setShowDatePicker(false)}
                    >
                      <View style={[styles.dateModalContent, { backgroundColor: colors.surface }]}>
                        <View style={styles.dateModalHeader}>
                          <TouchableOpacity onPress={() => setShowDatePicker(false)} data-testid="date-picker-cancel">
                            <Text style={[styles.dateModalActionText, { color: colors.textSecondary }]}>Cancel</Text>
                          </TouchableOpacity>
                          <Text style={[styles.dateModalTitle, { color: colors.textPrimary }]}>Select Date</Text>
                          <TouchableOpacity
                            onPress={() => {
                              setForm(p => ({ ...p, date: tempDate.toISOString().split('T')[0] }));
                              setShowDatePicker(false);
                            }}
                            data-testid="date-picker-done"
                          >
                            <Text style={[styles.dateModalActionText, { color: Accent.amethyst, fontWeight: '700' as any }]}>Done</Text>
                          </TouchableOpacity>
                        </View>
                        <DateTimePicker
                          value={tempDate}
                          mode="date"
                          display="spinner"
                          onChange={(_, selectedDate) => {
                            if (selectedDate) setTempDate(selectedDate);
                          }}
                          themeVariant={isDark ? 'dark' : 'light'}
                          style={{ height: 200 }}
                        />
                      </View>
                    </TouchableOpacity>
                  </Modal>
                )}

                {/* Notes Input */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>
                  {form.type === 'income' ? 'Mode of Receipt' : 'Mode of Payment'}
                </Text>
                <TouchableOpacity
                  data-testid="payment-mode-selector"
                  style={[styles.datePickerBtn, { borderColor: showPaymentDropdown ? colors.primary : colors.border, backgroundColor: colors.background }]}
                  onPress={() => setShowPaymentDropdown(!showPaymentDropdown)}
                >
                  <MaterialCommunityIcons
                    name={form.payment_mode === 'cash' ? 'cash' : 'bank'}
                    size={20}
                    color={form.payment_mode === 'cash' ? Accent.emerald : Accent.sapphire}
                  />
                  <Text style={[styles.datePickerText, { color: colors.textPrimary, flex: 1 }]}>
                    {form.payment_mode === 'cash' ? 'Cash' : form.payment_account_name}
                  </Text>
                  <MaterialCommunityIcons
                    name={showPaymentDropdown ? 'chevron-up' : 'chevron-down'}
                    size={20}
                    color={colors.textSecondary}
                  />
                </TouchableOpacity>
                {showPaymentDropdown && (
                  <View style={[styles.paymentDropdown, { backgroundColor: colors.surface, borderColor: colors.border }]}>
                    <TouchableOpacity
                      data-testid="payment-option-cash"
                      style={[styles.paymentOption, form.payment_mode === 'cash' && { backgroundColor: isDark ? 'rgba(16,185,129,0.1)' : 'rgba(16,185,129,0.08)' }]}
                      onPress={() => {
                        setForm(p => ({ ...p, payment_mode: 'cash', payment_account_name: 'Cash' }));
                        setShowPaymentDropdown(false);
                      }}
                    >
                      <MaterialCommunityIcons name="cash" size={20} color={Accent.emerald} />
                      <Text style={[styles.paymentOptionText, { color: colors.textPrimary }]}>Cash</Text>
                      {form.payment_mode === 'cash' && (
                        <MaterialCommunityIcons name="check" size={18} color={Accent.emerald} style={{ marginLeft: 'auto' }} />
                      )}
                    </TouchableOpacity>
                    {bankAccounts.map(bank => (
                      <TouchableOpacity
                        key={bank.id}
                        data-testid={`payment-option-${bank.id}`}
                        style={[styles.paymentOption, form.payment_mode === 'bank' && form.payment_account_name === bank.account_name && { backgroundColor: isDark ? 'rgba(59,130,246,0.1)' : 'rgba(59,130,246,0.08)' }]}
                        onPress={() => {
                          setForm(p => ({ ...p, payment_mode: 'bank', payment_account_name: bank.account_name }));
                          setShowPaymentDropdown(false);
                        }}
                      >
                        <MaterialCommunityIcons name="bank" size={20} color={Accent.sapphire} />
                        <View style={{ flex: 1 }}>
                          <Text style={[styles.paymentOptionText, { color: colors.textPrimary }]}>{bank.account_name}</Text>
                          <Text style={{ fontSize: 11, color: colors.textSecondary, fontFamily: 'DM Sans' }}>{bank.bank_name}{bank.is_default ? ' (Default)' : ''}</Text>
                        </View>
                        {form.payment_mode === 'bank' && form.payment_account_name === bank.account_name && (
                          <MaterialCommunityIcons name="check" size={18} color={Accent.sapphire} style={{ marginLeft: 'auto' }} />
                        )}
                      </TouchableOpacity>
                    ))}
                    {bankAccounts.length === 0 && (
                      <View style={[styles.paymentOption, { opacity: 0.6 }]}>
                        <MaterialCommunityIcons name="information-outline" size={16} color={colors.textSecondary} />
                        <Text style={{ fontSize: 12, color: colors.textSecondary, fontFamily: 'DM Sans' }}>Add bank accounts in Settings</Text>
                      </View>
                    )}
                  </View>
                )}

                {/* Notes Input */}
                <Text style={[styles.fieldLabel, { color: colors.textSecondary }]}>Notes (optional)</Text>
                <TextInput
                  style={[styles.textInput, styles.notesInput, { borderColor: colors.border, backgroundColor: colors.background, color: colors.textPrimary }]}
                  value={form.notes}
                  onChangeText={v => setForm(p => ({ ...p, notes: v }))}
                  placeholder="Add any notes..."
                  placeholderTextColor={colors.textSecondary}
                  multiline
                />

                {/* Tax Eligibility Hint */}
                {taxHint && (
                  <View data-testid="tax-eligibility-hint" style={[styles.taxHintBanner, { backgroundColor: isDark ? 'rgba(139,92,246,0.12)' : 'rgba(139,92,246,0.08)', borderColor: isDark ? 'rgba(139,92,246,0.25)' : 'rgba(139,92,246,0.15)' }]}>
                    <MaterialCommunityIcons name="lightning-bolt" size={16} color="#8B5CF6" />
                    <View style={{ flex: 1 }}>
                      <Text style={{ fontSize: 12, fontWeight: '700', color: '#8B5CF6', fontFamily: 'DM Sans' }}>Tax Deductible</Text>
                      <Text style={{ fontSize: 11, color: isDark ? 'rgba(139,92,246,0.8)' : 'rgba(139,92,246,0.9)', fontFamily: 'DM Sans', marginTop: 1 }}>{taxHint.label} - auto-added to Tax Planning</Text>
                    </View>
                  </View>
                )}

                {/* Recurring Toggle */}
                <View style={[styles.toggleCard, { backgroundColor: colors.background, borderColor: colors.border }]}>
                  <View style={styles.toggleRow}>
                    <View style={[styles.toggleIcon, { backgroundColor: 'rgba(147, 51, 234, 0.1)' }]}>
                      <MaterialCommunityIcons name="repeat" size={20} color="#9333EA" />
                    </View>
                    <View style={styles.toggleInfo}>
                      <Text style={[styles.toggleTitle, { color: colors.textPrimary }]}>Recurring Transaction</Text>
                      <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>Repeats automatically</Text>
                    </View>
                    <Switch
                      value={form.is_recurring}
                      onValueChange={v => setForm(p => ({ ...p, is_recurring: v }))}
                      trackColor={{ false: colors.border, true: 'rgba(147, 51, 234, 0.5)' }}
                      thumbColor={form.is_recurring ? Accent.amethyst : '#ccc'}
                    />
                  </View>
                  {form.is_recurring && (
                    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.freqRow}>
                      {RECURRING_FREQ.map(freq => (
                        <TouchableOpacity
                          key={freq}
                          style={[styles.freqChip, {
                            backgroundColor: form.recurring_frequency === freq ? Accent.amethyst : 'transparent',
                            borderColor: form.recurring_frequency === freq ? Accent.amethyst : colors.border,
                          }]}
                          onPress={() => setForm(p => ({ ...p, recurring_frequency: freq }))}
                        >
                          <Text style={{ fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' as any, color: form.recurring_frequency === freq ? '#fff' : colors.textSecondary }}>
                            {freq}
                          </Text>
                        </TouchableOpacity>
                      ))}
                    </ScrollView>
                  )}
                </View>

                {/* Split Toggle */}
                <View style={[styles.toggleCard, { backgroundColor: colors.background, borderColor: colors.border }]}>
                  <View style={styles.toggleRow}>
                    <View style={[styles.toggleIcon, { backgroundColor: 'rgba(245, 158, 11, 0.1)' }]}>
                      <MaterialCommunityIcons name="account-multiple" size={20} color={Accent.amber} />
                    </View>
                    <View style={styles.toggleInfo}>
                      <Text style={[styles.toggleTitle, { color: colors.textPrimary }]}>Split with others</Text>
                      <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>Divide the amount</Text>
                    </View>
                    <Switch
                      value={form.is_split}
                      onValueChange={v => setForm(p => ({ ...p, is_split: v }))}
                      trackColor={{ false: colors.border, true: 'rgba(245, 158, 11, 0.5)' }}
                      thumbColor={form.is_split ? Accent.amber : '#ccc'}
                    />
                  </View>
                  {form.is_split && (
                    <View style={styles.splitSection}>
                      <View style={styles.splitRow}>
                        <Text style={[styles.splitLabel, { color: colors.textSecondary }]}>Split count:</Text>
                        <View style={styles.splitControls}>
                          <TouchableOpacity
                            style={[styles.splitBtn, { borderColor: colors.border }]}
                            onPress={() => setForm(p => ({ ...p, split_count: String(Math.max(2, parseInt(p.split_count) - 1)) }))}
                          >
                            <MaterialCommunityIcons name="minus" size={16} color={colors.textPrimary} />
                          </TouchableOpacity>
                          <Text style={[styles.splitCount, { color: colors.textPrimary }]}>{form.split_count}</Text>
                          <TouchableOpacity
                            style={[styles.splitBtn, { borderColor: colors.border }]}
                            onPress={() => setForm(p => ({ ...p, split_count: String(Math.min(50, parseInt(p.split_count) + 1)) }))}
                          >
                            <MaterialCommunityIcons name="plus" size={16} color={colors.textPrimary} />
                          </TouchableOpacity>
                        </View>
                      </View>
                      <Text style={[styles.splitResult, { color: Accent.amber }]}>
                        Per person: {formatINRShort(parseFloat(form.amount || '0') / (parseInt(form.split_count) || 1))}
                      </Text>
                    </View>
                  )}
                </View>

                {/* Submit Button */}
                <TouchableOpacity
                  style={[styles.submitBtn, { opacity: (!form.amount || !form.category || !form.description) ? 0.5 : 1 }]}
                  onPress={handleSave}
                  disabled={saving || !form.amount || !form.category || !form.description}
                >
                  <LinearGradient
                    colors={[Accent.amethyst, '#EC4899']}
                    start={{ x: 0, y: 0 }}
                    end={{ x: 1, y: 0 }}
                    style={styles.submitGradient}
                  >
                    {saving ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <>
                        <MaterialCommunityIcons name={editingTxn ? 'check' : 'plus'} size={20} color="#fff" />
                        <Text style={styles.submitText}>{editingTxn ? 'Save Changes' : 'Add Transaction'}</Text>
                      </>
                    )}
                  </LinearGradient>
                </TouchableOpacity>

                {/* Delete Button (Edit Mode) */}
                {editingTxn && (
                  <TouchableOpacity
                    style={[styles.deleteBtn, { borderColor: colors.expense }]}
                    onPress={() => {
                      setShowModal(false);
                      setTimeout(() => handleDelete(editingTxn.id, editingTxn.description), 300);
                    }}
                  >
                    <MaterialCommunityIcons name="trash-can-outline" size={18} color={colors.expense} />
                    <Text style={[styles.deleteBtnText, { color: colors.expense }]}>Delete Transaction</Text>
                  </TouchableOpacity>
                )}

                <View style={{ height: 30 }} />
              </ScrollView>
            </View>
          </KeyboardAvoidingView>
        </View>
      </Modal>

      {/* Flagged Transactions Modal */}
      <FlaggedTransactionsModal
        visible={showFlaggedModal}
        onClose={() => setShowFlaggedModal(false)}
        onApproved={fetchTxns}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },

  // Source Toggle (Bank/UPI vs Credit Card)
  sourceToggleContainer: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 4,
    borderRadius: 14,
    borderWidth: 1,
  },
  sourceToggleBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: 10,
    gap: 6,
  },
  sourceToggleBtnActive: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  sourceToggleText: {
    fontSize: 13,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  ccBadge: {
    backgroundColor: '#8B5CF6',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 8,
    marginLeft: 4,
  },
  ccBadgeText: {
    fontSize: 10,
    fontFamily: 'DM Sans',
    fontWeight: '700' as any,
    color: '#fff',
  },

  // Flagged Transactions Bar
  flaggedBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginBottom: 12,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    gap: 10,
  },
  flaggedIcon: {
    width: 36,
    height: 36,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
  },
  flaggedContent: {
    flex: 1,
  },
  flaggedTitle: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  flaggedSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans',
    marginTop: 2,
  },

  // Sticky Header
  stickyHeader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
  },
  headerBlur: {
    borderBottomWidth: 1,
  },
  headerContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  headerLeft: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 22,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
    marginTop: 2,
  },
  headerActions: {
    flexDirection: 'row',
    gap: 8,
  },
  headerIconBtn: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchBar: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginBottom: 12,
    paddingHorizontal: 14,
    height: 44,
    borderRadius: 12,
    borderWidth: 1,
    gap: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    height: '100%',
  },

  // Scroll
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100,
  },

  // Filters
  filterSection: {
    paddingHorizontal: 16,
    marginBottom: 12,
  },
  filterPillsRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 8,
  },
  filterPill: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
  },
  filterPillText: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  categoryChipsRow: {
    flexDirection: 'row',
    gap: 8,
    paddingVertical: 4,
  },
  categoryChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    borderWidth: 1,
  },
  categoryChipText: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  clearFiltersBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    marginTop: 8,
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    backgroundColor: 'rgba(147, 51, 234, 0.08)',
  },
  clearFiltersText: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    color: Accent.amethyst,
  },

  // Summary Bar
  summaryBar: {
    flexDirection: 'row',
    marginHorizontal: 16,
    marginBottom: 16,
    paddingVertical: 14,
    borderRadius: 16,
    borderWidth: 1,
    justifyContent: 'space-around',
  },
  summaryItem: {
    alignItems: 'center',
  },
  summaryAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  summaryLabel: {
    fontSize: 11,
    marginTop: 2,
    textTransform: 'uppercase',
    letterSpacing: 0.3,
  },
  summaryDivider: {
    width: 1,
    height: 32,
  },

  // Loading Skeleton
  loadingContainer: {
    paddingHorizontal: 16,
  },
  skeletonCard: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderRadius: 16,
    marginBottom: 8,
    gap: 12,
  },
  skeletonIcon: {
    width: 46,
    height: 46,
    borderRadius: 14,
  },
  skeletonBody: {
    flex: 1,
    gap: 8,
  },
  skeletonLine: {
    height: 12,
    borderRadius: 6,
  },
  skeletonAmount: {
    width: 70,
    height: 18,
    borderRadius: 8,
  },

  // Empty State
  emptyState: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingTop: 80,
    paddingHorizontal: 40,
  },
  emptyIconWrap: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 20,
  },
  emptyTitle: {
    fontSize: 20,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    marginBottom: 8,
    textAlign: 'center',
  },
  emptySubtitle: {
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    marginBottom: 24,
  },
  emptyAddBtn: {
    borderRadius: 999,
    overflow: 'hidden',
  },
  emptyAddGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 24,
    paddingVertical: 14,
  },
  emptyAddText: {
    color: '#fff',
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  clearFiltersLargeBtn: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 12,
    backgroundColor: 'rgba(147, 51, 234, 0.1)',
  },
  clearFiltersLargeText: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
    color: Accent.amethyst,
  },

  // Date Header
  dateHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginTop: 4,
  },
  dateLabel: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  dateCount: {
    fontSize: 12,
  },

  // Transaction Card
  txnCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    padding: 14,
    borderRadius: 18,
    borderWidth: 1,
    marginBottom: 8,
    gap: 12,
  },
  txnIconWrap: {
    width: 48,
    height: 48,
    borderRadius: 14,
    justifyContent: 'center',
    alignItems: 'center',
  },
  txnContent: {
    flex: 1,
  },
  txnTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  txnMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginTop: 4,
    gap: 6,
  },
  txnCategory: {
    fontSize: 12,
  },
  txnDot: {
    fontSize: 12,
  },
  txnDate: {
    fontSize: 12,
  },
  txnBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 3,
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 6,
  },
  txnBadgeText: {
    fontSize: 10,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  txnAmountWrap: {
    alignItems: 'flex-end',
  },
  txnAmount: {
    fontSize: 16,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    letterSpacing: -0.3,
  },

  // FAB
  fab: {
    position: 'absolute',
    right: 20,
    bottom: 90,
    zIndex: 99999,
    borderRadius: 28,
    shadowColor: Accent.amethyst,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.4,
    shadowRadius: 12,
    elevation: 8,
    borderWidth: 2,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  fabGradient: {
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },

  // Modal
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'flex-end',
  },
  modalKav: {
    maxHeight: '90%',
  },
  modalContent: {
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    padding: 24,
    paddingBottom: 40,
  },
  modalHandle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#CBD5E1',
    alignSelf: 'center',
    marginBottom: 16,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  modalTitle: {
    fontSize: 22,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Type Selector
  typeSelector: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 20,
  },
  typeBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 14,
    borderRadius: 14,
    borderWidth: 1.5,
  },
  typeBtnText: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Form Fields
  fieldLabel: {
    fontSize: 12,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 8,
    marginTop: 4,
  },
  textInput: {
    height: 52,
    borderRadius: 14,
    borderWidth: 1,
    paddingHorizontal: 16,
    fontSize: 15,
    marginBottom: 14,
  },
  notesInput: {
    height: 80,
    paddingTop: 14,
    textAlignVertical: 'top',
  },
  taxHintBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
  },
  amountInputWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 60,
    borderRadius: 16,
    borderWidth: 1.5,
    paddingHorizontal: 16,
    marginBottom: 16,
  },
  rupeeSymbol: {
    fontSize: 26,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },
  amountInput: {
    flex: 1,
    fontSize: 30,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    paddingHorizontal: 8,
    height: '100%',
  },

  // Category Grid
  categoryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 16,
  },
  categoryOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
  },
  categoryOptionText: {
    fontSize: 13,
    fontFamily: 'DM Sans', fontWeight: '500' as any,
  },
  dropdownList: {
    borderWidth: 1,
    borderRadius: 14,
    marginBottom: 16,
    marginTop: -8,
    overflow: 'hidden',
  },
  dropdownItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 13,
    borderBottomWidth: 1,
  },
  suggestionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 6,
    marginBottom: 8,
  },
  suggestionChip: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 8,
    borderWidth: 1,
  },

  // Toggle Cards
  toggleCard: {
    borderRadius: 16,
    padding: 14,
    borderWidth: 1,
    marginBottom: 12,
  },
  toggleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  toggleIcon: {
    width: 40,
    height: 40,
    borderRadius: 12,
    justifyContent: 'center',
    alignItems: 'center',
  },
  toggleInfo: {
    flex: 1,
  },
  toggleTitle: {
    fontSize: 15,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  toggleDesc: {
    fontSize: 12,
    marginTop: 2,
  },
  freqRow: {
    marginTop: 12,
  },
  freqChip: {
    paddingHorizontal: 14,
    paddingVertical: 7,
    borderRadius: 16,
    borderWidth: 1,
    marginRight: 8,
  },

  // Split Section
  splitSection: {
    marginTop: 12,
    gap: 8,
  },
  splitRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  splitLabel: {
    fontSize: 13,
  },
  splitControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  splitBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  splitCount: {
    fontSize: 18,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
    minWidth: 28,
    textAlign: 'center',
  },
  splitResult: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Submit Button
  submitBtn: {
    borderRadius: 999,
    overflow: 'hidden',
    marginTop: 8,
  },
  submitGradient: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 56,
  },
  submitText: {
    color: '#fff',
    fontSize: 17,
    fontFamily: 'DM Sans', fontWeight: '700' as any,
  },

  // Delete Button
  deleteBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    height: 48,
    borderRadius: 14,
    borderWidth: 1.5,
    marginTop: 12,
  },
  deleteBtnText: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  
  // Buy/Sell Toggle for Investments
  buySellToggle: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 16,
  },
  buySellBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 12,
    borderWidth: 1.5,
  },
  buySellBtnActive: {
    borderWidth: 2,
  },
  buySellText: {
    fontSize: 14,
    fontFamily: 'DM Sans', fontWeight: '600' as any,
  },
  unitsRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  taxNote: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: 10,
    marginBottom: 16,
  },
  taxNoteText: {
    flex: 1,
    fontSize: 12,
    fontFamily: 'DM Sans',
    lineHeight: 16,
  },

  // Date Picker
  datePickerBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    height: 48,
    borderRadius: 12,
    borderWidth: 1,
    paddingHorizontal: 14,
    marginBottom: 12,
  },
  datePickerText: {
    flex: 1,
    fontSize: 15,
    fontFamily: 'DM Sans',
  },

  // iOS Date Modal
  dateModalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  dateModalContent: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 30,
  },
  dateModalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(0,0,0,0.08)',
  },
  dateModalTitle: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
  dateModalActionText: {
    fontSize: 16,
    fontFamily: 'DM Sans',
    fontWeight: '500' as any,
  },
  // Payment Mode Dropdown
  paymentDropdown: {
    borderRadius: 12,
    borderWidth: 1,
    marginTop: 4,
    marginBottom: 8,
    overflow: 'hidden',
  },
  paymentOption: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 14,
    paddingVertical: 12,
  },
  paymentOptionText: {
    fontSize: 14,
    fontFamily: 'DM Sans',
    fontWeight: '600' as any,
  },
});
