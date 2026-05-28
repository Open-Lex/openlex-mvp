#!/usr/bin/env python3
"""
eval_pipeline.py — Orchestrator für autonomes Overnight-Eval aller OpenLex Skills.
Startet: gen_questions → retrieval_eval → llm_eval → report → ntfy

Usage:
  tmux new -s eval
  cd /opt/openlex-sources && python3 scripts/eval/eval_pipeline.py 2>&1 | tee logs/eval_$(date +%Y%m%d_%H%M).log
  
  # Einzelner Skill (Test):
  python3 scripts/eval/eval_pipeline.py --skill datenschutz
  
  # Nur Layer 1:
  python3 scripts/eval/eval_pipeline.py --layer 1
  
  # Ab bestimmtem Schritt (Restart):
  python3 scripts/eval/eval_pipeline.py --from-step llm_eval
"""
import argparse, json, logging, os, sys, time
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Pfade
BASE            = Path("/opt/openlex-sources")
SCRIPTS_EVAL    = BASE / "scripts" / "eval"
STATE_FILE      = BASE / "state" / "eval_state.json"
LOGS_DIR        = BASE / "logs"
NTFY_CHANNEL    = "openlex-p2-e52c117a"

# Eval-Module (nach sys.path-Setup importieren)
sys.path.insert(0, str(SCRIPTS_EVAL))

# === State Management ===

def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            pass
    return {}


def save_state(state: dict):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def mark_step(state: dict, step: str, status: str, **kwargs):
    state[step] = {"status": status, "ts": datetime.now().isoformat(), **kwargs}
    save_state(state)


# === ntfy ===

def ntfy_push(msg: str):
    try:
        requests.post(
            f"https://ntfy.sh/{NTFY_CHANNEL}",
            data=msg.encode("utf-8"),
            headers={"Title": "OpenLex Eval", "Priority": "default"},
            timeout=10,
        )
    except Exception as e:
        log.warning(f"ntfy fehlgeschlagen: {e}")


# === Pipeline Steps ===

def step_gen_questions(state: dict, skills: list[str] | None = None):
    step = "gen_questions"
    if state.get(step, {}).get("status") == "DONE":
        log.info(f"[{step}] bereits DONE, überspringe")
        return
    
    mark_step(state, step, "RUNNING")
    ntfy_push(f"🔍 Eval Step 1/4: Fragen generieren...")
    
    try:
        import eval_gen_questions
        results = eval_gen_questions.run(skills)
        total = sum(results.values())
        mark_step(state, step, "DONE", total_questions=total, skills=len(results))
        log.info(f"[{step}] DONE: {total} Fragen für {len(results)} Skills")
        ntfy_push(f"✅ Fragen generiert: {total} Fragen für {len(results)} Skills")
    except Exception as e:
        mark_step(state, step, "FAILED", error=str(e))
        log.error(f"[{step}] FAILED: {e}")
        ntfy_push(f"❌ {step} FAILED: {e}")
        raise


def step_retrieval_eval(state: dict, skills: list[str] | None = None):
    step = "retrieval_eval"
    if state.get(step, {}).get("status") == "DONE":
        log.info(f"[{step}] bereits DONE, überspringe")
        return
    
    mark_step(state, step, "RUNNING")
    ntfy_push(f"🔬 Eval Step 2/4: Layer-1 Retrieval-Diagnose...")
    
    try:
        import eval_retrieval
        result = eval_retrieval.run(skills)
        avg = result.get("avg_score", 0)
        mark_step(state, step, "DONE", avg_l1_score=avg, output=result.get("output_file"))
        log.info(f"[{step}] DONE: Ø L1={avg:.1f}%")
        ntfy_push(f"✅ Layer-1 fertig: Ø {avg:.1f}% über {len(result.get('results', []))} Skills")
    except Exception as e:
        mark_step(state, step, "FAILED", error=str(e))
        log.error(f"[{step}] FAILED: {e}")
        ntfy_push(f"❌ {step} FAILED: {e}")
        raise


