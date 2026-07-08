"""
Multi-agent SOAR using CrewAI.

Three specialized security agents work in sequence to:
1. ThreatAnalystAgent — deep threat analysis and context assessment
2. ResponseCoordinatorAgent — plan and coordinate security response actions
3. IncidentReporterAgent — write formal incident documentation

Uses Claude (claude-sonnet-4-6) as the LLM for all agents.
Falls back to LangGraph SOAR (soar_agent.py) if CrewAI is unavailable.

Why CrewAI in addition to LangGraph?
  - CrewAI excels at role-based multi-agent collaboration
  - LangGraph excels at deterministic state-machine workflows
  - Together they cover both structured and emergent reasoning patterns
  - CrewAI agents can delegate to each other; LangGraph nodes cannot
"""
import logging
import os

logger = logging.getLogger(__name__)

_crewai_available = False
try:
    from crewai import Agent, Task, Crew, Process
    _crewai_available = True
except ImportError:
    logger.warning(
        "crewai not installed — crew-based SOAR disabled. "
        "Install with: pip install crewai>=0.80.0"
    )

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


def _get_llm():
    """Get the shared LLM instance for all crew agents."""
    if not ANTHROPIC_API_KEY:
        return None
    try:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model="claude-sonnet-4-6",
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.1,
            max_tokens=1500,
        )
    except Exception as e:
        logger.error("CrewAI LLM init failed: %s", e)
        return None


