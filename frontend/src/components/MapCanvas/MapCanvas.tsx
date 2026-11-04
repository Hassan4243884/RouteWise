import { useEffect, useRef, useCallback } from 'react';
import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { MapLibreOverlay } from '@deck.gl/maplibre';
import { PathLayer, ScatterplotLayer } from '@deck.gl/layers';
import { HeatmapLayer } from '@deck.gl/aggregation-layers';
import { useAppState, useAppDispatch } from '../../context/AppContext';
import { getRgba } from '../../utils/riskColors';
import { getCartoMapStyle, cartoTransformRequest } from '../../config/carto';
import type { Checkpoint, HeatmapPoint, RiskLevel, RouteResult } from '../../types';
import type { Layer } from '@deck.gl/core';

// ── Default map view ──────────────────────────────────────────────────────────
const INITIAL_VIEW = { center: [-96, 38] as [number, number], zoom: 4 };

// ── Heatmap color range (light theme — risk palette) ──────────────────────────
const HEATMAP_COLOR_RANGE: [number, number, number, number][] = [
  [ 5, 150, 105,   0],   // transparent
  [ 5, 150, 105, 100],   // low   #059669
  [217, 119,   6, 160],  // moderate #D97706
  [234,  88,  12, 210],  // high  #EA580C
  [220,  38,  38, 235],  // severe #DC2626
  [153,  27,  27, 255],  // no_travel #991B1B
];

// ── Layer builder ─────────────────────────────────────────────────────────────
function buildLayers(
  routes: RouteResult[],
  selectedRouteId: string | null,
  heatmapPoints: HeatmapPoint[],
  onHoverCheckpoint: (info: { x: number; y: number; object: Checkpoint } | null) => void,
): Layer[] {
  const layers: Layer[] = [];

  // 1. Heatmap layer
  if (heatmapPoints.length > 0) {
    layers.push(
      new HeatmapLayer({
        id: 'weather-heatmap',
        data: heatmapPoints,
        getPosition: (d: HeatmapPoint) => [d.lng, d.lat],
        getWeight: (d: HeatmapPoint) => d.intensity,
        radiusPixels: 70,
        intensity: 1.3,
        threshold: 0.05,
        colorRange: HEATMAP_COLOR_RANGE,
        opacity: 0.45,
      })
    );
  }

  // 2. Route paths — non-selected first, selected last
  const sorted = [...routes].sort(r => (r.id === selectedRouteId ? 1 : -1));

  for (const route of sorted) {
    const isSelected = route.id === selectedRouteId;
    const path = route.polyline.map(([lat, lng]) => [lng, lat]);
    const baseColor = getRgba(route.summary.worst_risk);

    const color: [number, number, number, number] = isSelected
      ? baseColor
      : [baseColor[0], baseColor[1], baseColor[2], 100];

    // Glow layer for selected route
    if (isSelected) {
      layers.push(
        new PathLayer({
          id: `route-glow-${route.id}`,
          data: [{ path }],
          getPath: (d: { path: [number, number][] }) => d.path,
          getColor: [baseColor[0], baseColor[1], baseColor[2], 40],
          getWidth: 18,
          widthUnits: 'pixels',
          capRounded: true,
          jointRounded: true,
          pickable: false,
        })
      );
    }

    layers.push(
      new PathLayer({
        id: `route-path-${route.id}`,
        data: [{ path, color, width: isSelected ? 5 : 3 }],
        getPath: d => d.path,
        getColor: d => d.color,
        getWidth: d => d.width,
        widthUnits: 'pixels',
        widthMinPixels: 2,
        capRounded: true,
        jointRounded: true,
        pickable: true,
      })
    );
  }

  // 3. Checkpoints + waypoint pins for selected route
  for (const route of sorted) {
    const isSelected = route.id === selectedRouteId;
    if (!isSelected) continue;

    // Checkpoint dots
    layers.push(
      new ScatterplotLayer({
        id: `checkpoints-${route.id}`,
        data: route.checkpoints,
        getPosition: (d: Checkpoint) => [d.lng, d.lat],
        getFillColor: (d: Checkpoint) => getRgba(d.risk_level as RiskLevel),
        getLineColor: [255, 255, 255, 240],
        getRadius: 8,
        radiusUnits: 'pixels',
        lineWidthMinPixels: 2,
        stroked: true,
        pickable: true,
        autoHighlight: true,
        highlightColor: [0, 0, 0, 40],
        onHover: (info: any) => {
          if (info.object) {
            onHoverCheckpoint({ x: info.x, y: info.y, object: info.object });
          } else {
            onHoverCheckpoint(null);
          }
        },
      })
    );

    // Origin pin (brand blue)
    if (route.polyline.length > 0) {
      const originCoord: [number, number] = [route.polyline[0][1], route.polyline[0][0]];
      const destCoord: [number, number] = [
        route.polyline[route.polyline.length - 1][1],
        route.polyline[route.polyline.length - 1][0],
      ];

      // Origin outer halo
      layers.push(
        new ScatterplotLayer({
          id: `origin-halo-${route.id}`,
          data: [{ coord: originCoord }],
          getPosition: d => d.coord,
          getFillColor: [2, 132, 199, 40],
          getRadius: 18,
          radiusUnits: 'pixels',
          pickable: false,
        }),
        new ScatterplotLayer({
          id: `origin-pin-${route.id}`,
          data: [{ coord: originCoord }],
          getPosition: d => d.coord,
          getFillColor: [2, 132, 199, 255],
          getLineColor: [255, 255, 255, 255],
          getRadius: 11,
          radiusUnits: 'pixels',
          lineWidthMinPixels: 2.5,
          stroked: true,
          pickable: false,
        }),
        new ScatterplotLayer({
          id: `origin-inner-${route.id}`,
          data: [{ coord: originCoord }],
          getPosition: d => d.coord,
          getFillColor: [255, 255, 255, 255],
          getRadius: 4,
          radiusUnits: 'pixels',
          pickable: false,
        })
      );

      // Destination outer halo
      layers.push(
        new ScatterplotLayer({
          id: `dest-halo-${route.id}`,
          data: [{ coord: destCoord }],
          getPosition: d => d.coord,
          getFillColor: [79, 70, 229, 40],
          getRadius: 18,
          radiusUnits: 'pixels',
          pickable: false,
        }),
        new ScatterplotLayer({
          id: `dest-pin-${route.id}`,
          data: [{ coord: destCoord }],
          getPosition: d => d.coord,
          getFillColor: [79, 70, 229, 255],
          getLineColor: [255, 255, 255, 255],
          getRadius: 11,
          radiusUnits: 'pixels',
          lineWidthMinPixels: 2.5,
          stroked: true,
          pickable: false,
        }),
        new ScatterplotLayer({
          id: `dest-inner-${route.id}`,
          data: [{ coord: destCoord }],
          getPosition: d => d.coord,
          getFillColor: [255, 255, 255, 255],
          getRadius: 4,
          radiusUnits: 'pixels',
          pickable: false,
        })
      );
    }
  }

  return layers;
}

