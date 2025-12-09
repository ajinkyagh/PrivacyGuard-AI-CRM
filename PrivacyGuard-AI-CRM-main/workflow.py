import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from langgraph.graph import StateGraph, END

from db import insert_lead, update_lead, log_interaction, schedule_action, fetch_dashboard_stats
from llm import score_lead_llm, generate_welcome_email, suggest_followup_actions
from email_util import send_email
from email_templates import get_document_email_template, get_welcome_email_template, get_followup_email_template
from utils import now_ist_iso, schedule_in_hours_ist
from pdfs import generate_quotation_pdf, generate_invoice_pdf, generate_contract_pdf
from telephony import initiate_outbound_call
import os

try:
    from langchain_core.runnables.config import RunnableConfig  # type: ignore
except Exception:  # pragma: no cover
    class RunnableConfig(dict):  # type: ignore
        pass


@dataclass
class WorkflowState:
    lead_data: Dict[str, Any]
    lead_score: int | None = None
    classification: str | None = None
    scheduled_actions: List[Dict[str, Any]] = field(default_factory=list)
    email_status: Dict[str, Any] | None = None
    document_status: Dict[str, Any] | None = None
    executed_agents: List[Dict[str, Any]] = field(default_factory=list)
    lead_id: int | None = None
    lead_stage: str | None = None
    estimated_conversion_probability: float | None = None


AGENT_NAMES = {
    "lead_intelligence": "LEAD_INTELLIGENCE_AGENT",
    "voice": "VOICE_AGENT",
    "email": "EMAIL_ORCHESTRATION_AGENT",
    "document": "DOCUMENT_GENERATION_AGENT",
    "analytics": "CRM_ANALYTICS_AGENT",
    "automation": "WORKFLOW_AUTOMATION_AGENT",
}


def _add_execution(state: WorkflowState, agent_key: str, action: str, status: str, details: Dict[str, Any]) -> None:
    state.executed_agents.append(
        {
            "agent": AGENT_NAMES[agent_key],
            "action": action,
            "status": status,
            "timestamp": now_ist_iso(),
            "details": details,
        }
    )


def agent_lead_intelligence(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        lead = state.lead_data
        score = score_lead_llm(lead.get("budget_range", ""), lead.get("interest", ""), lead.get("source", ""))
        classification = "cold_lead"
        if score >= 75:
            classification = "hot_lead"
        elif score >= 50:
            classification = "warm_prospect"

        lead_id = insert_lead(workflow_id, lead, score, classification)

        if lead.get("existing_customer") is True:
            classification = "vip_client"
            update_lead(lead_id, classification=classification)

        state.lead_score = score
        state.classification = classification
        state.lead_id = lead_id
        state.lead_stage = "new"

        log_interaction(lead_id, AGENT_NAMES["lead_intelligence"], "capture_and_score", "executed", {"score": score, "classification": classification})
        _add_execution(state, "lead_intelligence", "capture_and_score", "executed", {"score": score, "classification": classification})
    except Exception as e:
        logging.exception("Lead intelligence failed")
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["lead_intelligence"], "capture_and_score", "failed", {"error": str(e)})
        _add_execution(state, "lead_intelligence", "capture_and_score", "failed", {"error": str(e)})
    return state


def agent_voice(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        lead_id = state.lead_id or 0
        hours = 24
        if state.classification == "hot_lead":
            hours = 4
        when = schedule_in_hours_ist(hours)
        schedule_action(lead_id, "qualification_call", when, status="pending")
        update_lead(lead_id, stage="contacted")
        state.lead_stage = "contacted"
        detail = {"scheduled_time": when}

        # Real call initiation if provider configured
        provider = os.getenv("VOICE_PROVIDER")
        if provider:
            ok, info = initiate_outbound_call(provider, state.lead_data.get("phone", ""), payload={
                "lead_name": state.lead_data.get("name"),
                "lead_interest": state.lead_data.get("interest"),
                "workflow_id": workflow_id,
                "lead_id": lead_id,
            })
            detail.update({"call_initiated": ok, "call_info": info, "provider": provider})

        log_interaction(lead_id, AGENT_NAMES["voice"], "schedule_and_call", "scheduled", detail)
        _add_execution(state, "voice", "schedule_and_call", "scheduled", detail)
    except Exception as e:
        logging.exception("Voice agent failed")
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["voice"], "schedule_and_call", "failed", {"error": str(e)})
        _add_execution(state, "voice", "schedule_and_call", "failed", {"error": str(e)})
    return state