def step_llm_eval(state: dict, skills: list[str] | None = None):
    step = "llm_eval"
    if state.get(step, {}).get("status") == "DONE":
        log.info(f"[{step}] bereits DONE, überspringe")
        return
    
    mark_step(state, step, "RUNNING")
    n_skills = len(skills) if skills else 50
    ntfy_push(f"🤖 Eval Step 3/4: Layer-2 LLM-Eval (~{n_skills} Skills, ~6h)...")
    
    try:
        import eval_llm
        result = eval_llm.run(skills, ntfy_fn=ntfy_push)
        avg = result.get("avg_score", 0)
        mark_step(state, step, "DONE", avg_l2_score=avg, output=result.get("output_file"))
        log.info(f"[{step}] DONE: Ø L2={avg:.1f}")
        ntfy_push(f"✅ Layer-2 fertig: Ø {avg:.1f}/100")
    except Exception as e:
        mark_step(state, step, "FAILED", error=str(e))
        log.error(f"[{step}] FAILED: {e}")
        ntfy_push(f"❌ {step} FAILED: {e}")
        raise


def step_report(state: dict):
    step = "report"
    if state.get(step, {}).get("status") == "DONE":
        log.info(f"[{step}] bereits DONE, überspringe")
        return
    
    mark_step(state, step, "RUNNING")
    
    try:
        import eval_report
        out_file = eval_report.run()
        mark_step(state, step, "DONE", report_file=str(out_file))
        log.info(f"[{step}] DONE: {out_file}")
        
        # Lese erste Zeilen des Reports für ntfy
        preview = out_file.read_text()[:500]
        ntfy_push(f"📊 Eval abgeschlossen! Report: {out_file.name}\n\n{preview}")
    except Exception as e:
        mark_step(state, step, "FAILED", error=str(e))
        log.error(f"[{step}] FAILED: {e}")
        ntfy_push(f"❌ {step} FAILED: {e}")
        raise


# === Main ===

def main():
    parser = argparse.ArgumentParser(description="OpenLex Eval Pipeline")
    parser.add_argument("--skill", help="Nur diesen Skill testen")
    parser.add_argument("--layer", choices=["1", "2"], help="Nur Layer 1 oder 2")
    parser.add_argument("--from-step", choices=["gen_questions", "retrieval_eval", "llm_eval", "report"],
                        help="Ab diesem Schritt beginnen (State zurücksetzen)")
    parser.add_argument("--reset", action="store_true", help="State komplett zurücksetzen")
    args = parser.parse_args()
    
    skills = [args.skill] if args.skill else None
    
    state = load_state()
    
    if args.reset:
        state = {}
        save_state(state)
        log.info("State zurückgesetzt")
    
    if args.from_step:
        # Setze diesen und alle nachfolgenden Schritte zurück
        step_order = ["gen_questions", "retrieval_eval", "llm_eval", "report"]
        idx = step_order.index(args.from_step)
        for step in step_order[idx:]:
            state.pop(step, None)
        save_state(state)
        log.info(f"State ab {args.from_step} zurückgesetzt")
    
    log.info("=" * 60)
    log.info("OpenLex Eval Pipeline startet")
    log.info(f"Skills: {'alle' if not skills else skills}")
    log.info(f"Layer: {args.layer or '1+2'}")
    log.info("=" * 60)
    
    t0 = time.time()
    ntfy_push(f"🚀 OpenLex Eval Pipeline gestartet | Skills: {'alle (~50)' if not skills else skills} | Layer: {args.layer or '1+2'}")
    
    try:
        if args.layer != "2":
            step_gen_questions(state, skills)
            step_retrieval_eval(state, skills)
        
        if args.layer != "1":
            step_llm_eval(state, skills)
        
        step_report(state)
        
        duration = round((time.time() - t0) / 3600, 1)
        log.info(f"Pipeline abgeschlossen in {duration}h")
        mark_step(state, "pipeline_complete", "DONE", duration_h=duration)
        ntfy_push(f"🏁 Pipeline fertig in {duration}h! Alle Steps DONE.")
        
    except KeyboardInterrupt:
        log.info("Pipeline manuell abgebrochen (Ctrl+C)")
        ntfy_push("⚠️ Eval Pipeline manuell abgebrochen")
        sys.exit(1)
    except Exception as e:
        log.error(f"Pipeline FAILED: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
