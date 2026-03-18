import React, { useState, useCallback } from 'react';
import { View, Text, StyleSheet, TextInput, TouchableOpacity, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';

type Props = { token: string; isDark: boolean; colors: any };

const YEAR_OPTIONS = [5, 10, 15, 20, 25];

export const WealthProjector = ({ token, isDark, colors }: Props) => {
  const [years, setYears] = useState(10);
  const [customSip, setCustomSip] = useState('');
  const [customReturn, setCustomReturn] = useState('');
  const [result, setResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [activeScenario, setActiveScenario] = useState<string>('moderate');

  const project = useCallback(async () => {
    setLoading(true);
    try {
      const body: any = { years };
      if (customSip) body.monthly_sip = parseFloat(customSip);
      if (customReturn) body.expected_return_pct = parseFloat(customReturn);
      const res = await apiRequest('/sip-analytics/wealth-projection', { token, method: 'POST', body });
      setResult(res);
    } catch (e) { console.warn(e); }
    finally { setLoading(false); }
  }, [token, years, customSip, customReturn]);

  const scenarioColors: Record<string, string> = {
    conservative: '#F59E0B', moderate: '#10B981', aggressive: '#8B5CF6', custom: '#3B82F6',
  };

  const active = result?.scenarios?.[activeScenario];
  const maxFV = result ? Math.max(...Object.values(result.scenarios).map((s: any) => s.future_value)) : 0;

  return (
    <View data-testid="wealth-projector">
      <View style={[s.hdr, { backgroundColor: isDark ? 'rgba(139,92,246,0.08)' : 'rgba(139,92,246,0.04)' }]}>
        <MaterialCommunityIcons name="chart-timeline-variant-shimmer" size={20} color="#8B5CF6" />
        <Text style={[s.hdrText, { color: colors.textPrimary }]}>Wealth Projector</Text>
      </View>

      <Text style={[s.desc, { color: colors.textSecondary }]}>
        Project your future wealth based on current SIPs and investments.
      </Text>

      {/* Year selector */}
      <View style={s.yearRow}>
        {YEAR_OPTIONS.map(y => (
          <TouchableOpacity
            key={y}
            style={[s.yearBtn, {
              backgroundColor: years === y ? '#8B5CF618' : isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: years === y ? '#8B5CF6' : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
            }]}
            onPress={() => { setYears(y); setResult(null); }}
            data-testid={`year-${y}-btn`}
          >
            <Text style={[s.yearText, { color: years === y ? '#8B5CF6' : colors.textSecondary }]}>{y}Y</Text>
          </TouchableOpacity>
        ))}
      </View>

      {/* Custom inputs */}
      <View style={s.inputsRow}>
        <View style={[s.inputBox, {
          backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)',
          borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
        }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Monthly SIP (Rs)</Text>
          <TextInput
            style={[s.input, { color: colors.textPrimary }]}
            value={customSip}
            onChangeText={(v) => { setCustomSip(v); setResult(null); }}
            keyboardType="numeric"
            placeholder="Auto"
            placeholderTextColor={colors.textSecondary}
            data-testid="sip-amount-input"
          />
        </View>
        <View style={[s.inputBox, {
          backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.03)',
          borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
        }]}>
          <Text style={[s.inputLabel, { color: colors.textSecondary }]}>Return % (p.a.)</Text>
          <TextInput
            style={[s.input, { color: colors.textPrimary }]}
            value={customReturn}
            onChangeText={(v) => { setCustomReturn(v); setResult(null); }}
            keyboardType="numeric"
            placeholder="Auto"
            placeholderTextColor={colors.textSecondary}
            data-testid="return-pct-input"
          />
        </View>
      </View>

      <TouchableOpacity
        style={[s.btn, { opacity: loading ? 0.5 : 1 }]}
        onPress={project}
        disabled={loading}
        data-testid="project-wealth-btn"
      >
        {loading ? <ActivityIndicator color="#fff" size="small" /> : (
          <Text style={s.btnText}>Project My Wealth</Text>
        )}
      </TouchableOpacity>

      {result && (
        <View data-testid="projection-result">
          {/* Inputs used */}
          <View style={[s.inputsSummary, { backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)', borderColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)' }]}>
            <View style={s.inputSumItem}>
              <Text style={[s.inputSumLabel, { color: colors.textSecondary }]}>Monthly SIP</Text>
              <Text style={[s.inputSumVal, { color: colors.textPrimary }]}>{formatINRShort(result.inputs.monthly_sip)}</Text>
            </View>
            <View style={s.inputSumItem}>
              <Text style={[s.inputSumLabel, { color: colors.textSecondary }]}>Current Value</Text>
              <Text style={[s.inputSumVal, { color: colors.textPrimary }]}>{formatINRShort(result.inputs.current_value)}</Text>
            </View>
            <View style={s.inputSumItem}>
              <Text style={[s.inputSumLabel, { color: colors.textSecondary }]}>Duration</Text>
              <Text style={[s.inputSumVal, { color: colors.textPrimary }]}>{result.inputs.years} years</Text>
            </View>
          </View>

          {/* Scenario tabs */}
          <View style={s.scenarioRow}>
            {Object.keys(result.scenarios).map(key => (
              <TouchableOpacity
                key={key}
                style={[s.scenarioTab, {
                  backgroundColor: activeScenario === key ? scenarioColors[key] + '18' : 'transparent',
                  borderColor: activeScenario === key ? scenarioColors[key] : isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)',
                }]}
                onPress={() => setActiveScenario(key)}
                data-testid={`scenario-${key}`}
              >
                <Text style={[s.scenarioText, { color: activeScenario === key ? scenarioColors[key] : colors.textSecondary }]}>
                  {key.charAt(0).toUpperCase() + key.slice(1)}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          {/* Active scenario detail */}
          {active && (
            <View style={[s.scenarioCard, {
              backgroundColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.02)',
              borderColor: scenarioColors[activeScenario] + '30',
            }]}>
              <Text style={[s.scenarioCardTitle, { color: scenarioColors[activeScenario] }]}>
                {activeScenario.charAt(0).toUpperCase() + activeScenario.slice(1)} ({active.annual_return_pct}% p.a.)
              </Text>
              <Text style={[s.bigNum, { color: colors.textPrimary }]}>{formatINRShort(active.future_value)}</Text>
              <Text style={[s.bigLabel, { color: colors.textSecondary }]}>Projected Value in {years} Years</Text>

              <View style={s.scenarioStats}>
                <View style={s.scenarioStat}>
                  <Text style={[s.sStatLabel, { color: colors.textSecondary }]}>Total Invested</Text>
                  <Text style={[s.sStatVal, { color: colors.textPrimary }]}>{formatINRShort(active.total_invested)}</Text>
                </View>
                <View style={s.scenarioStat}>
                  <Text style={[s.sStatLabel, { color: colors.textSecondary }]}>Returns</Text>
                  <Text style={[s.sStatVal, { color: '#10B981' }]}>{formatINRShort(active.returns)}</Text>
                </View>
                <View style={s.scenarioStat}>
                  <Text style={[s.sStatLabel, { color: colors.textSecondary }]}>Multiplier</Text>
                  <Text style={[s.sStatVal, { color: '#8B5CF6' }]}>
                    {active.total_invested > 0 ? (active.future_value / active.total_invested).toFixed(1) : '0'}x
                  </Text>
                </View>
              </View>

              {/* Visual bar comparing scenarios */}
              <View style={{ marginTop: 14 }}>
                {Object.entries(result.scenarios).map(([key, sc]: [string, any]) => (
                  <View key={key} style={s.barRow}>
                    <Text style={[s.barLabel, { color: colors.textSecondary }]}>{key.slice(0, 4)}</Text>
                    <View style={[s.barBg, { backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)' }]}>
                      <View style={[s.barFill, { width: `${maxFV > 0 ? (sc.future_value / maxFV * 100) : 0}%`, backgroundColor: scenarioColors[key] }]} />
                    </View>
                    <Text style={[s.barVal, { color: scenarioColors[key] }]}>{formatINRShort(sc.future_value)}</Text>
                  </View>
                ))}
              </View>
            </View>
          )}

          {/* Year-by-year mini milestones */}
          {result.yearly_projection && result.yearly_projection.length > 0 && (
            <View style={{ marginTop: 14 }}>
              <Text style={[s.subhead, { color: colors.textPrimary }]}>Year-by-Year Milestones</Text>
              {result.yearly_projection.filter((_: any, i: number) => i % 2 === 0 || i === result.yearly_projection.length - 1).map((yr: any) => (
                <View key={yr.year} style={[s.mileRow, { borderBottomColor: isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.04)' }]}>
                  <Text style={[s.mileYear, { color: colors.textSecondary }]}>Year {yr.year}</Text>
                  <View>
                    <Text style={[s.mileVal, { color: colors.textPrimary }]}>{formatINRShort(yr.future_value)}</Text>
                    <Text style={[s.mileRet, { color: '#10B981' }]}>+{formatINRShort(yr.returns)}</Text>
                  </View>
                </View>
              ))}
            </View>
          )}
        </View>
      )}
    </View>
  );
};

const s = StyleSheet.create({
  hdr: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, marginBottom: 8 },
  hdrText: { fontSize: 15, fontWeight: '700' },
  desc: { fontSize: 13, marginBottom: 12, paddingHorizontal: 4 },
  yearRow: { flexDirection: 'row', gap: 8, marginBottom: 12, flexWrap: 'wrap' },
  yearBtn: { paddingHorizontal: 16, paddingVertical: 8, borderRadius: 20, borderWidth: 1 },
  yearText: { fontSize: 13, fontWeight: '600' },
  inputsRow: { flexDirection: 'row', gap: 10, marginBottom: 14 },
  inputBox: { flex: 1, borderWidth: 1, borderRadius: 10, padding: 10 },
  inputLabel: { fontSize: 10, marginBottom: 2 },
  input: { fontSize: 16, fontWeight: '600', padding: 0 },
  btn: { backgroundColor: '#8B5CF6', borderRadius: 10, paddingVertical: 12, alignItems: 'center', marginBottom: 16 },
  btnText: { color: '#fff', fontSize: 14, fontWeight: '700' },
  inputsSummary: { flexDirection: 'row', borderWidth: 1, borderRadius: 10, paddingVertical: 10, paddingHorizontal: 8, marginBottom: 12, justifyContent: 'space-around' },
  inputSumItem: { alignItems: 'center' },
  inputSumLabel: { fontSize: 10 },
  inputSumVal: { fontSize: 14, fontWeight: '700' },
  scenarioRow: { flexDirection: 'row', gap: 6, marginBottom: 12, flexWrap: 'wrap' },
  scenarioTab: { paddingHorizontal: 12, paddingVertical: 6, borderRadius: 16, borderWidth: 1 },
  scenarioText: { fontSize: 12, fontWeight: '600' },
  scenarioCard: { borderWidth: 1, borderRadius: 12, padding: 16 },
  scenarioCardTitle: { fontSize: 13, fontWeight: '700', marginBottom: 4 },
  bigNum: { fontSize: 28, fontWeight: '800', marginBottom: 2 },
  bigLabel: { fontSize: 12, marginBottom: 14 },
  scenarioStats: { flexDirection: 'row', justifyContent: 'space-around' },
  scenarioStat: { alignItems: 'center' },
  sStatLabel: { fontSize: 10 },
  sStatVal: { fontSize: 14, fontWeight: '700' },
  barRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 6 },
  barLabel: { width: 34, fontSize: 10, fontWeight: '600', textTransform: 'capitalize' },
  barBg: { flex: 1, height: 8, borderRadius: 4, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4 },
  barVal: { width: 56, fontSize: 11, fontWeight: '600', textAlign: 'right' },
  subhead: { fontSize: 14, fontWeight: '700', marginBottom: 8 },
  mileRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8, borderBottomWidth: 1 },
  mileYear: { fontSize: 13, fontWeight: '500' },
  mileVal: { fontSize: 14, fontWeight: '700', textAlign: 'right' },
  mileRet: { fontSize: 11, textAlign: 'right' },
});
