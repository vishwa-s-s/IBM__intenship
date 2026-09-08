import os
import json
from typing import Dict, Any, List
from google import genai
from dotenv import load_dotenv
from core import memory

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def generate_learning_plan(goal: str, target_date: str = "4 Weeks", daily_time: str = "1 Hour / Day", level: str = "Beginner") -> Dict[str, Any]:
    # Check existing documents for context grounding if available
    docs = memory.get_all_documents()
    doc_titles = [d["title"] for d in docs]
    doc_context = f"Available uploaded materials: {', '.join(doc_titles)}" if doc_titles else "No external files uploaded."

    prompt = f"""
You are an elite educational strategist and tutor. Build a personalized, step-by-step Learning Plan for a student.

Student Goal: {goal}
Timeline / Target Date: {target_date}
Daily Commitment: {daily_time}
Student Current Level: {level}
Context: {doc_context}

Output MUST be valid strict JSON only, without any markdown enclosing or additional text.
JSON Structure:
{{
  "title": "Comprehensive Study Plan: <Goal>",
  "overview": "Brief description of strategy, pacing, and learning philosophy.",
  "total_duration": "{target_date}",
  "modules": [
    {{
      "module_index": 1,
      "title": "Module 1: Foundations",
      "timeframe": "Week 1",
      "objectives": ["Objective 1", "Objective 2"],
      "topics": ["Topic 1", "Topic 2", "Topic 3"],
      "practice_tasks": ["Practice task 1", "Practice task 2"]
    }}
  ],
  "study_tips": ["Tip 1", "Tip 2"]
}}
"""

    if not client:
        # Fallback structured response if client is offline
        fallback_plan = {
            "title": f"Study Plan for {goal}",
            "overview": "A step-by-step roadmap to achieve your study goal.",
            "total_duration": target_date,
            "modules": [
                {
                    "module_index": 1,
                    "title": "Module 1: Core Fundamentals",
                    "timeframe": "Phase 1",
                    "objectives": ["Understand core terms and concepts"],
                    "topics": ["Introduction", "Key Principles"],
                    "practice_tasks": ["Complete initial review quiz"]
                }
            ],
            "study_tips": ["Consistency over intensity", "Active recall after each module"]
        }
        plan_id = memory.save_learning_plan(goal, target_date, daily_time, fallback_plan)
        fallback_plan["id"] = plan_id
        return fallback_plan

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        raw_text = response.text.strip()
        
        # Clean JSON markdown delimiters if present
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        plan_data = json.loads(raw_text)
        plan_id = memory.save_learning_plan(goal, target_date, daily_time, plan_data)
        plan_data["id"] = plan_id
        return plan_data
    except Exception as e:
        print(f"Error generating learning plan: {str(e)}")
        # Fallback plan creation
        fallback_plan = {
            "title": f"Study Plan: {goal}",
            "overview": f"Tailored plan for learning {goal}.",
            "total_duration": target_date,
            "modules": [
                {
                    "module_index": 1,
                    "title": "Module 1: Getting Started & Foundations",
                    "timeframe": "Week 1",
                    "objectives": [f"Grasp fundamental concepts of {goal}"],
                    "topics": ["Basics & Terminology", "Core Architecture"],
                    "practice_tasks": ["Create summary notes", "Take practice quiz"]
                },
                {
                    "module_index": 2,
                    "title": "Module 2: Practical Application & Mastery",
                    "timeframe": "Week 2",
                    "objectives": ["Apply knowledge to real scenarios"],
                    "topics": ["Advanced Strategies", "Problem Solving"],
                    "practice_tasks": ["Solve 5 practice problems"]
                }
            ],
            "study_tips": ["Use flashcards for key definitions", "Review mistakes weekly"]
        }
        plan_id = memory.save_learning_plan(goal, target_date, daily_time, fallback_plan)
        fallback_plan["id"] = plan_id
        return fallback_plan
