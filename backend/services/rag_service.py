import os
import glob
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from groq import Groq
from config import BASE_DIR, GROQ_API_KEY, GROQ_MODEL, SCHOOL_NAME

KB_DIR = BASE_DIR / "knowledge_base"

class PolicyRAGService:
    def __init__(self):
        self.encoder: Optional[SentenceTransformer] = None
        self.index: Optional[faiss.IndexFlatL2] = None
        self.chunks: List[Dict[str, Any]] = []
        self.groq_client: Optional[Groq] = None
        self.is_initialized: bool = False

    def initialize(self):
        """
        Loads knowledge base documents, splits them into ~200 word chunks,
        computes dense embeddings with sentence-transformers, and populates FAISS index.
        """
        print("[RAG] Initializing SentenceTransformer model...")
        # 'all-MiniLM-L6-v2' is lightweight, fast and produces 384-dimensional embeddings
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

        # Load knowledge base files
        self.chunks = []
        kb_files = glob.glob(str(KB_DIR / "*.txt"))

        for file_path in kb_files:
            file_name = Path(file_path).name
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Split by double newlines or sections
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            for p in paragraphs:
                # If paragraph is long, split roughly into 200 words
                words = p.split()
                if len(words) > 220:
                    for i in range(0, len(words), 180):
                        sub_text = " ".join(words[i:i+200])
                        self.chunks.append({
                            "source": file_name,
                            "text": sub_text
                        })
                else:
                    self.chunks.append({
                        "source": file_name,
                        "text": p
                    })

        if not self.chunks:
            print("[RAG] Warning: No policy documents found in knowledge_base directory.")
            return

        print(f"[RAG] Indexed {len(self.chunks)} text chunks across policy files.")
        texts = [c["text"] for c in self.chunks]
        embeddings = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity with normalized vectors
        self.index.add(embeddings.astype('float32'))

        # Setup Groq Client
        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key.strip())
                print("[RAG] Groq client initialized successfully.")
            except Exception as e:
                print(f"[RAG] Groq init warning: {e}")
                self.groq_client = None
        else:
            print("[RAG] Note: GROQ_API_KEY is not set. Intelligent local extractor will serve answers.")

        self.is_initialized = True

    def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.is_initialized or self.index is None:
            self.initialize()

        query_vector = self.encoder.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype('float32')
        scores, indices = self.index.search(query_vector, top_k)

        results = []
        for i, idx in enumerate(indices[0]):
            if idx != -1 and idx < len(self.chunks):
                results.append({
                    "score": float(scores[0][i]),
                    "source": self.chunks[idx]["source"],
                    "text": self.chunks[idx]["text"]
                })
        return results

    def answer_query(self, query: str) -> Dict[str, Any]:
        """
        Executes RAG pipeline:
        1. Vector search in FAISS.
        2. Prompt construction with grounded context.
        3. LLM generation with Groq, or fallback if Groq API is not set.
        """
        if not self.is_initialized:
            self.initialize()

        matched_chunks = self.retrieve_relevant_chunks(query, top_k=3)
        if not matched_chunks:
            return {
                "answer": f"I don't know. The requested information is not documented in the official school policies of {SCHOOL_NAME}.",
                "sources": [],
                "grounded": False
            }

        # Check relevance score (cosine similarity threshold)
        top_score = matched_chunks[0]["score"]
        if top_score < 0.25:
            return {
                "answer": f"I do not find information regarding this in the official policies of {SCHOOL_NAME}. Please refer to the school administration office for assistance.",
                "sources": [c["source"] for c in matched_chunks],
                "grounded": False
            }

        context_text = "\n\n---\n\n".join([f"[Source: {c['source']}]\n{c['text']}" for c in matched_chunks])
        sources = list(dict.fromkeys([c["source"] for c in matched_chunks]))

        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if self.groq_client is None and api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key.strip())
            except Exception:
                pass

        system_prompt = f"""You are the official AI Policy Assistant for {SCHOOL_NAME}.
You must answer questions strictly and only using the provided Policy Document Excerpts below.
Rules:
1. If the answer is not contained in the excerpts, say clearly: "I don't know based on the provided school policies."
2. Do not invent dates, rules, or fees.
3. Be concise, polite, professional, and cite which policy applies."""

        user_prompt = f"""Policy Document Excerpts:
{context_text}

Question: {query}
Answer:"""

        if self.groq_client:
            candidate_models = [
                os.getenv("GROQ_MODEL", GROQ_MODEL),
                "openai/gpt-oss-120b",
                "openai/gpt-oss-20b",
                "llama-3.3-70b-versatile",
                "llama-3.1-8b-instant"
            ]
            candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))
            for model_name in candidate_models:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        model=model_name,
                        temperature=0.2,
                        max_tokens=400,
                    )
                    answer = chat_completion.choices[0].message.content.strip()
                    return {
                        "answer": answer,
                        "sources": sources,
                        "grounded": True,
                        "model": model_name
                    }
                except Exception as e:
                    print(f"[RAG] Groq model '{model_name}' attempt error: {e}")

        # Local Grounded Fallback Answer Generator
        # Highlights key sentences directly from retrieved chunks
        best_chunk = matched_chunks[0]["text"]
        lines = [line.strip() for line in best_chunk.split("\n") if line.strip()]
        summary = " ".join(lines[:4])
        return {
            "answer": f"According to {sources[0]}: {summary}",
            "sources": sources,
            "grounded": True
        }

    def get_known_topics(self) -> List[Dict[str, str]]:
        return [
            {"topic": "Fee Policies & Due Dates", "prompt": "What is the fee due date and late surcharge policy?"},
            {"topic": "Fee Refund Rules", "prompt": "What is the fee refund policy if a student withdraws?"},
            {"topic": "Sibling Discounts", "prompt": "What fee concession or discount is provided for siblings?"},
            {"topic": "Exam Grading Scale", "prompt": "What is the grading scale and passing percentage for exams?"},
            {"topic": "Retake Examinations", "prompt": "What are the rules and fees for retake examinations?"},
            {"topic": "Admission Requirements", "prompt": "What are the age criteria and documents required for admission?"},
            {"topic": "Uniform Regulations", "prompt": "What is the required school uniform for boys and girls?"},
            {"topic": "Attendance & Leave Rules", "prompt": "What is the minimum attendance requirement and sick leave policy?"},
            {"topic": "Academic Calendar & Vacations", "prompt": "When are the winter vacation and annual exam dates?"}
        ]

rag_service = PolicyRAGService()
