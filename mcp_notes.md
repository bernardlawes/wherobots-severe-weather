# Agentic Tooling Notes

I used the Wherobots MCP server through VS Code with GitHub Copilot Agent during the discovery and development workflow.

## Where it accelerated the work

MCP was particularly useful for initial catalog discovery. I used it to identify the available Wherobots catalogs, explore NOAA and Overture datasets, inspect relevant tables, and execute exploratory SQL. This helped narrow the project quickly to NWS warning polygons and Overture power infrastructure without manually browsing the catalog.

The agent was also useful for rapidly testing questions about the data, such as infrastructure-class distributions and available severe-weather attributes. This shortened the path from a broad customer problem to a concrete spatial analysis.

## Where it fell over

The experience was less reliable when moving from discovery into more stateful, multi-step operations. Some tool calls were rejected because the AI client generated unsupported arguments, although the returned validation errors were clear enough to recover and retry.

I also encountered cases where the agent repeated table discovery rather than progressing to schema inspection, lost the handle for a successfully submitted SQL query, and experienced intermittent tool-call cancellations. In one case I was able to recover by supplying the existing query ID manually.

Separately, job submission through the Wherobots VS Code extension encountered a file-upload endpoint resolution issue in my environment. After confirming the issue with Wherobots, I used managed storage plus the Wherobots Python SDK as the submission path.

## What I would want next

The biggest improvement would be stronger state continuity across related tool calls—particularly preserving query/job identifiers and reliably transitioning from catalog discovery to schema inspection, query execution, and result retrieval.

Overall, MCP was most valuable as an accelerator for discovery and exploratory interaction. For the repeatable operational workflow, I preferred explicit Python/Sedona code and SDK-based job submission because the execution path was easier to inspect, reproduce, and explain.