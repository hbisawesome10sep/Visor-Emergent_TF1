import { useState } from 'react';

type DatePickerTarget = 'goal_deadline' | 'holding_buy_date' | 'sip_start_date';

export function useDatePicker() {
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [datePickerTarget, setDatePickerTarget] = useState<DatePickerTarget>('goal_deadline');
  const [datePickerValue, setDatePickerValue] = useState(new Date());

  const openDatePicker = (target: DatePickerTarget, initialValue?: Date) => {
    setDatePickerTarget(target);
    setDatePickerValue(initialValue || new Date());
    setShowDatePicker(true);
  };

  const closeDatePicker = () => {
    setShowDatePicker(false);
  };

  return {
    showDatePicker,
    datePickerTarget,
    datePickerValue,
    setDatePickerValue,
    openDatePicker,
    closeDatePicker,
  };
}
