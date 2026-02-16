import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity, RefreshControl,
  ActivityIndicator, Dimensions, Platform, StatusBar, Animated, Modal,
  TextInput, KeyboardAvoidingView, Alert, Share,
} from 'react-native';
import { SafeAreaView, useSafeAreaInsets } from 'react-native-safe-area-context';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { useRouter } from 'expo-router';
import * as FileSystem from 'expo-file-system';
import * as Sharing from 'expo-sharing';

import { useAuth } from '../src/context/AuthContext';
import { useTheme } from '../src/context/ThemeContext';
import { apiRequest } from '../src/utils/api';
import { formatINR, formatINRShort } from '../src/utils/formatters';

const { width: SCREEN_WIDTH } = Dimensions.get('window');

type TabType = 'ledger' | 'pnl' | 'balance';

const ASSET_CATEGORIES = ['Property', 'Vehicle', 'Electronics', 'Furniture', 'Jewelry', 'Other'];

// Indian number formatting with brackets for negative
const formatINRIndian = (amount: number, showBrackets = true): string => {
  const isNegative = amount < 0;
  const absAmount = Math.abs(amount);
  const [whole, decimal] = absAmount.toFixed(2).split('.');
  const digits = whole.split('').reverse();
  let formatted = '';
  for (let i = 0; i < digits.length; i++) {
    if (i === 3 || (i > 3 && (i - 3) % 2 === 0)) {
      formatted = ',' + formatted;
    }
    formatted = digits[i] + formatted;
  }
  const result = `₹${formatted}.${decimal}`;
  if (isNegative && showBrackets) {
    return `(${result})`;
  }
  return isNegative ? `-${result}` : result;
};

// Format date as Indian format "01-Feb-2026"
const formatIndianDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const day = date.getDate().toString().padStart(2, '0');
  return `${day}-${months[date.getMonth()]}-${date.getFullYear()}`;
};

// Get Indian FY string
const getIndianFY = (date?: Date): string => {
  const d = date || new Date();
  const year = d.getMonth() < 3 ? d.getFullYear() - 1 : d.getFullYear();
  return `FY ${year}-${(year + 1).toString().slice(-2)}`;
};

// Get FY dates
const getFYDates = (fyYear?: number): { start: string; end: string } => {
  const now = new Date();
  if (!fyYear) {
    fyYear = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
  }
  return {
    start: `${fyYear}-04-01`,
    end: `${fyYear + 1}-03-31`,
  };
};

type LedgerData = {
  fy_start: string;
  fy_end: string;
  accounts: Record<string, {
    entries: Array<{
      date: string;
      particulars: string;
      voucher_ref: string;
      account: string;
      debit: number;
      credit: number;
      balance: number;
    }>;
    total_debit: number;
    total_credit: number;
    closing_balance: number;
  }>;
  entry_count: number;
};

type PnLData = {
  period_start: string;
  period_end: string;
  income_sections: Array<{
    id: string;
    name: string;
    items: Array<{ category: string; amount: number }>;
    subtotal: number;
  }>;
  expense_sections: Array<{
    id: string;
    name: string;
    items: Array<{ category: string; amount: number }>;
    subtotal: number;
  }>;
  total_income: number;
  total_expenses: number;
  total_investments: number;
  surplus_deficit: number;
  allocation: {
    to_savings: number;
    to_investments: number;
    retained: number;
  };
};

type BalanceSheetData = {
  as_of_date: string;
  assets: {
    non_current: any;
    current: any;
    total: number;
  };
  liabilities: {
    non_current: any;
    current: any;
    total: number;
  };
  net_worth: {
    opening: number;
    surplus_for_period: number;
    closing: number;
  };
  total_liabilities_and_net_worth: number;
  is_balanced: boolean;
};

type FixedAsset = {
  id: string;
  name: string;
  category: string;
  purchase_date: string;
  purchase_value: number;
  current_value: number;
  depreciation_rate: number;
  accumulated_depreciation: number;
  notes?: string;
};

type Loan = {
  id: string;
  name: string;
  loan_type: string;
  principal_amount: number;
  interest_rate: number;
  tenure_months: number;
  start_date: string;
  emi_amount: number;
  lender?: string;
  account_number?: string;
  notes?: string;
  outstanding_principal: number;
  total_principal_paid: number;
  total_interest_paid: number;
  remaining_emis: number;
};

type EMIScheduleItem = {
  month: number;
  date: string;
  opening_balance: number;
  emi: number;
  principal: number;
  interest: number;
  closing_balance: number;
  status: string;
};

const LOAN_TYPES = ['Home Loan', 'Car Loan', 'Personal Loan', 'Education Loan', 'Credit Card', 'Other'];

const DATE_PRESETS = [
  { label: 'Current Month', key: 'month' },
  { label: 'Current Quarter', key: 'quarter' },
  { label: 'Current FY', key: 'year' },
  { label: 'Previous FY', key: 'prev_year' },
  { label: 'Custom', key: 'custom' },
];

