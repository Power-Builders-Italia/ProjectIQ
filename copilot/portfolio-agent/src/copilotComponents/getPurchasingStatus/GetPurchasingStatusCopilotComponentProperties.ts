import { z } from 'zod';
import zodToJsonSchema from 'zod-to-json-schema';

const propertiesSchema = z.object({
  project: z.string().optional().describe('Project code (for example PRJ-000123) or name, as written by the user.'),
  focus: z.enum(['approvals', 'orders', 'rfqs', 'invoices']).optional().describe('Section to open first.')
});

export type IGetPurchasingStatusProperties = z.infer<typeof propertiesSchema>;

export default zodToJsonSchema(propertiesSchema);
