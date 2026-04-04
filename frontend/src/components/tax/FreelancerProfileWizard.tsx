import React, { useState, useEffect } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, TextInput, ScrollView, ActivityIndicator, Alert, Modal } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { apiRequest } from '../../utils/api';
import { formatINRShort } from '../../utils/formatters';
import { Accent } from '../../utils/theme';

interface FreelancerProfileWizardProps {
  token: string;
  colors: any;
  isDark: boolean;
  visible: boolean;
  onClose: () => void;
  onSaved: () => void;
}

const PROFESSIONS = [
  { id: 'freelance_developer', label: 'Software Developer', icon: 'code-tags' },
  { id: 'freelance_designer', label: 'Designer/Artist', icon: 'palette' },
  { id: 'consultant', label: 'Consultant', icon: 'account-tie' },
  { id: 'freelance_writer', label: 'Writer/Content Creator', icon: 'pencil' },
  { id: 'doctor', label: 'Doctor/Medical', icon: 'medical-bag' },
  { id: 'lawyer', label: 'Lawyer/Legal', icon: 'gavel' },
  { id: 'chartered_accountant', label: 'CA/Accountant', icon: 'calculator' },
  { id: 'architect', label: 'Architect', icon: 'office-building' },
  { id: 'engineer', label: 'Engineer', icon: 'cog' },
  { id: 'other_professional', label: 'Other Professional', icon: 'account' },
];

