/**
 * theme.ts
 * --------
 * Chart colors for each theme. Recharts draws SVG and needs real color values,
 * so these mirror the CSS variables in app/globals.css.
 */

export type Theme = "dark" | "light";

export interface ChartColors {
  volt: string;
  amp: string;
  temp: string;
  power: string;
  grid: string;
  axis: string;
  muted: string;
  ink: string;
  panel: string;
  warnBand: string;
  critBand: string;
  warnInk: string;
  critInk: string;
}

export const CHART_COLORS: Record<Theme, ChartColors> = {
  dark: {
    volt: "#3987e5",
    amp: "#d95926",
    temp: "#199e70",
    power: "#9085e9",
    grid: "rgba(148, 170, 230, 0.12)",
    axis: "rgba(148, 170, 230, 0.30)",
    muted: "#8392b2",
    ink: "#eaf0ff",
    panel: "#0e1629",
    warnBand: "rgba(250, 178, 25, 0.14)",
    critBand: "rgba(224, 82, 82, 0.18)",
    warnInk: "#fbc24a",
    critInk: "#f58a8a",
  },
  light: {
    volt: "#2a78d6",
    amp: "#eb6834",
    temp: "#1baf7a",
    power: "#6250d6",
    grid: "rgba(15, 30, 70, 0.08)",
    axis: "rgba(15, 30, 70, 0.22)",
    muted: "#5a6784",
    ink: "#0b1530",
    panel: "#ffffff",
    warnBand: "rgba(250, 178, 25, 0.18)",
    critBand: "rgba(208, 59, 59, 0.13)",
    warnInk: "#7a4f00",
    critInk: "#a32222",
  },
};
