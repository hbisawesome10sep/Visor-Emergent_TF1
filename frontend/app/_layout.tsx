import { useEffect, useCallback } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, Platform } from 'react-native';
import {
  useFonts,
  DMSans_400Regular,
  DMSans_500Medium,
  DMSans_600SemiBold,
  DMSans_700Bold,
} from '@expo-google-fonts/dm-sans';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider, useAuth } from '../src/context/AuthContext';
import { ThemeProvider, useTheme } from '../src/context/ThemeContext';
import { SecurityProvider, useSecurity } from '../src/context/SecurityContext';
import { ScreenProvider } from '../src/context/ScreenContext';
import { ExperienceModeProvider } from '../src/context/ExperienceModeContext';
import { LockScreen } from '../src/components/LockScreen';
import { SecuritySetupScreen } from '../src/components/SecuritySetupScreen';
import { ModeNudge } from '../src/components/experience/ModeNudge';

SplashScreen.preventAutoHideAsync();

function SecurityLayer({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  const { isLocked, isSecuritySetupDone, isPinSetup, securityLoading } = useSecurity();

  // Wait for security state to load from AsyncStorage before deciding what to show
  if (token && securityLoading) {
    return (
      <>
        {children}
        <View style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: '#000', justifyContent: 'center', alignItems: 'center', zIndex: 99999 }}>
          <ActivityIndicator size="large" color="#10B981" />
        </View>
      </>
    );
  }

  return (
    <>
      {children}
      {token && !isSecuritySetupDone && <SecuritySetupScreen />}
      {token && isSecuritySetupDone && isLocked && isPinSetup && <LockScreen />}
      {/* AI Mode Upgrade Nudge */}
      {token && <ModeNudge />}
    </>
  );
}

function InnerLayout() {
  const { isDark, colors } = useTheme();
  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <SecurityLayer>
        <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
          <Stack.Screen name="index" />
          <Stack.Screen name="(auth)" />
          <Stack.Screen name="(tabs)" />
        </Stack>
      </SecurityLayer>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    DMSans_400Regular,
    DMSans_500Medium,
    DMSans_600SemiBold,
    DMSans_700Bold,
  });

  // On web, load DM Sans via Google Fonts CDN
  useEffect(() => {
    if (Platform.OS === 'web') {
      const link = document.createElement('link');
      link.href = 'https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap';
      link.rel = 'stylesheet';
      document.head.appendChild(link);
    }
  }, []);

  const isReady = fontsLoaded || fontError || Platform.OS === 'web';

  const onLayoutReady = useCallback(async () => {
    if (isReady) {
      await SplashScreen.hideAsync();
    }
  }, [isReady]);

  useEffect(() => {
    onLayoutReady();
  }, [onLayoutReady]);

  if (!isReady) {
    return (
      <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#000' }}>
        <ActivityIndicator size="large" color="#10B981" />
      </View>
    );
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <ExperienceModeProvider>
          <SecurityProvider>
            <ScreenProvider>
              <InnerLayout />
            </ScreenProvider>
          </SecurityProvider>
        </ExperienceModeProvider>
      </AuthProvider>
    </ThemeProvider>
  );
}
