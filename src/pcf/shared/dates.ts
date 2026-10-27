// Date-only helpers. WBS dates are DateOnly columns, handled as whole UTC days.

const DAY = 86400000;

/** Day number (days since 1970-01-01 UTC) of a date or ISO string; undefined when empty or invalid. */
export function toDay(value: Date | string | null | undefined): number | undefined {
    if (value === null || value === undefined || value === "") return undefined;
    const d = typeof value === "string" ? new Date(value.length === 10 ? value + "T00:00:00Z" : value) : value;
    const t = d.getTime();
    if (isNaN(t)) return undefined;
    return Math.floor(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) / DAY);
}

export function fromDay(day: number): Date {
    return new Date(day * DAY);
}

/** yyyy-mm-dd, the format the Web API expects for DateOnly columns. */
export function isoDay(day: number): string {
    return fromDay(day).toISOString().substring(0, 10);
}

const LOCALES: Record<number, string> = { 1031: "de-DE", 1033: "en-US", 1036: "fr-FR", 1040: "it-IT" };

/** Locale for day and month names in the user's Dataverse language (the browser locale for any other language). */
export function userLocale(languageId: number | undefined): string | undefined {
    return languageId === undefined ? undefined : LOCALES[languageId];
}
