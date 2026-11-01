"""
Scholarship Intelligence Dashboard.
A Streamlit web application providing metrics, search, evidence inspection,
confidence breakdown, and change history audit trails.
"""
import json
from datetime import datetime
import pandas as pd
import streamlit as st

from database.repository import ScholarshipRepository
from crawler.pipeline import ScholarshipCrawlerPipeline

st.set_page_config(
    page_title="Scholarship Intelligence Platform",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for executive dashboard aesthetic
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        font-size: 1.0rem;
        color: #64748B;
        margin-bottom: 1.5rem;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 16px;
        text-align: center;
    }
    .badge-verified {
        background-color: #DCFCE7;
        color: #166534;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-review {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-active {
        background-color: #E0E7FF;
        color: #3730A3;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-expired {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .evidence-box {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 12px 16px;
        border-radius: 4px;
        font-family: monospace;
        font-size: 0.9rem;
        margin: 8px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_repository():
    return ScholarshipRepository()


repo = get_repository()

# Sidebar: Controls, Filters & Actions
st.sidebar.title("Crawler Controls")

# Manual Crawl Action
if st.sidebar.button("Run Crawler Now", type="primary", use_container_width=True):
    with st.spinner("Executing live crawler pipeline (Discovery -> Fetching -> Extraction -> Verification)..."):
        pipeline = ScholarshipCrawlerPipeline(repo)
        results = pipeline.run_crawler(use_search=False, verbose=False)
        st.sidebar.success(f"Crawl Completed! Discovered: {results['discovered_total']}, Verified: {results['verified_count']}")
        st.rerun()

# Run Replay Test Mode Action
if st.sidebar.button("Run Replay Test Mode (2+ Changes)", use_container_width=True):
    with st.spinner("Replaying controlled test fixtures (scheme_change_v1 vs v2)..."):
        pipeline = ScholarshipCrawlerPipeline(repo)
        ch_res = pipeline.replay_change_test(verbose=False)
        st.sidebar.success(f"Replay Test Completed! {ch_res['changes_detected']} changes recorded to history.")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("Search & Filters")

search_query = st.sidebar.text_input("Search scholarships or keywords", placeholder="e.g. Pragati, IIT, Reliance")

provider_type = st.sidebar.selectbox(
    "Provider Type",
    ["ALL", "GOVERNMENT", "UNIVERSITY", "CORPORATE_CSR", "NGO_TRUST", "AGGREGATOR"],
    index=0,
)

verification_filter = st.sidebar.selectbox(
    "Verification Status",
    ["ALL", "VERIFIED", "REVIEW_REQUIRED"],
    index=0,
)

lifecycle_filter = st.sidebar.selectbox(
    "Lifecycle Status",
    ["ALL", "ACTIVE", "EXPIRING_SOON", "EXPIRED", "REVIEW_REQUIRED"],
    index=0,
)

min_confidence = st.sidebar.slider(
    "Minimum Confidence Score (%)",
    min_value=0.0,
    max_value=100.0,
    value=0.0,
    step=5.0,
)

sort_by = st.sidebar.selectbox(
    "Sort By",
    [
        ("Highest Confidence", "confidence_desc"),
        ("Upcoming Deadlines", "deadline_asc"),
        ("Alphabetical Name", "name_asc"),
    ],
    format_func=lambda x: x[0],
)[1]

# Header & Navigation Tabs
st.markdown('<div class="main-title">Scholarship Intelligence Engine</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">EDXSO AI Evaluation Platform · Automated Primary Source Verification</div>', unsafe_allow_html=True)

metrics = repo.get_metrics()

# Top KPI Summary Cards
col1, col2, col3, col4, col5, col6 = st.columns(6)
with col1:
    st.metric("Total Discovered", f"{metrics['total_discovered']}", help="Requirement: 20+")
with col2:
    st.metric("Officially Verified", f"{metrics['verified_count']}", help="Requirement: 15+")
with col3:
    st.metric("Confidence >= 95%", f"{metrics['above_95_count']}", help="Requirement: 10+")
with col4:
    st.metric("Active Schemes", f"{metrics['active_count']}")
with col5:
    st.metric("Expired Schemes", f"{metrics['expired_count']}", help="Requirement: 2+")
with col6:
    st.metric("Detected Changes", f"{metrics['total_changes']}", help="Requirement: 2+")

st.markdown("---")

tab1, tab2, tab3 = st.tabs(["Scholarship Directory", "Scholarship Detail & Audit View", "Detected Changes & History"])

# ----------------- TAB 1: DIRECTORY -----------------
with tab1:
    scholarships = repo.get_all_scholarships(
        search_query=search_query if search_query else None,
        provider_type=provider_type,
        verification_status=verification_filter,
        lifecycle_status=lifecycle_filter,
        min_confidence=min_confidence if min_confidence > 0 else None,
        sort_by=sort_by,
    )

    st.subheader(f"Discovered Schemes ({len(scholarships)} records matching criteria)")

    if not scholarships:
        st.info("No scholarships match the selected filters.")
    else:
        table_data = []
        for s in scholarships:
            table_data.append({
                "ID": s["id"],
                "Scholarship Name": s["name"],
                "Provider": s["provider"],
                "Type": s["provider_type"],
                "Benefit": s["benefit"] or "As per scheme rules",
                "Deadline": s["deadline"] or "Not specified",
                "Confidence": f"{s['confidence_score']:.1f}%",
                "Verification": s["verification_status"],
                "Lifecycle": s["lifecycle_status"],
            })

        df = pd.DataFrame(table_data)
        st.dataframe(
            df,
            column_config={
                "Confidence": st.column_config.ProgressColumn(
                    "Confidence",
                    format="%.1f%%",
                    min_value=0,
                    max_value=100,
                ),
                "ID": st.column_config.NumberColumn("ID", width="small"),
            },
            hide_index=True,
            use_container_width=True,
        )

# ----------------- TAB 2: SCHOLARSHIP DETAIL VIEW -----------------
with tab2:
    st.subheader("Deep-Dive Inspection & Evidence Audit")
    all_schs = repo.get_all_scholarships(sort_by="confidence_desc")
    
    if not all_schs:
        st.info("No scholarships available in database. Run the crawler to populate.")
    else:
        sch_options = {s["id"]: f"#{s['id']} - {s['name']} ({s['provider']})" for s in all_schs}
        selected_id = st.selectbox(
            "Select Scholarship to Inspect:",
            options=list(sch_options.keys()),
            format_func=lambda x: sch_options[x],
        )

        selected_sch = repo.get_scholarship_by_id(selected_id)
        evidence_list = repo.get_evidence_for_scholarship(selected_id)
        change_list = repo.get_changes_for_scholarship(selected_id)

        # Overview Header
        col_hdr1, col_hdr2 = st.columns([3, 1])
        with col_hdr1:
            st.markdown(f"### {selected_sch['name']}")
            st.markdown(f"**Provider:** {selected_sch['provider']} | **Category:** `{selected_sch['provider_type']}`")
            st.markdown(f"**Official Source:** [{selected_sch['official_source_url']}]({selected_sch['official_source_url']})")
            if selected_sch.get("application_url"):
                st.markdown(f"**Application URL:** [{selected_sch['application_url']}]({selected_sch['application_url']})")
        with col_hdr2:
            v_badge = "badge-verified" if selected_sch["verification_status"] == "VERIFIED" else "badge-review"
            l_badge = "badge-expired" if selected_sch["lifecycle_status"] == "EXPIRED" else "badge-active"
            st.markdown(
                f"""
                <div style="text-align: right; margin-top: 10px;">
                    <span class="{v_badge}">{selected_sch['verification_status']}</span><br><br>
                    <span class="{l_badge}">{selected_sch['lifecycle_status']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("---")

        # Key Information Cards
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown("**Financial Benefit:**")
            st.info(selected_sch["benefit"] or "Explicitly unspecified in summary")
        with c2:
            st.markdown("**Application Deadline:**")
            st.warning(selected_sch["deadline"] or "Explicitly unspecified")
        with c3:
            st.markdown("**Opening Date:**")
            st.text(selected_sch["opening_date"] or "Not specified")
        with c4:
            st.markdown("**Income Ceiling:**")
            if selected_sch.get("income_limit_inr"):
                st.text(f"INR {selected_sch['income_limit_inr']:,}")
            else:
                st.text("Not specified")

        # Criteria Details
        st.markdown("#### Eligibility & Academic Criteria")
        ecol1, ecol2 = st.columns(2)
        with ecol1:
            st.markdown(f"**Eligibility Details:** {selected_sch['eligibility'] or 'Not specified'}")
            st.markdown(f"**Academic Requirements:** {selected_sch['academic_requirements'] or 'Not specified'}")
            st.markdown(f"**Selection Procedure:** {selected_sch['selection_process'] or 'Standard merit verification'}")
        with ecol2:
            st.markdown(f"**Target Gender:** {selected_sch['gender_criteria'] or 'All eligible students'}")
            st.markdown(f"**Target Category:** {selected_sch['category_criteria'] or 'All categories'}")
            edu_json = selected_sch.get("education_levels")
            try:
                edu_list = json.loads(edu_json) if edu_json else []
            except Exception:
                edu_list = []
            st.markdown(f"**Education Level(s):** {', '.join(edu_list) if edu_list else 'Higher Education'}")

        st.markdown("---")

        # Mathematical Confidence Scoring Breakdown
        st.markdown("#### Mathematical Confidence Score Breakdown (100-Point Formula)")
        score_val = selected_sch["confidence_score"]
        st.progress(score_val / 100.0, text=f"Total Confidence Score: {score_val:.1f} / 100.0")

        # Parse score breakdown
        sb_raw = selected_sch.get("score_breakdown")
        if sb_raw:
            try:
                sb = json.loads(sb_raw) if isinstance(sb_raw, str) else sb_raw
                sb_rows = []
                for comp, details in sb.items():
                    if isinstance(details, dict):
                        sb_rows.append({
                            "Component": comp.replace("_", " ").title(),
                            "Awarded Points": f"{details.get('score', 0):.1f} / {details.get('max', '')}",
                            "Reason / Verification Logic": details.get("reason", ""),
                        })
                st.table(pd.DataFrame(sb_rows))
            except Exception as e:
                st.text(f"Raw breakdown: {sb_raw}")

        st.markdown("---")

        # Field-Level Traceable Evidence Audit Trail
        st.markdown("#### Field-Level Source Evidence Audit Trail")
        st.caption("Every claim extracted by the crawler is linked to an exact quotation and content snapshot.")

        if not evidence_list:
            st.warning("No field-level evidence records attached to this scholarship.")
        else:
            for ev in evidence_list:
                with st.expander(f"Field: {ev['field_name'].upper()} — Extracted Value: {ev['extracted_value'] or 'Present'}"):
                    st.markdown("**Primary Source URL:**")
                    st.write(ev["source_url"])
                    st.markdown("**Exact Supporting Quotation from Source:**")
                    st.markdown(f'<div class="evidence-box">"{ev["evidence_text"]}"</div>', unsafe_allow_html=True)
                    st.markdown(f"**Extraction Method:** `{ev['extraction_method']}` | **Captured Timestamp (UTC):** `{ev['fetched_at']}`")
                    if ev.get("snapshot_path"):
                        st.caption(f"Archived Snapshot Path: `{ev['snapshot_path']}`")
                    if ev.get("content_hash"):
                        st.caption(f"Content SHA-256 Fingerprint: `{ev['content_hash']}`")

        # Change History for this scholarship
        if change_list:
            st.markdown("---")
            st.markdown("#### Mutation History for this Scholarship")
            ch_data = []
            for ch in change_list:
                ch_data.append({
                    "Field": ch["field_name"],
                    "Old Value": ch["old_value"],
                    "New Value": ch["new_value"],
                    "Detected At (UTC)": ch["detected_at"],
                    "Source URL": ch.get("source_url"),
                })
            st.dataframe(pd.DataFrame(ch_data), use_container_width=True)

# ----------------- TAB 3: CHANGE DETECTION & HISTORY -----------------
with tab3:
    st.subheader("Detected Field Mutations & Crawl Run History")
    st.caption("Shows field-level differences detected across crawler runs (including test replay fixtures).")

    all_changes = repo.get_all_changes(limit=100)
    if not all_changes:
        st.info("No field mutations detected yet. Click 'Run Replay Test Mode' in the sidebar to simulate versioned snapshot changes.")
    else:
        st.write(f"Total changes recorded: **{len(all_changes)}**")
        changes_df_data = []
        for ch in all_changes:
            changes_df_data.append({
                "Scholarship": ch["scholarship_name"],
                "Provider": ch.get("scholarship_provider", ""),
                "Field Changed": ch["field_name"],
                "Previous Value": ch["old_value"],
                "Updated Value": ch["new_value"],
                "Detected Timestamp": ch["detected_at"],
            })
        st.dataframe(pd.DataFrame(changes_df_data), use_container_width=True)

    st.markdown("---")
    st.subheader("Crawl Execution History")
    with repo._get_conn() as conn:
        runs = conn.execute("SELECT * FROM crawl_runs ORDER BY id DESC LIMIT 10").fetchall()
        if runs:
            runs_data = [dict(r) for r in runs]
            st.dataframe(pd.DataFrame(runs_data), use_container_width=True)
