import type { Checkpoint } from '../../types';
import { getCss, RISK_LABEL } from '../../utils/riskColors';
import {
  formatEta,
  formatWind,
  formatRain,
  formatSnow,
  formatTemp,
} from '../../utils/formatters';
import { useAppState } from '../../context/AppContext';

export function CheckpointTooltip() {
  const { hoverInfo } = useAppState();
  if (!hoverInfo) return null;

  const { x, y, checkpoint } = hoverInfo;
  const { weather, risk_level, eta, distance_from_start_miles } = checkpoint;
  const riskColor = getCss(risk_level);

  // Offset tooltip from cursor
  const left = x + 16;
  const top  = y - 12;

  return (
    <div
      className="checkpoint-tooltip"
      style={{ left, top }}
      role="tooltip"
    >
      <div className="tooltip__header">
        <span className="tooltip__title">
          Mile {distance_from_start_miles.toFixed(0)}
        </span>
        <span
          className="tooltip__risk-badge"
          style={{ background: riskColor }}
        >
          {RISK_LABEL[risk_level]}
        </span>
      </div>

      <div className="tooltip__eta">
        ETA: {formatEta(eta)}
      </div>

      <div className="tooltip__weather">
        <div className="tooltip__weather-item">
          <span className="tooltip__weather-label">Wind</span>
          <span className="tooltip__weather-value">{formatWind(weather.wind_speed_mph)}</span>
        </div>
        <div className="tooltip__weather-item">
          <span className="tooltip__weather-label">Temp</span>
          <span className="tooltip__weather-value">{formatTemp(weather.temperature_f)}</span>
        </div>
        <div className="tooltip__weather-item">
          <span className="tooltip__weather-label">Rain</span>
          <span className="tooltip__weather-value">{formatRain(weather.rain_in_hr)}</span>
        </div>
        <div className="tooltip__weather-item">
          <span className="tooltip__weather-label">Snow</span>
          <span className="tooltip__weather-value">{formatSnow(weather.snow_in_hr)}</span>
        </div>
      </div>
    </div>
  );
}
