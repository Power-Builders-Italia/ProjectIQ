// SPFx plumbing: tenant settings through SPHttpClient and Dataverse calls through AadHttpClient.
import { AadHttpClient, SPHttpClient } from '@microsoft/sp-http';
import type { BaseComponentContext } from '@microsoft/sp-component-base';

import { DataverseClient, type HttpSend } from './DataverseClient';
import { ProjectIQService } from './ProjectIQService';
import {
  APP_ID_KEY, DEFAULT_APP_ID, DEFAULT_ENVIRONMENT_URL, ENVIRONMENT_URL_KEY, normaliseEnvironmentUrl, type AgentSettings,
} from '../settings';

export class SettingsMissingError extends Error {}

async function storageEntity(context: BaseComponentContext, key: string): Promise<string | undefined> {
  try {
    const web = context.pageContext.web?.absoluteUrl || context.pageContext.site?.absoluteUrl;
    if (!web) return undefined;
    const response = await context.spHttpClient.get(`${web}/_api/web/GetStorageEntity('${key}')`, SPHttpClient.configurations.v1);
    if (!response.ok) return undefined;
    const json = await response.json() as { Value?: string | null };
    return json.Value || undefined;
  } catch {
    return undefined;
  }
}

export async function loadSettings(context: BaseComponentContext): Promise<AgentSettings> {
  const [env, app] = await Promise.all([storageEntity(context, ENVIRONMENT_URL_KEY), storageEntity(context, APP_ID_KEY)]);
  const environmentUrl = normaliseEnvironmentUrl(env) || normaliseEnvironmentUrl(DEFAULT_ENVIRONMENT_URL);
  if (!environmentUrl) throw new SettingsMissingError(ENVIRONMENT_URL_KEY);
  return { environmentUrl, appId: app || DEFAULT_APP_ID || undefined };
}

export async function createService(context: BaseComponentContext, settings: AgentSettings): Promise<ProjectIQService> {
  const client = await context.aadHttpClientFactory.getClient(settings.environmentUrl);
  const send: HttpSend = async (method, url, headers, body) => {
    const response = await client.fetch(url, AadHttpClient.configurations.v1, { method, headers, body });
    return { ok: response.ok, status: response.status, statusText: response.statusText, text: () => response.text() };
  };
  return new ProjectIQService(new DataverseClient(settings.environmentUrl, send));
}
