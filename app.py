"""
Streamlit interface for the NovaTech Solutions HR assistant.
Usage: streamlit run app.py
"""

import streamlit as st
from src.rag import RAGChain
from src.config import TOP_K, DISTANCE_THRESHOLD, USE_RERANKING
from src.tools import detect_tools
from src.cache import (
    load_all_conversations,
    create_new_conversation,
    get_conversation,
    save_conversation,
    delete_conversation,
)
# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="Nova — NovaTech HR Assistant",
    page_icon="🏢",
    layout="centered",
)

# ============================================================
# DISPLAY SETTINGS
# ============================================================
SHOW_SOURCES = False
SHOW_CHUNKS = False

# ============================================================
# INIT
# ============================================================
@st.cache_resource
def load_rag():
    return RAGChain()

rag = load_rag()

# Session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "active_conversation_id" not in st.session_state:
    conversations = load_all_conversations()

    if conversations:
        current_conv = conversations[0]
    else:
        current_conv = create_new_conversation()

    st.session_state.active_conversation_id = current_conv["id"]
    st.session_state.messages = current_conv["messages"]
    st.session_state.chat_history = current_conv["chat_history"]

# ============================================================
# SIDEBAR
# ============================================================
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/company.png", width=60)
    st.title("Nova")
    st.caption("HR Assistant — NovaTech Solutions")

    st.divider()

    if st.button("➕ New conversation", use_container_width=True):
        new_conv = create_new_conversation()
        st.session_state.active_conversation_id = new_conv["id"]
        st.session_state.messages = new_conv["messages"]
        st.session_state.chat_history = new_conv["chat_history"]
        st.rerun()

    st.divider()
    st.subheader("Previous conversations")

    conversations = load_all_conversations()

    if not conversations:
        st.caption("No saved conversations.")
    else:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.active_conversation_id
            label = f"🟢 {conv['title']}" if is_active else conv["title"]

            col1, col2 = st.columns([5, 1])

            with col1:
                if st.button(label, key=f"open_{conv['id']}", use_container_width=True):
                    selected_conv = get_conversation(conv["id"])
                    if selected_conv:
                        st.session_state.active_conversation_id = selected_conv["id"]
                        st.session_state.messages = selected_conv["messages"]
                        st.session_state.chat_history = selected_conv["chat_history"]
                        st.rerun()

            with col2:
                if st.button("🗑️", key=f"delete_{conv['id']}"):
                    delete_conversation(conv["id"])

                    remaining = load_all_conversations()
                    if remaining:
                        st.session_state.active_conversation_id = remaining[0]["id"]
                        st.session_state.messages = remaining[0]["messages"]
                        st.session_state.chat_history = remaining[0]["chat_history"]
                    else:
                        new_conv = create_new_conversation()
                        st.session_state.active_conversation_id = new_conv["id"]
                        st.session_state.messages = new_conv["messages"]
                        st.session_state.chat_history = new_conv["chat_history"]

                    st.rerun()

    st.divider()

# ============================================================
# HEADER
# ============================================================
st.title("🏢 Nova — HR Assistant")
st.caption("Ask your questions about leave, telework, expenses, training, and more.")

# ============================================================
# CHAT HISTORY DISPLAY
# ============================================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # Show sources if enabled
        if msg["role"] == "assistant" and "sources" in msg and SHOW_SOURCES:
            with st.expander("📄 Sources consulted"):
                for s in msg["sources"]:
                    icon = "🏛️" if s["source"] == "gouv" else "🏢"
                    st.caption(f"{icon} {s['document']} (distance: {s['distance']:.3f})")

        # Show tools if present
        if msg["role"] == "assistant" and "tools" in msg:
            for tool in msg["tools"]:
                if tool["type"] == "form":
                    st.info(f"📋 **{tool['name']}**\n\n{tool['path']}")
                elif tool["type"] == "checklist":
                    st.success("✅ **Checklist**\n\n" + "\n".join(f"- [ ] {item}" for item in tool["items"]))
                elif tool["type"] == "contact":
                    st.warning(f"👤 **Contact: {tool['name']}**\n\n{tool['role']}\n\n✉️ {tool['email']}")

# ============================================================
# USER INPUT
# ============================================================
if prompt := st.chat_input("Your HR question..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate response
    with st.chat_message("assistant"):
        with st.spinner("Nova is thinking..."):
            result = rag.answer(
                question=prompt,
                chat_history=st.session_state.chat_history,
                top_k=TOP_K,
                distance_threshold=DISTANCE_THRESHOLD,
                use_reranking=USE_RERANKING,
            )

            answer = result["answer"]
            sources = result["sources"]
            chunks = result["chunks"]
            tool_call = result.get("tool_call")
            tool_result = result.get("tool_result")

            # Tools — detect relevant tools from the question
            tools_used = detect_tools(prompt)

        # Display answer
        st.markdown(answer)

        if tool_call:
            st.info(f"🛠️ Tool call used: {tool_call['tool']}\nArguments: {tool_call['arguments']}")
            st.write(f"Tool result: {tool_result}")

        # Display sources if enabled
        if SHOW_SOURCES and sources:
            with st.expander("📄 Sources consulted"):
                for s in sources:
                    icon = "🏛️" if s["source"] == "gouv" else "🏢"
                    st.caption(f"{icon} {s['document']} (distance: {s['distance']:.3f})")

        # Display tools
        for tool in tools_used:
            if tool["type"] == "form":
                st.info(f"📋 **{tool['name']}**\n\n{tool['path']}")
            elif tool["type"] == "checklist":
                st.success("✅ **Checklist**\n\n" + "\n".join(f"- [ ] {item}" for item in tool["items"]))
            elif tool["type"] == "contact":
                st.warning(f"👤 **Contact: {tool['name']}**\n\n{tool['role']}\n\n✉️ {tool['email']}")

        # Debug chunks if enabled
        if SHOW_CHUNKS and chunks:
            with st.expander("🔍 Retrieved chunks (debug)"):
                for i, c in enumerate(chunks):
                    score_info = f", score: {c.get('rerank_score', 'N/A')}" if "rerank_score" in c else ""
                    st.text(f"--- Chunk {i+1} (dist: {c['distance']:.3f}{score_info}) [{c['metadata']['document']}] ---")
                    st.text(c["text"][:500])
                    st.divider()

    # Save to session
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer,
        "sources": sources,
        "tools": tools_used,
    })

    # Update chat history for context
    st.session_state.chat_history.append({"role": "user", "content": prompt})
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # Persist conversation cache
    save_conversation(
        st.session_state.active_conversation_id,
        st.session_state.messages,
        st.session_state.chat_history,
    )
    # Limit history to last 10 exchanges
    if len(st.session_state.chat_history) > 20:
        st.session_state.chat_history = st.session_state.chat_history[-20:]