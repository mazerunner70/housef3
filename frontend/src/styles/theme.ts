export const colors = {
  primaryBrand: "#2C3E50", // Midnight Blue
  secondaryBrand: "#3498DB", // Peter River Blue

  backgroundLight: "#F8F9FA", // Very Light Gray
  backgroundSubtle: "#ECF0F1", // Clouds
  bordersDividers: "#BDC3C7", // Silver

  textPrimary: "#212529", // Near Black
  textSecondary: "#7F8C8D", // Asbestos
  textDisabled: "#B0BEC5", // Light Gray Blue

  accent: "#E67E22", // Carrot Orange
  success: "#2ECC71", // Emerald Green
  warning: "#F1C40F", // Sun Flower Yellow
  errorDanger: "#E74C3C", // Alizarin Crimson
  info: "#3498DB", // Peter River Blue
};

export const typography = {
  primaryFont: "'Inter', sans-serif",
  baseFontSize: "15px",
  lineHeightBody: 1.6,
  h1: "32px",
  h2: "26px",
  h3: "20px",
  h4: "16px",
  bodyText: "15px",
  smallCaptionText: "13px",
  buttonText: "14px",

  fontWeightNormal: 400,
  fontWeightMedium: 500,
  fontWeightSemiBold: 600,
  fontWeightBold: 700,
};

export const spacing = {
  baseUnit: "4px",
  xs: "4px",   // 1 * baseUnit
  s: "8px",    // 2 * baseUnit
  m: "12px",   // 3 * baseUnit
  l: "16px",   // 4 * baseUnit
  xl: "24px",  // 6 * baseUnit
  xxl: "32px", // 8 * baseUnit
};

export const borders = {
  radiusSmall: "4px",
  radiusMedium: "8px",
  borderWidth: "1px",
  borderColor: colors.bordersDividers,
};

export const shadows = {
  subtle: "0 2px 4px rgba(0,0,0,0.05)",
};

export const forms = {
  inputBackground: "#FFFFFF",
  inputBorder: `1px solid ${colors.bordersDividers}`,
  inputFocusBorderColor: colors.secondaryBrand,
  inputPadding: `${spacing.s} ${spacing.m}`, // 8px 12px
  labelFontSize: typography.smallCaptionText, // 13px or 14px, let's use smallCaption
};

export const buttons = {
  paddingStandard: `${spacing.s} ${spacing.xl}`, // 8px 24px
  paddingCompact: `6px ${spacing.l}`,       // 6px 16px
  heightStandard: "40px",
  heightCompact: "36px",
};

// It's often useful to have a theme object that combines all these
// if you're using a ThemeProvider from a library like styled-components
export const defaultTheme = {
  colors,
  typography,
  spacing,
  borders,
  shadows,
  forms,
  buttons,
}; 