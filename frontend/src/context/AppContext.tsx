import {
  createContext,
  useContext,
  useReducer,
  type ReactNode,
  type Dispatch,
} from 'react';
import type {
  AppStatus,
  HeatmapFrame,
  HoverInfo,
  RouteResult,
} from '../types';

// ── State ────────────────────────────────────────────────────────────────────

export interface AppState {
  status: AppStatus;
  error: string | null;
  routes: RouteResult[];
  recommendedRouteId: string | null;
  heatmapFrames: HeatmapFrame[];
  selectedRouteId: string | null;
  forecastHour: number;
  hoverInfo: HoverInfo | null;
}

const initialState: AppState = {
  status: 'idle',
  error: null,
  routes: [],
  recommendedRouteId: null,
  heatmapFrames: [],
  selectedRouteId: null,
  forecastHour: 0,
  hoverInfo: null,
};

// ── Actions ──────────────────────────────────────────────────────────────────

export type Action =
  | { type: 'FETCH_START' }
  | {
      type: 'FETCH_SUCCESS';
      routes: RouteResult[];
      recommendedRouteId: string;
      heatmapFrames: HeatmapFrame[];
    }
  | { type: 'FETCH_ERROR'; error: string }
  | { type: 'SELECT_ROUTE'; routeId: string }
  | { type: 'SET_FORECAST_HOUR'; hour: number }
  | { type: 'SET_HOVER_INFO'; info: HoverInfo | null }
  | { type: 'RESET' };

// ── Reducer ──────────────────────────────────────────────────────────────────

function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'FETCH_START':
      return { ...state, status: 'loading', error: null };

    case 'FETCH_SUCCESS':
      return {
        ...state,
        status: 'success',
        error: null,
        routes: action.routes,
        recommendedRouteId: action.recommendedRouteId,
        heatmapFrames: action.heatmapFrames,
        // Auto-select the recommended route
        selectedRouteId: action.recommendedRouteId,
        forecastHour: 0,
      };

    case 'FETCH_ERROR':
      return { ...state, status: 'error', error: action.error };

    case 'SELECT_ROUTE':
      return { ...state, selectedRouteId: action.routeId };

    case 'SET_FORECAST_HOUR':
      return { ...state, forecastHour: action.hour };

    case 'SET_HOVER_INFO':
      return { ...state, hoverInfo: action.info };

    case 'RESET':
      return initialState;

    default:
      return state;
  }
}

// ── Context ──────────────────────────────────────────────────────────────────

const AppStateContext = createContext<AppState | null>(null);
const AppDispatchContext = createContext<Dispatch<Action> | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, initialState);
  return (
    <AppStateContext.Provider value={state}>
      <AppDispatchContext.Provider value={dispatch}>
        {children}
      </AppDispatchContext.Provider>
    </AppStateContext.Provider>
  );
}

export function useAppState(): AppState {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within AppProvider');
  return ctx;
}

export function useAppDispatch(): Dispatch<Action> {
  const ctx = useContext(AppDispatchContext);
  if (!ctx) throw new Error('useAppDispatch must be used within AppProvider');
  return ctx;
}