def agent_email(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        template = "standard_welcome"
        if state.classification == "vip_client":
            template = "luxury_welcome_vip"
        elif state.classification == "hot_lead":
            template = "premium_welcome_hot"
        elif state.classification == "warm_prospect":
            template = "standard_welcome"

        # Use professional welcome email template
        customer_name = state.lead_data.get("name", "Valued Customer")
        vehicle_interest = state.lead_data.get("interest", "")
        email_template = get_welcome_email_template(customer_name, vehicle_interest)
        
        ok, info = send_email(state.lead_data.get("email", ""), email_template["subject"], email_template["body"])
        email_status = {"template": template, "sent": ok, **info}
        state.email_status = email_status
        log_interaction(state.lead_id or 0, AGENT_NAMES["email"], "send_welcome_email", "executed" if ok else "failed", email_status)
        _add_execution(state, "email", "send_welcome_email", "executed" if ok else "failed", email_status)
    except Exception as e:
        logging.exception("Email orchestration failed")
        state.email_status = {"sent": False, "error": str(e)}
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["email"], "send_welcome_email", "failed", {"error": str(e)})
        _add_execution(state, "email", "send_welcome_email", "failed", {"error": str(e)})
    return state


def agent_document(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        lead = state.lead_data
        classification = state.classification or "cold_lead"

        # Determine what to generate
        to_generate: List[str] = []
        if classification == "hot_lead":
            to_generate = ["quotation", "contract"]
        elif classification == "warm_prospect":
            to_generate = ["brochure"]  # brochure not a PDF here; we still send a quotation-like summary
        elif classification == "vip_client":
            to_generate = ["quotation", "contract"]

        attachments = []
        details: Dict[str, Any] = {"generated": []}

        if "quotation" in to_generate:
            qpdf = generate_quotation_pdf(lead, {"base_price": 100000000.0, "items": [{"name": lead.get("interest", "Vehicle"), "price": 100000000.0}]})
            attachments.append({"filename": "quotation.pdf", "content": qpdf, "mime": "application/pdf"})
            details["generated"].append("quotation.pdf")

        if "contract" in to_generate:
            cpdf = generate_contract_pdf(lead, {"delivery_location": "Mumbai Showroom", "payment_terms": "50% booking, 50% on delivery", "customizations": ["bespoke_interior", "two_tone_paint"]})
            attachments.append({"filename": "contract.pdf", "content": cpdf, "mime": "application/pdf"})
            details["generated"].append("contract.pdf")

        # Invoice generation removed - hot leads now get quotation + contract instead

        if attachments:
            # Determine document types for professional email template
            document_types = []
            if "quotation.pdf" in details["generated"]:
                document_types.append("quotation")
            if "invoice.pdf" in details["generated"]:
                document_types.append("invoice")
            if "contract.pdf" in details["generated"]:
                document_types.append("contract")
            
            # Generate professional email template
            customer_name = lead.get("name", "Valued Customer")
            vehicle_info = lead.get("interest", "")
            email_template = get_document_email_template(customer_name, document_types, vehicle_info)
            
            # Send professional email with attachments (HTML + plain text)
            html_body = email_template.get("html_body")
            ok, info = send_email(
                lead.get("email", ""), 
                email_template["subject"], 
                email_template["body"], 
                attachments=attachments,
                html_body=html_body
            )
            details["email_sent"] = ok
            details["email_template"] = "professional_document_email"
            details["document_types"] = document_types
            details.update(info)
            status = "executed" if ok else "failed"
        else:
            # If nothing generated, mark pending and schedule later
            eta = schedule_in_hours_ist(6)
            schedule_action(state.lead_id or 0, "document_generation", eta, status="pending")
            details["eta"] = eta
            status = "pending"

        state.document_status = {"status": status, **details}
        log_interaction(state.lead_id or 0, AGENT_NAMES["document"], "generate_documents", status, state.document_status)
        _add_execution(state, "document", "generate_documents", status, state.document_status)
    except Exception as e:
        logging.exception("Document generation failed")
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["document"], "generate_documents", "failed", {"error": str(e)})
        _add_execution(state, "document", "generate_documents", "failed", {"error": str(e)})
    return state


def agent_analytics(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        next_stage = "qualified"
        if state.classification == "hot_lead":
            next_stage = "opportunity"
        update_lead(state.lead_id or 0, stage=next_stage)
        state.lead_stage = next_stage
        stats = fetch_dashboard_stats()
        hot_ratio = (stats.get("hot_leads", 0) / stats.get("total_leads", 1)) if stats.get("total_leads", 0) else 0
        base = 0.2 + 0.5 * hot_ratio
        score_term = (state.lead_score or 0) / 200.0
        prob = min(0.95, max(0.05, base + score_term))
        state.estimated_conversion_probability = prob
        log_interaction(state.lead_id or 0, AGENT_NAMES["analytics"], "update_metrics", "executed", {"lead_stage": next_stage, "probability": prob, "dashboard": stats})
        _add_execution(state, "analytics", "update_metrics", "executed", {"lead_stage": next_stage, "probability": prob})
    except Exception as e:
        logging.exception("Analytics agent failed")
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["analytics"], "update_metrics", "failed", {"error": str(e)})
        _add_execution(state, "analytics", "update_metrics", "failed", {"error": str(e)})
    return state


