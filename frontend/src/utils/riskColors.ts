import type { RiskLevel } from '../types';

// ── RGBA arrays for deck.gl layers ────────────────────────────────────────────
export const RISK_RGBA: Record<RiskLevel, [number, number, number, number]> = {
  low:       [  5, 150,  105, 255],  // #059669
  moderate:  [217, 119,   6, 255],   // #D97706
  high:      [234,  88,  12, 255],   // #EA580C
  severe:    [220,  38,  38, 255],   // #DC2626
  no_travel: [153,  27,  27, 255],   // #991B1B
};

// ── CSS hex colours for DOM elements ─────────────────────────────────────────
export const RISK_CSS: Record<RiskLevel, string> = {
  low:       '#059669',
  moderate:  '#D97706',
  high:      '#EA580C',
  severe:    '#DC2626',
  no_travel: '#991B1B',
};

// ── Tailwind-style background tints ───────────────────────────────────────────
export const RISK_BG: Record<RiskLevel, string> = {
  low:       '#ECFDF5',
  moderate:  '#FFFBEB',
  high:      '#FFF7ED',
  severe:    '#FEF2F2',
  no_travel: '#450A0A18',
};

// ── Human-readable labels ─────────────────────────────────────────────────────
export const RISK_LABEL: Record<RiskLevel, string> = {
  low:       'Low',
  moderate:  'Moderate',
  high:      'High',
  severe:    'Severe',
  no_travel: 'No Travel',
};

export function getRgba(risk: RiskLevel): [number, number, number, number] {
  return RISK_RGBA[risk] ?? RISK_RGBA.low;
}

export function getCss(risk: RiskLevel): string {
  return RISK_CSS[risk] ?? RISK_CSS.low;
}

export function getBg(risk: RiskLevel): string {
  return RISK_BG[risk] ?? RISK_BG.low;
}
