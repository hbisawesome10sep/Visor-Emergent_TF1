import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet, Modal, ScrollView,
  TextInput, Switch, Alert, ActivityIndicator, Platform, KeyboardAvoidingView,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { Accent } from '../../utils/theme';

const STATES = [
  { label: 'Maharashtra', value: 'maharashtra', profTax: 2400 },
  { label: 'Karnataka', value: 'karnataka', profTax: 2400 },
  { label: 'West Bengal', value: 'west bengal', profTax: 2400 },
  { label: 'Andhra Pradesh', value: 'andhra pradesh', profTax: 2400 },
  { label: 'Telangana', value: 'telangana', profTax: 2400 },
  { label: 'Gujarat', value: 'gujarat', profTax: 2400 },
  { label: 'Kerala', value: 'kerala', profTax: 2400 },
  { label: 'Odisha', value: 'odisha', profTax: 2400 },
  { label: 'Tamil Nadu', value: 'tamil nadu', profTax: 1200 },
  { label: 'Madhya Pradesh', value: 'madhya pradesh', profTax: 2400 },
  { label: 'Bihar', value: 'bihar', profTax: 2500 },
  { label: 'Delhi', value: 'delhi', profTax: 0 },
  { label: 'Uttar Pradesh', value: 'uttar pradesh', profTax: 0 },
  { label: 'Rajasthan', value: 'rajasthan', profTax: 0 },
  { label: 'Punjab', value: 'punjab', profTax: 0 },
  { label: 'Haryana', value: 'haryana', profTax: 0 },
  { label: 'Other', value: 'other', profTax: 0 },
];

const METRO_CITIES = ['mumbai', 'delhi', 'kolkata', 'chennai', 'new delhi'];

interface Props {
  token: string;
  colors: any;
  isDark: boolean;
  existingProfile?: any;
  onSaved: (profile: any) => void;
}

interface WizardState {
  // Step 1
  employerName: string;
  city: string;
  state: string;
  cityType: 'metro' | 'non_metro';
  // Step 2
  basic: string;
  hra: string;
  special: string;
  lta: string;
  otherAllowances: string;
  annualBonus: string;
  // Step 3
  epf: string;
  profTax: string;
  tdsMonthly: string;
  isRentPaid: boolean;
  monthlyRent: string;
  landlordPAN: boolean;
}

