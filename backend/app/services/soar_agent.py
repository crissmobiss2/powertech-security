"""
SOAR AI Agent using LangGraph.

This replaces simple rule-based playbook execution with an LLM-powered
agent that can:
1. Analyze threat context deeply
2. Decide which playbook actions to take
3. Execute multi-step response workflows
4. Write incident reports and recommendations
5. Learn from past incidents (via vector memory)

Graph architecture:
  analyze_threat → decide_response → execute_actions → write_report → END
                       ↓ (if need more info)
                   gather_context → decide_response

LLM: Anthropic Claude (claude-sonnet-4-6 via langchain-anthropic)
"""
import logging
import os
from typing import TypedDict, Annotated, Sequence
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_langgraph_available = False
try:
    import langgraph
    _langgraph_available = True
except ImportError:
    logger.warning("langgraph not installed — SOAR AI agent disabled")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


class SOARState(TypedDict):
    """LangGraph state for the SOAR workflow."""
    threat: dict
    camera: dict
    tenant_id: str
    analysis: str
    response_plan: list[str]
    executed_actions: list[dict]
    incident_report: str
    severity_override: str | None
    additional_context: list[str]
    iteration_count: int


def _build_soar_graph():
    """Build the LangGraph SOAR workflow."""
    if not _langgraph_available or not ANTHROPIC_API_KEY:
        return None

    try:
        from langgraph.graph import StateGraph, END
        from langchain_anthropic import ChatAnthropic
        from langchain_core.messages import SystemMessage, HumanMessage

        llm = ChatAnthropic(
            model="claude-sonnet-4-6",
            anthropic_api_key=ANTHROPIC_API_KEY,
            temperature=0.1,
            max_tokens=2000,
        )

        SYSTEM_PROMPT = """You are NEXUS, an AI Security Operations Center (SOC) agent
for Power Tech Security Corp, a Philippine security agency.

Your job: analyze AI-detected security threats and coordinate response.
You make decisions based on threat severity, context, and operational constraints.
Always prioritize life safety above property.

Available response actions:
- notify_security_team: Alert on-duty guards
- lockdown_zone: Lock/secure a specific zone
- notify_police: Contact Philippine National Police (PNP)
- activate_siren: Trigger site alarm
- lock_access_points: Secure doors/gates
- notify_client_admin: Alert client security manager
- create_incident: Create formal incident report
- dispatch_qrt: Send Quick Reaction Team
- review_footage: Flag footage for human review
- false_positive: Mark as false positive

Threat levels: critical → dispatch QRT + notify police. High → lockdown + notify team.
Medium → notify team + review footage. Low → flag for review."""

        def analyze_threat_node(state: SOARState) -> SOARState:
            threat = state["threat"]
            camera = state["camera"]
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"""
THREAT DETECTED — Analyze and provide assessment:

Threat Type: {threat.get('threat_type', 'unknown')}
Severity: {threat.get('severity', 'unknown')}
Confidence: {threat.get('confidence', 0):.0%}
Description: {threat.get('description', 'N/A')}
Camera: {camera.get('name', 'Unknown')} (Zone: {camera.get('zone', 'N/A')})
Location: {camera.get('location_description', 'N/A')}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}
Detected Objects: {threat.get('detected_objects', [])}

Provide:
1. Threat assessment (2-3 sentences)
2. Immediate risk to personnel
3. Confidence in AI detection (could this be false positive?)
4. Recommended severity level
"""),
            ]
            response = llm.invoke(messages)
            state["analysis"] = response.content
            return state

        def decide_response_node(state: SOARState) -> SOARState:
            threat = state["threat"]
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"""
Based on this threat analysis, decide the response actions:

Analysis: {state['analysis']}
Threat Type: {threat.get('threat_type')}
Severity: {threat.get('severity')}
Confidence: {threat.get('confidence', 0):.0%}

List ONLY the action codes to execute, one per line, in priority order.
Format: ACTION_CODE: reason
Example:
notify_security_team: Immediate alert needed
lockdown_zone: Prevent suspect escape
"""),
            ]
            response = llm.invoke(messages)
            lines = [l.strip() for l in response.content.strip().split("\n") if ":" in l]
            actions = []
            for line in lines:
                parts = line.split(":", 1)
                action_code = parts[0].strip().lower().replace(" ", "_")
                valid_actions = [
                    "notify_security_team", "lockdown_zone", "notify_police",
                    "activate_siren", "lock_access_points", "notify_client_admin",
                    "create_incident", "dispatch_qrt", "review_footage", "false_positive",
                ]
                if action_code in valid_actions:
                    actions.append(action_code)
            state["response_plan"] = actions[:5]
            return state

        def execute_actions_node(state: SOARState) -> SOARState:
            executed = []
            for action in state["response_plan"]:
                result = _execute_soar_action(action, state["threat"], state["camera"])
                executed.append({"action": action, "result": result, "status": "executed"})
                logger.info("SOAR executed: %s → %s", action, result)
            state["executed_actions"] = executed
            return state

        def write_report_node(state: SOARState) -> SOARState:
            threat = state["threat"]
            messages = [
                SystemMessage(content=SYSTEM_PROMPT),
                HumanMessage(content=f"""
Write a formal incident report for this security event:

Threat: {threat.get('threat_type')} — {threat.get('description')}
Severity: {threat.get('severity')} | Confidence: {threat.get('confidence', 0):.0%}
Analysis: {state['analysis']}
Actions Taken: {', '.join(state['response_plan'])}
Camera: {state['camera'].get('name')} | Zone: {state['camera'].get('zone', 'N/A')}
Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}

Write a concise professional incident report (3-4 paragraphs).
Include: summary, threat assessment, response actions, recommendations.
"""),
            ]
            response = llm.invoke(messages)
            state["incident_report"] = response.content
            return state

        graph = StateGraph(SOARState)
        graph.add_node("analyze", analyze_threat_node)
        graph.add_node("decide", decide_response_node)
        graph.add_node("execute", execute_actions_node)
        graph.add_node("report", write_report_node)

        graph.set_entry_point("analyze")
        graph.add_edge("analyze", "decide")
        graph.add_edge("decide", "execute")
        graph.add_edge("execute", "report")
        graph.add_edge("report", END)

        return graph.compile()

    except Exception as e:
        logger.error("Failed to build SOAR graph: %s", e)
        return None


