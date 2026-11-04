import { useState, useRef, useEffect, useId } from 'react';

// ── Major North American freight / logistics hubs ─────────────────────────────
const FREIGHT_HUBS = [
  'Chicago, IL',
  'Dallas, TX',
  'Atlanta, GA',
  'Los Angeles, CA',
  'New York, NY',
  'Houston, TX',
  'Indianapolis, IN',
  'Memphis, TN',
  'Columbus, OH',
  'Kansas City, MO',
  'Denver, CO',
  'Salt Lake City, UT',
  'Seattle, WA',
  'Phoenix, AZ',
  'Louisville, KY',
  'Cincinnati, OH',
  'Charlotte, NC',
  'Nashville, TN',
  'Minneapolis, MN',
  'Detroit, MI',
  'Philadelphia, PA',
  'Baltimore, MD',
  'Jacksonville, FL',
  'Miami, FL',
  'San Antonio, TX',
  'El Paso, TX',
  'Albuquerque, NM',
  'Las Vegas, NV',
  'Sacramento, CA',
  'Portland, OR',
  'Spokane, WA',
  'Billings, MT',
  'Sioux Falls, SD',
  'Des Moines, IA',
  'Omaha, NE',
  'Tulsa, OK',
  'Little Rock, AR',
  'New Orleans, LA',
  'Birmingham, AL',
  'Richmond, VA',
  'Buffalo, NY',
  'Cleveland, OH',
  'Pittsburgh, PA',
  'St. Louis, MO',
  'San Francisco, CA',
  'San Diego, CA',
  'Fresno, CA',
  'Bakersfield, CA',
  'Reno, NV',
  'Boise, ID',
];

interface Props {
  id?: string;
  label: string;
  variant: 'origin' | 'dest';
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  disabled?: boolean;
}

export function SearchableCitySelect({
  id,
  label,
  variant,
  value,
  onChange,
  placeholder = 'Search cities…',
  disabled = false,
}: Props) {
  const uid = useId();
  const inputId = id ?? uid;
  const [query, setQuery] = useState(value);
  const [open, setOpen] = useState(false);
  const [cursor, setCursor] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLUListElement>(null);

  // Keep local query in sync when parent resets value
  useEffect(() => {
    setQuery(value);
  }, [value]);

  const filtered = query.trim()
    ? FREIGHT_HUBS.filter(h => h.toLowerCase().includes(query.toLowerCase()))
    : FREIGHT_HUBS;

  function select(city: string) {
    setQuery(city);
    onChange(city);
    setOpen(false);
    setCursor(-1);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const v = e.target.value;
    setQuery(v);
    onChange(v);
    setOpen(true);
    setCursor(-1);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) {
      if (e.key === 'ArrowDown' || e.key === 'Enter') setOpen(true);
      return;
    }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor(c => Math.min(c + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor(c => Math.max(c - 1, 0));
    } else if (e.key === 'Enter' && cursor >= 0) {
      e.preventDefault();
      select(filtered[cursor]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  }

  // Scroll active list item into view
  useEffect(() => {
    if (cursor >= 0 && listRef.current) {
      const el = listRef.current.children[cursor] as HTMLElement;
      el?.scrollIntoView({ block: 'nearest' });
    }
  }, [cursor]);

  // Close on outside click
  useEffect(() => {
    function onOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', onOutside);
    return () => document.removeEventListener('mousedown', onOutside);
  }, []);

  function clear() {
    setQuery('');
    onChange('');
    setOpen(true);
  }

  return (
    <div className="city-select" ref={containerRef}>
      {/* Label */}
      <label className="city-select__label" htmlFor={inputId}>
        <span
          className={`city-select__label-icon city-select__label-icon--${variant}`}
          aria-hidden="true"
        >
          {variant === 'origin' ? 'A' : 'B'}
        </span>
        {label}
      </label>

      {/* Input + clear btn */}
      <div className="city-select__input-wrap">
        <input
          id={inputId}
          className="city-select__input"
          type="text"
          autoComplete="off"
          spellCheck={false}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${inputId}-list`}
          aria-activedescendant={cursor >= 0 ? `${inputId}-item-${cursor}` : undefined}
          value={query}
          onChange={handleInputChange}
          onFocus={() => setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
        />
        <button
          className={`city-select__clear${query ? ' visible' : ''}`}
          type="button"
          onClick={clear}
          aria-label="Clear"
          tabIndex={-1}
        >
          ×
        </button>
      </div>

      {/* Dropdown */}
      {open && !disabled && (
        <div className="city-select__dropdown" role="listbox" id={`${inputId}-list`}>
          <ul className="city-select__list" ref={listRef}>
            {filtered.length > 0 ? (
              filtered.map((city, i) => (
                <li
                  key={city}
                  id={`${inputId}-item-${i}`}
                  className={`city-select__item${i === cursor ? ' city-select__item--active' : ''}`}
                  role="option"
                  aria-selected={i === cursor}
                  onMouseDown={() => select(city)}
                >
                  <span className="city-select__item-icon">📍</span>
                  {city}
                </li>
              ))
            ) : (
              <li className="city-select__no-results">No results — type to use custom address</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