export function SalaryProfileWizard({ token, colors, isDark, existingProfile, onSaved }: Props) {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [showStatePicker, setShowStatePicker] = useState(false);

  const defaults = existingProfile || {};
  const [form, setForm] = useState<WizardState>({
    employerName: defaults.employer_name || '',
    city: defaults.residence_city || '',
    state: defaults.state || '',
    cityType: defaults.city_type || 'non_metro',
    basic: defaults.monthly_basic?.toString() || '',
    hra: defaults.monthly_hra?.toString() || '',
    special: defaults.monthly_special_allowance?.toString() || '',
    lta: defaults.monthly_lta?.toString() || '',
    otherAllowances: defaults.monthly_other_allowances?.toString() || '',
    annualBonus: defaults.annual_bonus?.toString() || '',
    epf: defaults.employee_pf_monthly?.toString() || '',
    profTax: defaults.professional_tax_annual?.toString() || '',
    tdsMonthly: defaults.tds_monthly?.toString() || '',
    isRentPaid: defaults.is_rent_paid || false,
    monthlyRent: defaults.monthly_rent?.toString() || '',
    landlordPAN: defaults.landlord_pan_available || false,
  });

  const set = (key: keyof WizardState, value: any) => setForm(f => ({ ...f, [key]: value }));

  const grossMonthly = (
    parseFloat(form.basic || '0') +
    parseFloat(form.hra || '0') +
    parseFloat(form.special || '0') +
    parseFloat(form.lta || '0') / 12 +
    parseFloat(form.otherAllowances || '0')
  );

  const handleBasicChange = (v: string) => {
    set('basic', v);
    const b = parseFloat(v || '0');
    if (b > 0 && !form.epf) {
      set('epf', Math.round(Math.min(b * 0.12, 1800)).toString());
    }
  };

  const handleCityChange = (v: string) => {
    set('city', v);
    const isMetro = METRO_CITIES.includes(v.toLowerCase().trim());
    set('cityType', isMetro ? 'metro' : 'non_metro');
  };

  const handleStateSelect = (state: typeof STATES[0]) => {
    set('state', state.value);
    if (state.profTax > 0 && !form.profTax) {
      set('profTax', state.profTax.toString());
    }
    setShowStatePicker(false);
  };

  const save = async () => {
    if (!form.basic) { Alert.alert('Enter monthly basic salary'); return; }
    setSaving(true);
    try {
      const result = await apiRequest('/tax/salary-profile', {
        method: 'POST', token,
        body: {
          fy: '2025-26',
          employer_name: form.employerName,
          employment_type: 'salaried',
          monthly_basic: parseFloat(form.basic || '0'),
          monthly_hra: parseFloat(form.hra || '0'),
          monthly_special_allowance: parseFloat(form.special || '0'),
          monthly_lta: parseFloat(form.lta || '0') / 12,
          monthly_other_allowances: parseFloat(form.otherAllowances || '0'),
          annual_bonus: parseFloat(form.annualBonus || '0'),
          employee_pf_monthly: parseFloat(form.epf || '0'),
          professional_tax_annual: parseFloat(form.profTax || '0'),
          tds_monthly: parseFloat(form.tdsMonthly || '0'),
          residence_city: form.city,
          state: form.state,
          city_type: form.cityType,
          is_rent_paid: form.isRentPaid,
          monthly_rent: parseFloat(form.monthlyRent || '0'),
          landlord_pan_available: form.landlordPAN,
        },
      });
      onSaved(result.profile);
      setVisible(false);
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = [styles.input, {
    backgroundColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.04)',
    color: colors.textPrimary,
    borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
  }];
  const labelStyle = [styles.label, { color: colors.textSecondary }];

  return (
    <>
      {/* Trigger Card */}
      <TouchableOpacity
        data-testid="salary-profile-setup-card"
        style={[styles.triggerCard, {
          backgroundColor: isDark ? 'rgba(16,185,129,0.06)' : 'rgba(16,185,129,0.04)',
          borderColor: isDark ? 'rgba(16,185,129,0.25)' : 'rgba(16,185,129,0.18)',
        }]}
        onPress={() => setVisible(true)}
        activeOpacity={0.8}
      >
        <MaterialCommunityIcons name="currency-inr" size={16} color={Accent.emerald} />
        <View style={{ flex: 1, marginLeft: 10 }}>
          <Text style={[styles.triggerTitle, { color: colors.textPrimary }]}>
            {existingProfile ? 'Update Salary Profile' : 'Set Up Salary Profile'}
          </Text>
          <Text style={[styles.triggerSub, { color: colors.textSecondary }]}>
            {existingProfile
              ? `Gross: ₹${(existingProfile.gross_annual / 100000).toFixed(1)}L | HRA: ₹${(existingProfile.monthly_hra * 12 / 1000).toFixed(0)}K`
              : 'Enables HRA calculation, 80C EPF tracking & accurate tax'}
          </Text>
        </View>
        <MaterialCommunityIcons name="chevron-right" size={18} color={Accent.emerald} />
      </TouchableOpacity>

      {/* Modal */}
      <Modal visible={visible} animationType="slide" transparent>
        <KeyboardAvoidingView style={styles.overlay} behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
          <View style={[styles.sheet, { backgroundColor: isDark ? '#111827' : '#FFFFFF' }]}>
            {/* Sheet Header */}
            <View style={styles.sheetHeader}>
              <Text style={[styles.sheetTitle, { color: colors.textPrimary }]}>Salary Profile</Text>
              <TouchableOpacity onPress={() => setVisible(false)} style={styles.closeBtn}>
                <MaterialCommunityIcons name="close" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>

            {/* Step Indicator */}
            <View style={styles.steps}>
              {['Employment', 'Salary', 'Deductions'].map((s, i) => (
                <View key={i} style={styles.stepItem}>
                  <View style={[styles.stepDot, {
                    backgroundColor: step > i + 1 ? Accent.emerald : step === i + 1 ? '#F59E0B' : (isDark ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.1)'),
                  }]}>
                    {step > i + 1
                      ? <MaterialCommunityIcons name="check" size={10} color="#fff" />
                      : <Text style={styles.stepNum}>{i + 1}</Text>
                    }
                  </View>
                  <Text style={[styles.stepLabel, { color: step === i + 1 ? colors.textPrimary : colors.textSecondary }]}>{s}</Text>
                </View>
              ))}
            </View>

            <ScrollView style={styles.formScroll} showsVerticalScrollIndicator={false}>

              {/* STEP 1 */}
              {step === 1 && (
                <View style={styles.stepContent}>
                  <Text style={labelStyle}>Employer Name</Text>
                  <TextInput
                    data-testid="employer-name-input"
                    style={inputStyle} value={form.employerName}
                    onChangeText={v => set('employerName', v)}
                    placeholder="e.g. Tata Consultancy Services"
                    placeholderTextColor={colors.textSecondary}
                  />
                  <Text style={labelStyle}>City of Work</Text>
                  <TextInput
                    data-testid="city-input"
                    style={inputStyle} value={form.city}
                    onChangeText={handleCityChange}
                    placeholder="e.g. Mumbai, Bengaluru"
                    placeholderTextColor={colors.textSecondary}
                  />
                  {form.city.length > 0 && (
                    <View style={[styles.metroTag, {
                      backgroundColor: form.cityType === 'metro' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.1)',
                    }]}>
                      <MaterialCommunityIcons name="city-variant-outline" size={12} color={form.cityType === 'metro' ? Accent.emerald : '#F59E0B'} />
                      <Text style={[styles.metroTagText, { color: form.cityType === 'metro' ? Accent.emerald : '#F59E0B' }]}>
                        {form.cityType === 'metro' ? 'Metro city — HRA @ 50% of Basic' : 'Non-metro — HRA @ 40% of Basic'}
                      </Text>
                    </View>
                  )}
                  <Text style={labelStyle}>State</Text>
                  <TouchableOpacity
                    data-testid="state-picker-btn"
                    style={[inputStyle, styles.pickerBtn]}
                    onPress={() => setShowStatePicker(true)}
                  >
                    <Text style={{ color: form.state ? colors.textPrimary : colors.textSecondary, fontFamily: 'DM Sans', fontSize: 14 }}>
                      {STATES.find(s => s.value === form.state)?.label || 'Select state'}
                    </Text>
                    <MaterialCommunityIcons name="chevron-down" size={16} color={colors.textSecondary} />
                  </TouchableOpacity>
                </View>
              )}

              {/* STEP 2 */}
              {step === 2 && (
                <View style={styles.stepContent}>
                  <Text style={labelStyle}>Monthly Basic Salary *</Text>
                  <TextInput
                    data-testid="monthly-basic-input"
                    style={inputStyle} value={form.basic}
                    onChangeText={handleBasicChange}
                    keyboardType="numeric" placeholder="e.g. 50000"
                    placeholderTextColor={colors.textSecondary}
                  />
                  <Text style={labelStyle}>HRA Component (per month)</Text>
                  <TextInput
                    data-testid="monthly-hra-input"
                    style={inputStyle} value={form.hra}
                    onChangeText={v => set('hra', v)}
                    keyboardType="numeric" placeholder="e.g. 20000"
                    placeholderTextColor={colors.textSecondary}
                  />
                  <Text style={labelStyle}>Special Allowance (per month)</Text>
                  <TextInput style={inputStyle} value={form.special} onChangeText={v => set('special', v)} keyboardType="numeric" placeholder="e.g. 10000" placeholderTextColor={colors.textSecondary} />
                  <Text style={labelStyle}>LTA (annual)</Text>
                  <TextInput style={inputStyle} value={form.lta} onChangeText={v => set('lta', v)} keyboardType="numeric" placeholder="e.g. 30000" placeholderTextColor={colors.textSecondary} />
                  <Text style={labelStyle}>Annual Bonus (expected)</Text>
                  <TextInput style={inputStyle} value={form.annualBonus} onChangeText={v => set('annualBonus', v)} keyboardType="numeric" placeholder="e.g. 100000" placeholderTextColor={colors.textSecondary} />

                  {grossMonthly > 0 && (
                    <View style={[styles.grossCard, { backgroundColor: isDark ? 'rgba(245,158,11,0.08)' : 'rgba(245,158,11,0.06)', borderColor: 'rgba(245,158,11,0.2)' }]}>
                      <Text style={[styles.grossLabel, { color: colors.textSecondary }]}>Estimated Annual CTC</Text>
                      <Text style={[styles.grossValue, { color: '#F59E0B' }]}>
                        ₹{((grossMonthly * 12 + parseFloat(form.annualBonus || '0')) / 100000).toFixed(2)}L
                      </Text>
                    </View>
                  )}
                </View>
              )}

              {/* STEP 3 */}
              {step === 3 && (
                <View style={styles.stepContent}>
                  <Text style={[styles.sectionDivider, { color: '#F59E0B' }]}>Deductions</Text>
                  <Text style={labelStyle}>Employee PF (per month)</Text>
                  <TextInput
                    data-testid="epf-input"
                    style={inputStyle} value={form.epf}
                    onChangeText={v => set('epf', v)}
                    keyboardType="numeric" placeholder={`Auto: ₹${Math.round(Math.min(parseFloat(form.basic || '0') * 0.12, 1800))}`}
                    placeholderTextColor={colors.textSecondary}
                  />
                  <Text style={labelStyle}>Professional Tax (annual)</Text>
                  <TextInput
                    data-testid="prof-tax-input"
                    style={inputStyle} value={form.profTax}
                    onChangeText={v => set('profTax', v)}
                    keyboardType="numeric" placeholder="e.g. 2400 (from state)"
                    placeholderTextColor={colors.textSecondary}
                  />
                  <Text style={labelStyle}>Monthly TDS (by employer)</Text>
                  <TextInput
                    data-testid="tds-monthly-input"
                    style={inputStyle} value={form.tdsMonthly}
                    onChangeText={v => set('tdsMonthly', v)}
                    keyboardType="numeric" placeholder="e.g. 5000"
                    placeholderTextColor={colors.textSecondary}
                  />

                  <Text style={[styles.sectionDivider, { color: '#F59E0B', marginTop: 4 }]}>Housing</Text>
                  <View style={styles.switchRow}>
                    <View>
                      <Text style={[styles.switchLabel, { color: colors.textPrimary }]}>Do you pay rent?</Text>
                      <Text style={[styles.switchSub, { color: colors.textSecondary }]}>Enables HRA exemption calculation</Text>
                    </View>
                    <Switch
                      data-testid="rent-toggle"
                      value={form.isRentPaid}
                      onValueChange={v => set('isRentPaid', v)}
                      trackColor={{ false: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', true: 'rgba(245,158,11,0.5)' }}
                      thumbColor={form.isRentPaid ? '#F59E0B' : '#ccc'}
                    />
                  </View>
                  {form.isRentPaid && (
                    <>
                      <Text style={labelStyle}>Monthly Rent</Text>
                      <TextInput
                        data-testid="monthly-rent-input"
                        style={inputStyle} value={form.monthlyRent}
                        onChangeText={v => set('monthlyRent', v)}
                        keyboardType="numeric" placeholder="e.g. 25000"
                        placeholderTextColor={colors.textSecondary}
                      />
                      <View style={styles.switchRow}>
                        <Text style={[styles.switchLabel, { color: colors.textPrimary }]}>Landlord PAN available?</Text>
                        <Switch
                          value={form.landlordPAN}
                          onValueChange={v => set('landlordPAN', v)}
                          trackColor={{ false: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)', true: 'rgba(245,158,11,0.5)' }}
                          thumbColor={form.landlordPAN ? '#F59E0B' : '#ccc'}
                        />
                      </View>
                      {parseFloat(form.monthlyRent || '0') * 12 > 100000 && !form.landlordPAN && (
                        <View style={[styles.warningBanner, { backgroundColor: 'rgba(239,68,68,0.08)', borderColor: 'rgba(239,68,68,0.2)' }]}>
                          <MaterialCommunityIcons name="alert-outline" size={12} color="#EF4444" />
                          <Text style={[styles.warningText, { color: '#EF4444' }]}>
                            Landlord PAN mandatory for annual rent {'>'} ₹1L
                          </Text>
                        </View>
                      )}
                    </>
                  )}
                  <View style={{ height: 20 }} />
                </View>
              )}
            </ScrollView>

            {/* Navigation Buttons */}
            <View style={[styles.navRow, { borderTopColor: isDark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.06)' }]}>
              {step > 1 ? (
                <TouchableOpacity
                  style={[styles.backBtn, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}
                  onPress={() => setStep(s => s - 1)}
                >
                  <Text style={[styles.backBtnText, { color: colors.textSecondary }]}>Back</Text>
                </TouchableOpacity>
              ) : <View style={{ flex: 1 }} />}
              {step < 3 ? (
                <TouchableOpacity
                  data-testid="wizard-next-btn"
                  style={styles.nextBtn}
                  onPress={() => setStep(s => s + 1)}
                >
                  <Text style={styles.nextBtnText}>Next</Text>
                  <MaterialCommunityIcons name="arrow-right" size={16} color="#fff" />
                </TouchableOpacity>
              ) : (
                <TouchableOpacity
                  data-testid="wizard-save-btn"
                  style={[styles.nextBtn, { minWidth: 100 }]}
                  onPress={save}
                  disabled={saving}
                >
                  {saving
                    ? <ActivityIndicator size="small" color="#fff" />
                    : <Text style={styles.nextBtnText}>Save Profile</Text>
                  }
                </TouchableOpacity>
              )}
            </View>
          </View>
        </KeyboardAvoidingView>

        {/* State Picker Modal */}
        <Modal visible={showStatePicker} transparent animationType="fade">
          <TouchableOpacity style={styles.overlay} onPress={() => setShowStatePicker(false)} activeOpacity={1}>
            <View style={[styles.statePicker, { backgroundColor: isDark ? '#1F2937' : '#fff' }]}>
              <Text style={[styles.statePickerTitle, { color: colors.textPrimary }]}>Select State</Text>
              <ScrollView>
                {STATES.map(s => (
                  <TouchableOpacity
                    key={s.value}
                    style={[styles.stateRow, { borderBottomColor: isDark ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.05)' }]}
                    onPress={() => handleStateSelect(s)}
                  >
                    <Text style={[styles.stateName, { color: colors.textPrimary }]}>{s.label}</Text>
                    {s.profTax > 0
                      ? <Text style={[styles.stateTax, { color: colors.textSecondary }]}>PT: ₹{s.profTax}/yr</Text>
                      : <Text style={[styles.stateTaxNil, { color: colors.textSecondary }]}>No PT</Text>
                    }
                  </TouchableOpacity>
                ))}
              </ScrollView>
            </View>
          </TouchableOpacity>
        </Modal>
      </Modal>
    </>
  );
}

const styles = StyleSheet.create({
  overlay: { flex: 1, justifyContent: 'flex-end', backgroundColor: 'rgba(0,0,0,0.6)' },
  sheet: { borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '92%', paddingBottom: 20 },
  sheetHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 20, paddingBottom: 0 },
  sheetTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '800' },
  closeBtn: { padding: 4 },
  steps: { flexDirection: 'row', justifyContent: 'space-around', paddingHorizontal: 20, paddingVertical: 16 },
  stepItem: { alignItems: 'center', gap: 4 },
  stepDot: { width: 22, height: 22, borderRadius: 11, justifyContent: 'center', alignItems: 'center' },
  stepNum: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  stepLabel: { fontSize: 10, fontFamily: 'DM Sans', fontWeight: '600' },
  formScroll: { paddingHorizontal: 20, maxHeight: 420 },
  stepContent: { gap: 6 },
  label: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600', marginTop: 8, marginBottom: 2 },
  input: { height: 46, borderRadius: 10, paddingHorizontal: 14, fontSize: 14, fontFamily: 'DM Sans', borderWidth: 1 },
  pickerBtn: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  metroTag: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, paddingVertical: 6, borderRadius: 8, marginTop: 4 },
  metroTagText: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '600' },
  grossCard: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12, borderRadius: 10, borderWidth: 1, marginTop: 8 },
  grossLabel: { fontSize: 12, fontFamily: 'DM Sans' },
  grossValue: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '800' },
  sectionDivider: { fontSize: 11, fontFamily: 'DM Sans', fontWeight: '700', textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 12, marginBottom: 4 },
  switchRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 8 },
  switchLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  switchSub: { fontSize: 10, fontFamily: 'DM Sans', marginTop: 1 },
  warningBanner: { flexDirection: 'row', alignItems: 'center', gap: 6, padding: 8, borderRadius: 8, borderWidth: 1, marginTop: 4 },
  warningText: { fontSize: 11, fontFamily: 'DM Sans', flex: 1 },
  navRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingHorizontal: 20, paddingTop: 14, borderTopWidth: 1, gap: 12 },
  backBtn: { flex: 1, height: 46, borderRadius: 12, justifyContent: 'center', alignItems: 'center', borderWidth: 1 },
  backBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '600' },
  nextBtn: { flex: 1, height: 46, borderRadius: 12, backgroundColor: '#F59E0B', justifyContent: 'center', alignItems: 'center', flexDirection: 'row', gap: 6 },
  nextBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  // State picker
  statePicker: { margin: 20, borderRadius: 16, padding: 16, maxHeight: 400 },
  statePickerTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 12 },
  stateRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1 },
  stateName: { fontSize: 14, fontFamily: 'DM Sans' },
  stateTax: { fontSize: 12, fontFamily: 'DM Sans' },
  stateTaxNil: { fontSize: 11, fontFamily: 'DM Sans', fontStyle: 'italic' },
  // Trigger
  triggerCard: { flexDirection: 'row', alignItems: 'center', padding: 14, borderRadius: 14, borderWidth: 1, marginBottom: 14 },
  triggerTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  triggerSub: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 2 },
});
