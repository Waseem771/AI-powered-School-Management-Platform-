import os
import glob
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import numpy as np
try:
    import faiss
    from sentence_transformers import SentenceTransformer
    HAS_FAISS = True
except Exception as e:
    HAS_FAISS = False

from groq import Groq
from config import BASE_DIR, GROQ_API_KEY, GROQ_MODEL, SCHOOL_NAME

KB_DIR = BASE_DIR / "knowledge_base"

# How close a policy passage must be before it is treated as the answer. Set by measuring real
# questions: school questions score at least 0.39 (FAISS) or 0.12 (TF-IDF); unrelated ones at
# most 0.28 (FAISS). TF-IDF only sees shared words, so "moon" still finds "moon sighting".
MIN_SCORE_FAISS = 0.35
MIN_SCORE_TFIDF = 0.10
GROQ_TIMEOUT_SECONDS = 20
_MODEL_FOUND_NOTHING = "i don't know based on"
_LOCAL_ANSWER_MAX_LINES = 4
_COMMON_WORDS = frozenset(
    "a about all and are at be by can do does for from how i in is it me my of on or our school student students "
    "tell the their there to we what when where which who why will with you your".split()
)


def _cannot_answer() -> str:
    return (
        f"I cannot answer that from the school's records or the official policies of {SCHOOL_NAME}. "
        "Please ask the school administration office."
    )


def _key_terms(text: str) -> set:
    """Lower-case word starts, so "refunds" finds "refund" and "examinations" finds "examination"."""
    return {word[:6] for word in re.findall(r"\w+", text.lower()) if word not in _COMMON_WORDS and len(word) > 2}


