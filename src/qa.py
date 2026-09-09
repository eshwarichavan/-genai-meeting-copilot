"""Grounded RAG Q&A across all ingested meetings."""
from .logging_utils import timed_stage
from . import llm, vector_store

SYSTEM_PROMPT = """You are a meeting-notes assistant. Answer the user's question \
using ONLY the provided context excerpts from past meetings. Every claim must be \
traceable to a context excerpt; cite the meeting title and date in parentheses \
after each fact you use, e.g. (Sprint Planning, 2026-08-11). If the answer is not \
present in the context, reply with exactly: "I can't find this in the provided \
context." Do not use outside knowledge and do not guess."""


def answer(question: str) -> dict:
    with timed_stage("retrieval_ms") as rec:
        results = vector_store.query(question)
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        rec["retrieved"] = len(docs)

    if not docs:
        return {"answer": "I can't find this in the provided context.", "sources": [], "tokens": None}

    context = "\n\n---\n\n".join(
        f"[{meta['title']} — {meta['date']}]\n{doc}" for doc, meta in zip(docs, metas)
    )
    messages = [{"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}]

    with timed_stage("llm_ms") as rec:
        rec["stage_detail"] = "qa"
        resp = llm.chat(messages, system=SYSTEM_PROMPT, max_tokens=500)
        rec["input_tokens"] = resp.usage.input_tokens
        rec["output_tokens"] = resp.usage.output_tokens

    answer_text = "".join(block.text for block in resp.content if block.type == "text")
    sources = sorted({f"{m['title']} ({m['date']})" for m in metas})
    return {
        "answer": answer_text,
        "sources": sources,
        "tokens": {"input": resp.usage.input_tokens, "output": resp.usage.output_tokens},
    }
