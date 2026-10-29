// Language of the views: English, Italian, French or German, chosen from the SharePoint UI culture of the user
// (pageContext.cultureInfo), as the ProjectIQ PCF controls do with the Dataverse user language.
import { de } from './de';
import { en, type Strings } from './en';
import { fr } from './fr';
import { it } from './it';

export type { Strings };
export type Language = 'en' | 'it' | 'fr' | 'de';

const STRINGS: Record<Language, Strings> = { en, it, fr, de };

/** English strings, for the context sent to Copilot (the model answers in the user's language anyway). */
export const EN = en;

let current: Language = 'en';
let currentCulture: string | undefined;

/** Language of a culture name such as it-IT or de-CH; English when the language is not translated. */
export function resolveLanguage(culture: string | undefined): Language {
  const code = (culture || '').toLowerCase().split(/[-_]/)[0];
  return code === 'it' || code === 'fr' || code === 'de' ? code : 'en';
}

/** Sets the culture of the user, used for the texts and for number and date formats. */
export function setCulture(culture: string | undefined): void {
  currentCulture = culture || undefined;
  current = resolveLanguage(culture);
}

export const language = (): Language => current;

/** Culture for Intl formats: the SharePoint culture when known, otherwise the browser's. */
export const culture = (): string | undefined =>
  currentCulture || (typeof navigator !== 'undefined' ? navigator.language : undefined);

export const strings = (): Strings => STRINGS[current];
