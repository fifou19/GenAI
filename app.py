"""
Streamlit interface for the NovaTech Solutions HR assistant.
Usage: streamlit run app.py
"""

import streamlit as st
from src.agents import OrchestratorAgent
from src.config import TOP_K, DISTANCE_THRESHOLD, USE_RERANKING
from src.cache import (
    load_all_conversations,
    create_new_conversation,
    get_conversation,
    save_conversation,
    delete_conversation,
)

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nova — HR Assistant",
    page_icon="✦",
    layout="centered",
)

# ── SETTINGS ──────────────────────────────────────────────────────────────────
SHOW_SOURCES = False
SHOW_CHUNKS  = False

# ── GLOBAL CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ─── TOKENS ─────────────────────────────────────────── */
:root {
    --g:    #20E8AC;
    --gd:   #0fc48e;
    --g08:  rgba(32,232,172,.08);
    --g16:  rgba(32,232,172,.16);
    --g28:  rgba(32,232,172,.28);
    --ink:  #0d1b2a;
    --ink2: #3c5168;
    --ink3: #8fa3b1;
    --line: #deeeed;
    --sur:  #f6fdfb;
    --wh:   #ffffff;
    --r:    14px;
    --rs:   9px;
    --sd:   0 2px 16px rgba(13,27,42,.06);
    --sdg:  0 4px 22px rgba(32,232,172,.24);
}

/* ─── BASE ───────────────────────────────────────────── */
html, [class*="css"] { font-family: 'Inter', system-ui, sans-serif !important; }

/* hide streamlit chrome */
#MainMenu, footer, header,
[data-testid="stStatusWidget"],
[data-testid="stToolbar"]           { display: none !important; }

.stApp { background: var(--wh) !important; }

/* main column */
.main .block-container {
    padding-top:    1.5rem  !important;
    padding-bottom: 5rem    !important;
    max-width:      760px   !important;
}

/* ─── SIDEBAR ────────────────────────────────────────── */
[data-testid="stSidebar"] {
    background:   var(--wh)                          !important;
    border-right: 1.5px solid var(--line)            !important;
    box-shadow:   4px 0 28px rgba(13,27,42,.04)      !important;
}
[data-testid="stSidebar"] > div { padding-top: 1.1rem !important; }

[data-testid="stSidebar"] hr {
    border:     none                         !important;
    border-top: 1.5px solid var(--line)      !important;
    margin:     .65rem 0                     !important;
}

/* ─── BUTTONS ────────────────────────────────────────── */
/* Primary = New conversation */
[data-testid="baseButton-primary"] {
    background:    var(--g)                          !important;
    color:         var(--ink)                        !important;
    font-weight:   600                               !important;
    font-size:     .86rem                            !important;
    border:        none                              !important;
    border-radius: var(--rs)                         !important;
    box-shadow:    var(--sdg)                        !important;
    transition:    all .2s ease                      !important;
}
[data-testid="baseButton-primary"]:hover {
    background:   var(--gd)                          !important;
    transform:    translateY(-1px)                   !important;
    box-shadow:   0 6px 26px rgba(32,232,172,.38)   !important;
}

/* Secondary = conversation list & delete */
[data-testid="stSidebar"] [data-testid="baseButton-secondary"] {
    background:    transparent                       !important;
    border:        1.5px solid transparent           !important;
    color:         var(--ink2)                       !important;
    font-size:     .81rem                            !important;
    font-weight:   400                               !important;
    border-radius: var(--rs)                         !important;
    text-align:    left                              !important;
    padding:       .42rem .75rem                     !important;
    box-shadow:    none                              !important;
    transition:    all .15s ease                     !important;
}
[data-testid="stSidebar"] [data-testid="baseButton-secondary"]:hover {
    background:    var(--g08)                        !important;
    border-color:  var(--g)                          !important;
    color:         var(--ink)                        !important;
}

/* ─── CHAT MESSAGES ──────────────────────────────────── */
[data-testid="stChatMessage"] {
    background: transparent !important;
    border:     none        !important;
    padding:    .28rem 0    !important;
}

