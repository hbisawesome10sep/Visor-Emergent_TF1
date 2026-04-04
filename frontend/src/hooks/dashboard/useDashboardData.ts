import { useState, useCallback, useEffect } from 'react';
import { apiRequest } from '../../utils/api';

type FrequencyOption = 'Quarter' | 'Month' | 'Year' | 'Custom';

type DashboardStats = {
  total_income: number;
  total_expenses: number;
  total_investments: number;
  portfolio_invested: number;
  portfolio_current: number;
  net_balance: number;
  savings: number;
  savings_rate: number;
  expense_ratio: number;
  investment_ratio: number;
  category_breakdown: Record<string, number>;
  budget_items: Array<{ category: string; amount: number; percentage: number }>;
  invest_breakdown: Record<string, number>;
  recent_transactions: any[];
  monthly_income: number;
  monthly_expenses: number;
  monthly_investments: number;
  monthly_savings: number;
  goal_count: number;
  goal_progress: number;
  transaction_count: number;
  credit_card_summary?: {
    total_outstanding: number;
    total_limit: number;
    utilization: number;
    total_expenses: number;
    total_payments: number;
    monthly_expenses: number;
    cards_count: number;
  };
  health_score?: {
    overall: number;
    breakdown: Record<string, number>;
  };
  trend_data?: Array<{ label: string; income: number; expenses: number; investments: number }>;
  trend_insights?: string[];
  user_created_at?: string;
};

type Goal = {
  id: string;
  title: string;
  target_amount: number;
  current_amount: number;
  deadline: string;
  progress: number;
  category: string;
};

function toDateStr(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function getFinancialYear(): { start: Date; end: Date; label: string } {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const fyStartYear = month < 3 ? year - 1 : year;
  const start = new Date(fyStartYear, 3, 1);
  const end = new Date(fyStartYear + 1, 2, 31);
  const cappedEnd = end > now ? now : end;
  const label = `FY ${fyStartYear}-${String(fyStartYear + 1).slice(2)}`;
  return { start, end: cappedEnd, label };
}

export function useDashboardData(token: string | null) {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedFrequency, setSelectedFrequency] = useState<FrequencyOption>('Month');
  const [dateRange, setDateRange] = useState({
    start: new Date(new Date().getFullYear(), new Date().getMonth(), 1),
    end: new Date(),
  });
  const [userCreatedAt, setUserCreatedAt] = useState<string>('');

  const getDateRangeForFrequency = useCallback((freq: FrequencyOption): { start: Date; end: Date } => {
    const now = new Date();
    let start: Date;
    let end = now;
    
    switch (freq) {
      case 'Quarter':
        start = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
        break;
      case 'Year': {
        const fy = getFinancialYear();
        start = fy.start;
        end = fy.end;
        break;
      }
      case 'Custom':
        start = dateRange.start;
        end = dateRange.end;
        break;
      case 'Month':
      default:
        start = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
    }
    
    return { start, end };
  }, [dateRange]);

  const fetchData = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const now = new Date();
      let startDate: Date;
      let endDate = now;
      
      switch (selectedFrequency) {
        case 'Quarter':
          startDate = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
          break;
        case 'Year': {
          const fy = getFinancialYear();
          startDate = fy.start;
          endDate = fy.end;
          break;
        }
        case 'Custom':
          startDate = dateRange.start;
          endDate = dateRange.end;
          break;
        case 'Month':
        default:
          startDate = new Date(now.getFullYear(), now.getMonth(), 1);
          break;
      }
      
      const safeStart = isNaN(startDate.getTime()) ? new Date(now.getFullYear(), now.getMonth(), 1) : startDate;
      const safeEnd = isNaN(endDate.getTime()) ? now : endDate;
      const startStr = toDateStr(safeStart);
      const endStr = toDateStr(safeEnd);
      
      const [s, g] = await Promise.all([
        apiRequest(`/dashboard/stats?start_date=${startStr}&end_date=${endStr}&frequency=${selectedFrequency}`, { token }),
        apiRequest('/goals', { token }),
      ]);
      setStats(s);
      setGoals(g);
      if (s?.user_created_at) {
        setUserCreatedAt(s.user_created_at);
      }
    } catch (e: any) {
      console.warn('[Dashboard] Fetch error:', e?.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [token, selectedFrequency, dateRange]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  return {
    stats,
    goals,
    loading,
    refreshing,
    selectedFrequency,
    setSelectedFrequency,
    dateRange,
    setDateRange,
    userCreatedAt,
    fetchData,
    onRefresh,
    getDateRangeForFrequency,
  };
}
