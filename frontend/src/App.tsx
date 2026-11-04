import { AppProvider, useAppState, useAppDispatch } from './context/AppContext';
import { InputPanel } from './components/InputPanel/InputPanel';
import { MapCanvas } from './components/MapCanvas/MapCanvas';
import { RouteSummaryPanel } from './components/RouteSummaryPanel/RouteSummaryPanel';
import { ForecastSlider } from './components/ForecastSlider/ForecastSlider';
import { CheckpointTooltip } from './components/CheckpointTooltip/CheckpointTooltip';
import { SelectedRouteDossier } from './components/SelectedRouteDossier/SelectedRouteDossier';

// ── RouteWise Logo ────────────────────────────────────────────────────────────
function RouteWiseLogo() {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true">
      {/* Truck cab */}
      <rect x="2" y="9" width="11" height="8" rx="1" fill="white" opacity="0.9" />
      {/* Truck trailer */}
      <path d="M13 11h5.5l2.5 3v3H13V11Z" fill="white" opacity="0.7" />
      {/* Wheels */}
      <circle cx="6.5" cy="18" r="1.6" fill="white" />
      <circle cx="10.5" cy="18" r="1.6" fill="white" />
      <circle cx="18" cy="18" r="1.6" fill="white" />
      {/* Route path */}
      <path
        d="M3 7 Q7 3 12 6 Q17 9 21 5"
        stroke="white"
        strokeWidth="1.8"
        fill="none"
        strokeLinecap="round"
        opacity="0.85"
      />
    </svg>
  );
}

// ── Status pill in top bar ────────────────────────────────────────────────────
function TopBarStatus() {
  const { status, routes } = useAppState();

  const labels: Record<string, string> = {
    idle:    'Ready — enter a route to analyze',
    loading: 'Calculating weather-safe routes…',
    success: routes.length > 0
      ? `${routes.length} route${routes.length > 1 ? 's' : ''} analyzed`
      : 'Analysis complete',
    error:   'Analysis failed — please try again',
  };

  return (
    <div className={`status-pill status-pill--${status}`}>
      <div className={`status-dot status-dot--${status}`} />
      {labels[status] ?? 'Ready'}
    </div>
  );
}

// ── Reset Action ──────────────────────────────────────────────────────────────
function ResetButton() {
  const dispatch = useAppDispatch();
  const { status } = useAppState();
  if (status === 'idle') return null;
  return (
    <button
      className="btn-icon"
      onClick={() => dispatch({ type: 'RESET' })}
      title="Reset analysis"
      aria-label="Reset analysis"
    >
      ↺
    </button>
  );
}

// ── App Shell ─────────────────────────────────────────────────────────────────
function AppShell() {
  return (
    <div className="app-shell">

      {/* ── Top Navigation Bar ──────────────────────────────────── */}
      <header className="app-topbar" role="banner">
        {/* Brand */}
        <div className="topbar__brand">
          <div className="topbar__logo" aria-hidden="true">
            <RouteWiseLogo />
          </div>
          <div>
            <div className="topbar__name">
              Route<span>Wise</span>
            </div>
            <div className="topbar__tagline">Fleet Intelligence Platform</div>
          </div>
        </div>

        <div className="topbar__sep" />

        {/* Live status */}
        <div className="topbar__status">
          <TopBarStatus />
        </div>

        {/* Actions */}
        <div className="topbar__actions">
          <ResetButton />
        </div>
      </header>

      {/* ── 3-Column Workspace ──────────────────────────────────── */}
      <div className="app-workspace">

        {/* ── LEFT SIDEBAR: Route Planner + Route Options ─────── */}
        <aside
          className="sidebar sidebar-left"
          aria-label="Route planning panel"
        >
          <div className="sidebar__scroll">
            <InputPanel />
            <RouteSummaryPanel />
          </div>
        </aside>

        {/* ── CENTER: Interactive Map ──────────────────────────── */}
        <main className="canvas-center" aria-label="Interactive route map">
          <MapCanvas />
          <ForecastSlider />
          <CheckpointTooltip />
        </main>

        {/* ── RIGHT SIDEBAR: Selected Route Dossier ───────────── */}
        <aside
          className="sidebar sidebar-right"
          aria-label="Selected route details"
          style={{ display: 'flex', flexDirection: 'column' }}
        >
          <SelectedRouteDossier />
        </aside>

      </div>
    </div>
  );
}

// ── Root ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AppProvider>
      <AppShell />
    </AppProvider>
  );
}