[data-testid="stChatMessage"] p {
    font-size:   .9rem  !important;
    line-height: 1.72   !important;
    color:       var(--ink) !important;
    margin:      .15rem 0   !important;
}
[data-testid="stChatMessage"] li {
    font-size:   .88rem !important;
    line-height: 1.65   !important;
    color:       var(--ink2) !important;
}
[data-testid="stChatMessage"] h1,
[data-testid="stChatMessage"] h2,
[data-testid="stChatMessage"] h3 {
    color:       var(--ink) !important;
    font-weight: 600        !important;
}
[data-testid="stChatMessage"] strong {
    color:       var(--ink) !important;
    font-weight: 600        !important;
}

/* avatars */
[data-testid="chatAvatarIcon-assistant"] {
    background:    linear-gradient(135deg, var(--g), var(--gd)) !important;
    border-radius: 11px                                          !important;
}
[data-testid="chatAvatarIcon-user"] {
    background:    var(--ink)                                    !important;
    border-radius: 11px                                          !important;
}

/* ─── CHAT INPUT ─────────────────────────────────────── */
/* Barre fixe du bas */
[data-testid="stBottom"],
[data-testid="stBottom"] > div,
[data-testid="stBottom"] > div > div {
    background: var(--wh) !important;
}

/* Conteneur principal de l'input */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div,
[data-testid="stChatInput"] > div > div {
    background:    var(--wh) !important;
    color:         var(--ink) !important;
}
[data-testid="stChatInput"] {
    border:        2px solid var(--line)              !important;
    border-radius: 22px                               !important;
    box-shadow:    var(--sd)                          !important;
    overflow:      hidden                             !important;
    transition:    border-color .2s, box-shadow .2s   !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: var(--g)                            !important;
    box-shadow:   0 0 0 4px var(--g08), var(--sd)     !important;
}
/* Textarea elle-même */
[data-testid="stChatInput"] textarea {
    background:   var(--wh)   !important;
    color:        var(--ink)  !important;
    font-size:    .92rem      !important;
    caret-color:  var(--g)    !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: var(--ink3) !important;
}
/* Bouton envoyer */
[data-testid="stChatInputSubmitButton"] > button {
    background:    var(--g)       !important;
    border-radius: 12px           !important;
    border:        none           !important;
    transition:    all .18s ease  !important;
}
[data-testid="stChatInputSubmitButton"] > button:hover {
    background: var(--gd)     !important;
    transform:  scale(1.05)   !important;
}

/* ─── EXPANDER ───────────────────────────────────────── */
[data-testid="stExpander"] {
    border:        1.5px solid var(--line) !important;
    border-radius: var(--rs)               !important;
    background:    var(--sur)              !important;
    box-shadow:    none                    !important;
    margin:        .4rem 0                 !important;
}
[data-testid="stExpander"] summary {
    font-size: .79rem       !important;
    color:     var(--ink2)  !important;
    padding:   .5rem .8rem  !important;
}
[data-testid="stExpander"] summary:hover {
    color: var(--gd) !important;
}

/* ─── SPINNER ────────────────────────────────────────── */
.stSpinner > div > div { border-top-color: var(--g)     !important; }
.stSpinner p           { color: var(--ink3)              !important;
                         font-size: .82rem               !important; }

/* ─── CAPTION ────────────────────────────────────────── */
.stCaption p {
    font-size: .76rem    !important;
    color:     var(--ink3) !important;
}

/* ─── SCROLLBAR ──────────────────────────────────────── */
::-webkit-scrollbar             { width: 5px; height: 5px; }
::-webkit-scrollbar-track       { background: transparent; }
::-webkit-scrollbar-thumb       { background: var(--line); border-radius: 99px; }
::-webkit-scrollbar-thumb:hover { background: var(--g); }

