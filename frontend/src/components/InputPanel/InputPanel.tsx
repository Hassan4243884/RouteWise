import { useState } from 'react';
import { useAppDispatch } from '../../context/AppContext';
import { fetchRoutes, fetchHeatmap, boundsFromPolylines } from '../../api/routingApi';
import { defaultDepartureValue } from '../../utils/formatters';
import { SearchableCitySelect } from '../SearchableCitySelect/SearchableCitySelect';
import type { CheckpointInterval, HeatmapFrame } from '../../types';

const INTERVALS: CheckpointInterval[] = [10, 25, 50];

export function InputPanel() {
  const dispatch = useAppDispatch();

  const [origin, setOrigin] = useState('');
  const [destination, setDestination] = useState('');
  const [departureTime, setDepartureTime] = useState(defaultDepartureValue());
  const [loadWeight, setLoadWeight] = useState<number | ''>('');
  const [interval, setInterval] = useState<CheckpointInterval>(25);
  const [localError, setLocalError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  function swapRoutes() {
    const tmp = origin;
    setOrigin(destination);
    setDestination(tmp);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalError('');

    if (!origin.trim()) return setLocalError('Please enter or select an origin.');
    if (!destination.trim()) return setLocalError('Please enter or select a destination.');
    if (!departureTime) return setLocalError('Please select a departure date/time.');
    if (loadWeight === '' || loadWeight < 0) return setLocalError('Please enter a valid load weight (lbs).');

    const input = {
      origin: origin.trim(),
      destination: destination.trim(),
      departure_time: new Date(departureTime).toISOString(),
      load_weight_lbs: Number(loadWeight),
      checkpoint_interval_miles: interval,
    };

    dispatch({ type: 'FETCH_START' });
    setIsSubmitting(true);

    try {
      const routeData = await fetchRoutes(input);

      const polylines = routeData.routes.map(r => r.polyline);
      const bounds = boundsFromPolylines(polylines);

      let heatmapFrames: HeatmapFrame[] = [];
      try {
        const heatmapData = await fetchHeatmap(bounds, input.departure_time);
        heatmapFrames = heatmapData.frames;
      } catch {
        console.warn('Heatmap fetch failed — continuing without heatmap');
      }

      dispatch({
        type: 'FETCH_SUCCESS',
        routes: routeData.routes,
        recommendedRouteId: routeData.recommended_route_id,
        heatmapFrames,
      });
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error';
      dispatch({ type: 'FETCH_ERROR', error: msg });
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleReset() {
    setOrigin('');
    setDestination('');
    setDepartureTime(defaultDepartureValue());
    setLoadWeight('');
    setInterval(25);
    setLocalError('');
    dispatch({ type: 'RESET' });
  }

  return (
    <form onSubmit={handleSubmit} noValidate>
      {/* ── Route Inputs ──────────────────────────────────────────── */}
      <div className="sidebar__section">
        <p className="sidebar__section-title">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="4" cy="4" r="2"/><circle cx="12" cy="12" r="2"/>
            <path d="M4 6v3h8V6" strokeLinejoin="round"/>
          </svg>
          Route
        </p>

        <SearchableCitySelect
          id="origin-input"
          label="Origin"
          variant="origin"
          value={origin}
          onChange={setOrigin}
          placeholder="City, State or address…"
          disabled={isSubmitting}
        />

        {/* Swap button */}
        <div style={{ display: 'flex', justifyContent: 'center', margin: '4px 0' }}>
          <button
            type="button"
            className="route-swap-btn"
            onClick={swapRoutes}
            disabled={isSubmitting}
            title="Swap endpoints"
            aria-label="Swap endpoints"
          >
            ⇅
          </button>
        </div>

        <SearchableCitySelect
          id="destination-input"
          label="Destination"
          variant="dest"
          value={destination}
          onChange={setDestination}
          placeholder="City, State or address…"
          disabled={isSubmitting}
        />
      </div>

      {/* ── Departure & Load ──────────────────────────────────────── */}
      <div className="sidebar__section">
        <p className="sidebar__section-title">
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="2" y="3" width="12" height="11" rx="1.5"/>
            <path d="M5 1v4M11 1v4M2 7h12"/>
          </svg>
          Departure & Load
        </p>

        <div className="field" style={{ marginBottom: 10 }}>
          <label htmlFor="departure">Departure</label>
          <input
            id="departure"
            type="datetime-local"
            value={departureTime}
            onChange={e => setDepartureTime(e.target.value)}
            disabled={isSubmitting}
          />
        </div>

        <div className="field" style={{ marginBottom: 12 }}>
          <label htmlFor="load">Load Weight (lbs)</label>
          <input
            id="load"
            type="number"
            placeholder="e.g. 42000"
            min={0}
            max={200000}
            value={loadWeight}
            onChange={e => setLoadWeight(e.target.value === '' ? '' : Number(e.target.value))}
            disabled={isSubmitting}
          />
        </div>

        <div className="field">
          <label>Checkpoint Interval</label>
          <div className="interval-toggle">
            {INTERVALS.map(v => (
              <button
                key={v}
                type="button"
                className={interval === v ? 'active' : ''}
                onClick={() => setInterval(v)}
                disabled={isSubmitting}
              >
                {v} mi
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ── Error ─────────────────────────────────────────────────── */}
      {localError && (
        <div style={{ padding: '0 20px' }}>
          <div className="error-banner" role="alert">
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="8" cy="8" r="6"/>
              <path d="M8 5v3M8 11v.5"/>
            </svg>
            {localError}
          </div>
        </div>
      )}

      {/* ── Actions ───────────────────────────────────────────────── */}
      <div className="sidebar__section" style={{ borderBottom: 'none' }}>
        <button
          type="submit"
          className={`btn-submit${isSubmitting ? ' loading' : ''}`}
          disabled={isSubmitting}
        >
          {isSubmitting ? (
            <>
              <span className="spinner" />
              Analyzing Routes…
            </>
          ) : (
            <>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                <path d="M3 12h18M13 6l6 6-6 6"/>
              </svg>
              Find Safe Routes
            </>
          )}
        </button>

        <button
          type="button"
          className="btn-reset"
          onClick={handleReset}
          disabled={isSubmitting}
        >
          ↺ Reset
        </button>
      </div>
    </form>
  );
}
