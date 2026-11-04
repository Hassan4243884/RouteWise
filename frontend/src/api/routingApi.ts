import type { RouteFormInput, RoutesResponse, HeatmapResponse } from '../types';

const BASE = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api';

// ── Routes ────────────────────────────────────────────────────────────────────

export async function fetchRoutes(input: RouteFormInput): Promise<RoutesResponse> {
  const res = await fetch(`${BASE}/routes/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      origin: input.origin,
      destination: input.destination,
      departure_time: input.departure_time,
      load_weight_lbs: input.load_weight_lbs,
      checkpoint_interval_miles: input.checkpoint_interval_miles,
    }),
  });

  if (!res.ok) {
    let msg = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body?.error
        ? typeof body.error === 'string'
          ? body.error
          : JSON.stringify(body.error)
        : msg;
    } catch {/* ignore parse errors */}
    throw new Error(msg);
  }

  return res.json() as Promise<RoutesResponse>;
}

// ── Heatmap ──────────────────────────────────────────────────────────────────

export interface HeatmapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export async function fetchHeatmap(
  bounds: HeatmapBounds,
  departure_time: string,
): Promise<HeatmapResponse> {
  const res = await fetch(`${BASE}/heatmap/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      bounds,
      departure_time,
      grid_resolution: 0.25,
    }),
  });

  if (!res.ok) {
    let msg = `Heatmap request failed (${res.status})`;
    try {
      const body = await res.json();
      msg = body?.error ?? msg;
    } catch {/* ignore */}
    throw new Error(msg);
  }

  return res.json() as Promise<HeatmapResponse>;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Derive the bounding box from route polylines.
 * Backend polylines are [[lat, lng], ...].
 */
export function boundsFromPolylines(
  polylines: [number, number][][],
): HeatmapBounds {
  const lats = polylines.flat().map(([lat]) => lat);
  const lngs = polylines.flat().map(([, lng]) => lng);
  // Add 0.3° padding around the routes
  const pad = 0.3;
  return {
    north: Math.max(...lats) + pad,
    south: Math.min(...lats) - pad,
    east:  Math.max(...lngs) + pad,
    west:  Math.min(...lngs) - pad,
  };
}