export const FreelancerProfileWizard: React.FC<FreelancerProfileWizardProps> = ({
  token, colors, isDark, visible, onClose, onSaved,
}) => {
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [profession, setProfession] = useState('');
  const [grossReceipts, setGrossReceipts] = useState('');
  const [usePresumptive, setUsePresumptive] = useState(true);
  const [expenses, setExpenses] = useState('');
  const [gstRegistered, setGstRegistered] = useState(false);
  const [gstNumber, setGstNumber] = useState('');
  const [computation, setComputation] = useState<any>(null);

  const resetForm = () => {
    setStep(1);
    setProfession('');
    setGrossReceipts('');
    setUsePresumptive(true);
    setExpenses('');
    setGstRegistered(false);
    setGstNumber('');
    setComputation(null);
  };

  const handleSave = async () => {
    if (!profession || !grossReceipts) {
      Alert.alert('Missing Info', 'Please fill profession and gross receipts');
      return;
    }

    setSaving(true);
    try {
      const result = await apiRequest('/tax/freelancer-profile', {
        method: 'POST',
        token,
        body: {
          profession,
          gross_receipts: parseFloat(grossReceipts.replace(/,/g, '')),
          use_presumptive: usePresumptive,
          expenses_claimed: expenses ? parseFloat(expenses.replace(/,/g, '')) : null,
          gst_registered: gstRegistered,
          gst_number: gstNumber || null,
          fy: '2025-26',
        },
      });
      setComputation(result.profile.computation);
      setStep(3); // Show summary
      onSaved();
    } catch (e: any) {
      Alert.alert('Error', e.message || 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (!visible) return null;

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View style={[styles.modalOverlay, { backgroundColor: 'rgba(0,0,0,0.7)' }]}>
        <View style={[styles.modalContent, { backgroundColor: isDark ? '#0a0a0b' : '#fff' }]}>
          {/* Header */}
          <View style={styles.modalHeader}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
              <View style={[styles.iconWrap, { backgroundColor: 'rgba(139,92,246,0.12)' }]}>
                <MaterialCommunityIcons name="laptop" size={20} color="#8B5CF6" />
              </View>
              <View>
                <Text style={[styles.modalTitle, { color: colors.textPrimary }]}>
                  Freelancer Profile
                </Text>
                <Text style={[styles.modalSubtitle, { color: colors.textSecondary }]}>
                  Section 44ADA Presumptive Taxation
                </Text>
              </View>
            </View>
            <TouchableOpacity onPress={() => { resetForm(); onClose(); }}>
              <MaterialCommunityIcons name="close" size={24} color={colors.textSecondary} />
            </TouchableOpacity>
          </View>

          {/* Progress */}
          <View style={styles.progressRow}>
            {[1, 2, 3].map(s => (
              <View key={s} style={[styles.progressDot, { 
                backgroundColor: s <= step ? '#8B5CF6' : isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' 
              }]} />
            ))}
          </View>

          <ScrollView style={{ flex: 1 }} showsVerticalScrollIndicator={false}>
            {/* Step 1: Profession Selection */}
            {step === 1 && (
              <View style={styles.stepContent}>
                <Text style={[styles.stepTitle, { color: colors.textPrimary }]}>
                  Select Your Profession
                </Text>
                <View style={styles.professionGrid}>
                  {PROFESSIONS.map(p => (
                    <TouchableOpacity
                      key={p.id}
                      data-testid={`profession-${p.id}`}
                      style={[styles.professionChip, {
                        backgroundColor: profession === p.id 
                          ? (isDark ? 'rgba(139,92,246,0.2)' : 'rgba(139,92,246,0.1)')
                          : (isDark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.03)'),
                        borderColor: profession === p.id ? '#8B5CF6' : 'transparent',
                      }]}
                      onPress={() => setProfession(p.id)}
                    >
                      <MaterialCommunityIcons 
                        name={p.icon as any} 
                        size={18} 
                        color={profession === p.id ? '#8B5CF6' : colors.textSecondary} 
                      />
                      <Text style={[styles.professionLabel, { 
                        color: profession === p.id ? '#8B5CF6' : colors.textPrimary 
                      }]}>
                        {p.label}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
                <TouchableOpacity
                  style={[styles.nextBtn, { opacity: profession ? 1 : 0.5 }]}
                  onPress={() => profession && setStep(2)}
                  disabled={!profession}
                >
                  <Text style={styles.nextBtnText}>Next</Text>
                  <MaterialCommunityIcons name="arrow-right" size={18} color="#fff" />
                </TouchableOpacity>
              </View>
            )}

            {/* Step 2: Income Details */}
            {step === 2 && (
              <View style={styles.stepContent}>
                <Text style={[styles.stepTitle, { color: colors.textPrimary }]}>
                  Income Details (FY 2025-26)
                </Text>

                <View style={styles.inputGroup}>
                  <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>
                    Total Gross Receipts (Annual)
                  </Text>
                  <View style={[styles.inputWrapper, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
                    <Text style={[styles.inputPrefix, { color: colors.textSecondary }]}>₹</Text>
                    <TextInput
                      data-testid="gross-receipts-input"
                      style={[styles.input, { color: colors.textPrimary }]}
                      value={grossReceipts}
                      onChangeText={setGrossReceipts}
                      keyboardType="numeric"
                      placeholder="0"
                      placeholderTextColor={colors.textSecondary}
                    />
                  </View>
                  <Text style={[styles.inputHint, { color: colors.textSecondary }]}>
                    44ADA limit: ₹75 Lakhs
                  </Text>
                </View>

                {/* Presumptive Toggle */}
                <TouchableOpacity
                  style={[styles.toggleRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}
                  onPress={() => setUsePresumptive(!usePresumptive)}
                >
                  <View>
                    <Text style={[styles.toggleLabel, { color: colors.textPrimary }]}>
                      Use Presumptive Taxation (44ADA)
                    </Text>
                    <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>
                      50% of receipts treated as taxable profit
                    </Text>
                  </View>
                  <View style={[styles.toggleSwitch, { backgroundColor: usePresumptive ? '#8B5CF6' : (isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)') }]}>
                    <View style={[styles.toggleKnob, { transform: [{ translateX: usePresumptive ? 16 : 0 }] }]} />
                  </View>
                </TouchableOpacity>

                {/* Actual Expenses (if not presumptive) */}
                {!usePresumptive && (
                  <View style={styles.inputGroup}>
                    <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>
                      Actual Expenses Claimed
                    </Text>
                    <View style={[styles.inputWrapper, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
                      <Text style={[styles.inputPrefix, { color: colors.textSecondary }]}>₹</Text>
                      <TextInput
                        style={[styles.input, { color: colors.textPrimary }]}
                        value={expenses}
                        onChangeText={setExpenses}
                        keyboardType="numeric"
                        placeholder="0"
                        placeholderTextColor={colors.textSecondary}
                      />
                    </View>
                    <Text style={[styles.inputHint, { color: '#F59E0B' }]}>
                      ⚠️ Requires maintaining books & audit if profit &lt; 50%
                    </Text>
                  </View>
                )}

                {/* GST Toggle */}
                <TouchableOpacity
                  style={[styles.toggleRow, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}
                  onPress={() => setGstRegistered(!gstRegistered)}
                >
                  <View>
                    <Text style={[styles.toggleLabel, { color: colors.textPrimary }]}>
                      GST Registered
                    </Text>
                    <Text style={[styles.toggleDesc, { color: colors.textSecondary }]}>
                      Required if turnover &gt; ₹20L
                    </Text>
                  </View>
                  <View style={[styles.toggleSwitch, { backgroundColor: gstRegistered ? '#8B5CF6' : (isDark ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.2)') }]}>
                    <View style={[styles.toggleKnob, { transform: [{ translateX: gstRegistered ? 16 : 0 }] }]} />
                  </View>
                </TouchableOpacity>

                {gstRegistered && (
                  <View style={styles.inputGroup}>
                    <Text style={[styles.inputLabel, { color: colors.textSecondary }]}>GST Number</Text>
                    <View style={[styles.inputWrapper, { borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)' }]}>
                      <TextInput
                        style={[styles.input, { color: colors.textPrimary }]}
                        value={gstNumber}
                        onChangeText={setGstNumber}
                        placeholder="22AAAAA0000A1Z5"
                        placeholderTextColor={colors.textSecondary}
                        autoCapitalize="characters"
                      />
                    </View>
                  </View>
                )}

                <View style={styles.buttonRow}>
                  <TouchableOpacity style={[styles.backBtn, { borderColor: colors.textSecondary }]} onPress={() => setStep(1)}>
                    <MaterialCommunityIcons name="arrow-left" size={18} color={colors.textSecondary} />
                    <Text style={[styles.backBtnText, { color: colors.textSecondary }]}>Back</Text>
                  </TouchableOpacity>
                  <TouchableOpacity
                    style={[styles.nextBtn, { flex: 1, opacity: grossReceipts ? 1 : 0.5 }]}
                    onPress={handleSave}
                    disabled={!grossReceipts || saving}
                  >
                    {saving ? (
                      <ActivityIndicator size="small" color="#fff" />
                    ) : (
                      <>
                        <Text style={styles.nextBtnText}>Calculate</Text>
                        <MaterialCommunityIcons name="calculator" size={18} color="#fff" />
                      </>
                    )}
                  </TouchableOpacity>
                </View>
              </View>
            )}

            {/* Step 3: Computation Summary */}
            {step === 3 && computation && (
              <View style={styles.stepContent}>
                <View style={[styles.summaryCard, { backgroundColor: 'rgba(139,92,246,0.08)' }]}>
                  <MaterialCommunityIcons name="check-circle" size={40} color="#8B5CF6" />
                  <Text style={[styles.summaryTitle, { color: colors.textPrimary }]}>
                    Profile Saved!
                  </Text>
                  <Text style={[styles.summarySubtitle, { color: colors.textSecondary }]}>
                    {computation.method === 'presumptive_44ada' ? 'Section 44ADA Applied' : 'Actual Method Applied'}
                  </Text>
                </View>

                <View style={styles.computationGrid}>
                  <View style={[styles.computeItem, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
                    <Text style={[styles.computeLabel, { color: colors.textSecondary }]}>Gross Receipts</Text>
                    <Text style={[styles.computeValue, { color: colors.textPrimary }]}>
                      {formatINRShort(computation.gross_receipts)}
                    </Text>
                  </View>
                  <View style={[styles.computeItem, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
                    <Text style={[styles.computeLabel, { color: colors.textSecondary }]}>Deemed Expenses</Text>
                    <Text style={[styles.computeValue, { color: Accent.emerald }]}>
                      {formatINRShort(computation.deemed_expenses)}
                    </Text>
                  </View>
                  <View style={[styles.computeItem, { backgroundColor: 'rgba(139,92,246,0.08)' }]}>
                    <Text style={[styles.computeLabel, { color: colors.textSecondary }]}>Taxable Income</Text>
                    <Text style={[styles.computeValue, { color: '#8B5CF6', fontSize: 20 }]}>
                      {formatINRShort(computation.taxable_income)}
                    </Text>
                  </View>
                </View>

                {/* Notes */}
                <View style={[styles.notesSection, { backgroundColor: isDark ? 'rgba(255,255,255,0.03)' : 'rgba(0,0,0,0.02)' }]}>
                  <Text style={[styles.notesTitle, { color: colors.textPrimary }]}>Key Points</Text>
                  {computation.notes.map((note: string, idx: number) => (
                    <View key={idx} style={styles.noteItem}>
                      <MaterialCommunityIcons name="information-outline" size={14} color="#8B5CF6" />
                      <Text style={[styles.noteText, { color: colors.textSecondary }]}>{note}</Text>
                    </View>
                  ))}
                </View>

                <View style={styles.itrBadge}>
                  <MaterialCommunityIcons name="file-document-outline" size={16} color="#F59E0B" />
                  <Text style={[styles.itrText, { color: '#F59E0B' }]}>
                    ITR Form: {computation.itr_form}
                  </Text>
                </View>

                <TouchableOpacity style={styles.doneBtn} onPress={() => { resetForm(); onClose(); }}>
                  <Text style={styles.doneBtnText}>Done</Text>
                </TouchableOpacity>
              </View>
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, justifyContent: 'flex-end' },
  modalContent: { borderTopLeftRadius: 24, borderTopRightRadius: 24, maxHeight: '90%', paddingBottom: 34 },
  modalHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 16, borderBottomWidth: 1, borderBottomColor: 'rgba(255,255,255,0.06)' },
  iconWrap: { width: 44, height: 44, borderRadius: 12, justifyContent: 'center', alignItems: 'center' },
  modalTitle: { fontSize: 16, fontFamily: 'DM Sans', fontWeight: '700' },
  modalSubtitle: { fontSize: 12, fontFamily: 'DM Sans', marginTop: 2 },
  progressRow: { flexDirection: 'row', justifyContent: 'center', gap: 8, paddingVertical: 12 },
  progressDot: { width: 8, height: 8, borderRadius: 4 },
  stepContent: { padding: 16 },
  stepTitle: { fontSize: 15, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 16 },
  professionGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  professionChip: { flexDirection: 'row', alignItems: 'center', gap: 8, paddingHorizontal: 14, paddingVertical: 10, borderRadius: 10, borderWidth: 1, minWidth: '45%' },
  professionLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600' },
  inputGroup: { marginBottom: 16 },
  inputLabel: { fontSize: 12, fontFamily: 'DM Sans', fontWeight: '600', marginBottom: 6 },
  inputWrapper: { flexDirection: 'row', alignItems: 'center', borderWidth: 1, borderRadius: 10, paddingHorizontal: 12 },
  inputPrefix: { fontSize: 16, fontFamily: 'DM Sans', marginRight: 4 },
  input: { flex: 1, fontSize: 16, fontFamily: 'DM Sans', paddingVertical: 12 },
  inputHint: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 4 },
  toggleRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 14, borderRadius: 12, marginBottom: 12 },
  toggleLabel: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  toggleDesc: { fontSize: 11, fontFamily: 'DM Sans', marginTop: 2 },
  toggleSwitch: { width: 44, height: 24, borderRadius: 12, padding: 2 },
  toggleKnob: { width: 20, height: 20, borderRadius: 10, backgroundColor: '#fff' },
  buttonRow: { flexDirection: 'row', gap: 12, marginTop: 20 },
  backBtn: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 16, paddingVertical: 12, borderRadius: 10, borderWidth: 1 },
  backBtnText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '600' },
  nextBtn: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, backgroundColor: '#8B5CF6', paddingVertical: 14, borderRadius: 12, marginTop: 20 },
  nextBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
  summaryCard: { alignItems: 'center', padding: 24, borderRadius: 16, marginBottom: 20 },
  summaryTitle: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700', marginTop: 12 },
  summarySubtitle: { fontSize: 13, fontFamily: 'DM Sans', marginTop: 4 },
  computationGrid: { gap: 10, marginBottom: 16 },
  computeItem: { padding: 14, borderRadius: 12 },
  computeLabel: { fontSize: 11, fontFamily: 'DM Sans', marginBottom: 4 },
  computeValue: { fontSize: 18, fontFamily: 'DM Sans', fontWeight: '700' },
  notesSection: { padding: 14, borderRadius: 12, marginBottom: 16 },
  notesTitle: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700', marginBottom: 10 },
  noteItem: { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 8 },
  noteText: { fontSize: 11, fontFamily: 'DM Sans', flex: 1 },
  itrBadge: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 8, padding: 12, backgroundColor: 'rgba(245,158,11,0.1)', borderRadius: 10, marginBottom: 16 },
  itrText: { fontSize: 13, fontFamily: 'DM Sans', fontWeight: '700' },
  doneBtn: { backgroundColor: '#8B5CF6', paddingVertical: 14, borderRadius: 12, alignItems: 'center' },
  doneBtnText: { fontSize: 14, fontFamily: 'DM Sans', fontWeight: '700', color: '#fff' },
});
