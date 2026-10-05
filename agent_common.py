"""Shared construction settings; the five agent definitions are in agents/."""
from crew_config import POLICY
from crewai_compat import Agent


def make_agent(role, goal, speciality, llm, tools):
    return Agent(
        role=role, goal=goal, backstory=speciality + "\n\n" + POLICY,
        llm=llm, tools=tools, verbose=False, allow_delegation=False,
        max_iter=3, max_retry_limit=0, respect_context_window=False,
        reasoning=False, planning=False, memory=False, cache=False,
        # Explicit synchronous ReAct executor for the pinned CrewAI version.
        # Avoid implicit Flow-executor scheduling in Streamlit worker threads.
        executor_class="CrewAgentExecutor",
    )