def agent_automation(workflow_id: str, state: WorkflowState) -> WorkflowState:
    try:
        classification = state.classification or "cold_lead"
        default_actions = {
            "hot_lead": ["qualification_call_in_4h", "quotation_generation_after_call", "followup_email_in_1_day"],
            "warm_prospect": ["qualification_call_in_24h", "brochure_email_in_2_days", "followup_email_in_3_days"],
            "cold_lead": ["nurture_email_sequence_weekly"],
            "vip_client": ["vip_concierge_outreach_in_4h", "private_viewing_invite_in_2_days", "bespoke_configuration_session_in_3_days"],
        }
        actions = default_actions.get(classification, default_actions["cold_lead"])
        schedules: List[Tuple[str, int]] = []
        for a in actions:
            if "4h" in a:
                schedules.append((a, 4))
            elif "1_day" in a:
                schedules.append((a, 24))
            elif "2_days" in a:
                schedules.append((a, 48))
            elif "3_days" in a:
                schedules.append((a, 72))
            else:
                schedules.append((a, 168))

        scheduled = []
        for name, hours in schedules:
            when = schedule_in_hours_ist(hours)
            schedule_action(state.lead_id or 0, name, when, status="pending")
            scheduled.append({"action": name, "scheduled_time": when})
        state.scheduled_actions = scheduled
        log_interaction(state.lead_id or 0, AGENT_NAMES["automation"], "schedule_followups", "scheduled", {"actions": scheduled})
        _add_execution(state, "automation", "schedule_followups", "scheduled", {"actions": scheduled})
    except Exception as e:
        logging.exception("Automation agent failed")
        if state.lead_id:
            log_interaction(state.lead_id, AGENT_NAMES["automation"], "schedule_followups", "failed", {"error": str(e)})
        _add_execution(state, "automation", "schedule_followups", "failed", {"error": str(e)})
    return state


def _build_graph() -> StateGraph:
    graph: StateGraph = StateGraph(WorkflowState)

    def wrap(node_fn):
        def _run(state: WorkflowState, *, config: RunnableConfig | None = None):
            workflow_id = (config or {}).get("workflow_id", "")
            return node_fn(workflow_id, state)
        return _run

    graph.add_node("lead_intelligence", wrap(agent_lead_intelligence))
    graph.add_node("voice", wrap(agent_voice))
    graph.add_node("email", wrap(agent_email))
    graph.add_node("document", wrap(agent_document))
    graph.add_node("analytics", wrap(agent_analytics))
    graph.add_node("automation", wrap(agent_automation))

    graph.set_entry_point("lead_intelligence")
    graph.add_edge("lead_intelligence", "voice")
    graph.add_edge("voice", "email")
    graph.add_edge("email", "document")
    graph.add_edge("document", "analytics")
    graph.add_edge("analytics", "automation")
    graph.add_edge("automation", END)

    return graph


_graph = _build_graph()


def run_workflow(workflow_id: str, trigger: str, lead_data: Dict[str, Any]) -> Dict[str, Any]:
    state = WorkflowState(lead_data=lead_data)

    failures = 0
    try:
        # Use the correct method for LangGraph StateGraph
        result_state: WorkflowState = _graph.invoke(state)
    except Exception:
        logging.exception("LangGraph invoke failed, falling back to direct calls")
        for fn in [agent_lead_intelligence, agent_voice, agent_email, agent_document, agent_analytics, agent_automation]:
            before = len(state.executed_agents)
            state = fn(workflow_id, state)
            after = len(state.executed_agents)
            if after == before or state.executed_agents[-1]["status"] == "failed":
                failures += 1
        result_state = state

    for ex in result_state.executed_agents:
        if ex.get("status") == "failed":
            failures += 1

    status = "completed" if failures < 3 else "failed"
    if failures and status != "failed":
        status = "in_progress"

    response = {
        "workflow_id": workflow_id,
        "status": status,
        "executed_agents": result_state.executed_agents,
        "lead_stage": result_state.lead_stage,
        "lead_score": result_state.lead_score,
        "classification": result_state.classification,
        "next_actions": [a.get("action") for a in (result_state.scheduled_actions or [])],
        "estimated_conversion_probability": result_state.estimated_conversion_probability or 0.0,
    }
    return response
