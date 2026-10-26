/** Progress columns rendered as a bar in the Power Apps grid (Project and WBS Node: op365_progresspct). */
export const isProgressColumn = (name: string | undefined): boolean => !!name && /progresspct$/i.test(name);

/** Bar fill in percent, clamped to 0-100; null when the cell is empty. */
export function progressPercent(value: unknown): number | null {
    if (value === null || value === undefined || value === "") return null;
    const n = typeof value === "number" ? value : Number(value);
    if (!isFinite(n)) return null;
    return Math.min(100, Math.max(0, n));
}

/** Label shown next to the bar: whole percent. */
export const progressLabel = (pct: number): string => `${Math.round(pct)}%`;