def _build_security_crew(llm) -> "Crew | None":
    """Build the three-agent security response crew."""
    if not _crewai_available or llm is None:
        return None

    try:
        # Agent 1: Threat Analyst
        analyst = Agent(
            role="Senior Security Threat Analyst",
            goal=(
                "Accurately assess security threats detected by AI CCTV systems, "
                "determine their severity, and identify whether they are genuine incidents "
                "or false positives."
            ),
            backstory=(
                "You are a 15-year veteran security analyst with expertise in physical "
                "security, behavioral threat assessment, and CCTV forensics. You work for "
                "Power Tech Security Corp, a Philippine security agency. You have responded "
                "to hundreds of real security incidents and can quickly separate genuine "
                "threats from AI false positives."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        # Agent 2: Response Coordinator
        coordinator = Agent(
            role="Security Operations Response Coordinator",
            goal=(
                "Develop and coordinate the optimal security response plan based on the "
                "threat analysis, ensuring proportional, effective action while minimizing "
                "escalation and protecting all personnel."
            ),
            backstory=(
                "You are the Security Operations Center (SOC) shift supervisor at Power "
                "Tech Security Corp. You coordinate responses across field guards, client "
                "security teams, and Philippine National Police (PNP). You know exactly "
                "when to escalate and when to hold. RA 11917 compliance is your baseline."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=True,
        )

        # Agent 3: Incident Reporter
        reporter = Agent(
            role="Security Incident Documentation Specialist",
            goal=(
                "Write clear, accurate, legally-compliant incident reports that satisfy "
                "Philippine regulatory requirements (RA 11917, RA 10173) and client SLA "
                "reporting obligations."
            ),
            backstory=(
                "You are a certified security documentation specialist with expertise in "
                "Philippine security regulations. Your reports have been used in court "
                "proceedings and regulatory audits. You write in clear, precise English "
                "with no ambiguity."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        return analyst, coordinator, reporter

    except Exception as e:
        logger.error("Failed to build security crew agents: %s", e)
        return None


async def run_crew_soar_analysis(
    threat: dict,
    camera: dict,
    tenant_id: str,
) -> dict:
    """
    Run the multi-agent CrewAI SOAR analysis on a detected threat.

    Returns the same schema as soar_agent.run_soar_analysis() for
    drop-in compatibility.
    """
    if not _crewai_available or not ANTHROPIC_API_KEY:
        from app.services.soar_agent import run_soar_analysis
        return await run_soar_analysis(threat, camera, tenant_id)

    llm = _get_llm()
    if llm is None:
        from app.services.soar_agent import run_soar_analysis
        return await run_soar_analysis(threat, camera, tenant_id)

    crew_agents = _build_security_crew(llm)
    if crew_agents is None:
        from app.services.soar_agent import run_soar_analysis
        return await run_soar_analysis(threat, camera, tenant_id)

    analyst, coordinator, reporter = crew_agents

    threat_context = _format_threat_context(threat, camera)

    try:
        analysis_task = Task(
            description=f"""
Analyze this AI-detected security threat from a CCTV camera:

{threat_context}

Provide:
1. Threat validity assessment (is this a real threat or likely false positive?)
2. Risk level to personnel (none/low/medium/high/critical)
3. Context factors that increase or decrease concern
4. Confidence in AI detection accuracy
5. Immediate risk to life or property

Keep response under 200 words. Be direct and specific.
""",
            expected_output=(
                "A concise threat assessment covering validity, risk level, "
                "context factors, and confidence in AI detection."
            ),
            agent=analyst,
        )

        response_task = Task(
            description=f"""
Based on the threat analyst's assessment, plan the security response.

Threat context:
{threat_context}

Available actions (list only what's needed, in priority order):
- notify_security_team: Alert on-duty guards via radio/app
- lockdown_zone: Secure the specific zone
- notify_police: Contact Philippine National Police (PNP) 117
- activate_siren: Trigger site alarm
- lock_access_points: Secure electronic doors/gates
- notify_client_admin: Alert client security manager
- create_incident: Log formal incident record
- dispatch_qrt: Send Quick Reaction Team
- review_footage: Flag for human review
- false_positive: No action needed

Output: LIST of action codes only, one per line, with one sentence justification each.
Example: notify_security_team: Immediate guard awareness needed
""",
            expected_output=(
                "Ordered list of response action codes with brief justifications."
            ),
            agent=coordinator,
            context=[analysis_task],
        )

        report_task = Task(
            description=f"""
Write a formal security incident report for this event.

Threat: {threat.get('threat_type')} — {threat.get('description')}
Camera: {camera.get('name', 'Unknown')} | Zone: {camera.get('zone', 'N/A')}
Severity: {threat.get('severity')} | AI Confidence: {threat.get('confidence', 0):.0%}

Format requirements:
- INCIDENT SUMMARY: 2 sentences
- THREAT ASSESSMENT: from the analyst
- RESPONSE ACTIONS: from the coordinator
- RECOMMENDATIONS: 2-3 bullets for prevention
- REGULATORY NOTE: any RA 11917 or RA 10173 reporting requirements

Keep total report under 300 words. Professional tone.
""",
            expected_output=(
                "A formal incident report with summary, assessment, actions, "
                "and recommendations, suitable for regulatory filing."
            ),
            agent=reporter,
            context=[analysis_task, response_task],
        )

        crew = Crew(
            agents=[analyst, coordinator, reporter],
            tasks=[analysis_task, response_task, report_task],
            process=Process.sequential,
            verbose=False,
        )

        # Run synchronously in executor to avoid blocking async
        import asyncio
        loop = asyncio.get_event_loop()
        crew_result = await loop.run_in_executor(
            None,
            lambda: crew.kickoff(inputs={
                "threat_type": threat.get("threat_type", "unknown"),
                "severity": threat.get("severity", "unknown"),
                "camera_name": camera.get("name", "Unknown"),
            }),
        )

        # Parse response plan from coordinator's output
        response_plan = _parse_action_codes(str(response_task.output or ""))

        return {
            "analysis": str(analysis_task.output or ""),
            "response_plan": response_plan,
            "executed_actions": [{"action": a, "status": "queued"} for a in response_plan],
            "incident_report": str(report_task.output or crew_result),
            "ai_powered": True,
            "soar_engine": "crewai",
        }

    except Exception as e:
        logger.error("CrewAI SOAR failed: %s — falling back to LangGraph", e)
        from app.services.soar_agent import run_soar_analysis
        return await run_soar_analysis(threat, camera, tenant_id)


def _format_threat_context(threat: dict, camera: dict) -> str:
    return (
        f"Threat Type: {threat.get('threat_type', 'unknown')}\n"
        f"Severity: {threat.get('severity', 'unknown')}\n"
        f"AI Confidence: {threat.get('confidence', 0):.0%}\n"
        f"Description: {threat.get('description', 'N/A')}\n"
        f"Camera: {camera.get('name', 'Unknown')}\n"
        f"Zone: {camera.get('zone', 'N/A')}\n"
        f"Location: {camera.get('location_description', 'N/A')}\n"
        f"Detected Objects: {threat.get('detected_objects', [])}"
    )


VALID_ACTIONS = {
    "notify_security_team", "lockdown_zone", "notify_police",
    "activate_siren", "lock_access_points", "notify_client_admin",
    "create_incident", "dispatch_qrt", "review_footage", "false_positive",
}


def _parse_action_codes(text: str) -> list[str]:
    """Extract action codes from coordinator's response text."""
    actions = []
    for line in text.strip().split("\n"):
        parts = line.split(":", 1)
        if parts:
            code = parts[0].strip().lower().replace(" ", "_").replace("-", "_")
            if code in VALID_ACTIONS and code not in actions:
                actions.append(code)
    return actions[:6]  # limit to 6 actions max
