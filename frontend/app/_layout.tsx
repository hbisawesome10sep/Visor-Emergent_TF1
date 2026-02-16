import { useEffect, useCallback, useState } from 'react';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { View, ActivityIndicator, Platform } from 'react-native';
import {
  useFonts,
  SpaceGrotesk_400Regular,
  SpaceGrotesk_500Medium,
  SpaceGrotesk_600SemiBold,
  SpaceGrotesk_700Bold,
} from '@expo-google-fonts/space-grotesk';
import {
  Outfit_400Regular,
  Outfit_500Medium,
  Outfit_600SemiBold,
  Outfit_700Bold,
  Outfit_800ExtraBold,
} from '@expo-google-fonts/outfit';
import * as SplashScreen from 'expo-splash-screen';
import { AuthProvider } from '../src/context/AuthContext';
import { ThemeProvider, useTheme } from '../src/context/ThemeContext';

SplashScreen.preventAutoHideAsync();

function InnerLayout() {
  const { isDark, colors } = useTheme();
  return (
    <>
      <StatusBar style={isDark ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: colors.background } }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [fontsLoaded, fontError] = useFonts({
    SpaceGrotesk_400Regular,
    SpaceGrotesk_500Medium,
    SpaceGrotesk_600SemiBold,
    SpaceGrotesk_700Bold,
    Outfit_400Regular,
    Outfit_500Medium,
    Outfit_600SemiBold,
    Outfit_700Bold,
    Outfit_800ExtraBold,
  });

  // On web, load Google Fonts via CSS and create aliases for expo font naming
  useEffect(() => {
    if (Platform.OS === 'web') {
      const style = document.createElement('style');
      style.textContent = `
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@400;500;600;700;800&family=Space+Grotesk:wght@400;500;600;700&display=swap');

        [style*="SpaceGrotesk_400Regular"] { font-family: 'Space Grotesk', sans-serif !important; font-weight: 400 !important; }
        [style*="SpaceGrotesk_500Medium"] { font-family: 'Space Grotesk', sans-serif !important; font-weight: 500 !important; }
        [style*="SpaceGrotesk_600SemiBold"] { font-family: 'Space Grotesk', sans-serif !important; font-weight: 600 !important; }
        [style*="SpaceGrotesk_700Bold"] { font-family: 'Space Grotesk', sans-serif !important; font-weight: 700 !important; }
        [style*="Outfit_400Regular"] { font-family: 'Outfit', sans-serif !important; font-weight: 400 !important; }
        [style*="Outfit_500Medium"] { font-family: 'Outfit', sans-serif !important; font-weight: 500 !important; }
        [style*="Outfit_600SemiBold"] { font-family: 'Outfit', sans-serif !important; font-weight: 600 !important; }
        [style*="Outfit_700Bold"] { font-family: 'Outfit', sans-serif !important; font-weight: 700 !important; }
        [style*="Outfit_800ExtraBold"] { font-family: 'Outfit', sans-serif !important; font-weight: 800 !important; }
      `;
      document.head.appendChild(style);
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
        <ActivityIndicator size="large" color="#00FFD1" />
      </View>
    );
  }

  return (
    <ThemeProvider>
      <AuthProvider>
        <InnerLayout />
      </AuthProvider>
    </ThemeProvider>
  );
}