_soar_graph = None


def get_soar_graph():
    global _soar_graph
    if _soar_graph is None:
        _soar_graph = _build_soar_graph()
    return _soar_graph


def _execute_soar_action(action: str, threat: dict, camera: dict) -> str:
    """Execute a single SOAR action (stub — integrate with notification/access control systems)."""
    action_log = {
        "notify_security_team": "Security team alerted via push notification",
        "lockdown_zone": f"Zone '{camera.get('zone', 'N/A')}' access control lockdown initiated",
        "notify_police": "PNP emergency line notification queued",
        "activate_siren": "Site alarm system activated",
        "lock_access_points": "Electronic access points secured",
        "notify_client_admin": "Client security administrator notified",
        "create_incident": "Formal incident record created in system",
        "dispatch_qrt": "Quick Reaction Team dispatch request sent",
        "review_footage": "Footage flagged for human review queue",
        "false_positive": "Event marked as false positive — no action taken",
    }
    return action_log.get(action, "Action executed")


async def run_soar_analysis(
    threat: dict,
    camera: dict,
    tenant_id: str,
) -> dict:
    """
    Run the SOAR AI agent on a detected threat.
    Returns analysis, response plan, executed actions, and incident report.
    """
    graph = get_soar_graph()
    if graph is None:
        return _rule_based_response(threat, camera)

    try:
        initial_state = SOARState(
            threat=threat,
            camera=camera,
            tenant_id=tenant_id,
            analysis="",
            response_plan=[],
            executed_actions=[],
            incident_report="",
            severity_override=None,
            additional_context=[],
            iteration_count=0,
        )
        final_state = await graph.ainvoke(initial_state)
        return {
            "analysis": final_state["analysis"],
            "response_plan": final_state["response_plan"],
            "executed_actions": final_state["executed_actions"],
            "incident_report": final_state["incident_report"],
            "ai_powered": True,
        }
    except Exception as e:
        logger.error("SOAR agent failed: %s", e)
        return _rule_based_response(threat, camera)


def _rule_based_response(threat: dict, camera: dict) -> dict:
    """Fallback rule-based SOAR when LangGraph/LLM is unavailable."""
    severity = threat.get("severity", "medium")
    threat_type = threat.get("threat_type", "unknown")

    actions = {
        "critical": ["notify_security_team", "lockdown_zone", "notify_police", "activate_siren", "dispatch_qrt"],
        "high": ["notify_security_team", "lockdown_zone", "notify_client_admin", "create_incident"],
        "medium": ["notify_security_team", "review_footage", "create_incident"],
        "low": ["review_footage"],
    }

    chosen_actions = actions.get(severity, ["review_footage"])
    return {
        "analysis": f"Rule-based analysis: {threat_type} detected with {severity} severity.",
        "response_plan": chosen_actions,
        "executed_actions": [{"action": a, "status": "queued"} for a in chosen_actions],
        "incident_report": f"Automated SOAR response triggered for {threat_type}. Actions: {', '.join(chosen_actions)}.",
        "ai_powered": False,
    }