// ── Risk Legend ───────────────────────────────────────────────────────────────
const LEGEND_ITEMS = [
  { label: 'Low',       color: '#059669' },
  { label: 'Moderate',  color: '#D97706' },
  { label: 'High',      color: '#EA580C' },
  { label: 'Severe',    color: '#DC2626' },
  { label: 'No Travel', color: '#991B1B' },
];

// ── Component ─────────────────────────────────────────────────────────────────
export function MapCanvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef       = useRef<maplibregl.Map | null>(null);
  const overlayRef   = useRef<MapLibreOverlay | null>(null);
  const layerArgsRef = useRef<Parameters<typeof buildLayers> | null>(null);

  const { routes, selectedRouteId, heatmapFrames, forecastHour, status } = useAppState();
  const dispatch = useAppDispatch();

  const handleHoverCheckpoint = useCallback(
    (info: { x: number; y: number; object: Checkpoint } | null) => {
      dispatch({
        type: 'SET_HOVER_INFO',
        info: info ? { x: info.x, y: info.y, checkpoint: info.object } : null,
      });
    },
    [dispatch]
  );

  // Initialise map once
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: getCartoMapStyle() as maplibregl.StyleSpecification | string,
      transformRequest: cartoTransformRequest,
      center: INITIAL_VIEW.center,
      zoom: INITIAL_VIEW.zoom,
    });

    map.addControl(new maplibregl.NavigationControl(), 'bottom-right');

    map.on('load', () => {
      const initialLayers = layerArgsRef.current
        ? buildLayers(...layerArgsRef.current)
        : [];
      const overlay = new MapLibreOverlay({ layers: initialLayers });
      map.addControl(overlay);
      overlayRef.current = overlay;
    });

    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      overlayRef.current = null;
    };
  }, []);

  // Update deck.gl layers on state change
  useEffect(() => {
    const currentFrame = heatmapFrames[forecastHour] ?? null;
    const heatmapPoints = currentFrame ? currentFrame.points : [];

    const args: Parameters<typeof buildLayers> = [
      routes,
      selectedRouteId,
      heatmapPoints,
      handleHoverCheckpoint,
    ];

    layerArgsRef.current = args;

    if (overlayRef.current) {
      overlayRef.current.setProps({ layers: buildLayers(...args) });
    }
  }, [routes, selectedRouteId, heatmapFrames, forecastHour, handleHoverCheckpoint]);

  // Fit map to route bounds
  useEffect(() => {
    if (routes.length === 0 || !mapRef.current) return;

    const allLngs = routes.flatMap(r => r.polyline.map(([, lng]) => lng));
    const allLats = routes.flatMap(r => r.polyline.map(([lat]) => lat));

    mapRef.current.fitBounds(
      [
        [Math.min(...allLngs), Math.min(...allLats)],
        [Math.max(...allLngs), Math.max(...allLats)],
      ],
      { padding: 100, duration: 1000, essential: true }
    );
  }, [routes]);

  return (
    <>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Loading overlay */}
      {status === 'loading' && (
        <div className="map-loading" aria-live="polite">
          <div className="spinner spinner--light" style={{ width: 40, height: 40, borderWidth: 3 }} />
          <span className="map-loading__text">Calculating weather-safe routes…</span>
        </div>
      )}

      {/* Idle hint */}
      {status === 'idle' && (
        <div className="map-idle" aria-hidden="true">
          <div className="map-idle__card">
            <div className="map-idle__icon">🛣️</div>
            <div className="map-idle__heading">RouteWise</div>
            <div className="map-idle__sub">
              Enter your origin and destination in the left panel to analyze weather-safe truck routes.
            </div>
          </div>
        </div>
      )}

      {/* Risk legend */}
      {status === 'success' && routes.length > 0 && (
        <div className="risk-legend" aria-label="Risk level legend">
          <p className="risk-legend__title">Risk Level</p>
          {LEGEND_ITEMS.map(item => (
            <div key={item.label} className="risk-legend__item">
              <div className="risk-legend__swatch" style={{ background: item.color }} />
              <span>{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
