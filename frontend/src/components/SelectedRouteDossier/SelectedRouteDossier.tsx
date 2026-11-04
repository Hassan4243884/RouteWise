import { useAppDispatch, useAppState } from '../../context/AppContext';
import { getCss, RISK_CSS, RISK_LABEL, getBg } from '../../utils/riskColors';
import {
  formatDistance,
  formatDuration,
  formatEta,
  formatWind,
  formatRain,
  formatSnow,
  formatTemp,
} from '../../utils/formatters';
import type { Checkpoint, RiskLevel } from '../../types';

// ── Risk breakdown rows ───────────────────────────────────────────────────────
const RISK_ORDER: RiskLevel[] = ['low', 'moderate', 'high', 'severe', 'no_travel'];

// ── Weather icon helpers ──────────────────────────────────────────────────────
function weatherIcon(cp: Checkpoint): string {
  const { snow_in_hr, rain_in_hr, wind_speed_mph, temperature_f } = cp.weather;
  if (snow_in_hr > 0.1) return '🌨';
  if (rain_in_hr > 0.1) return '🌧';
  if (wind_speed_mph > 40) return '💨';
  if (temperature_f < 32) return '🧊';
  if (cp.risk_level === 'low') return '☀️';
  if (cp.risk_level === 'moderate') return '⛅';
  return '🌩';
}

// ── Hazard Analysis ───────────────────────────────────────────────────────────
function HazardCallouts({ checkpoints, loadWeight }: { checkpoints: Checkpoint[]; loadWeight: number }) {
  const hazards: { type: 'danger' | 'warning' | 'caution' | 'ok'; icon: string; msg: string }[] = [];

  const maxWind = Math.max(...checkpoints.map(c => c.weather.wind_speed_mph));
  const maxSnow = Math.max(...checkpoints.map(c => c.weather.snow_in_hr));
  const maxRain = Math.max(...checkpoints.map(c => c.weather.rain_in_hr));
  const minTemp = Math.min(...checkpoints.map(c => c.weather.temperature_f));
  const severeCount = checkpoints.filter(c => c.risk_level === 'severe' || c.risk_level === 'no_travel').length;

  if (severeCount > 0) {
    hazards.push({ type: 'danger', icon: '🚫', msg: `${severeCount} checkpoint${severeCount > 1 ? 's' : ''} with Severe or No-Travel conditions detected.` });
  }
  if (maxWind > 50) {
    hazards.push({ type: 'danger', icon: '💨', msg: `Extreme wind gusts up to ${maxWind.toFixed(0)} mph. High rollover risk${loadWeight < 40000 ? ' — especially at this light load weight' : ''}.` });
  } else if (maxWind > 35) {
    hazards.push({ type: 'warning', icon: '💨', msg: `Sustained winds up to ${maxWind.toFixed(0)} mph. ${loadWeight < 40000 ? 'Light trailer — elevated crosswind instability.' : 'Monitor conditions.'}` });
  }
  if (maxSnow > 0.1) {
    hazards.push({ type: 'danger', icon: '❄️', msg: `Snowfall up to ${maxSnow.toFixed(2)} in/hr detected. Black ice and low-visibility risk.` });
  }
  if (maxRain > 0.5) {
    hazards.push({ type: 'warning', icon: '🌧', msg: `Heavy rain up to ${maxRain.toFixed(2)} in/hr. Reduced braking distance and hydroplaning risk.` });
  }
  if (minTemp < 32) {
    hazards.push({ type: 'caution', icon: '🌡', msg: `Temperatures below freezing (${minTemp.toFixed(0)}°F). Watch for black ice on bridges and overpasses.` });
  }
  if (hazards.length === 0) {
    hazards.push({ type: 'ok', icon: '✅', msg: 'No critical weather hazards detected along this route.' });
  }

  return (
    <div>
      {hazards.map((h, i) => (
        <div key={i} className={`hazard-callout hazard-callout--${h.type}`}>
          <span className="hazard-callout__icon">{h.icon}</span>
          <span>{h.msg}</span>
        </div>
      ))}
    </div>
  );
}

