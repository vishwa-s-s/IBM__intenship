import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "study_assistant.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Documents table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL, -- 'pdf', 'text', 'url'
            source_info TEXT,
            chunk_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 2. Document Chunks (RAG index)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS doc_chunks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_id INTEGER,
            chunk_index INTEGER,
            content TEXT NOT NULL,
            embedding_json TEXT, -- JSON array of floats
            FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE
        )
    ''')
    
    # 3. Chat History (Memory across conversations)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT NOT NULL, -- 'user' or 'assistant'
            content TEXT NOT NULL,
            citations_json TEXT, -- JSON array of cited sources
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 4. Learning Plans
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal TEXT NOT NULL,
            target_date TEXT,
            daily_time TEXT,
            plan_json TEXT NOT NULL, -- JSON detailed breakdown
            completed_steps TEXT DEFAULT '[]', -- JSON array of step indices
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 5. Quizzes & Submissions
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quizzes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            quiz_type TEXT DEFAULT 'mcq',
            questions_json TEXT NOT NULL, -- JSON array of questions
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS quiz_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quiz_id INTEGER,
            score REAL,
            total_questions INTEGER,
            details_json TEXT, -- student responses and explanations
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(quiz_id) REFERENCES quizzes(id)
        )
    ''')
    
    # 6. Mistakes Bank (Memory tracking past mistakes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mistakes_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            question TEXT NOT NULL,
            user_answer TEXT,
            correct_answer TEXT NOT NULL,
            explanation TEXT,
            reviewed_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. Student Profile / Mastery Memory
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS student_profile (
            key TEXT PRIMARY KEY,
            value_json TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

# Initialize DB structure on import
init_db()

# --- Memory API Functions ---

def save_document(title: str, source_type: str, source_info: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (title, source_type, source_info) VALUES (?, ?, ?)",
        (title, source_type, source_info)
    )
    doc_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return doc_id

def save_doc_chunks(doc_id: int, chunks: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    for idx, c in enumerate(chunks):
        embedding_json = json.dumps(c.get("embedding", []))
        cursor.execute(
            "INSERT INTO doc_chunks (doc_id, chunk_index, content, embedding_json) VALUES (?, ?, ?, ?)",
            (doc_id, idx, c["content"], embedding_json)
        )
    cursor.execute("UPDATE documents SET chunk_count = ? WHERE id = ?", (len(chunks), doc_id))
    conn.commit()
    conn.close()

def get_all_documents() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM documents ORDER BY id DESC").fetchall()
    docs = [dict(row) for row in rows]
    conn.close()
    return docs

def get_all_doc_chunks() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT c.id, c.doc_id, c.chunk_index, c.content, c.embedding_json, d.title FROM doc_chunks c JOIN documents d ON c.doc_id = d.id").fetchall()
    chunks = []
    for row in rows:
        chunk = dict(row)
        chunk["embedding"] = json.loads(chunk["embedding_json"]) if chunk["embedding_json"] else []
        chunks.append(chunk)
    conn.close()
    return chunks

def add_chat_message(role: str, content: str, citations: Optional[List[str]] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_history (role, content, citations_json) VALUES (?, ?, ?)",
        (role, content, json.dumps(citations or []))
    )
    conn.commit()
    conn.close()

def get_recent_chat_history(limit: int = 10) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM chat_history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    history = [dict(r) for r in reversed(rows)]
    for h in history:
        h["citations"] = json.loads(h["citations_json"]) if h.get("citations_json") else []
    conn.close()
    return history

def save_learning_plan(goal: str, target_date: str, daily_time: str, plan_data: Dict[str, Any]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO learning_plans (goal, target_date, daily_time, plan_json) VALUES (?, ?, ?, ?)",
        (goal, target_date, daily_time, json.dumps(plan_data))
    )
    plan_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return plan_id

def get_latest_learning_plan() -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT * FROM learning_plans ORDER BY id DESC LIMIT 1").fetchone()
    conn.close()
    if not row:
        return None
    res = dict(row)
    res["plan"] = json.loads(res["plan_json"])
    res["completed_steps"] = json.loads(res["completed_steps"]) if res.get("completed_steps") else []
    return res

def toggle_plan_step(plan_id: int, step_index: int) -> List[int]:
    conn = get_db_connection()
    cursor = conn.cursor()
    row = cursor.execute("SELECT completed_steps FROM learning_plans WHERE id = ?", (plan_id,)).fetchone()
    if not row:
        conn.close()
        return []
    completed = json.loads(row["completed_steps"]) if row["completed_steps"] else []
    if step_index in completed:
        completed.remove(step_index)
    else:
        completed.append(step_index)
    cursor.execute("UPDATE learning_plans SET completed_steps = ? WHERE id = ?", (json.dumps(completed), plan_id))
    conn.commit()
    conn.close()
    return completed

def save_quiz(topic: str, quiz_type: str, questions: List[Dict[str, Any]]) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO quizzes (topic, quiz_type, questions_json) VALUES (?, ?, ?)",
        (topic, quiz_type, json.dumps(questions))
    )
    quiz_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return quiz_id

def save_quiz_attempt(quiz_id: int, score: float, total_questions: int, details: List[Dict[str, Any]]):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO quiz_attempts (quiz_id, score, total_questions, details_json) VALUES (?, ?, ?, ?)",
        (quiz_id, score, total_questions, json.dumps(details))
    )
    
    # Track mistakes
    for d in details:
        if not d.get("is_correct", False):
            cursor.execute(
                "INSERT INTO mistakes_bank (topic, question, user_answer, correct_answer, explanation) VALUES (?, ?, ?, ?, ?)",
                (d.get("topic", "General"), d.get("question", ""), d.get("user_answer", ""), d.get("correct_answer", ""), d.get("explanation", ""))
            )
            
    conn.commit()
    conn.close()

def get_mistakes_bank() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    rows = cursor.execute("SELECT * FROM mistakes_bank ORDER BY id DESC").fetchall()
    mistakes = [dict(r) for r in rows]
    conn.close()
    return mistakes

def get_student_dashboard_stats() -> Dict[str, Any]:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_docs = cursor.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    total_quizzes = cursor.execute("SELECT COUNT(*) FROM quiz_attempts").fetchone()[0]
    avg_score_row = cursor.execute("SELECT AVG(score) FROM quiz_attempts").fetchone()[0]
    avg_score = round(avg_score_row or 0, 1)
    
    total_mistakes = cursor.execute("SELECT COUNT(*) FROM mistakes_bank").fetchone()[0]
    
    # Calculate topic performance
    attempts = cursor.execute("SELECT details_json FROM quiz_attempts").fetchall()
    topic_scores = {}
    for att in attempts:
        try:
            details = json.loads(att["details_json"])
            for d in details:
                topic = d.get("topic", "General")
                if topic not in topic_scores:
                    topic_scores[topic] = {"correct": 0, "total": 0}
                topic_scores[topic]["total"] += 1
                if d.get("is_correct"):
                    topic_scores[topic]["correct"] += 1
        except Exception:
            pass
            
    mastery = []
    for top, data in topic_scores.items():
        pct = int((data["correct"] / data["total"]) * 100) if data["total"] > 0 else 0
        mastery.append({"topic": top, "mastery_pct": pct, "total_questions": data["total"]})
        
    conn.close()
    
    return {
        "total_documents": total_docs,
        "total_quizzes_taken": total_quizzes,
        "average_score": avg_score,
        "active_mistakes_count": total_mistakes,
        "topic_mastery": mastery
    }
