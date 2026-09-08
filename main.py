from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response, RedirectResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json

from core import scraper, analyzer, tts, cache, memory, rag, planner, quiz, tools

app = FastAPI(title="AI Learning & Study Assistant API")

# Serve the static frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- Request Models ---
class TextIngestRequest(BaseModel):
    title: str
    content: str

class UrlIngestRequest(BaseModel):
    url: str
    title: Optional[str] = None

class QARequest(BaseModel):
    query: str

class PlanGenerateRequest(BaseModel):
    goal: str
    target_date: str = "4 Weeks"
    daily_time: str = "1 Hour / Day"
    level: str = "Beginner"

class ToggleStepRequest(BaseModel):
    plan_id: int
    step_index: int

class QuizGenerateRequest(BaseModel):
    topic: str
    num_questions: int = 5
    quiz_type: str = "mcq"

class QuizSubmitRequest(BaseModel):
    quiz_id: int
    user_answers: Dict[str, str]
    questions: List[Dict[str, Any]]

class AudioTTSRequest(BaseModel):
    text: str
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"

# --- Endpoints ---

@app.get("/")
def read_root():
    return RedirectResponse(url="/static/index.html")

@app.get("/api/voices")
def get_voices():
    return {"voices": tts.get_voices()}

# 1. Study Materials & RAG Ingestion Endpoints
@app.get("/api/documents")
def list_documents():
    return {"documents": memory.get_all_documents()}

@app.post("/api/materials/text")
def ingest_text(req: TextIngestRequest):
    try:
        res = rag.ingest_document(req.title, "text", req.content, source_info="Direct text entry")
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/materials/pdf")
async def ingest_pdf(file: UploadFile = File(...)):
    try:
        pdf_bytes = await file.read()
        extracted_text = rag.extract_text_from_pdf_bytes(pdf_bytes)
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="Could not extract text from PDF.")
        
        doc_title = file.filename or "Uploaded PDF"
        res = rag.ingest_document(doc_title, "pdf", extracted_text, source_info=file.filename)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/materials/url")
def ingest_url(req: UrlIngestRequest):
    try:
        text_content = scraper.scrape_url(req.url)
        title = req.title if req.title else req.url
        res = rag.ingest_document(title, "url", text_content, source_info=req.url)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 2. Grounded RAG Question Answering Endpoint
@app.post("/api/qa")
def ask_question(req: QARequest):
    try:
        result = rag.answer_question_with_rag(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 3. Learning Plan Generator Endpoints
@app.post("/api/learning-plan/generate")
def create_plan(req: PlanGenerateRequest):
    try:
        plan_data = planner.generate_learning_plan(
            goal=req.goal,
            target_date=req.target_date,
            daily_time=req.daily_time,
            level=req.level
        )
        return {"status": "success", "plan": plan_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/learning-plan/current")
def get_current_plan():
    plan = memory.get_latest_learning_plan()
    return {"plan": plan}

@app.post("/api/learning-plan/toggle-step")
def toggle_step(req: ToggleStepRequest):
    completed = memory.toggle_plan_step(req.plan_id, req.step_index)
    return {"status": "success", "completed_steps": completed}

# 4. Interactive Quiz Arena Endpoints
@app.post("/api/quiz/generate")
def make_quiz(req: QuizGenerateRequest):
    try:
        q_data = quiz.generate_quiz(
            topic=req.topic,
            num_questions=req.num_questions,
            quiz_type=req.quiz_type
        )
        return q_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/quiz/submit")
def submit_quiz(req: QuizSubmitRequest):
    try:
        eval_result = quiz.evaluate_quiz_submission(
            quiz_id=req.quiz_id,
            user_answers=req.user_answers,
            questions=req.questions
        )
        return eval_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 5. Student Analytics & Memory Dashboard Endpoint
@app.get("/api/student/dashboard")
def get_dashboard():
    try:
        stats = memory.get_student_dashboard_stats()
        mistakes = memory.get_mistakes_bank()
        return {
            "stats": stats,
            "mistakes_bank": mistakes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 6. Audio Explanation TTS Endpoint
@app.post("/api/tts")
def text_to_speech(req: AudioTTSRequest):
    try:
        res = tools.generate_study_summary_audio(req.text, req.voice_id)
        if res["status"] == "error":
            raise HTTPException(status_code=500, detail=res["message"])
        return Response(content=res["audio_bytes"], media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
