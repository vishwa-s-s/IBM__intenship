import os
import io
import math
from typing import List, Dict, Any, Tuple
from google import genai
from dotenv import load_dotenv
from core import memory, scraper
import pypdf

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
    extracted = []
    for page in reader.pages:
        txt = page.extract_text()
        if txt:
            extracted.append(txt)
    return "\n\n".join(extracted)

def chunk_text(text: str, chunk_size: int = 600, overlap: int = 100) -> List[str]:
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        i += chunk_size - overlap
    return chunks if chunks else [text]

def get_embedding(text: str) -> List[float]:
    if not client:
        return []
    try:
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=text
        )
        # Handle embedding output format
        if hasattr(res, 'embedding') and hasattr(res.embedding, 'values'):
            return res.embedding.values
        elif hasattr(res, 'embeddings') and len(res.embeddings) > 0:
            return res.embeddings[0].values
    except Exception as e:
        print(f"Embedding error: {str(e)}")
    return []

def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    if not vec1 or not vec2 or len(vec1) != len(vec2):
        return 0.0
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)

def ingest_document(title: str, source_type: str, content: str, source_info: str = "") -> Dict[str, Any]:
    # 1. Save doc metadata
    doc_id = memory.save_document(title, source_type, source_info)
    
    # 2. Chunk text
    raw_chunks = chunk_text(content)
    
    # 3. Create embeddings
    processed_chunks = []
    for chunk_str in raw_chunks:
        emb = get_embedding(chunk_str)
        processed_chunks.append({
            "content": chunk_str,
            "embedding": emb
        })
        
    # 4. Save to memory RAG table
    memory.save_doc_chunks(doc_id, processed_chunks)
    
    return {
        "doc_id": doc_id,
        "title": title,
        "chunk_count": len(processed_chunks)
    }

def retrieve_relevant_chunks(query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    all_chunks = memory.get_all_doc_chunks()
    if not all_chunks:
        return []
        
    query_emb = get_embedding(query)
    
    scored_chunks = []
    for chunk in all_chunks:
        score = 0.0
        if query_emb and chunk.get("embedding"):
            score = cosine_similarity(query_emb, chunk["embedding"])
        else:
            # Fallback keyword overlap score if embedding isn't available
            query_words = set(query.lower().split())
            chunk_words = set(chunk["content"].lower().split())
            score = len(query_words.intersection(chunk_words)) / max(len(query_words), 1)
            
        scored_chunks.append((score, chunk))
        
    scored_chunks.sort(key=lambda x: x[0], reverse=True)
    return [c for score, c in scored_chunks[:top_k] if score > 0.01 or not query_emb]

def answer_question_with_rag(query: str) -> Dict[str, Any]:
    # 1. Retrieve top chunks
    relevant = retrieve_relevant_chunks(query, top_k=4)
    
    context_str = ""
    citations = []
    for idx, c in enumerate(relevant):
        context_str += f"\n--- Source {idx+1} ({c.get('title', 'Doc')}): ---\n{c['content']}\n"
        citations.append(f"{c.get('title', 'Document')}: \"{c['content'][:120]}...\"")
        
    # 2. Retrieve recent chat history memory
    history = memory.get_recent_chat_history(limit=4)
    history_str = ""
    for h in history:
        history_str += f"{h['role'].capitalize()}: {h['content']}\n"
        
    prompt = f"""
You are an expert AI Learning & Study Assistant. Your goal is to provide accurate, clear, and encouraging educational explanations.

Available Course Context:
{context_str if context_str else "No specific documents uploaded yet. Provide a helpful general answer based on your knowledge base."}

Recent Conversation History:
{history_str}

Student Question:
{query}

Instructions:
- Provide a clear, step-by-step breakdown.
- If relevant info is found in the Course Context, directly reference it and ground your answer.
- Keep the tone supportive, academic, and engaging.
- Use clean formatting with key terms highlighted.
"""

    if not client:
        return {
            "answer": "API Key is missing or invalid. Please configure GEMINI_API_KEY in .env.",
            "citations": citations
        }
        
    try:
        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        answer_text = response.text.strip()
        
        # Save to memory
        memory.add_chat_message("user", query)
        memory.add_chat_message("assistant", answer_text, citations)
        
        return {
            "answer": answer_text,
            "citations": citations,
            "used_context_count": len(relevant)
        }
    except Exception as e:
        return {
            "answer": f"Error generating answer: {str(e)}",
            "citations": citations
        }
