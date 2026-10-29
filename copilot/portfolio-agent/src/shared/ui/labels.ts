// Display names of the ProjectIQ choice values used by the views, in the user's language (or in English for the model context).
import { PROJECT_STATUS } from '../logic/portfolio';
import { STATUS } from '../projectiq/timesheet';
import { strings, type Strings } from '../i18n';

export function projectStatusLabel(status: number, s: Strings = strings()): string | undefined {
  const key = (Object.keys(PROJECT_STATUS) as (keyof typeof PROJECT_STATUS)[]).filter(k => PROJECT_STATUS[k] === status)[0];
  return key ? s.projectStatus[key] : undefined;
}

export function timeStatusLabel(status: number, s: Strings = strings()): string | undefined {
  const key = (Object.keys(STATUS) as (keyof typeof STATUS)[]).filter(k => STATUS[k] === status)[0];
  return key ? s.timeStatus[key] : undefined;
}
