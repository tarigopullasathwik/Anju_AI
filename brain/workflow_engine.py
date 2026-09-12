"""
Anju AI — Workflow Engine
Multi-step task planning, autonomous workflow execution, and progress tracking.
Allows Anju to break complex commands into sequential steps and execute them.
"""
import os
import json
import time
import threading
import re
from datetime import datetime
from typing import Optional, Callable

# ── Workflow State ──────────────────────────────────────────────────────────
_workflows = {}          # workflow_id -> Workflow
_workflow_lock = threading.Lock()
_next_id = 0

WORKFLOWS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory", "workflows.json")


class WorkflowStep:
    """A single step in a multi-step workflow."""
    def __init__(self, action: str, params: dict, description: str = ""):
        self.action = action
        self.params = params
        self.description = description
        self.status = "pending"  # pending | running | completed | failed | skipped
        self.result = None
        self.error = None
        self.started_at = None
        self.completed_at = None
        self.dependencies = []  # List of step indices this step depends on


class Workflow:
    """A multi-step workflow with dependency tracking and autonomous execution."""

    def __init__(self, name: str, steps: list[WorkflowStep] = None):
        global _next_id
        with _workflow_lock:
            _next_id += 1
            self.id = f"wf_{_next_id}_{int(time.time())}"

        self.name = name
        self.steps = steps or []
        self.status = "created"  # created | running | paused | completed | failed
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.completed_at = None
        self.current_step = 0
        self.owner = "Sathwik"
        self._on_step_complete = None
        self._on_complete = None
        self._on_error = None
        self._thread = None

    def add_step(self, action: str, params: dict, description: str = "", depends_on: list = None) -> int:
        """Add a step to the workflow. Returns the step index."""
        step = WorkflowStep(action, params, description)
        if depends_on:
            step.dependencies = depends_on
        self.steps.append(step)
        return len(self.steps) - 1

    def set_callbacks(self, on_step=None, on_complete=None, on_error=None):
        """Set callbacks for workflow events."""
        self._on_step_complete = on_step
        self._on_complete = on_complete
        self._on_error = on_error

    def to_dict(self) -> dict:
        """Serialize workflow to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "current_step": self.current_step,
            "owner": self.owner,
            "steps": [
                {
                    "action": s.action,
                    "params": s.params,
                    "description": s.description,
                    "status": s.status,
                    "result": str(s.result)[:200] if s.result else None,
                    "error": s.error,
                    "dependencies": s.dependencies,
                }
                for s in self.steps
            ]
        }


def execute_step(action: str, params: dict) -> str:
    """Execute a single workflow step by routing to the appropriate handler."""
    action_map = {
        "open_app": lambda: _import_and_call("automation.app_control", "open_application", params.get("app_name", "")),
        "web_search": lambda: _import_and_call("tools.web_search", "search_web", params.get("query", "")),
        "generate_pdf": lambda: _import_and_call("tools.pdf_generator", "generate_pdf", params.get("title", "Doc"), params.get("content", ""), params.get("filename", "output.pdf")),
        "generate_image": lambda: _import_and_call("tools.image_generator", "generate_image", params.get("prompt", "")),
        "remember": lambda: _import_and_call("memory.memory", "remember_fact", params.get("content", "")),
        "take_picture": lambda: _import_and_call("tools.camera", "take_picture", params.get("filename", "capture.jpg")),
        "execute_code": lambda: _import_and_call("tools.code_execution", "execute_python_code", params.get("python_code", "")),
        "write_file": lambda: _import_and_call("tools.file_ops", "write_file", params.get("filepath", ""), params.get("content", "")),
        "read_file": lambda: _import_and_call("tools.file_ops", "read_file", params.get("filepath", "")),
        "send_sms": lambda: _import_and_call("tools.phone_control", "send_sms", params.get("number", ""), params.get("message", "")),
        "open_phone_app": lambda: _import_and_call("tools.phone_control", "open_app", params.get("app_name", "")),
        "phone_screenshot": lambda: _import_and_call("tools.phone_control", "take_screenshot"),
        "phone_battery": lambda: _import_and_call("tools.phone_control", "get_battery"),
        "chat": lambda: params.get("response", "Step completed."),
    }

    handler = action_map.get(action)
    if handler:
        try:
            result = handler()
            return str(result)
        except Exception as e:
            return f"Error in step '{action}': {e}"
    return f"No handler for action: {action}"


def _import_and_call(module_path: str, func_name: str, *args, **kwargs):
    """Dynamically import a module and call a function."""
    import importlib
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func(*args, **kwargs)


def _save_workflows():
    """Persist all active workflows to disk."""
    try:
        with _workflow_lock:
            data = {wid: wf.to_dict() for wid, wf in _workflows.items()}
        os.makedirs(os.path.dirname(WORKFLOWS_FILE), exist_ok=True)
        with open(WORKFLOWS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Workflow] Save error: {e}")


def _load_workflows():
    """Load persisted workflows from disk."""
    global _workflows
    try:
        if os.path.exists(WORKFLOWS_FILE):
            with open(WORKFLOWS_FILE, "r") as f:
                data = json.load(f)
            # We just track IDs, execution state is rebuilt on demand
            for wid in data:
                _workflows[wid] = data[wid]
    except Exception as e:
        print(f"[Workflow] Load error: {e}")


# ══════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════

def create_workflow(name: str, steps: list[dict] = None) -> Workflow:
    """
    Create a new workflow from a list of step dicts.

    Each step dict: {"action": "...", "params": {...}, "description": "...", "depends_on": [indices]}
    """
    workflow = Workflow(name)

    if steps:
        for i, step_data in enumerate(steps):
            workflow.add_step(
                action=step_data.get("action", "chat"),
                params=step_data.get("params", {}),
                description=step_data.get("description", ""),
                depends_on=step_data.get("depends_on"),
            )

    with _workflow_lock:
        _workflows[workflow.id] = workflow

    _save_workflows()
    return workflow


def get_workflow(workflow_id: str) -> Optional[Workflow]:
    """Get a workflow by ID."""
    with _workflow_lock:
        return _workflows.get(workflow_id)


def list_workflows(status: str = None) -> list[dict]:
    """List all workflows, optionally filtered by status."""
    with _workflow_lock:
        wfs = []
        for wf in _workflows.values():
            if status is None or wf.status == status:
                wfs.append(wf.to_dict())
        return sorted(wfs, key=lambda x: x["created_at"], reverse=True)


def run_workflow(workflow_id: str, background: bool = True) -> str:
    """
    Execute a workflow. If background=True, runs in a separate thread.
    Returns status messages as execution progresses.
    """
    workflow = get_workflow(workflow_id)
    if not workflow:
        return f"Workflow '{workflow_id}' not found."

    if workflow.status == "running":
        return f"Workflow '{workflow.name}' is already running."

    workflow.status = "running"
    workflow.current_step = 0
    _save_workflows()

    if background:
        thread = threading.Thread(target=_execute_workflow, args=(workflow_id,), daemon=True)
        thread.start()
        return f"🚀 Workflow '{workflow.name}' started in background with {len(workflow.steps)} steps."
    else:
        return _execute_workflow(workflow_id)


def _execute_workflow(workflow_id: str) -> str:
    """Internal: execute all steps of a workflow in order with dependency resolution."""
    workflow = get_workflow(workflow_id)
    if not workflow:
        return "Workflow not found."

    from brain.brain import dashboard_instance

    total = len(workflow.steps)
    results = []

    for i, step in enumerate(workflow.steps):
        if workflow.status == "paused":
            results.append(f"⏸️ Workflow paused at step {i+1}/{total}.")
            break

        # Check dependencies
        deps_met = all(
            workflow.steps[d].status == "completed" for d in step.dependencies
        )
        if not deps_met:
            step.status = "skipped"
            results.append(f"⏭️ Step {i+1} skipped (dependencies not met): {step.description or step.action}")
            continue

        # Execute step
        step.status = "running"
        step.started_at = datetime.now()
        workflow.current_step = i

        # Notify dashboard
        if dashboard_instance:
            status_msg = f"⚙️ Step {i+1}/{total}: {step.description or step.action}..."
            dashboard_instance.add_message("Anju", f"_{status_msg}_", speak_flag=False)

        try:
            step.result = execute_step(step.action, step.params)
            step.status = "completed"
            step.completed_at = datetime.now()
            results.append(f"✅ Step {i+1}/{total} '{step.description or step.action}': Completed.")

            if dashboard_instance:
                dashboard_instance.add_message("Anju",
                    f"✅ **Step {i+1}/{total}** — {step.description or step.action}: Done.",
                    speak_flag=False)

        except Exception as e:
            step.status = "failed"
            step.error = str(e)
            results.append(f"❌ Step {i+1}/{total} '{step.action}' failed: {e}")

            if workflow._on_error:
                workflow._on_error(workflow, i, e)

            # If critical failure, stop the workflow
            if not step.params.get("continue_on_error", False):
                workflow.status = "failed"
                break

        # Small delay between steps for safety
        time.sleep(0.3)

    # Mark completion
    if workflow.status == "running":
        workflow.status = "completed"
    workflow.completed_at = datetime.now()
    workflow.updated_at = datetime.now()
    _save_workflows()

    final = f"📋 Workflow '{workflow.name}' completed. {sum(1 for s in workflow.steps if s.status == 'completed')}/{total} steps successful."
    results.append(final)

    if dashboard_instance:
        dashboard_instance.add_message("Anju", final, speak_flag=False)

    return "\n".join(results)


def pause_workflow(workflow_id: str) -> str:
    """Pause a running workflow."""
    workflow = get_workflow(workflow_id)
    if not workflow:
        return "Workflow not found."
    if workflow.status != "running":
        return f"Workflow '{workflow.name}' is not running."
    workflow.status = "paused"
    _save_workflows()
    return f"⏸️ Workflow '{workflow.name}' paused at step {workflow.current_step + 1}."


def cancel_workflow(workflow_id: str) -> str:
    """Cancel a workflow entirely."""
    workflow = get_workflow(workflow_id)
    if not workflow:
        return "Workflow not found."
    workflow.status = "failed"
    workflow.completed_at = datetime.now()
    _save_workflows()
    return f"🛑 Workflow '{workflow.name}' cancelled."


def plan_multi_step(command: str) -> list[dict]:
    """
    Parse a complex user command into multi-step workflow steps.
    Uses the task planner's LLM to break down the command.
    """
    from brain.task_planner import plan_task
    plans = plan_task(command)

    # If plans returns multiple items, it's already multi-step
    if len(plans) > 1:
        return plans

    # Try to detect compound commands locally
    steps = []

    # Split by "and then", "then", "after that", "also"
    parts = re.split(r'\b(?:and then|then|after that|followed by|next|also)\b', command, flags=re.IGNORECASE)
    if len(parts) > 1:
        for part in parts:
            part = part.strip()
            if part:
                sub_plans = plan_task(part)
                steps.extend(sub_plans)
    else:
        steps = plans

    return steps if steps else [{"action": "chat", "params": {}}]


def run_autonomous(command: str) -> str:
    """
    High-level: take a natural language command, plan it as a multi-step workflow,
    and execute it autonomously. Returns a summary.
    """
    # 1. Plan the tasks
    steps = plan_multi_step(command)

    if len(steps) == 0:
        return "I couldn't break that down into steps, Sathwik."

    if len(steps) == 1 and steps[0]["action"] == "chat":
        return "That seems like a simple conversation. Nothing to automate."

    # 2. Create workflow
    wf_steps = []
    for s in steps:
        wf_steps.append({
            "action": s.get("action", "chat"),
            "params": s.get("params", {}),
            "description": f"{s.get('action', 'task')}: {str(s.get('params', {}))[:60]}",
        })

    workflow = create_workflow(f"Auto: {command[:50]}...", wf_steps)

    # 3. Run in background
    result = run_workflow(workflow.id, background=True)

    return result


def get_workflow_summary() -> str:
    """Get a summary of all workflows for status reporting."""
    active = list_workflows("running")
    completed = list_workflows("completed")
    failed = list_workflows("failed")

    lines = ["📋 **Workflow Engine Status**", ""]
    lines.append(f"• **Active:** {len(active)} workflow(s)")
    lines.append(f"• **Completed:** {len(completed)} workflow(s)")
    lines.append(f"• **Failed:** {len(failed)} workflow(s)")

    if active:
        lines.append("")
        lines.append("**Currently Running:**")
        for w in active[:3]:
            steps_done = sum(1 for s in w.get("steps", []) if s["status"] in ["completed", "running"])
            total = len(w.get("steps", []))
            lines.append(f"  🔄 {w['name'][:40]}... ({steps_done}/{total} steps)")

    return "\n".join(lines)


# Load existing workflows on import
_load_workflows()
