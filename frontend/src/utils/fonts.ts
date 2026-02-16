import { Platform } from 'react-native';

// Font utility that works across web and native
// On web: uses Google Fonts family names loaded via CSS
// On native: uses expo-google-fonts registered names

const isWeb = Platform.OS === 'web';

export const Fonts = {
  spaceGrotesk: {
    regular: isWeb ? 'Space Grotesk' : 'SpaceGrotesk_400Regular',
    medium: isWeb ? 'Space Grotesk' : 'SpaceGrotesk_500Medium',
    semiBold: isWeb ? 'Space Grotesk' : 'SpaceGrotesk_600SemiBold',
    bold: isWeb ? 'Space Grotesk' : 'SpaceGrotesk_700Bold',
  },
  outfit: {
    regular: isWeb ? 'Outfit' : 'Outfit_400Regular',
    medium: isWeb ? 'Outfit' : 'Outfit_500Medium',
    semiBold: isWeb ? 'Outfit' : 'Outfit_600SemiBold',
    bold: isWeb ? 'Outfit' : 'Outfit_700Bold',
    extraBold: isWeb ? 'Outfit' : 'Outfit_800ExtraBold',
  },
} as const;

// Shorthand font style creators for common patterns
export const fontBold = { fontFamily: Fonts.spaceGrotesk.bold, ...(isWeb && { fontWeight: '700' as const }) };
export const fontSemiBold = { fontFamily: Fonts.outfit.semiBold, ...(isWeb && { fontWeight: '600' as const }) };
export const fontMedium = { fontFamily: Fonts.outfit.medium, ...(isWeb && { fontWeight: '500' as const }) };
export const fontRegular = { fontFamily: Fonts.outfit.regular, ...(isWeb && { fontWeight: '400' as const }) };
export const fontHeading = { fontFamily: Fonts.spaceGrotesk.bold, ...(isWeb && { fontWeight: '700' as const }) };
export const fontNumeric = { fontFamily: Fonts.spaceGrotesk.bold, ...(isWeb && { fontWeight: '700' as const }) };
