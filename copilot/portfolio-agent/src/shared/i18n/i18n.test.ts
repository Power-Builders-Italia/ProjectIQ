import { de } from './de';
import { en } from './en';
import { fr } from './fr';
import { it as italian } from './it';
import { language, resolveLanguage, setCulture, strings } from './index';
import { promptFor } from '../intents';
import { projectStatusLabel, timeStatusLabel } from '../ui/labels';

/** Paths of every leaf, with the number of parameters of the functions, to compare the shape of two string tables. */
function shape(value: unknown, path = ''): string[] {
  if (typeof value === 'function') return [`${path}()${value.length}`];
  if (Array.isArray(value)) return [`${path}[]`];
  if (value && typeof value === 'object') {
    return Object.keys(value).sort().reduce<string[]>((all, k) => all.concat(shape((value as Record<string, unknown>)[k], `${path}.${k}`)), []);
  }
  return [path];
}

/** Every text of a table, with the functions called on sample arguments. */
function texts(value: unknown): string[] {
  if (typeof value === 'string') return [value];
  if (typeof value === 'function') return [String((value as (...a: unknown[]) => unknown)(2, '3', 4, 5))];
  if (Array.isArray(value)) return value.map(String);
  if (value && typeof value === 'object') return Object.keys(value).reduce<string[]>((all, k) => all.concat(texts((value as Record<string, unknown>)[k])), []);
  return [];
}

describe('i18n', () => {
  afterEach(() => setCulture(undefined));

  it('maps SharePoint cultures to the four languages, English otherwise', () => {
    expect(resolveLanguage('it-IT')).toBe('it');
    expect(resolveLanguage('de-CH')).toBe('de');
    expect(resolveLanguage('fr_CA')).toBe('fr');
    expect(resolveLanguage('en-GB')).toBe('en');
    expect(resolveLanguage('es-ES')).toBe('en');
    expect(resolveLanguage(undefined)).toBe('en');
  });

  it('has the same keys and parameters in every language', () => {
    const reference = shape(en);
    for (const table of [italian, fr, de]) expect(shape(table)).toEqual(reference);
  });

  it('has no empty text', () => {
    for (const table of [en, italian, fr, de]) {
      for (const text of texts(table)) expect(text.trim()).not.toBe('');
    }
  });

  it('keeps the {project} placeholder in the prompts that need it', () => {
    for (const table of [italian, fr, de]) {
      for (const key of Object.keys(en.intents) as (keyof typeof en.intents)[]) {
        expect(table.intents[key].prompt.indexOf('{project}') >= 0).toBe(en.intents[key].prompt.indexOf('{project}') >= 0);
      }
    }
  });

  it('switches texts, prompts and labels with the culture', () => {
    setCulture('it-IT');
    expect(language()).toBe('it');
    expect(strings().common.openInApp).toBe('Apri in ProjectIQ');
    expect(promptFor('GetProjectHealth', 'PRJ-1')).toBe('Come sta andando il progetto PRJ-1?');
    expect(projectStatusLabel(365000001)).toBe('Sospeso');
    expect(timeStatusLabel(365000002)).toBe('Rifiutata');
    expect(projectStatusLabel(1, en)).toBe('In Progress');
    setCulture('nl-NL');
    expect(promptFor('GetProjectHealth', 'PRJ-1')).toBe('How is project PRJ-1 going?');
  });
});