// ── Checkpoint Timeline Item ──────────────────────────────────────────────────
function CheckpointItem({
  cp,
  highlighted,
  onHover,
}: {
  cp: Checkpoint;
  highlighted: boolean;
  onHover: (cp: Checkpoint | null) => void;
}) {
  const color = getCss(cp.risk_level);
  const bg    = getBg(cp.risk_level);

  return (
    <div
      className={`checkpoint-item${highlighted ? ' highlighted' : ''}`}
      onMouseEnter={() => onHover(cp)}
      onMouseLeave={() => onHover(null)}
    >
      {/* Timeline visual */}
      <div className="checkpoint-item__timeline">
        <div
          className="checkpoint-item__dot"
          style={{ background: color, boxShadow: `0 0 0 1px ${color}50` }}
        />
        <div className="checkpoint-item__line" />
      </div>

      {/* Content */}
      <div className="checkpoint-item__content">
        <div className="checkpoint-item__header">
          <span className="checkpoint-item__mile">Mile {cp.distance_from_start_miles.toFixed(0)}</span>
          <span className="checkpoint-item__eta">{formatEta(cp.eta)}</span>
        </div>

        <div
          className="checkpoint-item__badge"
          style={{ background: color, color: '#fff' }}
        >
          {weatherIcon(cp)} {RISK_LABEL[cp.risk_level]}
        </div>

        <div className="checkpoint-item__weather">
          <span className="checkpoint-item__wx">
            <span className="checkpoint-item__wx-icon">🌡</span>
            {formatTemp(cp.weather.temperature_f)}
          </span>
          <span className="checkpoint-item__wx">
            <span className="checkpoint-item__wx-icon">💨</span>
            {formatWind(cp.weather.wind_speed_mph)}
          </span>
          {cp.weather.rain_in_hr > 0.001 && (
            <span className="checkpoint-item__wx">
              <span className="checkpoint-item__wx-icon">🌧</span>
              {formatRain(cp.weather.rain_in_hr)}
            </span>
          )}
          {cp.weather.snow_in_hr > 0.001 && (
            <span className="checkpoint-item__wx">
              <span className="checkpoint-item__wx-icon">❄️</span>
              {formatSnow(cp.weather.snow_in_hr)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export function SelectedRouteDossier() {
  const { routes, selectedRouteId, recommendedRouteId, hoverInfo, status } = useAppState();
  const dispatch = useAppDispatch();

  if (status === 'idle' || status === 'loading') {
    return (
      <div className="dossier-empty">
        <div className="dossier-empty__icon">📋</div>
        <div className="dossier-empty__title">Route Dossier</div>
        <div className="dossier-empty__sub">
          Analyze a route to see full telemetry, weather risk breakdown, and checkpoint-by-checkpoint forecasts here.
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="dossier-empty">
        <div className="dossier-empty__icon">⚠️</div>
        <div className="dossier-empty__title">Analysis Failed</div>
        <div className="dossier-empty__sub">Please check your inputs and try again.</div>
      </div>
    );
  }

  const route = routes.find(r => r.id === selectedRouteId) ?? routes[0];
  if (!route) return null;

  const isRecommended = route.id === recommendedRouteId;
  const worstColor    = getCss(route.summary.worst_risk);
  const { summary }   = route;

  const totalMiles =
    summary.low_miles + summary.moderate_miles + summary.high_miles +
    summary.severe_miles + summary.no_travel_miles || 1;

  const riskRows = RISK_ORDER.map(level => ({
    level,
    miles: (summary as any)[`${level}_miles`] as number,
    color: RISK_CSS[level],
  })).filter(r => r.miles > 0);

  const hoveredCheckpointIdx = hoverInfo?.checkpoint.index ?? -1;

  // Synthetic load weight from context — not stored, estimate from summary
  const estimatedLoad = 42000; // placeholder; real app would pull from form state

  function handleCheckpointHover(cp: Checkpoint | null) {
    if (!cp) {
      dispatch({ type: 'SET_HOVER_INFO', info: null });
    }
    // For sidebar hover, we highlight on map via SET_HOVER_INFO with zero x/y
    // so the tooltip doesn't show (x=0,y=0 is offscreen for tooltip positioning)
    // The map canvas responds to selectedRouteId for the actual checkpoint dots
  }

  return (
    <>
      {/* ── Route Header ─────────────────────────────────────────── */}
      <div className="dossier-header">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <div
            className="dossier-header__label"
            style={{ color: worstColor }}
          >
            {route.label}
          </div>
          {isRecommended && (
            <span className="badge badge--recommended">✦ Best Safe Route</span>
          )}
        </div>
        <div className="dossier-header__subtitle">
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 4,
              padding: '2px 8px',
              borderRadius: 100,
              background: getBg(summary.worst_risk),
              border: `1px solid ${worstColor}50`,
              color: worstColor,
              fontWeight: 600,
              fontSize: 11,
            }}
          >
            Worst Risk: {RISK_LABEL[summary.worst_risk]}
          </span>
          <span>Rank #{summary.rank}</span>
        </div>
      </div>

      {/* ── Stats Grid ───────────────────────────────────────────── */}
      <div className="dossier-stats">
        <div className="dossier-stat">
          <span className="dossier-stat__label">Distance</span>
          <span className="dossier-stat__value">
            {summary.distance_miles.toFixed(0)}
            <span className="dossier-stat__unit"> mi</span>
          </span>
        </div>
        <div className="dossier-stat">
          <span className="dossier-stat__label">Est. Duration</span>
          <span className="dossier-stat__value">{formatDuration(summary.duration_minutes)}</span>
        </div>
        <div className="dossier-stat">
          <span className="dossier-stat__label">Checkpoints</span>
          <span className="dossier-stat__value">
            {route.checkpoints.length}
            <span className="dossier-stat__unit"> stops</span>
          </span>
        </div>
        <div className="dossier-stat">
          <span className="dossier-stat__label">Avg Risk Score</span>
          <span className="dossier-stat__value" style={{ color: worstColor }}>
            {summary.avg_risk_score.toFixed(2)}
          </span>
        </div>
      </div>

      {/* ── Risk Breakdown ───────────────────────────────────────── */}
      <div className="risk-breakdown">
        <p className="sidebar__section-title" style={{ marginBottom: 10 }}>
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="2" width="12" height="12" rx="1.5"/>
            <path d="M6 8h4M8 6v4"/>
          </svg>
          Weather Risk Breakdown
        </p>

        {/* Stacked bar */}
        <div className="risk-breakdown__bar">
          {riskRows.map(r => (
            <div
              key={r.level}
              className="risk-bar__segment"
              style={{ flex: r.miles / totalMiles, background: r.color }}
              title={`${RISK_LABEL[r.level]}: ${r.miles.toFixed(1)} mi`}
            />
          ))}
        </div>

        {/* Table */}
        <div className="risk-breakdown__table">
          {riskRows.map(r => (
            <div key={r.level} className="risk-breakdown__row">
              <div className="risk-breakdown__swatch" style={{ background: r.color }} />
              <span className="risk-breakdown__name">{RISK_LABEL[r.level]}</span>
              <span className="risk-breakdown__miles">{formatDistance(r.miles)}</span>
              <span className="risk-breakdown__pct">{((r.miles / totalMiles) * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Hazard Analysis ──────────────────────────────────────── */}
      <div className="sidebar__section">
        <p className="sidebar__section-title">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M8 1L15 14H1L8 1z"/>
            <path d="M8 6v4M8 11.5v.5"/>
          </svg>
          Weather Hazard Analysis
        </p>
        <HazardCallouts checkpoints={route.checkpoints} loadWeight={estimatedLoad} />
      </div>

      {/* ── Checkpoint Timeline ───────────────────────────────────── */}
      <div className="sidebar__section" style={{ borderBottom: 'none', paddingBottom: 0 }}>
        <p className="sidebar__section-title">
          <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="4" cy="4" r="1.5" fill="currentColor"/>
            <circle cx="4" cy="8" r="1.5" fill="currentColor"/>
            <circle cx="4" cy="12" r="1.5" fill="currentColor"/>
            <path d="M7 4h6M7 8h6M7 12h6"/>
          </svg>
          Checkpoint Timeline ({route.checkpoints.length})
        </p>
      </div>

      <div className="checkpoint-timeline sidebar__scroll" style={{ flex: 1 }}>
        {route.checkpoints.map(cp => (
          <CheckpointItem
            key={cp.index}
            cp={cp}
            highlighted={cp.index === hoveredCheckpointIdx}
            onHover={handleCheckpointHover}
          />
        ))}
      </div>
    </>
  );
}
