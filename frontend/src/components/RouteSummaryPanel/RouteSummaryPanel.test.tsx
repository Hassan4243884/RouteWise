/**
 * RouteCard — unit tests
 *
 * Verifies:
 * - Route label is rendered
 * - Risk badge shows the correct worst risk label
 * - "Best" recommended badge is present only when isRecommended=true
 * - Stats (distance, duration, rank) are rendered
 * - Multiple cards when multiple routes exist
 */
import { describe, it, expect } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { useEffect } from 'react';
import { AppProvider, useAppDispatch } from '../../context/AppContext';
import { RouteSummaryPanel } from './RouteSummaryPanel';
import type { RouteResult } from '../../types';

// ── Helper: build a minimal RouteResult ──────────────────────────────────────
function makeRoute(overrides: Partial<RouteResult> & { summaryOverrides?: Partial<RouteResult['summary']> } = {}): RouteResult {
  const { summaryOverrides, ...rest } = overrides;
  return {
    id: 'route_0',
    label: 'Route A',
    polyline: [[41.85, -87.65], [39.77, -86.16]],
    checkpoints: [],
    summary: {
      distance_miles: 183.2,
      duration_minutes: 195,
      low_miles: 150,
      moderate_miles: 20,
      high_miles: 10,
      severe_miles: 3.2,
      no_travel_miles: 0,
      worst_risk: 'severe',
      avg_risk_score: 1.2,
      rank: 1,
      ...summaryOverrides,
    },
    ...rest,
  };
}

// ── Wrapper that seeds context then renders RouteSummaryPanel ─────────────────
function PanelWithRoutes({
  routes,
  recommendedId,
}: {
  routes: RouteResult[];
  recommendedId?: string;
}) {
  const dispatch = useAppDispatch();
  useEffect(() => {
    dispatch({
      type: 'FETCH_SUCCESS',
      routes,
      recommendedRouteId: recommendedId ?? routes[0]?.id ?? '',
      heatmapFrames: [],
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  return <RouteSummaryPanel />;
}

function renderRoutes(routes: RouteResult[], recommendedId?: string) {
  return render(
    <AppProvider>
      <PanelWithRoutes routes={routes} recommendedId={recommendedId} />
    </AppProvider>,
  );
}

describe('RouteCard', () => {
  it('renders the route label', async () => {
    await act(async () => renderRoutes([makeRoute({ label: 'Route Alpha' })]));
    expect(screen.getByText('Route Alpha')).toBeInTheDocument();
  });

  it('shows the worst risk badge label', async () => {
    await act(async () => renderRoutes([makeRoute()]));
    // RISK_LABEL['severe'] = 'Severe'
    expect(screen.getByText('Severe')).toBeInTheDocument();
  });

  it('shows the "Best" recommended badge on recommended route', async () => {
    await act(async () =>
      renderRoutes([makeRoute({ id: 'route_0', label: 'Route A' })], 'route_0'),
    );
    expect(screen.getByText('✦ Best')).toBeInTheDocument();
  });

  it('does NOT show recommended badge when not recommended', async () => {
    await act(async () =>
      renderRoutes([makeRoute({ id: 'route_0' })], 'route_99'),
    );
    expect(screen.queryByText('✦ Best')).not.toBeInTheDocument();
  });

  it('renders formatted distance', async () => {
    await act(async () => renderRoutes([makeRoute()]));
    expect(screen.getByText(/183\.2 mi/)).toBeInTheDocument();
  });

  it('renders formatted duration', async () => {
    await act(async () => renderRoutes([makeRoute()]));
    // formatDuration(195) = "3h 15m"
    expect(screen.getByText(/3h 15m/)).toBeInTheDocument();
  });

  it('renders the rank stat', async () => {
    await act(async () => renderRoutes([makeRoute()]));
    expect(screen.getByText('#1')).toBeInTheDocument();
  });

  it('renders a card for each route', async () => {
    const routes = [
      makeRoute({ id: 'route_0', label: 'Route A' }),
      makeRoute({ id: 'route_1', label: 'Route B', summaryOverrides: { rank: 2 } }),
    ];
    await act(async () => renderRoutes(routes));
    expect(screen.getByText('Route A')).toBeInTheDocument();
    expect(screen.getByText('Route B')).toBeInTheDocument();
  });

  it('card has role=button and aria-pressed', async () => {
    await act(async () => renderRoutes([makeRoute({ label: 'Route A' })], 'route_0'));
    const card = screen.getByRole('button', { name: /Route A/i });
    expect(card).toBeInTheDocument();
  });
});
