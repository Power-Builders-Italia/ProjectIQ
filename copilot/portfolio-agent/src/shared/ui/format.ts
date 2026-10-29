// Number and date formats in the browser's locale; amounts in the record currency symbol when known.
import { fromDay } from '../projectiq/dates';

const locale = (): string | undefined => (typeof navigator !== 'undefined' ? navigator.language : undefined);

export function money(value: number, symbol?: string, compact = false): string {
  const text = new Intl.NumberFormat(locale(), {
    maximumFractionDigits: compact ? 1 : 0,
    notation: compact && Math.abs(value) >= 10000 ? 'compact' : 'standard',
  }).format(value);
  return symbol ? `${symbol} ${text}` : text;
}

export const hours = (value: number): string =>
  new Intl.NumberFormat(locale(), { maximumFractionDigits: 2 }).format(value) + ' h';

export const pct = (ratio: number): string => `${Math.round(ratio * 100)}%`;

export function date(day: number | undefined): string {
  if (day === undefined) return '–';
  return new Intl.DateTimeFormat(locale(), { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(fromDay(day));
}

export function shortDate(day: number | undefined): string {
  if (day === undefined) return '–';
  return new Intl.DateTimeFormat(locale(), { day: '2-digit', month: 'short', timeZone: 'UTC' }).format(fromDay(day));
}

export function weekday(day: number): string {
  return new Intl.DateTimeFormat(locale(), { weekday: 'short', day: '2-digit', timeZone: 'UTC' }).format(fromDay(day));
}

/** Day number of today in the local time zone (the dates of ProjectIQ are date-only). */
export function localToday(now: Date = new Date()): number {
  return Math.floor(Date.UTC(now.getFullYear(), now.getMonth(), now.getDate()) / 86400000);
}
