import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  health: z.enum(['offTrack', 'atRisk', 'onTrack']).optional().describe('Show only projects with this health, for example offTrack for "over budget" or "late" projects.'),
  customer: z.string().optional().describe('Customer name to filter the projects.'),
  manager: z.string().optional().describe('Project manager name to filter the projects.'),
  includeClosed: z.boolean().optional().describe('Include closed projects.')
});

export type IGetPortfolioHealthProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
