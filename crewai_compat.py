"""Load the pinned CrewAI release without breaking Python 3.12 warnings.

CrewAI 1.15.22 replaces warnings.warn with a filter lacking the Python 3.12
skip_file_prefixes keyword. Restore the original function after import so
Matplotlib's PDF export and other libraries retain the standard warning API.
This does not suppress warnings or change agent execution.
"""
import warnings

import crew_config  # Configure telemetry/storage before CrewAI's first import.

_original_warn = warnings.warn
import crewai as _crewai

if (getattr(warnings.warn, "__module__", "") == "crewai" and
        "_suppress_pydantic_deprecation_warnings" in getattr(warnings.warn, "__qualname__", "")):
    warnings.warn = _original_warn

Agent = _crewai.Agent
BaseLLM = _crewai.BaseLLM
Crew = _crewai.Crew
Process = _crewai.Process
Task = _crewai.Task
from crewai.tools import BaseTool, tool
