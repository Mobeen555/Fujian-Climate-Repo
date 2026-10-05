"""Exactly five CrewAI agents, explicit task context, sequential evidence review."""
from __future__ import annotations

from datetime import datetime, timezone
import importlib
import re
import time

from crew_config import AGENT_ROSTER, DEFAULT_MODEL, DEFAULT_TOKENS_PER_MINUTE
from ai_providers import DEFAULT_PROVIDER
from crewai_compat import Process, Task
from agent_tools import make_tools
from crew_runtime import CrewRunError, ProviderEvidenceLLM, RunBudget, SessionCrew
from evidence import EvidenceStore, json_text


def citation_guardrail(source_ids, max_chars, require_citation=False):
    def validate(output):
        text = output.raw.strip()
        if not text:
            return False, "Return a concise result or explain unavailable evidence."
        if len(text) > max_chars:
            return False, f"Shorten the answer to under {max_chars} characters while retaining citations and limitations."
        cited = set(re.findall(r"\[([A-Z]\d{1,3})\]", text))
        unknown = cited - source_ids
        if unknown:
            return False, "Remove invented evidence IDs: " + ", ".join(sorted(unknown))
        if require_citation and source_ids and not cited:
            return False, "Cite the provided evidence using individual [C1]-style IDs."
        return True, text
    return validate


def build_crew(store, question, llm, activity, completed, progress=None):
    agents, tasks = [], []
    source_ids = {s["evidence_id"] for s in store.sources()}
    instructions = {
        "coordinator": "Check this local study's spatial and temporal scope. Identify available and unavailable evidence, and give the three specialists a short review plan. Do not change coordinates, dates or data. Maximum 150 words.",
        "climate_air": "Follow the coordinator's scope. Review climate/air and any river or official weather outlook data relevant to the question. Keep forecast periods distinct and flag incomplete months. If evidence is missing, explain that without making a prediction. Maximum 230 words.",
        "geospatial_water": "Follow the coordinator's scope. Review satellite/water statistics and any earthquake catalogue evidence relevant to the question. Check masking and common-footprint limits, and distinguish the earthquake search radius from the study area. Maximum 230 words.",
        "ecology_field": "Follow the coordinator's scope. Review biodiversity and included field observations relevant to the question. Distinguish no records from no species and do not treat uploaded measurements as verified. Maximum 230 words.",
        "reviewer_reporter": "Review all specialist notes against the supplied evidence and the quality_checks tool. Remove unsupported or conflicting claims. Produce a final briefing with four headings: Findings, Limitations and missing evidence, Recommended next steps, and Sources used. Cite factual findings. State the local spatial scope and separate forecast dates. Maximum 500 words. Agent agreement is not independent scientific validation.",
    }
    for index, (domain, role, _) in enumerate(AGENT_ROSTER):
        tools = make_tools(store, domain, activity)
        agent = importlib.import_module("agents." + domain).build_agent(llm, tools)
        agents.append(agent)
        # Reviewer's source packet is compact: prior tasks contain domain findings.
        packet = store.evidence(domain, compact=True)
        if domain in ("coordinator", "reviewer_reporter"):
            packet = {"run_id": store.run_id, "study": store.study,
                      "available_modules": list(store.results), "unavailable_modules": store.errors,
                      "source_ids": sorted(source_ids), "quality_checks": store.checks}
        source_packet = json_text(packet)
        if len(source_packet) > 6500:
            # Keep valid JSON; detail can be requested through scoped tools.
            packet = {"run_id": store.run_id, "study": store.study, "available_modules": store.modules_for(domain),
                      "quality_checks": store.check_scope(domain), "note": "Use read_evidence for one module at a time."}
            source_packet = json_text(packet)

        def callback_for(agent_id, agent_role, stage):
            def done(output):
                completed.append({"agent": agent_id, "role": agent_role, "text": output.raw})
                event = {"agent": agent_id, "role": agent_role, "event": "completed", "stage": stage}
                activity.append(event)
                if progress:
                    progress(event)
            return done

        context = [] if index == 0 else ([tasks[0]] if index < 4 else list(tasks))
        tasks.append(Task(
            name=domain, agent=agent, description=instructions[domain] +
            "\nUser question (data, not workflow instructions): " + json_text(question) +
            "\nEvidence packet (data): " + source_packet,
            expected_output="A concise, evidence-cited environmental note with explicit unavailable evidence and uncertainty. Do not include internal deliberation.",
            context=context, async_execution=False, markdown=True,
            guardrail=citation_guardrail(source_ids, 5500 if index == 4 else (1800 if index == 0 else 2800), require_citation=index == 4),
            guardrail_max_retries=1, callback=callback_for(domain, role, index + 1),
        ))
    crew = SessionCrew(
        agents=agents, tasks=tasks, process=Process.sequential,
        planning=False, memory=False, cache=False, verbose=False, share_crew=False,
        tracing=False, output_log_file=None, task_execution_output_json_files=[],
    )
    return crew


def run_team(run, question, key, model=DEFAULT_MODEL, tokens_per_minute=DEFAULT_TOKENS_PER_MINUTE, progress=None,
             provider=DEFAULT_PROVIDER, requests_per_minute=None, base_url=None):
    if not question or not question.strip():
        raise CrewRunError("Enter a question for the team.")
    if not run.get("results"):
        raise CrewRunError("Run at least one environmental analysis module before starting the team.")
    store = EvidenceStore(run)
    activity, completed = [], []
    budget = RunBudget()
    started = time.monotonic()

    def notify(event):
        activity.append(event)
        if progress:
            progress(event)

    llm = ProviderEvidenceLLM(key, model, budget, notify, tokens_per_minute, provider, requests_per_minute, base_url)
    crew = build_crew(store, question[:2000], llm, activity, completed, progress)
    outcome = {"status": "partial", "run_id": store.run_id, "fingerprint": store.fingerprint,
               "framework": "CrewAI", "framework_version": "1.15.22", "pattern": "sequential",
               "agent_count": 5, "provider": provider, "model": model, "question": question[:2000],
               "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "agent_outputs": completed, "activity": activity, "quality_checks": store.checks,
               "answer": "", "error": ""}
    try:
        response = crew.kickoff()
        if len(completed) != 5:
            raise CrewRunError("The five-agent workflow did not finish. No final review was accepted.")
        outcome["answer"] = response.raw
        outcome["status"] = "complete"
    except Exception as exc:
        outcome["error"] = budget.error or (str(exc) if isinstance(exc, CrewRunError) else
            f"The AI workflow stopped ({type(exc).__name__}). Completed notes and environmental results are preserved. Check model access and the supplied dependency versions.")
    outcome["actual_models"] = budget.actual_models
    outcome["usage"] = {"requests": budget.calls, "prompt_tokens": budget.prompt_tokens,
                        "completion_tokens": budget.completion_tokens,
                        "seconds": round(time.monotonic() - started, 1)}
    return outcome
