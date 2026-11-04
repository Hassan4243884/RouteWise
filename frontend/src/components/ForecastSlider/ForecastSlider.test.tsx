/**
 * ForecastSlider — unit tests
 *
 * Verifies:
 * - Slider is hidden when heatmapFrames is empty
 * - Slider renders when heatmapFrames are present
 * - "Now" label shown at hour=0
 * - "+Nh" label shown for non-zero hours
 * - Moving the slider dispatches SET_FORECAST_HOUR with correct value
 * - All tick labels are present
 */
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { AppProvider, useAppDispatch } from '../../context/AppContext';
import { ForecastSlider } from './ForecastSlider';
import { useEffect } from 'react';
import type { HeatmapFrame } from '../../types';

// ── Seed helper: wraps ForecastSlider and pre-seeds frames into context ────────
function SliderWithFrames({ frames }: { frames: HeatmapFrame[] }) {
  const dispatch = useAppDispatch();

  useEffect(() => {
    if (frames.length > 0) {
      dispatch({
        type: 'FETCH_SUCCESS',
        routes: [],
        recommendedRouteId: '',
        heatmapFrames: frames,
      });
    }
  }, []); // eslint-disable-line

  return <ForecastSlider />;
}

function makeFrames(count = 49): HeatmapFrame[] {
  return Array.from({ length: count }, (_, i) => ({
    hour_offset: i,
    points: [],
  }));
}

function renderSlider(frames: HeatmapFrame[]) {
  return render(
    <AppProvider>
      <SliderWithFrames frames={frames} />
    </AppProvider>,
  );
}

describe('ForecastSlider', () => {
  it('renders nothing when heatmapFrames is empty', () => {
    const { container } = renderSlider([]);
    expect(container.firstChild).toBeNull();
  });

  it('renders when frames are present', () => {
    renderSlider(makeFrames());
    expect(screen.getByRole('region', { name: /weather forecast slider/i })).toBeInTheDocument();
  });

  it('shows "Now" at hour=0 by default', () => {
    const { container } = renderSlider(makeFrames());
    expect(container.querySelector('.forecast-slider__value')?.textContent).toBe('Now');
  });

  it('range input starts at 0', () => {
    renderSlider(makeFrames());
    const slider = screen.getByRole('slider');
    expect(slider).toHaveValue('0');
  });

  it('range input has min=0 and max=48', () => {
    renderSlider(makeFrames());
    const slider = screen.getByRole('slider');
    expect(slider).toHaveAttribute('min', '0');
    expect(slider).toHaveAttribute('max', '48');
  });

  it('displays "+24h" label after sliding to 24', async () => {
    const { container } = renderSlider(makeFrames());
    const slider = screen.getByRole('slider');
    await act(async () => {
      fireEvent.change(slider, { target: { value: '24' } });
    });
    expect(container.querySelector('.forecast-slider__value')?.textContent).toBe('+24h');
  });

  it('all 9 tick labels are rendered', () => {
    renderSlider(makeFrames());
    const ticks = [0, 6, 12, 18, 24, 30, 36, 42, 48];
    for (const t of ticks) {
      const label = t === 0 ? 'Now' : `+${t}h`;
      // There may be multiple 'Now' (value + tick) so check at least one
      const elements = screen.getAllByText(label);
      expect(elements.length).toBeGreaterThanOrEqual(1);
    }
  });
});
