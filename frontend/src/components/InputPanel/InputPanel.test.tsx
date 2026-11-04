/**
 * InputPanel — unit tests
 *
 * Verifies:
 * - Form renders all required fields and labels
 * - Shows validation error when origin is empty
 * - Shows validation error when destination is empty
 * - Shows validation error when load weight is missing
 * - Interval toggle buttons are present and clickable
 * - Submit button is present
 * - Validation blocks submit when fields missing
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AppProvider } from '../../context/AppContext';
import { InputPanel } from './InputPanel';

// Mock the API modules — we don't want real HTTP calls in unit tests
vi.mock('../../api/routingApi', () => ({
  fetchRoutes: vi.fn(),
  fetchHeatmap: vi.fn(),
  boundsFromPolylines: vi.fn(() => ({ north: 1, south: 0, east: 1, west: 0 })),
}));

function renderPanel() {
  return render(
    <AppProvider>
      <InputPanel />
    </AppProvider>,
  );
}

describe('InputPanel — rendering', () => {
  it('renders the origin field', () => {
    renderPanel();
    expect(screen.getByLabelText(/origin/i)).toBeInTheDocument();
  });

  it('renders the destination field', () => {
    renderPanel();
    expect(screen.getByLabelText(/destination/i)).toBeInTheDocument();
  });

  it('renders the departure datetime field', () => {
    renderPanel();
    expect(screen.getByLabelText(/departure/i)).toBeInTheDocument();
  });

  it('renders the load weight field', () => {
    renderPanel();
    expect(screen.getByLabelText(/load/i)).toBeInTheDocument();
  });

  it('renders three interval toggle buttons', () => {
    renderPanel();
    expect(screen.getByText('10 mi')).toBeInTheDocument();
    expect(screen.getByText('25 mi')).toBeInTheDocument();
    expect(screen.getByText('50 mi')).toBeInTheDocument();
  });

  it('renders the submit button', () => {
    renderPanel();
    expect(screen.getByRole('button', { name: /find safe routes/i })).toBeInTheDocument();
  });
});

describe('InputPanel — validation', () => {
  it('shows an error when origin is blank on submit', async () => {
    renderPanel();
    // Leave origin blank, fill others
    await userEvent.type(screen.getByLabelText(/destination/i), 'Indianapolis, IN');
    await userEvent.type(screen.getByLabelText(/load/i), '35000');

    fireEvent.submit(screen.getByRole('button', { name: /find safe routes/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/origin/i);
    });
  });

  it('shows an error when destination is blank on submit', async () => {
    renderPanel();
    await userEvent.type(screen.getByLabelText(/origin/i), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText(/load/i), '35000');

    fireEvent.submit(screen.getByRole('button', { name: /find safe routes/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/destination/i);
    });
  });

  it('shows an error when load weight is missing', async () => {
    renderPanel();
    await userEvent.type(screen.getByLabelText(/origin/i), 'Chicago, IL');
    await userEvent.type(screen.getByLabelText(/destination/i), 'Indianapolis, IN');
    // Leave load weight empty

    fireEvent.submit(screen.getByRole('button', { name: /find safe routes/i }).closest('form')!);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toHaveTextContent(/load weight/i);
    });
  });
});

describe('InputPanel — interval toggle', () => {
  it('clicking "10 mi" selects the 10-mile interval', async () => {
    renderPanel();
    const btn10 = screen.getByText('10 mi');
    await userEvent.click(btn10);
    // Button should receive the "active" class after click
    expect(btn10).toHaveClass('active');
  });

  it('clicking "50 mi" selects the 50-mile interval', async () => {
    renderPanel();
    const btn50 = screen.getByText('50 mi');
    await userEvent.click(btn50);
    expect(btn50).toHaveClass('active');
  });

  it('default selected interval is 25 miles', () => {
    renderPanel();
    expect(screen.getByText('25 mi')).toHaveClass('active');
  });
});
