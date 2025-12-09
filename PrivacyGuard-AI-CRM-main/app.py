import json
import logging
import os
import random
import string
from datetime import datetime
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from workflow import run_workflow
from db import init_db, fetch_dashboard_stats, fetch_pipeline_counts, fetch_pipeline_leads, fetch_leads, fetch_interactions, fetch_forecast_revenue, log_interaction, update_lead
from telephony import initiate_outbound_call, normalize_webhook


load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    CORS(app)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    # Initialize DB on startup
    init_db()

    api_token = os.getenv("API_BEARER_TOKEN", "changeme")

    def _auth_ok(req) -> bool:
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return False
        provided = auth_header.split(" ", 1)[1].strip()
        return provided == api_token

    

    @app.route("/", methods=["GET"])  # serve UI
    def root() -> Tuple[str, int] | Any:
        try:
            return send_from_directory("static", "index.html")
        except Exception:
            return "UI not found", 404

    
    @app.route("/dashboard", methods=["GET"])  # serve dashboard UI
    def dashboard_page() -> Tuple[str, int] | Any:
        try:
            return send_from_directory("static", "dashboard_white.html")
        except Exception:
            return "Dashboard not found", 404

    @app.route("/contact", methods=["GET"])  # serve customer form
    def contact_page() -> Tuple[str, int] | Any:
        try:
            return send_from_directory("static", "customer_form.html")
        except Exception:
            return "Contact form not found", 404

    @app.route("/health", methods=["GET"])  # simple liveness
    def health() -> Tuple[str, int]:
        return "ok", 200

    # Voice: initiate outbound call
    @app.route("/voice/call", methods=["POST"])  # protected
    def voice_call():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = request.get_json(silent=True) or {}
        to_phone = data.get("to_phone")
        if not to_phone:
            return jsonify({"error": "to_phone is required"}), 400
        provider = os.getenv("VOICE_PROVIDER", "vapi")
        ok, info = initiate_outbound_call(provider, to_phone, payload=data.get("variables"))
        return jsonify({"provider": provider, "ok": ok, "info": info}), (200 if ok else 500)

    # Voice: webhook for status/transcripts
    @app.route("/voice/webhook/<provider>", methods=["POST"])  # no auth (providers call this); secure via secret if available
    def voice_webhook(provider: str):
        try:
            body = request.get_json(force=True, silent=False) or {}
        except Exception:
            body = {}
        event = normalize_webhook(provider, body)
        # Optionally map to a lead if phone is present
        lead_id = int((request.args.get("lead_id") or 0))
        log_interaction(lead_id, "VOICE_PROVIDER", "webhook_event", event.get("status") or "received", event)
        return "ok", 200

    # API: metrics and pipeline
    @app.route("/api/metrics", methods=["GET"])  # protected
    def api_metrics():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401
        stats = fetch_dashboard_stats()
        forecast = fetch_forecast_revenue()
        counts = fetch_pipeline_counts()
        return jsonify({"stats": stats, "pipeline_counts": counts, "forecast_revenue": forecast})

    @app.route("/api/kanban", methods=["GET"])  # protected
    def api_kanban():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = fetch_pipeline_leads()
        return jsonify(data)

    @app.route("/api/leads", methods=["GET"])  # protected
    def api_leads():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401
        limit = int(request.args.get("limit", 100))
        data = fetch_leads(limit=limit)
        return jsonify(data)

    @app.route("/api/interactions/<int:lead_id>", methods=["GET"])  # protected
    def api_interactions(lead_id: int):
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401
        data = fetch_interactions(lead_id, limit=int(request.args.get("limit", 100)))
        return jsonify(data)

    @app.route("/workflow/run", methods=["POST"])
    def workflow_run():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401

        try:
            payload = request.get_json(force=True, silent=False)
        except Exception:
            return jsonify({"error": "Invalid JSON"}), 400

        # Basic validation
        if not isinstance(payload, dict):
            return jsonify({"error": "Payload must be a JSON object"}), 400

        trigger = payload.get("trigger")
        lead_data = payload.get("lead_data", {})
        if trigger not in {"new_lead", "follow_up", "quotation_request", "deal_closing"}:
            return jsonify({"error": "Invalid trigger"}), 400

        required_fields = ["name", "phone", "email", "source", "interest", "budget_range"]
        missing = [f for f in required_fields if not lead_data.get(f)]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        # Create workflow id
        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        workflow_id = f"wf_{ts}_{rand}"

        try:
            result = run_workflow(workflow_id=workflow_id, trigger=trigger, lead_data=lead_data)
        except Exception as e:
            logging.exception("Workflow failed with unhandled exception")
            return (
                jsonify(
                    {
                        "workflow_id": workflow_id,
                        "status": "failed",
                        "error": str(e),
                    }
                ),
                500,
            )

        return jsonify(result), 200

    @app.route("/workflow/test", methods=["POST"])  # runs with sample data if no payload provided
    def workflow_test():
        if not _auth_ok(request):
            return jsonify({"error": "Unauthorized"}), 401

        payload = request.get_json(silent=True) or {}
        sample = {
            "trigger": "new_lead",
            "lead_data": {
                "name": "Rajesh Sharma",
                "phone": "+919876543210",
                "email": "rajesh@example.com",
                "source": "website_form",
                "interest": "Rolls-Royce Phantom",
                "budget_range": "8-10 crore",
            },
        }
        sample.update(payload)

        ts = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
        rand = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
        workflow_id = f"wf_{ts}_{rand}"

        try:
            result = run_workflow(workflow_id=workflow_id, trigger=sample["trigger"], lead_data=sample["lead_data"])
        except Exception as e:
            logging.exception("Workflow test failed")
            return jsonify({"workflow_id": workflow_id, "status": "failed", "error": str(e)}), 500

        return jsonify(result), 200

    @app.route("/api/leads/<int:lead_id>/stage", methods=["PUT"])  # update lead stage
    def update_lead_stage(lead_id: int):
        try:
            if not _auth_ok(request):
                return jsonify({"error": "Unauthorized"}), 401
            
            data = request.get_json()
            new_stage = data.get("stage")
            action = data.get("action", "")
            
            if not new_stage:
                return jsonify({"error": "Stage is required"}), 400
            
            # Update lead stage in database
            success = update_lead(lead_id, stage=new_stage)
            
            if success:
                # Log the stage change
                log_interaction(lead_id, "SALES_MANAGER", f"stage_update_{action}", "executed", {
                    "new_stage": new_stage,
                    "action": action,
                    "updated_by": "sales_manager"
                })
                
                return jsonify({
                    "success": True,
                    "lead_id": lead_id,
                    "new_stage": new_stage,
                    "action": action
                }), 200
            else:
                return jsonify({"error": "Failed to update lead stage"}), 500
                
        except Exception as e:
            logging.exception("Update lead stage failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/leads/<int:lead_id>/actions", methods=["POST"])  # sales manager actions
    def sales_manager_action(lead_id: int):
        try:
            if not _auth_ok(request):
                return jsonify({"error": "Unauthorized"}), 401
            
            data = request.get_json()
            action = data.get("action")
            notes = data.get("notes", "")
            
            if not action:
                return jsonify({"error": "Action is required"}), 400
            
            # Map actions to stages
            action_mapping = {
                "hold": "contacted",
                "qualify": "qualified", 
                "opportunity": "opportunity",
                "close_won": "closed_won",
                "close_lost": "closed_lost",
                "reopen": "qualified"
            }
            
            new_stage = action_mapping.get(action)
            if not new_stage:
                return jsonify({"error": "Invalid action"}), 400
            
            # Update lead stage
            success = update_lead(lead_id, stage=new_stage)
            
            if success:
                # Log the action
                log_interaction(lead_id, "SALES_MANAGER", f"action_{action}", "executed", {
                    "action": action,
                    "new_stage": new_stage,
                    "notes": notes,
                    "updated_by": "sales_manager"
                })
                
                return jsonify({
                    "success": True,
                    "lead_id": lead_id,
                    "action": action,
                    "new_stage": new_stage,
                    "notes": notes
                }), 200
            else:
                return jsonify({"error": "Failed to update lead"}), 500
                
        except Exception as e:
            logging.exception("Sales manager action failed")
            return jsonify({"error": str(e)}), 500

    @app.route("/generate-token", methods=["GET"])
    def generate_token():
        """Generate a short-lived token for secure operations."""
        token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
        return jsonify({"token": token}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.getenv("PORT", "5001"))
    app.run(host="0.0.0.0", port=port, debug=True)
