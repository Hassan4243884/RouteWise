/**
 * CARTO credentials and basemap configuration.
 *
 * Reads CARTO_BASE_URL and CARTO_API_TOKEN from the environment (.env.local),
 * supporting both CARTO_* and VITE_CARTO_* prefixes.
 */

export const CARTO_BASE_URL: string =
  (import.meta.env.CARTO_BASE_URL as string | undefined) ||
  (import.meta.env.VITE_CARTO_BASE_URL as string | undefined) ||
  'https://gcp-us-east1.api.carto.com';

export const CARTO_API_TOKEN: string =
  (import.meta.env.CARTO_API_TOKEN as string | undefined) ||
  (import.meta.env.VITE_CARTO_API_TOKEN as string | undefined) ||
  '';

/**
 * Returns the CARTO Positron map style for MapLibre GL.
 * If CARTO_API_TOKEN is provided, it uses CARTO's Positron vector GL style
 * authenticated with the token. Otherwise, falls back to public Positron raster tiles.
 */
export function getCartoMapStyle(): string | { version: 8; sources: Record<string, unknown>; layers: unknown[] } {
  const token = CARTO_API_TOKEN.trim();

  if (token) {
    // Vector GL style with token query parameter
    return `https://basemaps.cartocdn.com/gl/positron-gl-style/style.json?api_key=${encodeURIComponent(token)}`;
  }

  // Fallback raster tile style
  return {
    version: 8,
    sources: {
      'carto-light': {
        type: 'raster',
        tiles: [
          'https://a.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png',
          'https://b.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png',
          'https://c.basemaps.cartocdn.com/rastertiles/light_all/{z}/{x}/{y}.png',
        ],
        tileSize: 256,
        attribution:
          '© <a href="https://carto.com/" target="_blank" rel="noopener">CARTO</a>, © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a>',
      },
    },
    layers: [
      {
        id: 'carto-light-layer',
        type: 'raster',
        source: 'carto-light',
        minzoom: 0,
        maxzoom: 20,
      },
    ],
  };
}

/**
 * MapLibre transformRequest hook that attaches the CARTO API token and
 * Bearer authorization header to all CARTO resource requests (vector tiles, fonts, sprites).
 */
export function cartoTransformRequest(url: string): { url: string; headers?: Record<string, string> } {
  const token = CARTO_API_TOKEN.trim();
  if (!token) return { url };

  const isCarto =
    url.includes('carto.com') ||
    url.includes('cartocdn.com') ||
    (CARTO_BASE_URL && url.startsWith(CARTO_BASE_URL));

  if (isCarto) {
    const hasKey = url.includes('api_key=') || url.includes('key=');
    const delimiter = url.includes('?') ? '&' : '?';
    return {
      url: hasKey ? url : `${url}${delimiter}api_key=${encodeURIComponent(token)}`,
      headers: {
        Authorization: `Bearer ${token}`,
      },
    };
  }

  return { url };
}
