# Application structure

The entrypoint is `app.py`. It contains the Streamlit interface and the research
calculation/replay functions. `environment.py` supplies the original public data
adapters, maps and standard reports. `evidence.py` scopes saved run evidence and
invalidates reviews when data changes.

`ai_providers.py` declares supported providers and endpoint/model checks.
`crew_runtime.py` implements a CrewAI BaseLLM adapter over HTTPS chat-completion
APIs and the owner-configured local Ollama endpoint. No additional provider SDK
or implicit OpenAI key is needed. Provider-specific request fields are selected
explicitly; unsupported cache metadata is not forwarded.

`crewai_compat.py` restores Python's standard warning function after the pinned
CrewAI import, avoiding a Python 3.12 / Matplotlib PDF-export conflict. It does
not suppress scientific warnings or change agent calculations.

`crew_config.py` defines run budgets and the five-role roster. `agent_common.py`
uses the explicit synchronous `CrewAgentExecutor` supported by the pinned
CrewAI release, avoiding implicit Flow scheduling inside Streamlit workers.
This executor is version-sensitive: keep the supplied CrewAI pin and rerun tests
before upgrading it. `agents/` contains exactly five agent definitions.

`crew_workflow.py` executes coordinator, climate/air, geospatial/water,
ecology/field, then reviewer/reporter in order. The app runs the team in one
worker thread; the Streamlit thread receives progress through a queue. Agents
have bounded iterations and cannot delegate, browse arbitrary URLs or execute
arbitrary code. The reviewer receives prior specialist notes and scoped evidence.

`agent_tools.py` provides the default evidence tools. The research app supplies
the corresponding audited tools through `research_agent_tools`, adding executed
arguments, output hashes and bounded result previews to the activity record.
These are execution records, not hidden model reasoning or independent data
validation.

Provider keys remain on each adapter instance. No run export includes secrets.
Review reuse is limited to the current Streamlit session and matching evidence,
question, provider and model. Failed reviews do not become completed cached
answers. A fresh review is explicitly requested by the user.

The application needs no database, login service or Supabase. Session data is
temporary; downloadable packages provide the durable research record.
