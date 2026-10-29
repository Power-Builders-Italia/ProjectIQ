# ProjectIQ Portfolio Agent

SPFx 1.24 Copilot UX components and declarative agent that show ProjectIQ (Dataverse) in Microsoft 365 Copilot: portfolio and project health, budget, timeline, resource load, purchasing, supplier compliance, hour approval and timesheet submission. Modelled on the PnP sample [zava-project-tracker](https://github.com/pnp/spfx-copilot-components/tree/main/samples/zava-project-tracker), with live data read with the user's delegated token.

- User and admin guide: [docs/en/portfolio-agent.md](../../docs/en/portfolio-agent.md)
- Build, structure and conventions: [docs/dev-environment.md](../../docs/dev-environment.md#portfolio-agent-spfx-copilot-components)

```bash
npm ci
npm test        # Jest on the business rules and the Dataverse client
npm run build   # sharepoint/solution/projectiq-portfolio-agent.sppkg
```
