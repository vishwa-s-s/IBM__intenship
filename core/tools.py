import os
import json
from typing import Dict, Any, List
from core import memory, tts

def generate_study_summary_audio(text: str, voice_id: str = "21m00Tcm4TlvDq8ikWAM") -> Dict[str, Any]:
    try:
        audio_bytes = tts.generate_audio(text[:1000], voice_id)
        return {
            "status": "success",
            "audio_bytes": audio_bytes
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

def export_learning_plan_markdown(plan_data: Dict[str, Any]) -> str:
    md = f"# {plan_data.get('title', 'Learning Plan')}\n\n"
    md += f"**Overview**: {plan_data.get('overview', '')}\n"
    md += f"**Target Duration**: {plan_data.get('total_duration', '')}\n\n"
    
    for mod in plan_data.get("modules", []):
        md += f"## Module {mod.get('module_index', '')}: {mod.get('title', '')}\n"
        md += f"*Timeframe*: {mod.get('timeframe', '')}\n\n"
        md += "### Objectives:\n"
        for obj in mod.get("objectives", []):
            md += f"- {obj}\n"
        md += "\n### Key Topics:\n"
        for top in mod.get("topics", []):
            md += f"- {top}\n"
        md += "\n### Practice Tasks:\n"
        for task in mod.get("practice_tasks", []):
            md += f"- [ ] {task}\n"
        md += "\n---\n\n"
        
    if plan_data.get("study_tips"):
        md += "## Study Tips & Pacing\n"
        for tip in plan_data["study_tips"]:
            md += f"- {tip}\n"
            
    return md
