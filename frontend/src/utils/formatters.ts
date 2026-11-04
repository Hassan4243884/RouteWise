export function formatDuration(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

export function formatDistance(miles: number): string {
  return `${miles.toFixed(1)} mi`;
}

export function formatEta(isoString: string): string {
  try {
    return new Date(isoString).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function formatDatetime(isoString: string): string {
  try {
    return new Date(isoString).toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export function formatWind(mph: number): string {
  return `${mph.toFixed(1)} mph`;
}

export function formatRain(inHr: number): string {
  return `${inHr.toFixed(3)} in/hr`;
}

export function formatSnow(inHr: number): string {
  return `${inHr.toFixed(2)} in/hr`;
}

export function formatTemp(f: number): string {
  return `${f.toFixed(0)}°F`;
}

/** Default datetime-local value: 1 hour from now (passes backend validation) */
export function defaultDepartureValue(): string {
  const d = new Date(Date.now() + 3_600_000);
  // datetime-local format: "YYYY-MM-DDTHH:MM"
  return d.toISOString().slice(0, 16);
}
