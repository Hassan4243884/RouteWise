/**
 * riskColors.ts — unit tests
 *
 * Verifies:
 * - getRgba returns the correct RGBA tuple for each risk level (light theme palette)
 * - getCss returns the correct hex string for each risk level
 * - Unknown values fall back to 'low'
 */
import { describe, it, expect } from 'vitest';
import { getRgba, getCss, RISK_RGBA, RISK_CSS, RISK_LABEL } from '../utils/riskColors';
import type { RiskLevel } from '../types';

const RISK_LEVELS: RiskLevel[] = ['low', 'moderate', 'high', 'severe', 'no_travel'];

describe('getRgba', () => {
  it('returns a 4-element array for every valid risk level', () => {
    for (const level of RISK_LEVELS) {
      const rgba = getRgba(level);
      expect(rgba).toHaveLength(4);
      rgba.forEach(channel => {
        expect(channel).toBeGreaterThanOrEqual(0);
        expect(channel).toBeLessThanOrEqual(255);
      });
    }
  });

  it('returns correct RGBA for "low" (#059669)', () => {
    expect(getRgba('low')).toEqual([5, 150, 105, 255]);
  });

  it('returns correct RGBA for "moderate" (#D97706)', () => {
    expect(getRgba('moderate')).toEqual([217, 119, 6, 255]);
  });

  it('returns correct RGBA for "high" (#EA580C)', () => {
    expect(getRgba('high')).toEqual([234, 88, 12, 255]);
  });

  it('returns correct RGBA for "severe" (#DC2626)', () => {
    expect(getRgba('severe')).toEqual([220, 38, 38, 255]);
  });

  it('returns correct RGBA for "no_travel" (#991B1B)', () => {
    expect(getRgba('no_travel')).toEqual([153, 27, 27, 255]);
  });

  it('falls back to low RGBA for unknown values', () => {
    // @ts-expect-error testing invalid input
    const result = getRgba('unknown_risk');
    expect(result).toEqual(RISK_RGBA.low);
  });
});

describe('getCss', () => {
  it('returns a hex string starting with # for every risk level', () => {
    for (const level of RISK_LEVELS) {
      expect(getCss(level)).toMatch(/^#[0-9a-f]{6}$/i);
    }
  });

  it('returns correct hex for "low"', () => {
    expect(getCss('low')).toBe('#059669');
  });

  it('returns correct hex for "no_travel"', () => {
    expect(getCss('no_travel')).toBe('#991B1B');
  });

  it('falls back to low CSS for unknown values', () => {
    // @ts-expect-error testing invalid input
    expect(getCss('anything')).toBe(RISK_CSS.low);
  });
});

describe('RISK_LABEL', () => {
  it('maps every risk level to a human-readable string', () => {
    expect(RISK_LABEL.low).toBe('Low');
    expect(RISK_LABEL.moderate).toBe('Moderate');
    expect(RISK_LABEL.high).toBe('High');
    expect(RISK_LABEL.severe).toBe('Severe');
    expect(RISK_LABEL.no_travel).toBe('No Travel');
  });
});
