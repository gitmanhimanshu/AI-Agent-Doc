"""Streamlit UI for the Document Generator."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="Document Generator",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif; }
.main .block-container { max-width: 1100px; padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)

from app.config import settings


with st.sidebar:
    st.title("📄 Document Generator")
    st.caption("Smart document creation tool")
    st.divider()

    st.subheader("🗺️ Processing Pipeline")
    st.code(
        "  START\n"
        "    │\n"
        "    ▼\n"
        " Validate\n"
        "    │\n"
        "    ▼\n"
        "   Plan\n"
        "    │\n"
        "    ▼\n"
        "  Execute\n"
        "    │\n"
        "    ▼\n"
        "  Render\n"
        "    │\n"
        "    ▼\n"
        "  Respond\n"
        "    │\n"
        "    ▼\n"
        "   END",
        language=None,
    )

    st.divider()
    st.caption("© 2026 Document Generator")



st.title("📄 Document Generator")
st.caption("Describe any business document and get a professionally formatted Word file in seconds")
st.divider()


tab_generate, tab_documents = st.tabs(["🚀 Generate Document", "📂 My Documents"])


# --- Tab 1: Generate Document ---
with tab_generate:

    user_request = st.text_area(
        "📝 What document would you like?",
        placeholder="e.g. Create a project plan for launching a food-ordering app with a timeline, team roles, milestones, and a budget.",
        height=100,
    )

    col_btn, col_ex1, col_ex2 = st.columns([1, 1, 1])
    with col_btn:
        run_clicked = st.button("🚀 Generate", width="stretch", type="primary")
    with col_ex1:
        if st.button("📋 Example: Project Plan", width="stretch"):
            st.session_state["prefill"] = (
                "Create a project plan for launching a company mobile app for online food "
                "ordering. Include a timeline, team roles, milestones, and a budget."
            )
            st.rerun()
    with col_ex2:
        if st.button("📊 Example: Strategy Brief", width="stretch"):
            st.session_state["prefill"] = (
                "We need some kind of document for the leadership offsite next month about "
                "our AI strategy. It should be a quick executive brief but also cover the "
                "technical roadmap in detail, mention budget (we don't have exact numbers "
                "yet), and it must fit on one page but be comprehensive. Figure out the "
                "best structure yourself."
            )
            st.rerun()

    if "prefill" in st.session_state:
        user_request = st.session_state.pop("prefill")

    st.divider()


    if run_clicked and user_request and user_request.strip():

        from app.agent import DocumentAgent
        from app.guardrails import GuardrailError
        from app.llm import LLMError

        agent = DocumentAgent()
        total_start = time.time()

        progress_bar = st.progress(0, text="Starting pipeline...")
        step_names = ["validate", "plan", "execute", "render", "respond"]
        step_labels = {
            "validate": "🛡️ Step 1/5 — Validating input...",
            "plan":     "🧠 Step 2/5 — Planning document structure...",
            "execute":  "⚙️ Step 3/5 — Writing sections...",
            "render":   "📄 Step 4/5 — Rendering document...",
            "respond":  "✅ Step 5/5 — Finalizing...",
        }

        step_results = {}

        async def stream_agent():
            async for event in agent._graph.astream({"request": user_request}):
                for node_name, node_output in event.items():
                    step_results[node_name] = node_output
                    idx = step_names.index(node_name) if node_name in step_names else 0
                    progress_bar.progress(
                        (idx + 1) / len(step_names),
                        text=step_labels.get(node_name, "Processing..."),
                    )

        pipeline_error: str | None = None
        try:
            asyncio.run(stream_agent())
        except GuardrailError as exc:
            pipeline_error = f"⚠️ Invalid request — {exc}"
        except LLMError as exc:
            pipeline_error = f"🤖 The AI service is unavailable right now — {exc}"
        except Exception as exc:  # noqa: BLE001 — surface any error cleanly in the UI
            pipeline_error = f"❌ Something went wrong — {exc}"

        if pipeline_error:
            progress_bar.empty()
            st.error(pipeline_error)
            st.info(
                "💡 Tip: Enter a clear request of at least a few words — for example, "
                "*'Create a project plan for a mobile app launch with timeline and budget.'*"
            )
            st.stop()

        total_time = round(time.time() - total_start, 2)
        progress_bar.progress(1.0, text=f"✅ Complete in {total_time}s")



        # STEP 1 — Validate
        if "validate" in step_results:
            with st.expander("🛡️ Step 1 — Input Validation", expanded=True):
                data = step_results["validate"]
                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Request Length", f"{len(user_request)} chars")
                with c2:
                    st.metric("Status", "✅ Passed")
                st.info(f"**Processed request:** {data.get('clean_request', user_request)}")

        # STEP 2 — Plan
        if "plan" in step_results:
            with st.expander("🧠 Step 2 — Document Planning", expanded=True):
                data = step_results["plan"]
                plan = data["plan"]
                task_list = data["task_list"]

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Document Type", plan.document_type)
                with c2:
                    st.metric("Sections", len(plan.sections))
                with c3:
                    st.metric("Audience", plan.audience[:25])

                st.success(f"**Title:** {plan.title}")
                st.write(f"**Objective:** {plan.objective}")

                if plan.assumptions:
                    st.warning("**Assumptions (where info was missing):**")
                    for a in plan.assumptions:
                        st.write(f"- {a}")

                st.subheader("📋 Task List")
                for task in task_list:
                    st.write(f"- {task}")

        # STEP 3 — Execute
        if "execute" in step_results:
            with st.expander("⚙️ Step 3 — Content Generation", expanded=True):
                data = step_results["execute"]
                sections = data["sections"]
                warnings = data.get("warnings", [])

                ok_count = sum(1 for s in sections if s.status == "ok")
                deg_count = sum(1 for s in sections if s.status == "degraded")

                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("Total Sections", len(sections))
                with c2:
                    st.metric("Successful", ok_count)
                with c3:
                    st.metric("Needs Review", deg_count)

                for sec in sections:
                    status_icon = "✅" if sec.status == "ok" else "⚠️"
                    with st.container(border=True):
                        st.subheader(f"{status_icon} {sec.heading}")
                        for block in sec.blocks:
                            if block.type == "paragraph":
                                st.write(block.text)
                            elif block.type == "bullets":
                                for item in block.items:
                                    st.write(f"- {item}")
                            elif block.type == "table":
                                if block.rows:
                                    import pandas as pd
                                    cols = block.headers[:len(block.rows[0])] if block.headers else None
                                    df = pd.DataFrame(block.rows, columns=cols)
                                    st.dataframe(df, use_container_width=True)

                if warnings:
                    st.warning("**Warnings:**")
                    for w in warnings:
                        st.write(f"⚠️ {w}")

        # STEP 4 — Render
        if "render" in step_results:
            with st.expander("📄 Step 4 — Document Rendering", expanded=True):
                data = step_results["render"]
                filename = data["document_filename"]

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Format", "Word (.docx)")
                with c2:
                    st.metric("Filename", filename[:40])

                st.info("Document styled with cover page, professional headings, formatted tables, and footer.")

        # STEP 5 — Respond
        if "respond" in step_results:
            with st.expander("✅ Step 5 — Final Result", expanded=True):
                data = step_results["respond"]

                c1, c2 = st.columns(2)
                with c1:
                    st.metric("Status", data.get("status", "success"))
                with c2:
                    st.metric("Total Time", f"{total_time}s")

                st.success(data.get("message", ""))


        if "render" in step_results:
            filename = step_results["render"]["document_filename"]
            doc_path = settings.output_dir / filename
            if doc_path.exists():
                st.divider()
                st.subheader("🎉 Document Ready!")
                with open(doc_path, "rb") as f:
                    st.download_button(
                        label=f"📥 Download {filename}",
                        data=f.read(),
                        file_name=filename,
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        width="stretch",
                        type="primary",
                    )

    elif run_clicked:
        st.warning("Please enter a document request first.")


# --- Tab 2: My Documents ---
with tab_documents:
    st.subheader("📂 My Documents")
    st.caption("All your generated documents in one place.")

    docs_dir = Path(settings.output_dir)
    docs_dir.mkdir(parents=True, exist_ok=True)
    doc_files = sorted(docs_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not doc_files:
        st.info("No documents yet. Go to **Generate Document** to create your first one!")
    else:
        st.write(f"**{len(doc_files)} document(s) found**")
        st.divider()

        for doc_path in doc_files:
            stat = doc_path.stat()
            size_kb = round(stat.st_size / 1024, 1)
            mod_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime))

            with st.container(border=True):
                col_info, col_dl = st.columns([3, 1])

                with col_info:
                    st.markdown(f"**📄 {doc_path.name}**")
                    st.caption(f"Size: {size_kb} KB  ·  Created: {mod_time}")

                with col_dl:
                    with open(doc_path, "rb") as f:
                        st.download_button(
                            label="📥 Download",
                            data=f.read(),
                            file_name=doc_path.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            width="stretch",
                            key=f"dl_{doc_path.name}",
                        )
