import { aliases, mdi } from "vuetify/iconsets/mdi-svg";
import type { ThemeDefinition } from "vuetify";

/**
 * Dark-first palette for an inspection tool: neutral greys so model colour is the
 * only saturated thing on screen, one accent, and separation carried by 1px
 * borders rather than shadows.
 */
const cadDark: ThemeDefinition = {
  dark: true,
  colors: {
    background: "#0e1013",
    surface: "#16191e",
    "surface-bright": "#2c333c",
    "surface-light": "#272d35",
    "surface-variant": "#1e232a",
    "on-surface-variant": "#c3cad4",
    primary: "#4c8dff",
    "primary-darken-1": "#2f6fe0",
    secondary: "#5c6675",
    "secondary-darken-1": "#47536b",
    error: "#ff6b6b",
    info: "#4c8dff",
    success: "#4ec9a5",
    warning: "#e0b450",
    "on-background": "#e4e7ec",
    "on-surface": "#e4e7ec",
  },
  variables: {
    "border-color": "#5c6675",
    "border-opacity": 0.5,
    "high-emphasis-opacity": 0.94,
    "medium-emphasis-opacity": 0.68,
    "disabled-opacity": 0.36,
    "theme-overlay-multiplier": 1,
  },
};

/** Same roles inverted, so the tool stays usable when the OS asks for light. */
const cadLight: ThemeDefinition = {
  dark: false,
  colors: {
    background: "#eef0f3",
    surface: "#ffffff",
    "surface-bright": "#ffffff",
    "surface-light": "#e8ebef",
    "surface-variant": "#f4f6f8",
    "on-surface-variant": "#3d4551",
    primary: "#1f6feb",
    "primary-darken-1": "#1558c4",
    secondary: "#5a6472",
    "secondary-darken-1": "#414b58",
    error: "#d13b3b",
    info: "#1f6feb",
    success: "#1f8a68",
    warning: "#9a6b00",
    "on-background": "#161a20",
    "on-surface": "#161a20",
  },
  variables: {
    "border-color": "#8b95a3",
    "border-opacity": 0.55,
    "high-emphasis-opacity": 0.92,
    "medium-emphasis-opacity": 0.66,
    "disabled-opacity": 0.38,
    "theme-overlay-multiplier": 1,
  },
};

export const themes = { cadDark, cadLight };

export const defaultThemeName = () =>
  window.matchMedia("(prefers-color-scheme: dark)").matches ? "cadDark" : "cadLight";

/**
 * Vuetify's own icons (checkbox, chevron, dropdown caret, clear) default to the
 * MDI *font*, which this project does not install — they were previously patched
 * with hardcoded white data-URI backgrounds that broke in light theme. The
 * mdi-svg set inlines the same glyphs as SVG paths and inherits currentColor.
 */
export const icons = {
  defaultSet: "mdi",
  aliases,
  sets: { mdi },
};
