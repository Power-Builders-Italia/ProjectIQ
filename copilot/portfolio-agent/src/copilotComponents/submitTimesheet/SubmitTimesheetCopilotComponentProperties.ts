import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  project: z.string().optional().describe('Project code (for example PRJ-000123) or name, as written by the user.'),
  hours: z.number().optional().describe('Hours to log on the day, 0-24 in quarter hours.'),
  date: z.string().optional().describe('Day of the hours as yyyy-mm-dd; "today" or "yesterday" are accepted.'),
  wbsNode: z.string().optional().describe('WBS phase or task code or name within the project.'),
  notes: z.string().optional().describe('Note for the time entry.'),
  weekOf: z.string().optional().describe('Any day of the week to show, yyyy-mm-dd; default the current week.')
});

export type ISubmitTimesheetProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
