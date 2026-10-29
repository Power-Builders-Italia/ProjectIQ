// Where the agent finds the ProjectIQ Dataverse environment.
// 1. SharePoint tenant property (storage entity) ProjectIQEnvironmentUrl, set once by a SharePoint administrator;
// 2. otherwise DEFAULT_ENVIRONMENT_URL below, set before building a package for a single customer.
// ProjectIQAppId (optional) is the id of the ProjectIQ model-driven app, used in the "Open in ProjectIQ" links.

export const ENVIRONMENT_URL_KEY = 'ProjectIQEnvironmentUrl';
export const APP_ID_KEY = 'ProjectIQAppId';

export const DEFAULT_ENVIRONMENT_URL = '';
export const DEFAULT_APP_ID = '';

export interface AgentSettings {
  environmentUrl: string;
  appId?: string;
}

/** Normalises an environment URL to https://host without path; undefined when it is not a Dataverse URL. */
export function normaliseEnvironmentUrl(value: string | undefined): string | undefined {
  const v = (value || '').trim();
  const m = /^https:\/\/([a-z0-9-]+(\.[a-z0-9-]+)*\.(dynamics\.com|dynamics\.cn|microsoftdynamics\.de|crm\.dynamics\.us|appsplatform\.us))\/?/i.exec(v);
  return m ? `https://${m[1].toLowerCase()}` : undefined;
}

/** Link that opens a record in the ProjectIQ app. */
export function recordUrl(settings: AgentSettings, table: string, id: string): string {
  const app = settings.appId ? `appid=${encodeURIComponent(settings.appId)}&` : '';
  return `${settings.environmentUrl}/main.aspx?${app}pagetype=entityrecord&etn=${table}&id=${encodeURIComponent(id)}`;
}

/** Link that opens a list (entity list view) in the ProjectIQ app. */
export function listUrl(settings: AgentSettings, table: string): string {
  const app = settings.appId ? `appid=${encodeURIComponent(settings.appId)}&` : '';
  return `${settings.environmentUrl}/main.aspx?${app}pagetype=entitylist&etn=${table}`;
}
