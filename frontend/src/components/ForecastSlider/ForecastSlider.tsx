import { useAppDispatch, useAppState } from '../../context/AppContext';

const TICKS = [0, 6, 12, 18, 24, 30, 36, 42, 48];

export function ForecastSlider() {
  const { forecastHour, heatmapFrames } = useAppState();
  const dispatch = useAppDispatch();

  if (heatmapFrames.length === 0) return null;

  const label = forecastHour === 0 ? 'Now' : `+${forecastHour}h`;

  return (
    <div className="forecast-slider" role="region" aria-label="Weather forecast slider">
      <div className="forecast-slider__header">
        <span className="forecast-slider__label">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
          </svg>
          Weather Forecast
        </span>
        <span className="forecast-slider__value">{label}</span>
      </div>

      <div className="forecast-slider__track">
        <input
          type="range"
          className="forecast-slider__range"
          min={0}
          max={48}
          step={1}
          value={forecastHour}
          onChange={e => dispatch({ type: 'SET_FORECAST_HOUR', hour: Number(e.target.value) })}
          aria-label="Forecast hour offset"
          aria-valuemin={0}
          aria-valuemax={48}
          aria-valuenow={forecastHour}
          aria-valuetext={label}
        />
      </div>

      <div className="forecast-slider__ticks">
        {TICKS.map(t => (
          <span key={t} className="forecast-slider__tick">
            {t === 0 ? 'Now' : `+${t}h`}
          </span>
        ))}
      </div>
    </div>
  );
}