class PolicyRAGService:
    def __init__(self):
        self.encoder = None
        self.index = None
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
        self.chunks: List[Dict[str, Any]] = []
        self.groq_client: Optional[Groq] = None
        self.is_initialized: bool = False

    def initialize(self):
        """
        Loads knowledge base documents, splits them into ~200 word chunks,
        computes dense embeddings with sentence-transformers + FAISS (or TF-IDF fallback),
        and populates index.
        """
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

        if HAS_FAISS:
            try:
                print("[RAG] Initializing SentenceTransformer model...")
                self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
                texts = [c["text"] for c in self.chunks]
                embeddings = self.encoder.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
                dimension = embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dimension)
                self.index.add(embeddings.astype('float32'))
            except Exception as e:
                print(f"[RAG] FAISS/SentenceTransformer error: {e}. Falling back to TF-IDF.")
                self.encoder = None
                self.index = None

        if self.index is None:
            from sklearn.feature_extraction.text import TfidfVectorizer
            print("[RAG] Using Scikit-Learn TF-IDF vector retrieval engine for policy documents.")
            texts = [c["text"] for c in self.chunks]
            self.tfidf_vectorizer = TfidfVectorizer(stop_words='english')
            self.tfidf_matrix = self.tfidf_vectorizer.fit_transform(texts)

        # Setup Groq Client
        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key.strip(), timeout=GROQ_TIMEOUT_SECONDS, max_retries=1)
                print("[RAG] Groq client initialized successfully.")
            except Exception as e:
                print(f"[RAG] Groq init warning: {e}")
                self.groq_client = None
        else:
            print("[RAG] Note: GROQ_API_KEY is not set. Intelligent local extractor will serve answers.")

        self.is_initialized = True

    def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        if not self.is_initialized:
            self.initialize()

        if self.index is not None and self.encoder is not None:
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
        elif self.tfidf_vectorizer is not None and self.tfidf_matrix is not None:
            from sklearn.metrics.pairwise import cosine_similarity
            query_vector = self.tfidf_vectorizer.transform([query])
            sims = cosine_similarity(query_vector, self.tfidf_matrix)[0]
            top_indices = np.argsort(-sims)[:top_k]
            results = []
            for idx in top_indices:
                score = float(sims[idx])
                if score > 0:
                    results.append({
                        "score": score,
                        "source": self.chunks[idx]["source"],
                        "text": self.chunks[idx]["text"]
                    })
            return results
        return []

    def answer_query(self, query: str, history: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
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
            return {"answer": _cannot_answer(), "sources": [], "grounded": False}

        # A weak match is an unrelated passage, not an answer.
        if matched_chunks[0]["score"] < self._minimum_score():
            return {"answer": _cannot_answer(), "sources": [], "grounded": False}

        context_text = "\n\n---\n\n".join([f"[Source: {c['source']}]\n{c['text']}" for c in matched_chunks])
        sources = list(dict.fromkeys([c["source"] for c in matched_chunks]))

        api_key = os.getenv("GROQ_API_KEY", GROQ_API_KEY)
        if self.groq_client is None and api_key and api_key.strip():
            try:
                self.groq_client = Groq(api_key=api_key.strip(), timeout=GROQ_TIMEOUT_SECONDS, max_retries=1)
            except Exception:
                pass

        system_prompt = f"""You are the official AI Policy Assistant for {SCHOOL_NAME}.
You must answer questions strictly and only using the provided Policy Document Excerpts below.
You maintain conversation continuity with the user.
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
            
            chat_messages = [{"role": "system", "content": system_prompt}]
            if history:
                for msg in history[-6:]:
                    r = msg.get("role")
                    c = msg.get("content")
                    if r in ("user", "assistant") and c:
                        chat_messages.append({"role": r, "content": str(c)[:600]})
            chat_messages.append({"role": "user", "content": user_prompt})

            for model_name in candidate_models:
                try:
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=chat_messages,
                        model=model_name,
                        temperature=0.2,
                        max_tokens=400,
                    )
                    answer = chat_completion.choices[0].message.content.strip()
                    if _MODEL_FOUND_NOTHING in answer.lower():
                        return {"answer": _cannot_answer(), "sources": [], "grounded": False}
                    return {
                        "answer": answer,
                        "sources": sources,
                        "grounded": True,
                        "model": model_name
                    }
                except Exception as e:
                    print(f"[RAG] Groq model '{model_name}' attempt error: {e}")

        source, summary = self._local_answer(query, matched_chunks)
        return {
            "answer": f"According to {source}: {summary}",
            "sources": [source],
            "grounded": True
        }

    def _minimum_score(self) -> float:
        return MIN_SCORE_FAISS if self.index is not None else MIN_SCORE_TFIDF

    @staticmethod
    def _local_answer(query: str, chunks: List[Dict[str, Any]]) -> tuple:
        """With no language model: the section heading and the lines that share the question's words.

        Looks through all retrieved passages, because the closest one overall can miss the one
        line that holds the answer.
        """
        terms = _key_terms(query)
        best_source, best_lines, best_overlap = chunks[0]["source"], [], 0
        for chunk in chunks:
            lines = [line.strip() for line in chunk["text"].split("\n") if line.strip()]
            scored = [(len(terms & _key_terms(line)), line) for line in lines[1:]]
            overlap = max((score for score, _ in scored), default=0)
            if overlap > best_overlap:
                matching = [line for score, line in scored if score == overlap or score >= 2]
                best_source, best_lines, best_overlap = chunk["source"], [lines[0], *matching], overlap
        if not best_lines:
            best_lines = [line.strip() for line in chunks[0]["text"].split("\n") if line.strip()]
        return best_source, " ".join(best_lines[:_LOCAL_ANSWER_MAX_LINES + 1])

    def status(self) -> Dict[str, Any]:
        """What this process is really using. Nothing is loaded until the first policy question."""
        if not self.is_initialized:
            engine = "not_loaded"
        else:
            engine = "faiss" if self.index is not None else "tfidf"
        return {"engine": engine, "documents": len({chunk["source"] for chunk in self.chunks})}

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