export default function BooksScreen() {
  const { token, user } = useAuth();
  const { colors, isDark } = useTheme();
  const router = useRouter();

  const [activeTab, setActiveTab] = useState<TabType>('ledger');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [exporting, setExporting] = useState(false);

  // Ledger state
  const [ledgerData, setLedgerData] = useState<LedgerData | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<string | null>(null);
  const [expandedAccounts, setExpandedAccounts] = useState<Set<string>>(new Set());

  // P&L state
  const [pnlData, setPnlData] = useState<PnLData | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [pnlPeriod, setPnlPeriod] = useState<'month' | 'quarter' | 'year' | 'custom'>('year');

  // Balance Sheet state
  const [balanceSheet, setBalanceSheet] = useState<BalanceSheetData | null>(null);

  // Fixed Assets state
  const [fixedAssets, setFixedAssets] = useState<FixedAsset[]>([]);
  const [showAssetModal, setShowAssetModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState<FixedAsset | null>(null);
  const [assetForm, setAssetForm] = useState({
    name: '',
    category: 'Property',
    purchase_date: '',
    purchase_value: '',
    current_value: '',
    depreciation_rate: '10',
    notes: '',
  });
  const [saving, setSaving] = useState(false);

  // Export modal
  const [showExportModal, setShowExportModal] = useState(false);

  // Loan state
  const [loans, setLoans] = useState<Loan[]>([]);
  const [showLoanModal, setShowLoanModal] = useState(false);
  const [editingLoan, setEditingLoan] = useState<Loan | null>(null);
  const [showEMISchedule, setShowEMISchedule] = useState<string | null>(null);
  const [emiSchedule, setEmiSchedule] = useState<EMIScheduleItem[]>([]);
  const [loanForm, setLoanForm] = useState({
    name: '',
    loan_type: 'Home Loan',
    principal_amount: '',
    interest_rate: '',
    tenure_months: '',
    start_date: '',
    emi_amount: '',
    lender: '',
    account_number: '',
    notes: '',
  });

  // Date range state
  const [datePreset, setDatePreset] = useState<string>('year');
  const [customStartDate, setCustomStartDate] = useState('');
  const [customEndDate, setCustomEndDate] = useState('');
  const [showDatePicker, setShowDatePicker] = useState(false);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  // Get date range based on preset
  const getDateRange = useCallback(() => {
    const now = new Date();
    const currentYear = now.getMonth() < 3 ? now.getFullYear() - 1 : now.getFullYear();
    
    switch (datePreset) {
      case 'month':
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
        const monthEnd = new Date(now.getFullYear(), now.getMonth() + 1, 0);
        return {
          start: monthStart.toISOString().split('T')[0],
          end: monthEnd.toISOString().split('T')[0],
        };
      case 'quarter':
        const quarterMonth = Math.floor(now.getMonth() / 3) * 3;
        const qStart = new Date(now.getFullYear(), quarterMonth, 1);
        const qEnd = new Date(now.getFullYear(), quarterMonth + 3, 0);
        return {
          start: qStart.toISOString().split('T')[0],
          end: qEnd.toISOString().split('T')[0],
        };
      case 'prev_year':
        return {
          start: `${currentYear - 1}-04-01`,
          end: `${currentYear}-03-31`,
        };
      case 'custom':
        return {
          start: customStartDate || `${currentYear}-04-01`,
          end: customEndDate || `${currentYear + 1}-03-31`,
        };
      case 'year':
      default:
        return getFYDates(currentYear);
    }
  }, [datePreset, customStartDate, customEndDate]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    try {
      const dateRange = getDateRange();
      const [ledger, pnl, bs, assets, loansData] = await Promise.all([
        apiRequest(`/books/ledger?start_date=${dateRange.start}&end_date=${dateRange.end}`, { token }),
        apiRequest(`/books/pnl?start_date=${dateRange.start}&end_date=${dateRange.end}`, { token }),
        apiRequest('/books/balance-sheet', { token }),
        apiRequest('/assets', { token }),
        apiRequest('/loans', { token }),
      ]);
      setLedgerData(ledger);
      setPnlData(pnl);
      setBalanceSheet(bs);
      setFixedAssets(assets || []);
      setLoans(loansData || []);
    } catch (e) {
      console.error('Error fetching books data:', e);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, getDateRange]);

  useEffect(() => {
    fetchData();
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, [fetchData, fadeAnim]);

  // Refetch when date preset changes
  useEffect(() => {
    if (!loading) {
      fetchData();
    }
  }, [datePreset, customStartDate, customEndDate]);

  const onRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const toggleAccountExpand = (account: string) => {
    setExpandedAccounts(prev => {
      const next = new Set(prev);
      if (next.has(account)) {
        next.delete(account);
      } else {
        next.add(account);
      }
      return next;
    });
  };

  const toggleSectionExpand = (sectionId: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(sectionId)) {
        next.delete(sectionId);
      } else {
        next.add(sectionId);
      }
      return next;
    });
  };

  const handleSaveAsset = async () => {
    if (!assetForm.name || !assetForm.purchase_value) {
      Alert.alert('Error', 'Please fill in required fields');
      return;
    }
    
    setSaving(true);
    try {
      const data = {
        name: assetForm.name,
        category: assetForm.category,
        purchase_date: assetForm.purchase_date || new Date().toISOString().split('T')[0],
        purchase_value: parseFloat(assetForm.purchase_value),
        current_value: parseFloat(assetForm.current_value || assetForm.purchase_value),
        depreciation_rate: parseFloat(assetForm.depreciation_rate || '10'),
        notes: assetForm.notes || null,
      };
      
      if (editingAsset) {
        await apiRequest(`/assets/${editingAsset.id}`, { method: 'PUT', body: data, token });
      } else {
        await apiRequest('/assets', { method: 'POST', body: data, token });
      }
      
      setShowAssetModal(false);
      setEditingAsset(null);
      setAssetForm({ name: '', category: 'Property', purchase_date: '', purchase_value: '', current_value: '', depreciation_rate: '10', notes: '' });
      fetchData();
    } catch (e) {
      Alert.alert('Error', 'Failed to save asset');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    Alert.alert('Delete Asset', 'Are you sure you want to delete this asset?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest(`/assets/${assetId}`, { method: 'DELETE', token });
            fetchData();
          } catch (e) {
            Alert.alert('Error', 'Failed to delete asset');
          }
        },
      },
    ]);
  };

  // Loan management functions
  const handleSaveLoan = async () => {
    if (!loanForm.name || !loanForm.principal_amount || !loanForm.interest_rate || !loanForm.tenure_months) {
      Alert.alert('Error', 'Please fill in all required fields');
      return;
    }
    
    setSaving(true);
    try {
      const data = {
        name: loanForm.name,
        loan_type: loanForm.loan_type,
        principal_amount: parseFloat(loanForm.principal_amount),
        interest_rate: parseFloat(loanForm.interest_rate),
        tenure_months: parseInt(loanForm.tenure_months),
        start_date: loanForm.start_date || new Date().toISOString().split('T')[0],
        emi_amount: loanForm.emi_amount ? parseFloat(loanForm.emi_amount) : null,
        lender: loanForm.lender || null,
        account_number: loanForm.account_number || null,
        notes: loanForm.notes || null,
      };
      
      if (editingLoan) {
        await apiRequest(`/loans/${editingLoan.id}`, { method: 'PUT', body: data, token });
      } else {
        await apiRequest('/loans', { method: 'POST', body: data, token });
      }
      
      setShowLoanModal(false);
      setEditingLoan(null);
      setLoanForm({
        name: '', loan_type: 'Home Loan', principal_amount: '', interest_rate: '',
        tenure_months: '', start_date: '', emi_amount: '', lender: '', account_number: '', notes: '',
      });
      fetchData();
    } catch (e) {
      Alert.alert('Error', 'Failed to save loan');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteLoan = async (loanId: string) => {
    Alert.alert('Delete Loan', 'Are you sure you want to delete this loan?', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await apiRequest(`/loans/${loanId}`, { method: 'DELETE', token });
            fetchData();
          } catch (e) {
            Alert.alert('Error', 'Failed to delete loan');
          }
        },
      },
    ]);
  };

  const viewEMISchedule = async (loanId: string) => {
    try {
      const loanDetail = await apiRequest(`/loans/${loanId}`, { token });
      setEmiSchedule(loanDetail.emi_schedule || []);
      setShowEMISchedule(loanId);
    } catch (e) {
      Alert.alert('Error', 'Failed to load EMI schedule');
    }
  };

  const handleExport = async (format: 'csv' | 'json' | 'excel' | 'pdf') => {
    setExporting(true);
    try {
      const dateRange = getDateRange();
      let filename = `Visor_${activeTab === 'ledger' ? 'Ledger' : activeTab === 'pnl' ? 'PnL' : 'BalanceSheet'}_${new Date().toISOString().split('T')[0]}`;
      
      if (format === 'excel' || format === 'pdf') {
        // Call backend API for Excel/PDF export
        const response = await fetch(
          `${process.env.EXPO_PUBLIC_BACKEND_URL}/api/books/export/${activeTab === 'balance' ? 'balance' : activeTab}/${format}?start_date=${dateRange.start}&end_date=${dateRange.end}`,
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
        
        if (!response.ok) {
          throw new Error('Export failed');
        }
        
        // For mobile: download and share
        if (Platform.OS !== 'web') {
          const blob = await response.blob();
          const fileUri = FileSystem.documentDirectory + filename + (format === 'excel' ? '.xlsx' : '.pdf');
          
          // Convert blob to base64
          const reader = new FileReader();
          reader.onload = async () => {
            const base64 = (reader.result as string).split(',')[1];
            await FileSystem.writeAsStringAsync(fileUri, base64, { encoding: 'base64' });
            
            if (await Sharing.isAvailableAsync()) {
              await Sharing.shareAsync(fileUri, {
                mimeType: format === 'excel' 
                  ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' 
                  : 'application/pdf',
                dialogTitle: `Share ${activeTab === 'ledger' ? 'Ledger' : activeTab === 'pnl' ? 'P&L' : 'Balance Sheet'}`,
              });
            } else {
              Alert.alert('Success', `File saved as ${filename}.${format === 'excel' ? 'xlsx' : 'pdf'}`);
            }
            setExporting(false);
            setShowExportModal(false);
          };
          reader.readAsDataURL(blob);
        } else {
          // For web: use browser download
          const blob = await response.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = filename + (format === 'excel' ? '.xlsx' : '.pdf');
          document.body.appendChild(a);
          a.click();
          document.body.removeChild(a);
          URL.revokeObjectURL(url);
          setExporting(false);
          setShowExportModal(false);
          Alert.alert('Success', `Downloaded ${filename}.${format === 'excel' ? 'xlsx' : 'pdf'}`);
        }
        return;
      }
      
      // CSV and JSON exports (handled locally)
      let content = '';
      
      if (format === 'csv') {
        // Enhanced CSV export with proper formatting
        const disclaimer = `"Generated by Visor Finance App"\n"Report Date: ${new Date().toLocaleDateString('en-IN')}"\n"Period: ${dateRange.start} to ${dateRange.end}"\n\n`;
        
        if (activeTab === 'ledger' && ledgerData) {
          content = disclaimer + 'Date,Particulars,Voucher Ref,Account,Debit (₹),Credit (₹),Balance (₹)\n';
          Object.entries(ledgerData.accounts).forEach(([account, data]) => {
            content += `\n"${account}"\n`;
            data.entries.forEach(entry => {
              content += `${entry.date},"${entry.particulars}",${entry.voucher_ref},"${entry.account}",${entry.debit.toFixed(2)},${entry.credit.toFixed(2)},${entry.balance.toFixed(2)}\n`;
            });
            content += `"Closing Balance",,,,"${data.total_debit.toFixed(2)}","${data.total_credit.toFixed(2)}","${data.closing_balance.toFixed(2)}"\n`;
          });
        } else if (activeTab === 'pnl' && pnlData) {
          content = disclaimer + '"INCOME & EXPENDITURE STATEMENT"\n\n';
          content += '"INCOME"\n';
          content += 'Section,Category,Amount (₹)\n';
          pnlData.income_sections.forEach(section => {
            content += `\n"${section.id}. ${section.name}"\n`;
            section.items.forEach(item => {
              content += `,"${item.category}",${item.amount.toFixed(2)}\n`;
            });
            content += `"Sub-total",,${section.subtotal.toFixed(2)}\n`;
          });
          content += `\n"TOTAL INCOME",,${pnlData.total_income.toFixed(2)}\n\n`;
          
          content += '"EXPENDITURE"\n';
          pnlData.expense_sections.forEach(section => {
            content += `\n"${section.id}. ${section.name}"\n`;
            section.items.forEach(item => {
              content += `,"${item.category}",${item.amount.toFixed(2)}\n`;
            });
            content += `"Sub-total",,${section.subtotal.toFixed(2)}\n`;
          });
          content += `\n"TOTAL EXPENDITURE",,${pnlData.total_expenses.toFixed(2)}\n\n`;
          content += `"${pnlData.surplus_deficit >= 0 ? 'SURPLUS' : 'DEFICIT'} FOR THE PERIOD",,${Math.abs(pnlData.surplus_deficit).toFixed(2)}\n`;
        } else if (activeTab === 'balance' && balanceSheet) {
          content = disclaimer + '"STATEMENT OF FINANCIAL POSITION (BALANCE SHEET)"\n';
          content += `"As at ${balanceSheet.as_of_date}"\n\n`;
          
          content += '"I. ASSETS"\n';
          content += '"(1) Non-Current Assets"\n';
          content += `"Fixed Assets (Net)",${balanceSheet.assets.non_current.fixed_assets.net_value.toFixed(2)}\n`;
          content += `"Long-term Investments",${balanceSheet.assets.non_current.long_term_investments.total.toFixed(2)}\n`;
          content += `"Total Non-Current Assets",${balanceSheet.assets.non_current.total.toFixed(2)}\n\n`;
          
          content += '"(2) Current Assets"\n';
          content += `"Short-term Investments",${balanceSheet.assets.current.short_term_investments.total.toFixed(2)}\n`;
          content += `"Cash & Bank Balances",${balanceSheet.assets.current.cash_bank.total.toFixed(2)}\n`;
          content += `"Total Current Assets",${balanceSheet.assets.current.total.toFixed(2)}\n\n`;
          
          content += `"TOTAL ASSETS",${balanceSheet.assets.total.toFixed(2)}\n\n`;
          
          content += '"II. LIABILITIES"\n';
          content += `"Long-term Borrowings",${balanceSheet.liabilities.non_current.total.toFixed(2)}\n`;
          content += `"Current Liabilities",${balanceSheet.liabilities.current.total.toFixed(2)}\n`;
          content += `"TOTAL LIABILITIES",${balanceSheet.liabilities.total.toFixed(2)}\n\n`;
          
          content += '"III. NET WORTH"\n';
          content += `"Closing Net Worth",${balanceSheet.net_worth.closing.toFixed(2)}\n\n`;
          
          content += `"LIABILITIES + NET WORTH",${balanceSheet.total_liabilities_and_net_worth.toFixed(2)}\n`;
          content += `\n"Balance Sheet ${balanceSheet.is_balanced ? 'BALANCED ✓' : 'DISCREPANCY ✗'}"\n`;
        }
        filename += '.csv';
      } else if (format === 'json') {
        const exportData = {
          report_type: activeTab,
          generated_at: new Date().toISOString(),
          period: dateRange,
          user: user?.full_name,
          data: activeTab === 'ledger' ? ledgerData : activeTab === 'pnl' ? pnlData : balanceSheet,
        };
        content = JSON.stringify(exportData, null, 2);
        filename += '.json';
      }
      
      // Write file and share
      const fileUri = FileSystem.documentDirectory + filename;
      await FileSystem.writeAsStringAsync(fileUri, content, { encoding: FileSystem.EncodingType.UTF8 });
      
      if (await Sharing.isAvailableAsync()) {
        await Sharing.shareAsync(fileUri, {
          mimeType: format === 'json' ? 'application/json' : 'text/csv',
          dialogTitle: `Share ${activeTab === 'ledger' ? 'Ledger' : activeTab === 'pnl' ? 'P&L' : 'Balance Sheet'}`,
        });
      } else {
        Alert.alert('Success', `File saved as ${filename}`);
      }
    } catch (e) {
      console.error('Export error:', e);
      Alert.alert('Error', 'Failed to export data. Please try again.');
    } finally {
      setExporting(false);
      setShowExportModal(false);
    }
  };

  const styles = StyleSheet.create({
    container: {
      flex: 1,
      backgroundColor: colors.background,
    },
    header: {
      paddingHorizontal: 20,
      paddingTop: Platform.OS === 'android' ? StatusBar.currentHeight || 20 : 0,
      paddingBottom: 16,
    },
    headerContent: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
    },
    backButton: {
      padding: 8,
      borderRadius: 12,
      backgroundColor: colors.surface + '80',
    },
    headerTitle: {
      fontSize: 24,
      fontWeight: '700',
      color: colors.textPrimary,
    },
    headerSubtitle: {
      fontSize: 14,
      color: colors.textSecondary,
      marginTop: 4,
    },
    exportButton: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingHorizontal: 16,
      paddingVertical: 10,
      borderRadius: 12,
      backgroundColor: colors.primary,
    },
    exportButtonText: {
      color: '#FFF',
      fontWeight: '600',
      marginLeft: 6,
    },
    tabsContainer: {
      flexDirection: 'row',
      paddingHorizontal: 16,
      marginBottom: 16,
      gap: 8,
    },
    tab: {
      flex: 1,
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      paddingVertical: 12,
      paddingHorizontal: 12,
      borderRadius: 12,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
    },
    tabActive: {
      backgroundColor: colors.primary + '15',
      borderColor: colors.primary,
    },
    tabText: {
      fontSize: 13,
      fontWeight: '600',
      color: colors.textSecondary,
      marginLeft: 6,
    },
    tabTextActive: {
      color: colors.primary,
    },
    content: {
      flex: 1,
    },
    section: {
      marginHorizontal: 16,
      marginBottom: 16,
      borderRadius: 16,
      backgroundColor: colors.surface,
      overflow: 'hidden',
      borderWidth: 1,
      borderColor: colors.border,
    },
    sectionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 16,
      paddingVertical: 14,
      backgroundColor: colors.surface,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    sectionTitle: {
      fontSize: 16,
      fontWeight: '700',
      color: colors.textPrimary,
    },
    sectionSubtitle: {
      fontSize: 13,
      color: colors.textSecondary,
      marginTop: 2,
    },
    // Ledger specific styles
    accountGroup: {
      marginHorizontal: 16,
      marginBottom: 12,
    },
    accountGroupHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingVertical: 12,
      paddingHorizontal: 16,
      backgroundColor: colors.surface,
      borderRadius: 12,
      borderWidth: 1,
      borderColor: colors.border,
    },
    accountGroupTitle: {
      fontSize: 15,
      fontWeight: '600',
      color: colors.textPrimary,
    },
    accountGroupBalance: {
      fontSize: 14,
      fontWeight: '700',
      color: colors.primary,
    },
    ledgerTable: {
      marginTop: 8,
      borderRadius: 8,
      overflow: 'hidden',
      backgroundColor: colors.background,
    },
    tableHeader: {
      flexDirection: 'row',
      backgroundColor: isDark ? colors.surface : '#F1F5F9',
      paddingVertical: 10,
      paddingHorizontal: 12,
    },
    tableHeaderText: {
      fontSize: 11,
      fontWeight: '700',
      color: colors.textSecondary,
      textTransform: 'uppercase',
    },
    tableRow: {
      flexDirection: 'row',
      paddingVertical: 10,
      paddingHorizontal: 12,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    tableRowAlt: {
      backgroundColor: isDark ? colors.surface + '50' : '#F8FAFC',
    },
    tableCell: {
      fontSize: 12,
      color: colors.textPrimary,
    },
    tableCellBold: {
      fontWeight: '700',
    },
    // P&L specific styles
    pnlSection: {
      marginBottom: 16,
    },
    pnlSectionHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingVertical: 14,
      paddingHorizontal: 16,
      backgroundColor: colors.surface,
      borderRadius: 12,
      borderLeftWidth: 4,
    },
    pnlSectionTitle: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.textPrimary,
    },
    pnlSectionSubtotal: {
      fontSize: 15,
      fontWeight: '700',
    },
    pnlItem: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingVertical: 10,
      paddingHorizontal: 20,
      borderBottomWidth: 1,
      borderBottomColor: colors.border + '50',
    },
    pnlItemText: {
      fontSize: 13,
      color: colors.textSecondary,
    },
    pnlItemAmount: {
      fontSize: 13,
      fontWeight: '500',
      color: colors.textPrimary,
    },
    pnlTotal: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingVertical: 16,
      paddingHorizontal: 16,
      backgroundColor: isDark ? colors.surface : '#F1F5F9',
      marginTop: 8,
      borderRadius: 12,
      borderWidth: 2,
      borderColor: colors.border,
    },
    pnlTotalText: {
      fontSize: 15,
      fontWeight: '700',
      color: colors.textPrimary,
    },
    pnlTotalAmount: {
      fontSize: 16,
      fontWeight: '800',
    },
    surplusBox: {
      marginHorizontal: 16,
      marginVertical: 16,
      padding: 20,
      borderRadius: 16,
      borderWidth: 2,
    },
    surplusTitle: {
      fontSize: 14,
      fontWeight: '600',
      marginBottom: 4,
    },
    surplusAmount: {
      fontSize: 24,
      fontWeight: '800',
    },
    // Balance Sheet styles
    bsCategory: {
      marginBottom: 16,
    },
    bsCategoryHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: 12,
      paddingHorizontal: 16,
      backgroundColor: colors.surface,
      borderRadius: 12,
      borderLeftWidth: 4,
    },
    bsCategoryTitle: {
      fontSize: 16,
      fontWeight: '700',
      color: colors.textPrimary,
      flex: 1,
    },
    bsCategoryTotal: {
      fontSize: 15,
      fontWeight: '700',
    },
    bsSubSection: {
      marginTop: 8,
      marginLeft: 16,
      paddingLeft: 12,
      borderLeftWidth: 2,
      borderLeftColor: colors.border,
    },
    bsSubTitle: {
      fontSize: 13,
      fontWeight: '600',
      color: colors.textSecondary,
      marginBottom: 8,
    },
    bsItem: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      paddingVertical: 8,
    },
    bsItemText: {
      fontSize: 13,
      color: colors.textPrimary,
    },
    bsItemAmount: {
      fontSize: 13,
      fontWeight: '500',
      color: colors.textPrimary,
    },
    balanceBadge: {
      flexDirection: 'row',
      alignItems: 'center',
      alignSelf: 'center',
      paddingHorizontal: 16,
      paddingVertical: 8,
      borderRadius: 20,
      marginBottom: 16,
    },
    balanceBadgeText: {
      fontSize: 14,
      fontWeight: '600',
      marginLeft: 6,
    },
    // Asset styles
    assetCard: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    assetIcon: {
      width: 44,
      height: 44,
      borderRadius: 12,
      alignItems: 'center',
      justifyContent: 'center',
      marginRight: 12,
    },
    assetInfo: {
      flex: 1,
    },
    assetName: {
      fontSize: 15,
      fontWeight: '600',
      color: colors.textPrimary,
    },
    assetCategory: {
      fontSize: 12,
      color: colors.textSecondary,
      marginTop: 2,
    },
    assetValue: {
      alignItems: 'flex-end',
    },
    assetCurrentValue: {
      fontSize: 15,
      fontWeight: '700',
      color: colors.textPrimary,
    },
    assetDepreciation: {
      fontSize: 11,
      color: colors.error,
      marginTop: 2,
    },
    addAssetButton: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 16,
      gap: 8,
    },
    addAssetText: {
      fontSize: 14,
      fontWeight: '600',
      color: colors.primary,
    },
    // Modal styles
    modalOverlay: {
      flex: 1,
      backgroundColor: isDark ? 'rgba(0,0,0,0.85)' : 'rgba(0,0,0,0.5)',
      justifyContent: 'flex-end',
    },
    modalContent: {
      backgroundColor: isDark ? '#1E293B' : '#FFFFFF',
      borderTopLeftRadius: 24,
      borderTopRightRadius: 24,
      paddingTop: 20,
      maxHeight: '90%',
    },
    modalHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingHorizontal: 20,
      paddingBottom: 16,
      borderBottomWidth: 1,
      borderBottomColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
    },
    modalTitle: {
      fontSize: 18,
      fontWeight: '700',
      color: isDark ? '#F8FAFC' : '#1E293B',
    },
    modalBody: {
      padding: 20,
    },
    inputLabel: {
      fontSize: 13,
      fontWeight: '600',
      color: isDark ? '#94A3B8' : '#64748B',
      marginBottom: 8,
      marginTop: 16,
    },
    input: {
      backgroundColor: isDark ? '#0F172A' : '#F8FAFC',
      borderRadius: 12,
      paddingHorizontal: 16,
      paddingVertical: 14,
      fontSize: 16,
      color: isDark ? '#F8FAFC' : '#1E293B',
      borderWidth: 1,
      borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
    },
    categoryPicker: {
      flexDirection: 'row',
      flexWrap: 'wrap',
      gap: 8,
    },
    categoryChip: {
      paddingHorizontal: 14,
      paddingVertical: 8,
      borderRadius: 20,
      backgroundColor: isDark ? '#0F172A' : '#F1F5F9',
      borderWidth: 1,
      borderColor: isDark ? 'rgba(255,255,255,0.15)' : 'rgba(0,0,0,0.1)',
    },
    categoryChipActive: {
      backgroundColor: isDark ? 'rgba(16,185,129,0.2)' : 'rgba(16,185,129,0.1)',
      borderColor: '#10B981',
    },
    categoryChipText: {
      fontSize: 13,
      color: isDark ? '#94A3B8' : '#64748B',
    },
    categoryChipTextActive: {
      color: '#10B981',
      fontWeight: '600',
    },
    saveButton: {
      backgroundColor: colors.primary,
      borderRadius: 12,
      paddingVertical: 16,
      alignItems: 'center',
      marginTop: 24,
    },
    saveButtonText: {
      color: '#FFF',
      fontSize: 16,
      fontWeight: '700',
    },
    // Export modal styles
    exportOption: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: 16,
      paddingHorizontal: 20,
      borderBottomWidth: 1,
      borderBottomColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
    },
    exportOptionIcon: {
      width: 48,
      height: 48,
      borderRadius: 12,
      alignItems: 'center',
      justifyContent: 'center',
      marginRight: 16,
    },
    exportOptionTitle: {
      fontSize: 16,
      fontWeight: '600',
      color: isDark ? '#F8FAFC' : '#1E293B',
    },
    exportOptionDesc: {
      fontSize: 12,
      color: isDark ? '#94A3B8' : '#64748B',
      marginTop: 2,
    },
    emptyState: {
      alignItems: 'center',
      paddingVertical: 40,
    },
    emptyStateText: {
      fontSize: 15,
      color: colors.textSecondary,
      marginTop: 12,
    },
    fyInfo: {
      flexDirection: 'row',
      alignItems: 'center',
      justifyContent: 'center',
      paddingVertical: 8,
      paddingHorizontal: 16,
      backgroundColor: colors.primary + '10',
      borderRadius: 8,
      marginHorizontal: 16,
      marginBottom: 16,
    },
    fyInfoText: {
      fontSize: 13,
      color: colors.primary,
      fontWeight: '600',
      marginLeft: 8,
    },
    // Date range selector styles
    dateSelector: {
      flexDirection: 'row',
      paddingHorizontal: 16,
      marginBottom: 12,
      gap: 6,
    },
    dateSelectorChip: {
      paddingHorizontal: 12,
      paddingVertical: 6,
      borderRadius: 16,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
    },
    dateSelectorChipActive: {
      backgroundColor: colors.primary + '20',
      borderColor: colors.primary,
    },
    dateSelectorChipText: {
      fontSize: 12,
      color: colors.textSecondary,
    },
    dateSelectorChipTextActive: {
      color: colors.primary,
      fontWeight: '600',
    },
    // Loan styles
    loanCard: {
      marginHorizontal: 16,
      marginBottom: 12,
      borderRadius: 16,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      overflow: 'hidden',
    },
    loanCardHeader: {
      flexDirection: 'row',
      alignItems: 'center',
      padding: 16,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    loanIcon: {
      width: 48,
      height: 48,
      borderRadius: 12,
      alignItems: 'center',
      justifyContent: 'center',
      marginRight: 12,
    },
    loanInfo: {
      flex: 1,
    },
    loanName: {
      fontSize: 16,
      fontWeight: '600',
      color: colors.textPrimary,
    },
    loanType: {
      fontSize: 12,
      color: colors.textSecondary,
      marginTop: 2,
    },
    loanAmount: {
      alignItems: 'flex-end',
    },
    loanOutstanding: {
      fontSize: 16,
      fontWeight: '700',
      color: colors.error,
    },
    loanEMI: {
      fontSize: 11,
      color: colors.textSecondary,
      marginTop: 2,
    },
    loanDetails: {
      padding: 16,
      backgroundColor: isDark ? colors.background : '#F8FAFC',
    },
    loanDetailRow: {
      flexDirection: 'row',
      justifyContent: 'space-between',
      marginBottom: 8,
    },
    loanDetailLabel: {
      fontSize: 13,
      color: colors.textSecondary,
    },
    loanDetailValue: {
      fontSize: 13,
      fontWeight: '500',
      color: colors.textPrimary,
    },
    loanActions: {
      flexDirection: 'row',
      justifyContent: 'flex-end',
      paddingTop: 12,
      borderTopWidth: 1,
      borderTopColor: colors.border,
      gap: 12,
    },
    loanActionBtn: {
      flexDirection: 'row',
      alignItems: 'center',
      paddingVertical: 8,
      paddingHorizontal: 12,
      borderRadius: 8,
      backgroundColor: colors.primary + '10',
    },
    loanActionText: {
      fontSize: 13,
      fontWeight: '600',
      color: colors.primary,
      marginLeft: 4,
    },
    // EMI Schedule styles
    emiScheduleContainer: {
      marginHorizontal: 16,
      marginTop: 12,
      borderRadius: 12,
      backgroundColor: colors.surface,
      borderWidth: 1,
      borderColor: colors.border,
      maxHeight: 300,
    },
    emiScheduleHeader: {
      flexDirection: 'row',
      backgroundColor: isDark ? colors.surface : '#F1F5F9',
      paddingVertical: 10,
      paddingHorizontal: 12,
      borderBottomWidth: 1,
      borderBottomColor: colors.border,
    },
    emiRow: {
      flexDirection: 'row',
      paddingVertical: 10,
      paddingHorizontal: 12,
      borderBottomWidth: 1,
      borderBottomColor: colors.border + '50',
    },
    emiRowPaid: {
      backgroundColor: '#10B981' + '10',
    },
    emiRowCurrent: {
      backgroundColor: '#F59E0B' + '20',
    },
    emiCell: {
      fontSize: 11,
      color: colors.textPrimary,
    },
    emiCellBold: {
      fontWeight: '600',
    },
  });

  const renderLedgerTab = () => {
    if (!ledgerData) return null;
    const accounts = Object.entries(ledgerData.accounts);
    
    if (accounts.length === 0) {
      return (
        <View style={styles.emptyState}>
          <MaterialCommunityIcons name="book-open-variant" size={48} color={colors.textSecondary} />
          <Text style={styles.emptyStateText}>No ledger entries found</Text>
        </View>
      );
    }

    // Group accounts by type
    const assetAccounts = accounts.filter(([name]) => name.includes('Cash') || name.includes('Bank') || name.includes('Investment'));
    const expenseAccounts = accounts.filter(([name]) => !name.includes('Income') && !name.includes('Cash') && !name.includes('Bank') && !name.includes('Investment'));
    const incomeAccounts = accounts.filter(([name]) => name.includes('Income'));

    const renderAccountGroup = (title: string, accountList: typeof accounts, color: string) => {
      if (accountList.length === 0) return null;
      
      return (
        <View style={styles.accountGroup}>
          <View style={[styles.sectionHeader, { borderLeftWidth: 4, borderLeftColor: color, borderRadius: 12 }]}>
            <Text style={styles.sectionTitle}>{title}</Text>
          </View>
          {accountList.map(([accountName, data], idx) => (
            <View key={accountName}>
              <TouchableOpacity
                style={[styles.accountGroupHeader, { marginTop: 8 }]}
                onPress={() => toggleAccountExpand(accountName)}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <MaterialCommunityIcons
                    name={expandedAccounts.has(accountName) ? 'chevron-down' : 'chevron-right'}
                    size={20}
                    color={colors.textSecondary}
                  />
                  <Text style={[styles.accountGroupTitle, { marginLeft: 8 }]}>{accountName}</Text>
                </View>
                <Text style={styles.accountGroupBalance}>
                  {formatINRIndian(data.closing_balance)}
                </Text>
              </TouchableOpacity>
              
              {expandedAccounts.has(accountName) && (
                <View style={styles.ledgerTable}>
                  <View style={styles.tableHeader}>
                    <Text style={[styles.tableHeaderText, { width: 70 }]}>Date</Text>
                    <Text style={[styles.tableHeaderText, { flex: 1 }]}>Particulars</Text>
                    <Text style={[styles.tableHeaderText, { width: 65, textAlign: 'right' }]}>Debit</Text>
                    <Text style={[styles.tableHeaderText, { width: 65, textAlign: 'right' }]}>Credit</Text>
                    <Text style={[styles.tableHeaderText, { width: 70, textAlign: 'right' }]}>Balance</Text>
                  </View>
                  {data.entries.slice(0, 20).map((entry, i) => (
                    <View key={i} style={[styles.tableRow, i % 2 === 1 && styles.tableRowAlt]}>
                      <Text style={[styles.tableCell, { width: 70 }]}>{formatIndianDate(entry.date).slice(0, 6)}</Text>
                      <Text style={[styles.tableCell, { flex: 1 }]} numberOfLines={1}>{entry.particulars}</Text>
                      <Text style={[styles.tableCell, { width: 65, textAlign: 'right' }]}>
                        {entry.debit > 0 ? formatINRShort(entry.debit) : '-'}
                      </Text>
                      <Text style={[styles.tableCell, { width: 65, textAlign: 'right' }]}>
                        {entry.credit > 0 ? formatINRShort(entry.credit) : '-'}
                      </Text>
                      <Text style={[styles.tableCell, styles.tableCellBold, { width: 70, textAlign: 'right' }]}>
                        {formatINRShort(entry.balance)}
                      </Text>
                    </View>
                  ))}
                  <View style={[styles.tableRow, { backgroundColor: isDark ? colors.primary + '20' : '#E8F5E9' }]}>
                    <Text style={[styles.tableCell, styles.tableCellBold, { flex: 1 }]}>Closing Balance</Text>
                    <Text style={[styles.tableCell, styles.tableCellBold, { width: 65, textAlign: 'right' }]}>
                      {formatINRShort(data.total_debit)}
                    </Text>
                    <Text style={[styles.tableCell, styles.tableCellBold, { width: 65, textAlign: 'right' }]}>
                      {formatINRShort(data.total_credit)}
                    </Text>
                    <Text style={[styles.tableCell, styles.tableCellBold, { width: 70, textAlign: 'right', color: colors.primary }]}>
                      {formatINRShort(data.closing_balance)}
                    </Text>
                  </View>
                </View>
              )}
            </View>
          ))}
        </View>
      );
    };

    return (
      <ScrollView showsVerticalScrollIndicator={false}>
        <View style={styles.fyInfo}>
          <MaterialCommunityIcons name="calendar" size={16} color={colors.primary} />
          <Text style={styles.fyInfoText}>
            {getIndianFY()} ({formatIndianDate(ledgerData.fy_start)} to {formatIndianDate(ledgerData.fy_end)})
          </Text>
        </View>
        
        {renderAccountGroup('Assets', assetAccounts, '#10B981')}
        {renderAccountGroup('Income', incomeAccounts, '#3B82F6')}
        {renderAccountGroup('Expenses', expenseAccounts, '#EF4444')}
        
        <View style={{ height: 100 }} />
      </ScrollView>
    );
  };

  const renderPnLTab = () => {
    if (!pnlData) return null;

    const sectionColors: Record<string, string> = {
      'A': '#10B981', 'B': '#3B82F6', 'C': '#8B5CF6', 'D': '#F59E0B',
      'E': '#EF4444', 'F': '#DC2626', 'G': '#7C3AED', 'H': '#06B6D4', 'I': '#6B7280',
    };

    return (
      <ScrollView showsVerticalScrollIndicator={false} style={{ paddingHorizontal: 16 }}>
        <View style={styles.fyInfo}>
          <MaterialCommunityIcons name="calendar-range" size={16} color={colors.primary} />
          <Text style={styles.fyInfoText}>
            Period: {formatIndianDate(pnlData.period_start)} to {formatIndianDate(pnlData.period_end)}
          </Text>
        </View>

        {/* Income Section */}
        <View style={[styles.section, { marginHorizontal: 0 }]}>
          <View style={styles.sectionHeader}>
            <View>
              <Text style={styles.sectionTitle}>INCOME</Text>
              <Text style={styles.sectionSubtitle}>Revenue & Earnings</Text>
            </View>
            <Text style={[styles.sectionTitle, { color: '#10B981' }]}>{formatINRIndian(pnlData.total_income)}</Text>
          </View>
          
          {pnlData.income_sections.map(section => (
            <View key={section.id} style={styles.pnlSection}>
              <TouchableOpacity
                style={[styles.pnlSectionHeader, { borderLeftColor: sectionColors[section.id] || '#10B981' }]}
                onPress={() => toggleSectionExpand(section.id)}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <MaterialCommunityIcons
                    name={expandedSections.has(section.id) ? 'chevron-down' : 'chevron-right'}
                    size={18}
                    color={colors.textSecondary}
                  />
                  <Text style={[styles.pnlSectionTitle, { marginLeft: 8 }]}>{section.id}. {section.name}</Text>
                </View>
                <Text style={[styles.pnlSectionSubtotal, { color: sectionColors[section.id] || '#10B981' }]}>
                  {formatINRIndian(section.subtotal)}
                </Text>
              </TouchableOpacity>
              
              {expandedSections.has(section.id) && section.items.map((item, i) => (
                <View key={i} style={styles.pnlItem}>
                  <Text style={styles.pnlItemText}>{item.category}</Text>
                  <Text style={styles.pnlItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              ))}
            </View>
          ))}
        </View>

        {/* Expense Section */}
        <View style={[styles.section, { marginHorizontal: 0 }]}>
          <View style={styles.sectionHeader}>
            <View>
              <Text style={styles.sectionTitle}>EXPENDITURE</Text>
              <Text style={styles.sectionSubtitle}>Expenses & Outflows</Text>
            </View>
            <Text style={[styles.sectionTitle, { color: '#EF4444' }]}>{formatINRIndian(pnlData.total_expenses)}</Text>
          </View>
          
          {pnlData.expense_sections.map(section => (
            <View key={section.id} style={styles.pnlSection}>
              <TouchableOpacity
                style={[styles.pnlSectionHeader, { borderLeftColor: sectionColors[section.id] || '#EF4444' }]}
                onPress={() => toggleSectionExpand(section.id)}
              >
                <View style={{ flexDirection: 'row', alignItems: 'center' }}>
                  <MaterialCommunityIcons
                    name={expandedSections.has(section.id) ? 'chevron-down' : 'chevron-right'}
                    size={18}
                    color={colors.textSecondary}
                  />
                  <Text style={[styles.pnlSectionTitle, { marginLeft: 8 }]}>{section.id}. {section.name}</Text>
                </View>
                <Text style={[styles.pnlSectionSubtotal, { color: sectionColors[section.id] || '#EF4444' }]}>
                  {formatINRIndian(section.subtotal)}
                </Text>
              </TouchableOpacity>
              
              {expandedSections.has(section.id) && section.items.map((item, i) => (
                <View key={i} style={styles.pnlItem}>
                  <Text style={styles.pnlItemText}>{item.category}</Text>
                  <Text style={styles.pnlItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              ))}
            </View>
          ))}
        </View>

        {/* Surplus/Deficit */}
        <View style={[
          styles.surplusBox,
          {
            backgroundColor: pnlData.surplus_deficit >= 0 ? '#10B981' + '15' : '#EF4444' + '15',
            borderColor: pnlData.surplus_deficit >= 0 ? '#10B981' : '#EF4444',
          }
        ]}>
          <Text style={[styles.surplusTitle, { color: pnlData.surplus_deficit >= 0 ? '#10B981' : '#EF4444' }]}>
            {pnlData.surplus_deficit >= 0 ? 'SURPLUS' : 'DEFICIT'} FOR THE PERIOD
          </Text>
          <Text style={[styles.surplusAmount, { color: pnlData.surplus_deficit >= 0 ? '#10B981' : '#EF4444' }]}>
            {formatINRIndian(Math.abs(pnlData.surplus_deficit))}
          </Text>
        </View>

        {/* Allocation */}
        {pnlData.surplus_deficit > 0 && (
          <View style={[styles.section, { marginHorizontal: 0 }]}>
            <View style={styles.sectionHeader}>
              <Text style={styles.sectionTitle}>ALLOCATION OF SURPLUS</Text>
            </View>
            <View style={{ padding: 16 }}>
              <View style={styles.bsItem}>
                <Text style={styles.bsItemText}>Transferred to Investments</Text>
                <Text style={styles.bsItemAmount}>{formatINRIndian(pnlData.total_investments)}</Text>
              </View>
              <View style={styles.bsItem}>
                <Text style={styles.bsItemText}>Transferred to Savings</Text>
                <Text style={styles.bsItemAmount}>{formatINRIndian(pnlData.allocation.to_savings)}</Text>
              </View>
              <View style={styles.bsItem}>
                <Text style={styles.bsItemText}>Retained as Cash/Bank Balance</Text>
                <Text style={styles.bsItemAmount}>{formatINRIndian(pnlData.allocation.retained)}</Text>
              </View>
            </View>
          </View>
        )}

        <View style={{ height: 100 }} />
      </ScrollView>
    );
  };

  const renderBalanceSheetTab = () => {
    if (!balanceSheet) return null;

    return (
      <ScrollView showsVerticalScrollIndicator={false} style={{ paddingHorizontal: 16 }}>
        <View style={styles.fyInfo}>
          <MaterialCommunityIcons name="calendar-check" size={16} color={colors.primary} />
          <Text style={styles.fyInfoText}>
            As at {formatIndianDate(balanceSheet.as_of_date)}
          </Text>
        </View>

        {/* Balance Verification Badge */}
        <View style={[
          styles.balanceBadge,
          { backgroundColor: balanceSheet.is_balanced ? '#10B981' + '20' : '#EF4444' + '20' }
        ]}>
          <MaterialCommunityIcons
            name={balanceSheet.is_balanced ? 'check-circle' : 'alert-circle'}
            size={20}
            color={balanceSheet.is_balanced ? '#10B981' : '#EF4444'}
          />
          <Text style={[styles.balanceBadgeText, { color: balanceSheet.is_balanced ? '#10B981' : '#EF4444' }]}>
            {balanceSheet.is_balanced ? 'Balance Sheet Balanced ✓' : 'Balance Sheet Discrepancy'}
          </Text>
        </View>

        {/* ASSETS Section */}
        <View style={[styles.section, { marginHorizontal: 0 }]}>
          <View style={[styles.bsCategoryHeader, { borderLeftColor: '#3B82F6' }]}>
            <MaterialCommunityIcons name="bank" size={22} color="#3B82F6" style={{ marginRight: 12 }} />
            <Text style={styles.bsCategoryTitle}>I. ASSETS</Text>
            <Text style={[styles.bsCategoryTotal, { color: '#3B82F6' }]}>
              {formatINRIndian(balanceSheet.assets.total)}
            </Text>
          </View>

          {/* Non-Current Assets */}
          <View style={styles.bsSubSection}>
            <Text style={styles.bsSubTitle}>(1) Non-Current Assets</Text>
            
            {/* Fixed Assets */}
            <Text style={[styles.bsSubTitle, { fontSize: 12, marginTop: 8 }]}>(a) Property & Fixed Assets</Text>
            {fixedAssets.length > 0 ? (
              fixedAssets.map(asset => (
                <View key={asset.id} style={styles.assetCard}>
                  <View style={[styles.assetIcon, { backgroundColor: '#3B82F6' + '20' }]}>
                    <MaterialCommunityIcons
                      name={asset.category === 'Property' ? 'home' : asset.category === 'Vehicle' ? 'car' : 'laptop'}
                      size={22}
                      color="#3B82F6"
                    />
                  </View>
                  <View style={styles.assetInfo}>
                    <Text style={styles.assetName}>{asset.name}</Text>
                    <Text style={styles.assetCategory}>{asset.category} • {formatIndianDate(asset.purchase_date)}</Text>
                  </View>
                  <View style={styles.assetValue}>
                    <Text style={styles.assetCurrentValue}>
                      {formatINRShort(asset.purchase_value - asset.accumulated_depreciation)}
                    </Text>
                    <Text style={styles.assetDepreciation}>
                      Dep: {formatINRShort(asset.accumulated_depreciation)}
                    </Text>
                  </View>
                  <TouchableOpacity
                    onPress={() => handleDeleteAsset(asset.id)}
                    style={{ padding: 8, marginLeft: 8 }}
                  >
                    <MaterialCommunityIcons name="delete-outline" size={20} color={colors.error} />
                  </TouchableOpacity>
                </View>
              ))
            ) : (
              <View style={styles.bsItem}>
                <Text style={styles.bsItemText}>No fixed assets recorded</Text>
              </View>
            )}
            
            <TouchableOpacity
              style={styles.addAssetButton}
              onPress={() => setShowAssetModal(true)}
            >
              <MaterialCommunityIcons name="plus-circle" size={20} color={colors.primary} />
              <Text style={styles.addAssetText}>Add Fixed Asset</Text>
            </TouchableOpacity>
            
            {/* Long-term Investments */}
            <Text style={[styles.bsSubTitle, { fontSize: 12, marginTop: 16 }]}>(b) Long-Term Investments</Text>
            {balanceSheet.assets.non_current.long_term_investments.items.map((item: any, i: number) => (
              item.amount > 0 && (
                <View key={i} style={styles.bsItem}>
                  <Text style={styles.bsItemText}>{item.name}</Text>
                  <Text style={styles.bsItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              )
            ))}
            
            <View style={[styles.bsItem, { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 8, paddingTop: 12 }]}>
              <Text style={[styles.bsItemText, { fontWeight: '700' }]}>Total Non-Current Assets</Text>
              <Text style={[styles.bsItemAmount, { fontWeight: '700', color: '#3B82F6' }]}>
                {formatINRIndian(balanceSheet.assets.non_current.total)}
              </Text>
            </View>
          </View>

          {/* Current Assets */}
          <View style={styles.bsSubSection}>
            <Text style={styles.bsSubTitle}>(2) Current Assets</Text>
            
            <Text style={[styles.bsSubTitle, { fontSize: 12, marginTop: 8 }]}>(a) Short-Term Investments</Text>
            {balanceSheet.assets.current.short_term_investments.items.map((item: any, i: number) => (
              item.amount > 0 && (
                <View key={i} style={styles.bsItem}>
                  <Text style={styles.bsItemText}>{item.name}</Text>
                  <Text style={styles.bsItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              )
            ))}
            
            <Text style={[styles.bsSubTitle, { fontSize: 12, marginTop: 16 }]}>(b) Cash & Bank Balances</Text>
            {balanceSheet.assets.current.cash_bank.items.map((item: any, i: number) => (
              <View key={i} style={styles.bsItem}>
                <Text style={styles.bsItemText}>{item.name}</Text>
                <Text style={styles.bsItemAmount}>{formatINRIndian(item.amount)}</Text>
              </View>
            ))}
            
            <View style={[styles.bsItem, { borderTopWidth: 1, borderTopColor: colors.border, marginTop: 8, paddingTop: 12 }]}>
              <Text style={[styles.bsItemText, { fontWeight: '700' }]}>Total Current Assets</Text>
              <Text style={[styles.bsItemAmount, { fontWeight: '700', color: '#3B82F6' }]}>
                {formatINRIndian(balanceSheet.assets.current.total)}
              </Text>
            </View>
          </View>
        </View>

        {/* LIABILITIES & NET WORTH Section */}
        <View style={[styles.section, { marginHorizontal: 0 }]}>
          <View style={[styles.bsCategoryHeader, { borderLeftColor: '#EF4444' }]}>
            <MaterialCommunityIcons name="credit-card-outline" size={22} color="#EF4444" style={{ marginRight: 12 }} />
            <Text style={styles.bsCategoryTitle}>II. LIABILITIES</Text>
            <Text style={[styles.bsCategoryTotal, { color: '#EF4444' }]}>
              {formatINRIndian(balanceSheet.liabilities.total)}
            </Text>
          </View>

          <View style={styles.bsSubSection}>
            <Text style={styles.bsSubTitle}>(1) Long-Term Borrowings</Text>
            {balanceSheet.liabilities.non_current.long_term_borrowings.items.length > 0 ? (
              balanceSheet.liabilities.non_current.long_term_borrowings.items.map((item: any, i: number) => (
                <View key={i} style={styles.bsItem}>
                  <Text style={styles.bsItemText}>{item.name}</Text>
                  <Text style={styles.bsItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              ))
            ) : (
              <View style={styles.bsItem}>
                <Text style={[styles.bsItemText, { fontStyle: 'italic' }]}>No long-term borrowings</Text>
              </View>
            )}
            
            <Text style={[styles.bsSubTitle, { marginTop: 16 }]}>(2) Current Liabilities</Text>
            {balanceSheet.liabilities.current.short_term_borrowings.items.length > 0 ? (
              balanceSheet.liabilities.current.short_term_borrowings.items.map((item: any, i: number) => (
                <View key={i} style={styles.bsItem}>
                  <Text style={styles.bsItemText}>{item.name}</Text>
                  <Text style={styles.bsItemAmount}>{formatINRIndian(item.amount)}</Text>
                </View>
              ))
            ) : (
              <View style={styles.bsItem}>
                <Text style={[styles.bsItemText, { fontStyle: 'italic' }]}>No current liabilities</Text>
              </View>
            )}
            
            {/* Add Loan Button */}
            <TouchableOpacity
              style={styles.addAssetButton}
              onPress={() => setShowLoanModal(true)}
            >
              <MaterialCommunityIcons name="plus-circle" size={20} color={colors.primary} />
              <Text style={styles.addAssetText}>Add Loan/Liability</Text>
            </TouchableOpacity>
          </View>

          {/* Loans List */}
          {loans.length > 0 && (
            <View style={{ paddingHorizontal: 16, paddingBottom: 16 }}>
              <Text style={[styles.bsSubTitle, { marginBottom: 12 }]}>Active Loans</Text>
              {loans.map(loan => (
                <View key={loan.id} style={[styles.loanCard, { marginHorizontal: 0, marginBottom: 8 }]}>
                  <View style={styles.loanCardHeader}>
                    <View style={[styles.loanIcon, { backgroundColor: '#EF4444' + '20' }]}>
                      <MaterialCommunityIcons
                        name={loan.loan_type.includes('Home') ? 'home' : loan.loan_type.includes('Car') ? 'car' : 'bank'}
                        size={22}
                        color="#EF4444"
                      />
                    </View>
                    <View style={styles.loanInfo}>
                      <Text style={styles.loanName}>{loan.name}</Text>
                      <Text style={styles.loanType}>{loan.loan_type} • {loan.lender || 'N/A'}</Text>
                    </View>
                    <View style={styles.loanAmount}>
                      <Text style={styles.loanOutstanding}>{formatINRShort(loan.outstanding_principal)}</Text>
                      <Text style={styles.loanEMI}>EMI: {formatINRShort(loan.emi_amount)}/mo</Text>
                    </View>
                  </View>
                  <View style={styles.loanDetails}>
                    <View style={styles.loanDetailRow}>
                      <Text style={styles.loanDetailLabel}>Principal</Text>
                      <Text style={styles.loanDetailValue}>{formatINRIndian(loan.principal_amount)}</Text>
                    </View>
                    <View style={styles.loanDetailRow}>
                      <Text style={styles.loanDetailLabel}>Interest Rate</Text>
                      <Text style={styles.loanDetailValue}>{loan.interest_rate}% p.a.</Text>
                    </View>
                    <View style={styles.loanDetailRow}>
                      <Text style={styles.loanDetailLabel}>Remaining EMIs</Text>
                      <Text style={styles.loanDetailValue}>{loan.remaining_emis} of {loan.tenure_months}</Text>
                    </View>
                    <View style={styles.loanDetailRow}>
                      <Text style={styles.loanDetailLabel}>Interest Paid</Text>
                      <Text style={[styles.loanDetailValue, { color: '#EF4444' }]}>{formatINRIndian(loan.total_interest_paid)}</Text>
                    </View>
                    <View style={styles.loanActions}>
                      <TouchableOpacity style={styles.loanActionBtn} onPress={() => viewEMISchedule(loan.id)}>
                        <MaterialCommunityIcons name="calendar-month" size={16} color={colors.primary} />
                        <Text style={styles.loanActionText}>EMI Schedule</Text>
                      </TouchableOpacity>
                      <TouchableOpacity
                        style={[styles.loanActionBtn, { backgroundColor: '#EF4444' + '10' }]}
                        onPress={() => handleDeleteLoan(loan.id)}
                      >
                        <MaterialCommunityIcons name="delete-outline" size={16} color="#EF4444" />
                        <Text style={[styles.loanActionText, { color: '#EF4444' }]}>Delete</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>

        {/* NET WORTH Section */}
        <View style={[styles.section, { marginHorizontal: 0 }]}>
          <View style={[styles.bsCategoryHeader, { borderLeftColor: '#10B981' }]}>
            <MaterialCommunityIcons name="wallet" size={22} color="#10B981" style={{ marginRight: 12 }} />
            <Text style={styles.bsCategoryTitle}>III. NET WORTH</Text>
            <Text style={[styles.bsCategoryTotal, { color: '#10B981' }]}>
              {formatINRIndian(balanceSheet.net_worth.closing)}
            </Text>
          </View>

          <View style={styles.bsSubSection}>
            <View style={styles.bsItem}>
              <Text style={styles.bsItemText}>Opening Net Worth</Text>
              <Text style={styles.bsItemAmount}>{formatINRIndian(balanceSheet.net_worth.opening)}</Text>
            </View>
            <View style={styles.bsItem}>
              <Text style={styles.bsItemText}>Add: Surplus for the Period</Text>
              <Text style={[styles.bsItemAmount, { color: '#10B981' }]}>
                {formatINRIndian(balanceSheet.net_worth.surplus_for_period)}
              </Text>
            </View>
            <View style={[styles.bsItem, { borderTopWidth: 2, borderTopColor: colors.border, marginTop: 8, paddingTop: 12 }]}>
              <Text style={[styles.bsItemText, { fontWeight: '700' }]}>Closing Net Worth</Text>
              <Text style={[styles.bsItemAmount, { fontWeight: '700', color: '#10B981' }]}>
                {formatINRIndian(balanceSheet.net_worth.closing)}
              </Text>
            </View>
          </View>
        </View>

        {/* Final Totals */}
        <View style={[styles.pnlTotal, { marginTop: 16 }]}>
          <View>
            <Text style={styles.pnlTotalText}>TOTAL ASSETS</Text>
          </View>
          <Text style={[styles.pnlTotalAmount, { color: '#3B82F6' }]}>
            {formatINRIndian(balanceSheet.assets.total)}
          </Text>
        </View>
        
        <View style={[styles.pnlTotal, { marginTop: 8 }]}>
          <View>
            <Text style={styles.pnlTotalText}>LIABILITIES + NET WORTH</Text>
          </View>
          <Text style={[styles.pnlTotalAmount, { color: '#10B981' }]}>
            {formatINRIndian(balanceSheet.total_liabilities_and_net_worth)}
          </Text>
        </View>

        <View style={{ height: 100 }} />
      </ScrollView>
    );
  };

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center' }}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={{ marginTop: 16, color: isDark ? '#94A3B8' : '#64748B' }}>Loading financial records...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
      <StatusBar barStyle={isDark ? 'light-content' : 'dark-content'} />
      
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerContent}>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <MaterialCommunityIcons name="arrow-left" size={24} color={isDark ? '#F8FAFC' : '#1E293B'} />
          </TouchableOpacity>
          <View style={{ flex: 1, marginLeft: 16 }}>
            <Text style={styles.headerTitle}>Books & Reports</Text>
            <Text style={styles.headerSubtitle}>{user?.full_name} • {getIndianFY()}</Text>
          </View>
          <TouchableOpacity style={styles.exportButton} onPress={() => setShowExportModal(true)}>
            <MaterialCommunityIcons name="download" size={18} color="#FFF" />
            <Text style={styles.exportButtonText}>Export</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Tabs */}
      <View style={styles.tabsContainer}>
        <TouchableOpacity
          style={[styles.tab, activeTab === 'ledger' && styles.tabActive]}
          onPress={() => setActiveTab('ledger')}
        >
          <MaterialCommunityIcons
            name="book-open-page-variant"
            size={18}
            color={activeTab === 'ledger' ? colors.primary : colors.textSecondary}
          />
          <Text style={[styles.tabText, activeTab === 'ledger' && styles.tabTextActive]}>Ledger</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'pnl' && styles.tabActive]}
          onPress={() => setActiveTab('pnl')}
        >
          <MaterialCommunityIcons
            name="chart-bar"
            size={18}
            color={activeTab === 'pnl' ? colors.primary : colors.textSecondary}
          />
          <Text style={[styles.tabText, activeTab === 'pnl' && styles.tabTextActive]}>P&L</Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.tab, activeTab === 'balance' && styles.tabActive]}
          onPress={() => setActiveTab('balance')}
        >
          <MaterialCommunityIcons
            name="scale-balance"
            size={18}
            color={activeTab === 'balance' ? colors.primary : colors.textSecondary}
          />
          <Text style={[styles.tabText, activeTab === 'balance' && styles.tabTextActive]}>Balance Sheet</Text>
        </TouchableOpacity>
      </View>

      {/* Date Range Selector */}
      <View style={styles.dateSelector}>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 6 }}>
          {DATE_PRESETS.map(preset => (
            <TouchableOpacity
              key={preset.key}
              style={[styles.dateSelectorChip, datePreset === preset.key && styles.dateSelectorChipActive]}
              onPress={() => setDatePreset(preset.key)}
            >
              <Text style={[styles.dateSelectorChipText, datePreset === preset.key && styles.dateSelectorChipTextActive]}>
                {preset.label}
              </Text>
            </TouchableOpacity>
          ))}
        </ScrollView>
      </View>

      {/* Custom Date Input (when custom is selected) */}
      {datePreset === 'custom' && (
        <View style={{ flexDirection: 'row', paddingHorizontal: 16, marginBottom: 12, gap: 8 }}>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 11, color: isDark ? '#94A3B8' : '#64748B', marginBottom: 4 }}>From</Text>
            <TextInput
              style={[styles.input, { paddingVertical: 10, fontSize: 13 }]}
              value={customStartDate}
              onChangeText={setCustomStartDate}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
            />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={{ fontSize: 11, color: isDark ? '#94A3B8' : '#64748B', marginBottom: 4 }}>To</Text>
            <TextInput
              style={[styles.input, { paddingVertical: 10, fontSize: 13 }]}
              value={customEndDate}
              onChangeText={setCustomEndDate}
              placeholder="YYYY-MM-DD"
              placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
            />
          </View>
        </View>
      )}

      {/* Content */}
      <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
        <ScrollView
          refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
          showsVerticalScrollIndicator={false}
        >
          {activeTab === 'ledger' && renderLedgerTab()}
          {activeTab === 'pnl' && renderPnLTab()}
          {activeTab === 'balance' && renderBalanceSheetTab()}
        </ScrollView>
      </Animated.View>

      {/* Add Asset Modal */}
      <Modal visible={showAssetModal} transparent animationType="slide">
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>{editingAsset ? 'Edit Asset' : 'Add Fixed Asset'}</Text>
                <TouchableOpacity onPress={() => { setShowAssetModal(false); setEditingAsset(null); }}>
                  <MaterialCommunityIcons name="close" size={24} color={isDark ? '#F8FAFC' : '#1E293B'} />
                </TouchableOpacity>
              </View>
              
              <ScrollView style={styles.modalBody}>
                <Text style={[styles.inputLabel, { marginTop: 0 }]}>Asset Name *</Text>
                <TextInput
                  style={styles.input}
                  value={assetForm.name}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, name: t }))}
                  placeholder="e.g., Residential Apartment"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>Category</Text>
                <View style={styles.categoryPicker}>
                  {ASSET_CATEGORIES.map(cat => (
                    <TouchableOpacity
                      key={cat}
                      style={[styles.categoryChip, assetForm.category === cat && styles.categoryChipActive]}
                      onPress={() => setAssetForm(f => ({ ...f, category: cat }))}
                    >
                      <Text style={[styles.categoryChipText, assetForm.category === cat && styles.categoryChipTextActive]}>
                        {cat}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                
                <Text style={styles.inputLabel}>Purchase Date</Text>
                <TextInput
                  style={styles.input}
                  value={assetForm.purchase_date}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, purchase_date: t }))}
                  placeholder="YYYY-MM-DD"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>Purchase Value (₹) *</Text>
                <TextInput
                  style={styles.input}
                  value={assetForm.purchase_value}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, purchase_value: t }))}
                  placeholder="5000000"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Current Value (₹)</Text>
                <TextInput
                  style={styles.input}
                  value={assetForm.current_value}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, current_value: t }))}
                  placeholder="5500000"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Annual Depreciation Rate (%)</Text>
                <TextInput
                  style={styles.input}
                  value={assetForm.depreciation_rate}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, depreciation_rate: t }))}
                  placeholder="10"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Notes</Text>
                <TextInput
                  style={[styles.input, { height: 80, textAlignVertical: 'top' }]}
                  value={assetForm.notes}
                  onChangeText={(t) => setAssetForm(f => ({ ...f, notes: t }))}
                  placeholder="Additional notes..."
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  multiline
                />
                
                <TouchableOpacity
                  style={[styles.saveButton, saving && { opacity: 0.6 }]}
                  onPress={handleSaveAsset}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color="#FFF" />
                  ) : (
                    <Text style={styles.saveButtonText}>{editingAsset ? 'Update Asset' : 'Add Asset'}</Text>
                  )}
                </TouchableOpacity>
                
                <View style={{ height: 40 }} />
              </ScrollView>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* Export Modal */}
      <Modal visible={showExportModal} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Export Report</Text>
              <TouchableOpacity onPress={() => setShowExportModal(false)}>
                <MaterialCommunityIcons name="close" size={24} color={isDark ? '#F8FAFC' : '#1E293B'} />
              </TouchableOpacity>
            </View>
            
            <View style={{ paddingHorizontal: 20, paddingTop: 12 }}>
              <Text style={{ fontSize: 13, color: isDark ? '#94A3B8' : '#64748B', marginBottom: 16 }}>
                Export your {activeTab === 'ledger' ? 'General Ledger' : activeTab === 'pnl' ? 'Profit & Loss Statement' : 'Balance Sheet'} in your preferred format
              </Text>
            </View>
            
            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('csv')} disabled={exporting}>
              <View style={[styles.exportOptionIcon, { backgroundColor: '#10B981' + '20' }]}>
                <MaterialCommunityIcons name="file-delimited" size={24} color="#10B981" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>CSV Format</Text>
                <Text style={styles.exportOptionDesc}>Comma-separated values for spreadsheets</Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={24} color={isDark ? '#94A3B8' : '#64748B'} />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('excel')} disabled={exporting}>
              <View style={[styles.exportOptionIcon, { backgroundColor: '#8B5CF6' + '20' }]}>
                <MaterialCommunityIcons name="microsoft-excel" size={24} color="#8B5CF6" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>Excel Format</Text>
                <Text style={styles.exportOptionDesc}>Formatted .xlsx workbook with styling</Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={24} color={isDark ? '#94A3B8' : '#64748B'} />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('pdf')} disabled={exporting}>
              <View style={[styles.exportOptionIcon, { backgroundColor: '#EF4444' + '20' }]}>
                <MaterialCommunityIcons name="file-pdf-box" size={24} color="#EF4444" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>PDF Format</Text>
                <Text style={styles.exportOptionDesc}>Professional report for printing & sharing</Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={24} color={isDark ? '#94A3B8' : '#64748B'} />
            </TouchableOpacity>
            
            <TouchableOpacity style={styles.exportOption} onPress={() => handleExport('json')} disabled={exporting}>
              <View style={[styles.exportOptionIcon, { backgroundColor: '#3B82F6' + '20' }]}>
                <MaterialCommunityIcons name="code-json" size={24} color="#3B82F6" />
              </View>
              <View style={{ flex: 1 }}>
                <Text style={styles.exportOptionTitle}>JSON Format</Text>
                <Text style={styles.exportOptionDesc}>Structured data for developers & APIs</Text>
              </View>
              <MaterialCommunityIcons name="chevron-right" size={24} color={isDark ? '#94A3B8' : '#64748B'} />
            </TouchableOpacity>
            
            {exporting && (
              <View style={{ padding: 20, alignItems: 'center' }}>
                <ActivityIndicator size="large" color={colors.primary} />
                <Text style={{ marginTop: 12, color: isDark ? '#94A3B8' : '#64748B' }}>Generating report...</Text>
              </View>
            )}
            
            <View style={{ height: 40 }} />
          </View>
        </View>
      </Modal>

      {/* Add Loan Modal */}
      <Modal visible={showLoanModal} transparent animationType="slide">
        <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={{ flex: 1 }}>
          <View style={styles.modalOverlay}>
            <View style={styles.modalContent}>
              <View style={styles.modalHeader}>
                <Text style={styles.modalTitle}>{editingLoan ? 'Edit Loan' : 'Add Loan/Liability'}</Text>
                <TouchableOpacity onPress={() => { setShowLoanModal(false); setEditingLoan(null); }}>
                  <MaterialCommunityIcons name="close" size={24} color={isDark ? '#F8FAFC' : '#1E293B'} />
                </TouchableOpacity>
              </View>
              
              <ScrollView style={styles.modalBody}>
                <Text style={[styles.inputLabel, { marginTop: 0 }]}>Loan Name *</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.name}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, name: t }))}
                  placeholder="e.g., HDFC Home Loan"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>Loan Type</Text>
                <View style={styles.categoryPicker}>
                  {LOAN_TYPES.map(type => (
                    <TouchableOpacity
                      key={type}
                      style={[styles.categoryChip, loanForm.loan_type === type && styles.categoryChipActive]}
                      onPress={() => setLoanForm(f => ({ ...f, loan_type: type }))}
                    >
                      <Text style={[styles.categoryChipText, loanForm.loan_type === type && styles.categoryChipTextActive]}>
                        {type}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                
                <Text style={styles.inputLabel}>Principal Amount (₹) *</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.principal_amount}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, principal_amount: t }))}
                  placeholder="5000000"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Annual Interest Rate (%) *</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.interest_rate}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, interest_rate: t }))}
                  placeholder="8.5"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Tenure (Months) *</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.tenure_months}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, tenure_months: t }))}
                  placeholder="240"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Start Date</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.start_date}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, start_date: t }))}
                  placeholder="YYYY-MM-DD"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>EMI Amount (₹) - Auto-calculated if empty</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.emi_amount}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, emi_amount: t }))}
                  placeholder="Auto-calculated"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  keyboardType="numeric"
                />
                
                <Text style={styles.inputLabel}>Lender Name</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.lender}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, lender: t }))}
                  placeholder="e.g., HDFC Bank"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>Loan Account Number</Text>
                <TextInput
                  style={styles.input}
                  value={loanForm.account_number}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, account_number: t }))}
                  placeholder="e.g., LOAN123456"
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                />
                
                <Text style={styles.inputLabel}>Notes</Text>
                <TextInput
                  style={[styles.input, { height: 80, textAlignVertical: 'top' }]}
                  value={loanForm.notes}
                  onChangeText={(t) => setLoanForm(f => ({ ...f, notes: t }))}
                  placeholder="Additional notes..."
                  placeholderTextColor={isDark ? '#64748B' : '#94A3B8'}
                  multiline
                />
                
                <TouchableOpacity
                  style={[styles.saveButton, saving && { opacity: 0.6 }]}
                  onPress={handleSaveLoan}
                  disabled={saving}
                >
                  {saving ? (
                    <ActivityIndicator color="#FFF" />
                  ) : (
                    <Text style={styles.saveButtonText}>{editingLoan ? 'Update Loan' : 'Add Loan'}</Text>
                  )}
                </TouchableOpacity>
                
                <View style={{ height: 40 }} />
              </ScrollView>
            </View>
          </View>
        </KeyboardAvoidingView>
      </Modal>

      {/* EMI Schedule Modal */}
      <Modal visible={showEMISchedule !== null} transparent animationType="slide">
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, { maxHeight: '80%' }]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>EMI Schedule</Text>
              <TouchableOpacity onPress={() => setShowEMISchedule(null)}>
                <MaterialCommunityIcons name="close" size={24} color={colors.text} />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={{ paddingHorizontal: 16 }}>
              <View style={styles.emiScheduleHeader}>
                <Text style={[styles.tableHeaderText, { width: 35 }]}>#</Text>
                <Text style={[styles.tableHeaderText, { width: 70 }]}>Date</Text>
                <Text style={[styles.tableHeaderText, { flex: 1, textAlign: 'right' }]}>EMI</Text>
                <Text style={[styles.tableHeaderText, { flex: 1, textAlign: 'right' }]}>Principal</Text>
                <Text style={[styles.tableHeaderText, { flex: 1, textAlign: 'right' }]}>Interest</Text>
                <Text style={[styles.tableHeaderText, { flex: 1, textAlign: 'right' }]}>Balance</Text>
              </View>
              
              {emiSchedule.map((emi, idx) => (
                <View
                  key={idx}
                  style={[
                    styles.emiRow,
                    emi.status === 'paid' && styles.emiRowPaid,
                    emi.status === 'current' && styles.emiRowCurrent,
                  ]}
                >
                  <Text style={[styles.emiCell, { width: 35 }]}>{emi.month}</Text>
                  <Text style={[styles.emiCell, { width: 70 }]}>{formatIndianDate(emi.date).slice(0, 6)}</Text>
                  <Text style={[styles.emiCell, styles.emiCellBold, { flex: 1, textAlign: 'right' }]}>
                    {formatINRShort(emi.emi)}
                  </Text>
                  <Text style={[styles.emiCell, { flex: 1, textAlign: 'right' }]}>
                    {formatINRShort(emi.principal)}
                  </Text>
                  <Text style={[styles.emiCell, { flex: 1, textAlign: 'right' }]}>
                    {formatINRShort(emi.interest)}
                  </Text>
                  <Text style={[styles.emiCell, { flex: 1, textAlign: 'right' }]}>
                    {formatINRShort(emi.closing_balance)}
                  </Text>
                </View>
              ))}
              
              <View style={{ height: 40 }} />
            </ScrollView>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}
