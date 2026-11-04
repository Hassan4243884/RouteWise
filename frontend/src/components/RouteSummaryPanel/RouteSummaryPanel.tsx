import type { RouteResult } from '../../types';
import { getCss, RISK_CSS, RISK_LABEL } from '../../utils/riskColors';
import { formatDistance, formatDuration } from '../../utils/formatters';
import { useAppDispatch, useAppState } from '../../context/AppContext';

export function RouteSummaryPanel() {
  const { routes, recommendedRouteId, selectedRouteId, status } = useAppState();
  const dispatch = useAppDispatch();

  if (status === 'idle') {
    return (
      <div className="sidebar__section">
        <div className="routes-empty">
          <div className="routes-empty__icon">🗺</div>
          <p className="routes-empty__text">
            Enter your route details and click <strong>Analyze Safe Routes</strong> to see options here.
          </p>
        </div>
      </div>
    );
  }

  if (status === 'loading') {
    return (
      <div className="sidebar__section">
        <div className="routes-empty">
          <div className="spinner spinner--light" style={{ width: 28, height: 28, borderWidth: 3 }} />
          <p className="routes-empty__text">Calculating weather-safe routes…</p>
        </div>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="sidebar__section">
        <div className="routes-empty">
          <div className="routes-empty__icon">⚠️</div>
          <p className="routes-empty__text">Route analysis failed. Please check your inputs and try again.</p>
        </div>
      </div>
    );
  }

  if (routes.length === 0) return null;

  const totalMiles = (r: RouteResult) =>
    r.summary.low_miles + r.summary.moderate_miles + r.summary.high_miles +
    r.summary.severe_miles + r.summary.no_travel_miles || 1;

  return (
    <div className="sidebar__section">
      <p className="sidebar__section-title">
        <svg width="12" height="12" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M2 12l4-4 4 4 4-8"/>
        </svg>
        Route Options ({routes.length})
      </p>

      <div className="route-cards-container">
        {routes.map(route => {
          const isSelected   = selectedRouteId === route.id;
          const isRecommended = recommendedRouteId === route.id;
          const accentColor  = getCss(route.summary.worst_risk);
          const total        = totalMiles(route);

          const segments = [
            { key: 'low',       miles: route.summary.low_miles,       color: RISK_CSS.low },
            { key: 'moderate',  miles: route.summary.moderate_miles,  color: RISK_CSS.moderate },
            { key: 'high',      miles: route.summary.high_miles,      color: RISK_CSS.high },
            { key: 'severe',    miles: route.summary.severe_miles,    color: RISK_CSS.severe },
            { key: 'no_travel', miles: route.summary.no_travel_miles, color: RISK_CSS.no_travel },
          ].filter(s => s.miles > 0);

          return (
            <div
              key={route.id}
              className={`route-card${isSelected ? ' selected' : ''}`}
              role="button"
              tabIndex={0}
              aria-pressed={isSelected}
              aria-label={`${route.label}${isRecommended ? ', recommended route' : ''}`}
              onClick={() => dispatch({ type: 'SELECT_ROUTE', routeId: route.id })}
              onKeyDown={e => e.key === 'Enter' && dispatch({ type: 'SELECT_ROUTE', routeId: route.id })}
            >
              {/* Left accent bar */}
              <div className="route-card__accent" style={{ background: accentColor }} />

              {/* Top row */}
              <div className="route-card__top">
                <span className="route-card__label">{route.label}</span>
                <div className="route-card__badges">
                  {isRecommended && (
                    <span className="badge badge--recommended">✦ Best</span>
                  )}
                  <span
                    className="badge badge--risk"
                    style={{ color: accentColor, borderColor: accentColor + '50' }}
                  >
                    {RISK_LABEL[route.summary.worst_risk]}
                  </span>
                </div>
              </div>

              {/* Stats */}
              <div className="route-card__meta">
                <div className="route-card__stat">
                  <span className="route-card__stat-label">Distance</span>
                  <span className="route-card__stat-value">{formatDistance(route.summary.distance_miles)}</span>
                </div>
                <div className="route-card__stat">
                  <span className="route-card__stat-label">Duration</span>
                  <span className="route-card__stat-value">{formatDuration(route.summary.duration_minutes)}</span>
                </div>
                <div className="route-card__stat">
                  <span className="route-card__stat-label">Rank</span>
                  <span className="route-card__stat-value" style={{ color: isRecommended ? '#059669' : undefined }}>
                    #{route.summary.rank}
                  </span>
                </div>
              </div>

              {/* Risk breakdown bar */}
              <div className="risk-bar" title="Risk breakdown by miles">
                {segments.map(s => (
                  <div
                    key={s.key}
                    className="risk-bar__segment"
                    style={{ flex: s.miles / total, background: s.color }}
                    title={`${RISK_LABEL[s.key as keyof typeof RISK_LABEL]}: ${s.miles.toFixed(1)} mi`}
                  />
                ))}
              </div>

              {/* Legend */}
              <div className="risk-bar__legend">
                {segments.map(s => (
                  <span key={s.key} className="risk-bar__legend-item">
                    <span className="risk-bar__legend-dot" style={{ background: s.color }} />
                    {s.miles.toFixed(0)} mi
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
