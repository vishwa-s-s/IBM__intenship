import os
import json
from typing import List, Dict, Any
from google import genai
from dotenv import load_dotenv
from core import memory, rag

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def generate_quiz(topic: str = "General Knowledge", num_questions: int = 5, quiz_type: str = "mcq") -> Dict[str, Any]:
    # Check if we have relevant documents in RAG store
    relevant_chunks = rag.retrieve_relevant_chunks(topic, top_k=5)
    context_str = "\n".join([c["content"] for c in relevant_chunks]) if relevant_chunks else ""

    prompt = f"""
You are an expert examiner. Generate an interactive practice quiz to test student comprehension.

Topic: {topic}
Number of Questions: {num_questions}
Quiz Type: {quiz_type} (Options: 'mcq' for multiple choice, 'flashcard' for Q&A review)
Reference Study Context:
{context_str if context_str else "Use general domain knowledge for this topic."}

Output MUST be strict JSON only with NO markdown syntax, matching this exact schema:
{{
  "topic": "{topic}",
  "quiz_type": "{quiz_type}",
  "questions": [
    {{
      "id": 1,
      "topic": "{topic}",
      "question": "Clear question text?",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option A",
      "explanation": "Detailed explanation why Option A is correct and grounded in concepts."
    }}
  ]
}}
"""

    if not client:
        # Static fallback quiz
        fallback_questions = [
            {
                "id": 1,
                "topic": topic,
                "question": f"What is the key objective when studying {topic}?",
                "options": [
                    "To understand fundamental principles and application",
                    "To memorize facts without understanding",
                    "To skip problem solving",
                    "None of the above"
                ],
                "correct_answer": "To understand fundamental principles and application",
                "explanation": "Effective learning requires grasping foundational concepts and practical application."
            }
        ]
        quiz_id = memory.save_quiz(topic, quiz_type, fallback_questions)
        return {
            "quiz_id": quiz_id,
            "topic": topic,
            "quiz_type": quiz_type,
            "questions": fallback_questions
        }

    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        raw_text = response.text.strip()
        
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            raw_text = "\n".join(lines).strip()
            
        quiz_data = json.loads(raw_text)
        questions = quiz_data.get("questions", [])
        
        quiz_id = memory.save_quiz(topic, quiz_type, questions)
        
        return {
            "quiz_id": quiz_id,
            "topic": topic,
            "quiz_type": quiz_type,
            "questions": questions
        }
    except Exception as e:
        print(f"Error generating quiz: {str(e)}")
        fallback_questions = [
            {
                "id": 1,
                "topic": topic,
                "question": f"Which approach best describes mastering {topic}?",
                "options": [
                    "Structured practice and conceptual mastery",
                    "Rote passive reading",
                    "Avoiding practice tests",
                    "Ignoring mistakes"
                ],
                "correct_answer": "Structured practice and conceptual mastery",
                "explanation": "Active recall and structured practice lead to long-term memory retention."
            }
        ]
        quiz_id = memory.save_quiz(topic, quiz_type, fallback_questions)
        return {
            "quiz_id": quiz_id,
            "topic": topic,
            "quiz_type": quiz_type,
            "questions": fallback_questions
        }

def evaluate_quiz_submission(quiz_id: int, user_answers: Dict[str, str], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    correct_count = 0
    total = len(questions)
    details = []

    for q in questions:
        q_id_str = str(q.get("id"))
        user_ans = user_answers.get(q_id_str, "").strip()
        correct_ans = str(q.get("correct_answer", "")).strip()
        
        is_correct = (user_ans.lower() == correct_ans.lower())
        if is_correct:
            correct_count += 1
            
        details.append({
            "question_id": q.get("id"),
            "topic": q.get("topic", "General"),
            "question": q.get("question"),
            "user_answer": user_ans,
            "correct_answer": correct_ans,
            "is_correct": is_correct,
            "explanation": q.get("explanation", "")
        })

    score_pct = round((correct_count / total * 100), 1) if total > 0 else 0.0
    
    # Save attempt to memory DB & log mistakes
    memory.save_quiz_attempt(quiz_id, score_pct, total, details)

    return {
        "score_pct": score_pct,
        "correct_count": correct_count,
        "total_questions": total,
        "details": details
    }
