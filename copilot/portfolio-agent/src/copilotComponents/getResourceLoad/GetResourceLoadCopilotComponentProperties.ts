import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  resource: z.string().optional().describe('Name of the person; "me" for the signed-in user; empty for everyone.'),
  from: z.string().optional().describe('First day of the period, yyyy-mm-dd; default this week.'),
  weeks: z.number().optional().describe('Number of weeks to show, 1-26; default 8.')
});

export type IGetResourceLoadProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
