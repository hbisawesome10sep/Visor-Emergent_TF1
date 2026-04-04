"""
Script to refactor investments.tsx to use custom hooks
"""

# Read original file
with open('/app/frontend/app/(tabs)/investments.tsx', 'r') as f:
    lines = f.readlines()

# Find the component start
component_start = None
for i, line in enumerate(lines):
    if 'export default function InvestmentsScreen()' in line:
        component_start = i
        break

if component_start is None:
    print("Could not find component start")
    exit(1)

# New imports to add
new_imports = """import {
  useInvestmentData,
  useHoldingsManager,
  useDatePicker,
  useRiskProfile,
  useGoalsManager,
  useSIPManager,
} from '../../src/hooks/investments';
"""

# Find where to insert new imports (after existing imports from investments)
import_insert_idx = None
for i, line in enumerate(lines[:50]):
    if "from '../../src/components/investments'" in line:
        # Find end of this import (might be multiline)
        j = i
        while j < len(lines) and ');' not in lines[j]:
            j += 1
        import_insert_idx = j + 1
        break

# New component body (just the state initialization part)
hook_initialization = '''  const { token } = useAuth();
  const { colors, isDark } = useTheme();
  const { setCurrentScreen } = useScreenContext();
  const insets = useSafeAreaInsets();
  const HEADER_HEIGHT = 70 + insets.top;

  // Custom hooks for data & state management
  const {
    marketData, stats, portfolio, goals, setGoals, holdingsData, rebalanceData,
    recurringData, sipSuggestions, setSipSuggestions,
    riskProfile, setRiskProfile, riskScore, setRiskScore, riskBreakdown, setRiskBreakdown,
    riskSaved, setRiskSaved, loading, refreshing, fetchData, onRefresh, fadeAnim,
  } = useInvestmentData(token);

  const {
    showHoldingModal, setShowHoldingModal, showCasModal, setShowCasModal,
    holdingForm, setHoldingForm, casPassword, setCasPassword,
    uploadingStatement, setUploadingStatement, refreshingPrices,
    handleRefreshPrices, handleStatementUpload, handleClearHoldings,
  } = useHoldingsManager(token, fetchData);

  const {
    showDatePicker, datePickerTarget, datePickerValue, setDatePickerValue,
    openDatePicker, closeDatePicker,
  } = useDatePicker();

  const {
    showRiskModal, setShowRiskModal, riskStep, setRiskStep,
    riskAnswers, showRiskResult, setShowRiskResult,
    handleRiskAnswer, handleSubmitRiskProfile, resetRiskAssessment,
  } = useRiskProfile(token, fetchData);

  const {
    showGoalModal, setShowGoalModal, editGoal, goalForm, setGoalForm,
    saving: savingGoal, handleAddGoal, handleEditGoal, handleSaveGoal, handleDeleteGoal,
  } = useGoalsManager(token, fetchData);

  const {
    showSipModal, setShowSipModal, editSip, sipForm, setSipForm,
    saving: savingSip, handleAddSip, handleEditSip, handleSaveSip, handleDeleteSip,
  } = useSIPManager(token, fetchData);

  const [showEMITracker, setShowEMITracker] = useState(false);
'''

print("✓ Refactoring script prepared")
print(f"  - Component starts at line {component_start}")
print(f"  - Will insert imports at line {import_insert_idx}")
print("  - Ready to update file")
