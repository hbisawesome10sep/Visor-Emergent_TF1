import { useState, useCallback } from 'react';
import { Alert } from 'react-native';

type FrequencyOption = 'Quarter' | 'Month' | 'Year' | 'Custom';

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

export function useFrequencyFilter(
  setSelectedFrequency: (freq: FrequencyOption) => void,
  setDateRange: (range: { start: Date; end: Date }) => void
) {
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [customStartDate, setCustomStartDate] = useState(new Date(new Date().getFullYear(), 0, 1));
  const [customEndDate, setCustomEndDate] = useState(new Date());
  const [showNativePicker, setShowNativePicker] = useState(false);
  const [activePickerField, setActivePickerField] = useState<'start' | 'end'>('start');

  const handleFrequencyChange = useCallback((freq: FrequencyOption) => {
    if (freq === 'Custom') {
      const fy = getFinancialYear();
      setCustomStartDate(fy.start);
      setCustomEndDate(new Date());
      setShowDatePicker(true);
    } else {
      setSelectedFrequency(freq);
    }
  }, [setSelectedFrequency]);

  const handleApplyCustomRange = useCallback(() => {
    if (customStartDate > customEndDate) {
      Alert.alert('Invalid Range', 'Start date must be before end date');
      return;
    }
    setDateRange({ start: customStartDate, end: customEndDate });
    setSelectedFrequency('Custom');
    setShowDatePicker(false);
  }, [customStartDate, customEndDate, setDateRange, setSelectedFrequency]);

  const openDatePicker = useCallback((field: 'start' | 'end') => {
    setActivePickerField(field);
    setShowNativePicker(true);
  }, []);

  const handleNativeDateChange = useCallback((event: any, selectedDate?: Date) => {
    setShowNativePicker(false);
    if (event.type === 'dismissed' || !selectedDate) return;
    if (activePickerField === 'start') {
      setCustomStartDate(selectedDate);
    } else {
      setCustomEndDate(selectedDate);
    }
  }, [activePickerField]);

  return {
    showDatePicker,
    setShowDatePicker,
    customStartDate,
    customEndDate,
    showNativePicker,
    activePickerField,
    handleFrequencyChange,
    handleApplyCustomRange,
    openDatePicker,
    handleNativeDateChange,
  };
}
