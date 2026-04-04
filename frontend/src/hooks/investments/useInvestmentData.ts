import { useState, useCallback, useEffect, useRef } from 'react';
import { Animated, AppState } from 'react-native';
import { useFocusEffect } from 'expo-router';
import { apiRequest } from '../../utils/api';
import type {
  MarketItem, DashboardStats, PortfolioData, Goal,
  HoldingsData, RecurringData,
} from '../../components/investments/types';

interface InvestmentDataState {
  marketData: MarketItem[];
  stats: DashboardStats | null;
  portfolio: PortfolioData | null;
  goals: Goal[];
  holdingsData: HoldingsData | null;
  rebalanceData: any;
  recurringData: RecurringData | null;
  sipSuggestions: Array<{ id: string; fund_name: string; isin: string }>;
  riskProfile: 'Conservative' | 'Moderate' | 'Aggressive';
  riskScore: number;
  riskBreakdown: Record<string, number>;
  riskSaved: boolean;
  loading: boolean;
  refreshing: boolean;
}

export function useInvestmentData(token: string | null) {
  const [marketData, setMarketData] = useState<MarketItem[]>([]);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioData | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [holdingsData, setHoldingsData] = useState<HoldingsData | null>(null);
  const [rebalanceData, setRebalanceData] = useState<any>(null);
  const [recurringData, setRecurringData] = useState<RecurringData | null>(null);
  const [sipSuggestions, setSipSuggestions] = useState<Array<{ id: string; fund_name: string; isin: string }>>([]);
  const [riskProfile, setRiskProfile] = useState<'Conservative' | 'Moderate' | 'Aggressive'>('Moderate');
  const [riskScore, setRiskScore] = useState(0);
  const [riskBreakdown, setRiskBreakdown] = useState<Record<string, number>>({});
  const [riskSaved, setRiskSaved] = useState(false);
  const fadeAnim = useRef(new Animated.Value(0)).current;

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

  // Re-fetch when tab comes back into focus
  useFocusEffect(
    useCallback(() => {
      fetchData();
    }, [fetchData])
  );

  // Auto-refresh when user returns from background
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') fetchData();
    });
    return () => sub.remove();
  }, [fetchData]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchData();
  }, [fetchData]);

  return {
    marketData,
    stats,
    portfolio,
    goals,
    setGoals,
    holdingsData,
    rebalanceData,
    recurringData,
    sipSuggestions,
    setSipSuggestions,
    riskProfile,
    setRiskProfile,
    riskScore,
    setRiskScore,
    riskBreakdown,
    setRiskBreakdown,
    riskSaved,
    setRiskSaved,
    loading,
    refreshing,
    fetchData,
    onRefresh,
    fadeAnim,
  };
}
