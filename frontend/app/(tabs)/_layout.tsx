import { Tabs } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useTheme } from '../../src/context/ThemeContext';
import { Platform, View } from 'react-native';

export default function TabLayout() {
  const { colors, isDark } = useTheme();

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: isDark ? '#52525B' : '#A1A1AA',
        tabBarStyle: {
          backgroundColor: isDark ? '#000000' : '#FFFFFF',
          borderTopColor: isDark ? '#18181B' : '#E4E4E7',
          borderTopWidth: 1,
          height: Platform.OS === 'ios' ? 88 : 64,
          paddingBottom: Platform.OS === 'ios' ? 28 : 8,
          paddingTop: 8,
          elevation: 0,
        },
        tabBarLabelStyle: {
          fontFamily: 'Outfit', fontWeight: '600' as any,
          fontSize: 10,
          letterSpacing: 0.3,
          textTransform: 'uppercase',
        },
      }}
    >
      <Tabs.Screen
        name="index"
        options={{
          title: 'Dashboard',
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? {
              shadowColor: color,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: isDark ? 0.6 : 0,
              shadowRadius: 8,
            } : undefined}>
              <MaterialCommunityIcons name="view-dashboard-outline" size={24} color={color} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="transactions"
        options={{
          title: 'Transactions',
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? {
              shadowColor: color,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: isDark ? 0.6 : 0,
              shadowRadius: 8,
            } : undefined}>
              <MaterialCommunityIcons name="swap-horizontal-circle-outline" size={24} color={color} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="insights"
        options={{
          title: 'Insights',
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? {
              shadowColor: color,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: isDark ? 0.6 : 0,
              shadowRadius: 8,
            } : undefined}>
              <MaterialCommunityIcons name="chart-arc" size={24} color={color} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="investments"
        options={{
          title: 'Invest',
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? {
              shadowColor: color,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: isDark ? 0.6 : 0,
              shadowRadius: 8,
            } : undefined}>
              <MaterialCommunityIcons name="chart-timeline-variant-shimmer" size={24} color={color} />
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: 'Settings',
          tabBarIcon: ({ color, focused }) => (
            <View style={focused ? {
              shadowColor: color,
              shadowOffset: { width: 0, height: 0 },
              shadowOpacity: isDark ? 0.6 : 0,
              shadowRadius: 8,
            } : undefined}>
              <MaterialCommunityIcons name="cog-outline" size={24} color={color} />
            </View>
          ),
        }}
      />
    </Tabs>
  );
}