/* ─── SELECTION ──────────────────────────────────────── */
::selection { background: var(--g16); color: var(--ink); }
</style>
""", unsafe_allow_html=True)


# ── HELPERS ───────────────────────────────────────────────────────────────────

def _card(icon, accent, bg, border, title, subtitle=None, body_html=""):
    """Render a styled HTML card for the Streamlit UI."""
    sub = (
        f'<div style="color:#6b7a8d;font-size:.8rem;margin:.12rem 0 .45rem;'
        f'line-height:1.45">{subtitle}</div>'
        if subtitle else ""
    )
    return f"""
    <div style="
        background:{bg};
        border:1.5px solid {border};
        border-left:4px solid {accent};
        border-radius:13px;
        padding:.85rem 1.1rem;
        margin:.45rem 0;
        display:flex;
        align-items:flex-start;
        gap:.7rem;
        font-family:'Inter',sans-serif;
    ">
        <div style="font-size:1.25rem;line-height:1.25;flex-shrink:0;margin-top:.05rem">
            {icon}
        </div>
        <div style="flex:1;min-width:0">
            <div style="font-weight:600;color:#0d1b2a;font-size:.88rem;line-height:1.35">
                {title}
            </div>
            {sub}
            {body_html}
        </div>
    </div>
    """


def render_tool(tool: dict) -> None:
    """Render a tool card in the Streamlit app based on the tool type."""
    if tool["type"] == "form":
        st.html(
            _card(
                "📋", "#20E8AC",
                "linear-gradient(135deg,#f0fbf7,#e6fdf5)",
                "#c8ede1",
                tool["name"],
                subtitle=tool["path"],
            )
        )

    elif tool["type"] == "checklist":
        items_html = "".join(
            f'<div style="display:flex;align-items:flex-start;gap:.45rem;margin:.28rem 0">'
            f'<div style="width:15px;height:15px;border:2px solid #20E8AC;border-radius:5px;'
            f'flex-shrink:0;margin-top:2px"></div>'
            f'<span style="font-size:.84rem;color:#0d1b2a;line-height:1.55">{item}</span></div>'
            for item in tool["items"]
        )
        st.html(
            _card(
                "✅", "#20E8AC",
                "#f7fdfa", "#c8ede1",
                "Checklist — Prochaines étapes",
                body_html=items_html,
            )
        )

    elif tool["type"] == "contact":
        email_html = (
            f'<a href="mailto:{tool["email"]}" '
            f'style="color:#20E8AC;font-size:.82rem;font-weight:500;text-decoration:none">'
            f'✉️&nbsp;{tool["email"]}</a>'
        )
        st.html(
            _card(
                "👤", "#a78bfa",
                "linear-gradient(135deg,#f8f7ff,#f1f0ff)",
                "#ddd6fe",
                tool["name"],
                subtitle=tool["role"],
                body_html=email_html,
            )
        )


# ── INIT ──────────────────────────────────────────────────────────────────────

@st.cache_resource
def load_rag():
    """Create and cache the RAG orchestrator agent."""
    return OrchestratorAgent()

rag = load_rag()

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "active_conversation_id" not in st.session_state:
    conversations = load_all_conversations()
    current_conv  = conversations[0] if conversations else create_new_conversation()
    st.session_state.active_conversation_id = current_conv["id"]
    st.session_state.messages               = current_conv["messages"]
    st.session_state.chat_history           = current_conv["chat_history"]


# ── SIDEBAR ───────────────────────────────────────────────────────────────────

with st.sidebar:
    # Logo + branding
    st.html("""
    <div style="padding:.1rem .4rem 1rem;display:flex;align-items:center;gap:.7rem;
                font-family:'Inter',sans-serif">
        <div style="
            width:40px;height:40px;
            background:linear-gradient(135deg,#20E8AC,#0fc48e);
            border-radius:13px;
            display:flex;align-items:center;justify-content:center;
            font-size:1.2rem;
            box-shadow:0 4px 16px rgba(32,232,172,.32);
            flex-shrink:0;
        ">&#x2736;</div>
        <div>
            <div style="font-weight:700;color:#0d1b2a;font-size:1.02rem;line-height:1.1">Nova</div>
            <div style="font-size:.7rem;color:#8fa3b1;margin-top:.1rem">NovaTech Solutions</div>
        </div>
    </div>
    """)

    st.divider()

    if st.button("＋  Nouvelle conversation", use_container_width=True, type="primary"):
        new_conv = create_new_conversation()
        st.session_state.active_conversation_id = new_conv["id"]
        st.session_state.messages               = new_conv["messages"]
        st.session_state.chat_history           = new_conv["chat_history"]
        st.rerun()

    st.divider()

    st.markdown(
        '<p style="font-size:.71rem;font-weight:600;color:#8fa3b1;'
        'text-transform:uppercase;letter-spacing:.065em;'
        'margin:.1rem .2rem .55rem;font-family:Inter,sans-serif">Conversations</p>',
        unsafe_allow_html=True,
    )

    conversations = load_all_conversations()

    if not conversations:
        st.markdown(
            '<p style="font-size:.8rem;color:#8fa3b1;padding:.4rem .2rem;'
            'font-family:Inter,sans-serif">Aucune conversation.</p>',
            unsafe_allow_html=True,
        )
    else:
        for conv in conversations:
            is_active = conv["id"] == st.session_state.active_conversation_id
            col1, col2 = st.columns([6, 1])

            with col1:
                label = ("🟢 " if is_active else "   ") + conv["title"]
                if st.button(label, key=f"open_{conv['id']}", use_container_width=True):
                    selected = get_conversation(conv["id"])
                    if selected:
                        st.session_state.active_conversation_id = selected["id"]
                        st.session_state.messages               = selected["messages"]
                        st.session_state.chat_history           = selected["chat_history"]
                        st.rerun()

            with col2:
                if st.button("×", key=f"del_{conv['id']}", help="Supprimer"):
                    delete_conversation(conv["id"])
                    remaining = load_all_conversations()
                    if remaining:
                        st.session_state.active_conversation_id = remaining[0]["id"]
                        st.session_state.messages               = remaining[0]["messages"]
                        st.session_state.chat_history           = remaining[0]["chat_history"]
                    else:
                        nc = create_new_conversation()
                        st.session_state.active_conversation_id = nc["id"]
                        st.session_state.messages               = nc["messages"]
                        st.session_state.chat_history           = nc["chat_history"]
                    st.rerun()

    st.divider()
    st.markdown(
        '<p style="font-size:.69rem;color:#b0c4d0;line-height:1.7;'
        'margin:.1rem .1rem 0;font-family:Inter,sans-serif">'
        '<br>© 2025 NovaTech Solutions</p>',
        unsafe_allow_html=True,
    )


# ── PAGE HEADER ───────────────────────────────────────────────────────────────

st.html("""
<div style="
    display:flex;align-items:center;gap:.9rem;
    padding:1rem 0 1.15rem;
    border-bottom:1.5px solid #deeeed;
    margin-bottom:1.3rem;
    font-family:'Inter',sans-serif;
">
    <div style="
        width:46px;height:46px;
        background:linear-gradient(135deg,#20E8AC,#0fc48e);
        border-radius:15px;
        display:flex;align-items:center;justify-content:center;
        font-size:1.45rem;
        box-shadow:0 6px 22px rgba(32,232,172,.32);
        flex-shrink:0;
    ">✦</div>
    <div>
        <h1 style="margin:0;font-size:1.3rem;font-weight:700;
                   color:#0d1b2a;line-height:1.2">Nova</h1>
        <p style="margin:0;font-size:.76rem;color:#8fa3b1">
            Assistant RH &middot; NovaTech Solutions
        </p>
    </div>
</div>
""")


# ── EMPTY STATE ───────────────────────────────────────────────────────────────

if not st.session_state.messages:
    st.html("""
    <div style="text-align:center;padding:2.5rem 1rem 1.5rem;font-family:'Inter',sans-serif">
        <div style="
            width:64px;height:64px;
            background:linear-gradient(135deg,#20E8AC,#0fc48e);
            border-radius:20px;
            display:inline-flex;align-items:center;justify-content:center;
            font-size:1.8rem;
            box-shadow:0 8px 28px rgba(32,232,172,.28);
            margin-bottom:1.1rem;
        ">✦</div>
        <h2 style="font-size:1.1rem;font-weight:700;color:#0d1b2a;margin:0 0 .5rem">
            Hello, I’m Nova &#x1F44B;
        </h2>
        <p style="font-size:.86rem;color:#8fa3b1;max-width:400px;
                  margin:0 auto 2rem;line-height:1.7">
            Your HR assistant for NovaTech Solutions. Ask your questions about
            leave, remote work, expense reports, training, and more.
        </p>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:.6rem;
                    max-width:460px;margin:0 auto">
            <div style="background:#f6fdfb;border:1.5px solid #deeeed;border-radius:13px;
                        padding:.8rem 1rem;text-align:left">
                <div style="font-size:1.05rem;margin-bottom:.3rem">&#x1F3D6;&#xFE0F;</div>
                <div style="font-size:.82rem;font-weight:600;color:#0d1b2a">Paid Leave</div>
                <div style="font-size:.74rem;color:#8fa3b1;margin-top:.15rem">
                    Rights, balances, procedures
                </div>
            </div>
            <div style="background:#f6fdfb;border:1.5px solid #deeeed;border-radius:13px;
                        padding:.8rem 1rem;text-align:left">
                <div style="font-size:1.05rem;margin-bottom:.3rem">&#x1F3E0;</div>
                <div style="font-size:.82rem;font-weight:600;color:#0d1b2a">Remote Work</div>
                <div style="font-size:.74rem;color:#8fa3b1;margin-top:.15rem">
                    Policy &amp; Forms
                </div>
            </div>
            <div style="background:#f6fdfb;border:1.5px solid #deeeed;border-radius:13px;
                        padding:.8rem 1rem;text-align:left">
                <div style="font-size:1.05rem;margin-bottom:.3rem">&#x1F393;</div>
                <div style="font-size:.82rem;font-weight:600;color:#0d1b2a">Training / CPF</div>
                <div style="font-size:.74rem;color:#8fa3b1;margin-top:.15rem">
                    Access &amp; Requests
                </div>
            </div>
            <div style="background:#f6fdfb;border:1.5px solid #deeeed;border-radius:13px;
                        padding:.8rem 1rem;text-align:left">
                <div style="font-size:1.05rem;margin-bottom:.3rem">&#x1F4B0;</div>
                <div style="font-size:.82rem;font-weight:600;color:#0d1b2a">Expense Reports</div>
                <div style="font-size:.74rem;color:#8fa3b1;margin-top:.15rem">
                    Submission &amp; Reimbursement
                </div>
            </div>
        </div>
    </div>
    """)


# ── CHAT HISTORY DISPLAY ──────────────────────────────────────────────────────

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            if "sources" in msg and SHOW_SOURCES and msg["sources"]:
                with st.expander("📄 Sources consulted"):
                    for s in msg["sources"]:
                        icon = "🏛️" if s["source"] == "gouv" else "🏢"
                        st.caption(f"{icon} **{s['document']}** — distance : {s['distance']:.3f}")

            if "tools" in msg:
                for tool in msg["tools"]:
                    render_tool(tool)


# ── USER INPUT ────────────────────────────────────────────────────────────────

if prompt := st.chat_input("Ask your HR question…"):

    # append & display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # generate response
    with st.chat_message("assistant"):
        with st.spinner("Nova réfléchit…"):
            result = rag.answer(
                question=prompt,
                chat_history=st.session_state.chat_history,
                top_k=TOP_K,
                distance_threshold=DISTANCE_THRESHOLD,
                use_reranking=USE_RERANKING,
            )

        answer     = result["answer"]
        sources    = result["sources"]
        chunks     = result["chunks"]
        tools_used = result.get("agent_results", {}).get("action", {}).get("tools", [])

        st.markdown(answer)

        if SHOW_SOURCES and sources:
            with st.expander("📄 Sources consulted"):
                for s in sources:
                    icon = "🏛️" if s["source"] == "gouv" else "🏢"
                    st.caption(f"{icon} **{s['document']}** — distance : {s['distance']:.3f}")

        for tool in tools_used:
            render_tool(tool)

        if SHOW_CHUNKS and chunks:
            with st.expander("🔍 Chunks récupérés (debug)"):
                for i, c in enumerate(chunks):
                    score = f", score:{c.get('rerank_score','N/A')}" if "rerank_score" in c else ""
                    st.text(
                        f"— Chunk {i+1} "
                        f"(dist:{c['distance']:.3f}{score}) "
                        f"[{c['metadata']['document']}]"
                    )
                    st.text(c["text"][:500])
                    st.divider()

    # persist to session state
    st.session_state.messages.append({
        "role":    "assistant",
        "content": answer,
        "sources": sources,
        "tools":   tools_used,
    })

    st.session_state.chat_history.append({"role": "user",      "content": prompt})
    st.session_state.chat_history.append({"role": "assistant", "content": answer})

    if len(st.session_state.chat_history) > 20:
        st.session_state.chat_history = st.session_state.chat_history[-20:]

    save_conversation(
        st.session_state.active_conversation_id,
        st.session_state.messages,
        st.session_state.chat_history,
    )
