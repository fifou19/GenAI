
from prompts.prompts_llm import SYSTEM_PROMPT, FEW_SHOT_EXAMPLES, infer_answer_language
 
# RAG PROMPT TEMPLATE
# ============================================================
def build_rag_prompt(question: str, context_chunks: list[dict]) -> str:
    """
    Builds the final prompt sent to the LLM with the RAG context.
    Tells the model to answer in the same language as the employee's latest message.
    """
    # Format context chunks
    context_parts = []
    for i, chunk in enumerate(context_chunks):
        meta = chunk.get("metadata", {})
        title = meta.get("title") or meta.get("document", "unknown")
        section = meta.get("section", "")

        label = f"[Source {i+1}] {title}"
        if section:
            label += f" — {section}"
        context_parts.append(f"{label}\n{chunk['text']}")

    context_text = "\n\n---\n\n".join(context_parts)

    answer_language = infer_answer_language(question)

    prompt = f"""IMPORTANT: The final answer for this request must be written in {answer_language}.
Use the current employee question as the source of truth for language.
Do not let previous history or few-shot examples change the answer language.

Here are the relevant documents to answer the employee's question:

{context_text}

---

Employee question: {question}

Answer following the requested format. If the information is not in the documents above, say so clearly."""

    return prompt


# ============================================================
# MESSAGES BUILDER (for chat APIs)
# ============================================================
def build_messages(question: str, context_chunks: list[dict], 
                   chat_history: list[dict] = None) -> list[dict]: # type: ignore
    """
    Builds the full list of messages for the LLM API.
    Includes: system prompt + few-shot examples + history + question with RAG context.
    """
    answer_language = infer_answer_language(question)
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.append({
        "role": "system",
        "content": (
            "The few-shot examples below demonstrate tone and formatting only. "
            "They are not factual context for the current question."
        ),
    })
    messages.append({
        "role": "system",
        "content": (
            f"For the current request, the final answer must be written in {answer_language}. "
            "Use the latest employee question as the source of truth for language, not previous history."
        ),
    })
    
    # Few-shot examples
    messages.extend(FEW_SHOT_EXAMPLES)
    
    # Conversation history if present
    if chat_history:
        messages.extend(chat_history)
    
    # Current question with RAG context
    rag_prompt = build_rag_prompt(question, context_chunks)
    messages.append({"role": "user", "content": rag_prompt})
    
    return messages
