"""
Student Opportunity Agent - Streamlit Application
A personalized opportunity discovery and agentic recommendation engine for college students.
"""

import html
import os
import re
from datetime import date
import streamlit as st

from engine.matcher import evaluate_opportunities, CLOSING_SOON_DAYS
from engine.agent import generate_llm_agent_insight, generate_offline_agent_insight
from engine.sources import get_opportunity_repository

esc = html.escape  # every value interpolated into unsafe_allow_html markup goes through this

# Page setup
st.set_page_config(
    page_title="Student Opportunity Agent",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E88E5, #7E57C2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 16px;
        border: 1px solid #e9ecef;
        text-align: center;
    }
    .badge-eligible {
        background-color: #d4edda;
        color: #155724;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-ineligible {
        background-color: #f8d7da;
        color: #721c24;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-urgent {
        background-color: #ffeeba;
        color: #856404;
        padding: 4px 10px;
        border-radius: 12px;
        font-weight: 600;
        font-size: 0.82rem;
        display: inline-block;
    }
    .badge-type {
        background-color: #e2e3e5;
        color: #383d41;
        padding: 4px 8px;
        border-radius: 8px;
        font-size: 0.8rem;
        display: inline-block;
    }
    .skill-tag {
        background-color: #e3f2fd;
        color: #0d47a1;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-right: 4px;
        display: inline-block;
        margin-bottom: 4px;
    }
    .missing-tag {
        background-color: #fff3e0;
        color: #e65100;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 0.78rem;
        margin-right: 4px;
        display: inline-block;
        margin-bottom: 4px;
    }
    .opportunity-card {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        background-color: #ffffff;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .score-circle {
        font-size: 1.5rem;
        font-weight: 800;
        color: #1e88e5;
    }
</style>
""", unsafe_allow_html=True)

# Modular Source Layer: Queries live feeds with automatic local JSON fallback
@st.cache_data(ttl=120)
def load_opportunities_from_repository():
    repo = get_opportunity_repository()
    items, status = repo.get_opportunities()
    return items, status

raw_opportunities, source_status = load_opportunities_from_repository()


@st.cache_data(show_spinner=False, ttl=3600, max_entries=256)
def cached_agent_insight(student, opportunity, use_llm, _api_key):
    """Agent output cached per (profile, opportunity, mode): no repeat LLM calls on every rerun.
    `_api_key` has a leading underscore so Streamlit does not hash/store it in the cache key."""
    if use_llm:
        return generate_llm_agent_insight(student, opportunity, _api_key)
    return generate_offline_agent_insight(student, opportunity)


def stipend_value(text):
    """Best-effort numeric part of a stipend/prize string (handles Indian 1,25,000 grouping)."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", str(text or "").replace("\u20b9", " "))
    try:
        return float(m.group(0).replace(",", "")) if m else 0.0
    except ValueError:
        return 0.0

# Default Persona Profiles for quick Hackathon Demos
DEMO_PERSONAS = {
    "Custom Profile": None,
    "🚀 3rd Year SDE Intern Candidate (Google / Microsoft)": {
        "name": "Aarav Sharma",
        "degree": "B.Tech",
        "branch": "Computer Science",
        "year": "3rd Year",
        "cgpa": 8.6,
        "skills": ["Python", "C++", "Data Structures", "Algorithms", "Git", "SQL"],
        "interests": ["Software Engineering", "Competitive Programming", "Cloud"],
        "preferred_types": ["Internship", "Coding Competition"],
        "preferred_mode": "Hybrid"
    },
    "💡 2nd Year Web & Hackathon Builder": {
        "name": "Priya Patel",
        "degree": "B.Tech",
        "branch": "Information Technology",
        "year": "2nd Year",
        "cgpa": 8.1,
        "skills": ["JavaScript", "React", "Python", "Full Stack Development", "Git", "GitHub"],
        "interests": ["Web Development", "Web3", "Social Impact"],
        "preferred_types": ["Hackathon", "Fellowship"],
        "preferred_mode": "Any"
    },
    "🤖 4th Year AI/ML Researcher": {
        "name": "Rohan Gupta",
        "degree": "B.Tech",
        "branch": "Computer Science",
        "year": "4th Year",
        "cgpa": 7.8,
        "skills": ["Python", "Machine Learning", "Linear Algebra", "Probability & Statistics", "PyTorch"],
        "interests": ["AI/ML", "Data Science", "Research"],
        "preferred_types": ["Internship", "Fellowship"],
        "preferred_mode": "Remote"
    },
    "🌟 2nd Year Scholarship & Open Source Aspirant": {
        "name": "Sneha Kulkarni",
        "degree": "B.Tech",
        "branch": "Electronics & Communication",
        "year": "2nd Year",
        "cgpa": 8.9,
        "skills": ["C++", "Python", "Git", "GitHub", "Problem Solving", "Communication"],
        "interests": ["Leadership", "Diversity in Tech", "Academics", "Open Source"],
        "preferred_types": ["Scholarship", "Fellowship"],
        "preferred_mode": "Any"
    }
}

# ----------------- SIDEBAR: STUDENT PROFILE -----------------
with st.sidebar:
    st.title("Student Profile")
    st.caption("Configure your profile or load a preset persona.")

    persona_choice = st.selectbox(
        "⚡ Quick Demo Persona (Hackathon Presets):",
        options=list(DEMO_PERSONAS.keys()),
        index=1  # Default to 3rd Year SDE Intern Candidate
    )

    preset = DEMO_PERSONAS[persona_choice]

    with st.form("profile_form"):
        name = st.text_input("Full Name", value=preset["name"] if preset else "Student Candidate")
        
        col_deg, col_yr = st.columns(2)
        with col_deg:
            degree = st.selectbox(
                "Degree",
                options=["B.Tech", "B.E.", "BCA", "MCA", "M.Tech", "B.Sc"],
                index=["B.Tech", "B.E.", "BCA", "MCA", "M.Tech", "B.Sc"].index(preset["degree"]) if preset else 0
            )
        with col_yr:
            year = st.selectbox(
                "Current Year",
                options=["1st Year", "2nd Year", "3rd Year", "4th Year"],
                index=["1st Year", "2nd Year", "3rd Year", "4th Year"].index(preset["year"]) if preset else 2
            )

        branch = st.selectbox(
            "Branch / Major",
            options=[
                "Computer Science",
                "Information Technology",
                "Electronics & Communication",
                "Electrical Engineering",
                "Mechanical Engineering",
                "Other"
            ],
            index=["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Other"].index(preset["branch"]) if preset and preset["branch"] in ["Computer Science", "Information Technology", "Electronics & Communication", "Electrical Engineering", "Mechanical Engineering", "Other"] else 0
        )

        cgpa = st.slider("CGPA (Scale 10.0)", min_value=5.0, max_value=10.0, value=float(preset["cgpa"]) if preset else 8.2, step=0.1)

        # Standard technical skills
        available_skills = [
            "Python", "C++", "Java", "Data Structures", "Algorithms",
            "JavaScript", "React", "Full Stack Development", "Git", "GitHub",
            "SQL", "Machine Learning", "PyTorch", "Docker", "Solidity",
            "Web3", "Flutter", "Linear Algebra", "Probability & Statistics",
            "Problem Solving", "Communication", "System Design"
        ]
        
        default_skills = preset["skills"] if preset else ["Python", "Data Structures", "Algorithms", "Git"]
        # Ensure default skills exist in options
        for s in default_skills:
            if s not in available_skills:
                available_skills.append(s)

        selected_skills = st.multiselect(
            "Skills & Proficiencies",
            options=available_skills,
            default=default_skills
        )

        extra_skills = st.text_input("Additional Custom Skills (comma-separated)", value="")
        if extra_skills.strip():
            custom_list = [s.strip() for s in extra_skills.split(",") if s.strip()]
            seen, merged = set(), []
            for sk in selected_skills + custom_list:      # ordered, case-insensitive de-dupe
                if sk.strip().lower() not in seen:
                    seen.add(sk.strip().lower())
                    merged.append(sk.strip())
            selected_skills = merged

        # Interests / Domains
        domain_options = [
            "Software Engineering", "Web Development", "AI/ML", "Data Science",
            "Web3", "Cloud", "Open Source", "Competitive Programming",
            "Leadership", "Diversity in Tech", "Mobile Development", "Academics",
            "Social Impact", "Research"
        ]
        default_interests = preset["interests"] if preset else ["Software Engineering", "AI/ML"]
        for i in default_interests:   # never crash if a preset uses an unlisted interest
            if i not in domain_options:
                domain_options.append(i)
        selected_interests = st.multiselect(
            "Career & Tech Interests",
            options=domain_options,
            default=default_interests
        )

        # Target Opportunity Types
        type_options = ["Internship", "Hackathon", "Coding Competition", "Scholarship", "Fellowship"]
        default_types = preset["preferred_types"] if preset else type_options
        preferred_types = st.multiselect(
            "Interested Opportunity Types",
            options=type_options,
            default=default_types
        )

        # Work Mode
        mode_options = ["Any", "Remote", "Hybrid", "In-Person"]
        default_mode = preset["preferred_mode"] if preset else "Any"
        preferred_mode = st.selectbox(
            "Preferred Work Mode",
            options=mode_options,
            index=mode_options.index(default_mode) if default_mode in mode_options else 0
        )

        save_btn = st.form_submit_button("⚡ Update & Re-rank Agent", use_container_width=True)

    # Optional Gemini API Key expander
    with st.expander("🔑 Agent LLM Settings (Optional)"):
        st.caption("The agent has an integrated deterministic reasoning engine that works 100% offline. Optionally enter a Gemini API Key to enable live LLM generation.")
        api_key_input = st.text_input("Gemini API Key", type="password", value=os.environ.get("GEMINI_API_KEY", ""))

    # Modular Data Source Layer Info
    with st.expander("📡 Data Sources & Fallback Status"):
        st.markdown(f"**Total Opportunities:** `{len(raw_opportunities)}`")
        st.markdown(f"**Loaded from:** `{', '.join(source_status.get('sources_succeeded', [])) or 'none'}`")
        st.markdown(f"**Fallback used:** `{'Yes' if source_status.get('fallback_used') else 'No'}`")
        for failed_name in source_status.get("sources_failed", []):
            st.warning(f"{failed_name}: {source_status.get('errors', {}).get(failed_name, 'failed')}")
        st.caption("🛡️ **Fault Tolerance:** If a live source fails, the system automatically falls back to local storage with zero downtime.")

# Student dictionary
name = (name or "").strip() or "Student Candidate"
student_profile = {
    "name": name,
    "degree": degree,
    "year": year,
    "branch": branch,
    "cgpa": cgpa,
    "skills": selected_skills,
    "interests": selected_interests,
    "preferred_types": preferred_types,
    "preferred_mode": preferred_mode
}

# ----------------- MAIN CONTENT & DASHBOARD -----------------

# Title banner
col_header, col_status = st.columns([3, 1])
with col_header:
    st.markdown('<div class="main-header">🎯 Student Opportunity Agent</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Autonomous opportunity matching, hard eligibility verification, and personalized agent roadmaps.</div>', unsafe_allow_html=True)
with col_status:
    st.markdown(f"""
    <div style="background-color: #f1f5f9; padding: 10px 14px; border-radius: 8px; border-left: 4px solid #1E88E5; margin-top: 10px; color: #0f172a;">
        <span style="font-size: 0.85rem; color: #475569;">Active Profile:</span><br/>
        <b>{esc(name)}</b> ({esc(year)} • {esc(branch)})
    </div>
    """, unsafe_allow_html=True)

# Run evaluation engine
reference_sim_date = date.today()
evaluated_opps = evaluate_opportunities(student_profile, raw_opportunities, reference_sim_date)

# Key Metrics Row
eligible_opps = [o for o in evaluated_opps if o["is_eligible"] and not o["is_expired"]]
urgent_opps = [o for o in eligible_opps if o["deadline_info"]["status"] == "Closing Soon"]
top_score = max([o["match_score"] for o in eligible_opps], default=0)

m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric("Total Opportunities", f"{len(evaluated_opps)} listed")
with m2:
    st.metric("Open & Eligible", f"{len(eligible_opps)} verified", delta=f"{int(len(eligible_opps)/max(1, len(evaluated_opps))*100)}% clearance")
with m3:
    st.metric("Top Relevance Score", f"{top_score} / 100", help="Best score among open opportunities you are eligible for")
with m4:
    st.metric(f"Closing Soon (\u2264{CLOSING_SOON_DAYS} Days)", f"{len(urgent_opps)} urgent")

st.divider()

# ----------------- FILTER & SEARCH BAR -----------------
f1, f2, f3, f4 = st.columns([2, 1.5, 1.5, 2])

with f1:
    search_query = st.text_input("🔍 Search opportunities, companies, skills...", placeholder="e.g. Google, Python, Hackathon")

with f2:
    filter_eligibility = st.selectbox(
        "Eligibility Filter",
        options=["Eligible Only (Recommended)", "Show All (Including Ineligible)", "Ineligible Only"]
    )
    hide_expired = st.checkbox("Hide expired", value=True)

with f3:
    filter_type = st.selectbox(
        "Opportunity Type",
        options=["All Types"] + sorted({o["type"] for o in evaluated_opps})
    )

with f4:
    sort_by = st.selectbox(
        "Sort By",
        options=["Match Score (Highest First)", "Deadline (Closing Soonest)", "Stipend / Prize (Highest)", "Alphabetical (A-Z)"]
    )

# Apply filters
filtered_opps = list(evaluated_opps)   # copy: sorting below must not mutate evaluated_opps

if hide_expired:
    filtered_opps = [o for o in filtered_opps if not o["is_expired"]]

if search_query.strip():
    q = search_query.strip().lower()
    filtered_opps = [
        o for o in filtered_opps
        if q in str(o.get("title") or "").lower()
        or q in str(o.get("organization") or "").lower()
        or q in str(o.get("description") or "").lower()
        or q in str(o.get("type") or "").lower()
        or any(q in str(s).lower() for s in (o.get("skills") or []))
        or any(q in str(t).lower() for t in (o.get("domain_tags") or []))
    ]

if filter_eligibility == "Eligible Only (Recommended)":
    filtered_opps = [o for o in filtered_opps if o["is_eligible"]]
elif filter_eligibility == "Ineligible Only":
    filtered_opps = [o for o in filtered_opps if not o["is_eligible"]]

if filter_type != "All Types":
    filtered_opps = [o for o in filtered_opps if o["type"] == filter_type]

# Sorting
if sort_by == "Match Score (Highest First)":
    filtered_opps.sort(key=lambda x: (1 if x["is_eligible"] else 0, x["match_score"]), reverse=True)
elif sort_by == "Deadline (Closing Soonest)":
    filtered_opps.sort(key=lambda x: (
        9999 if x["deadline_info"]["days_left"] is None or x["deadline_info"]["days_left"] < 0 else x["deadline_info"]["days_left"]
    ))
elif sort_by == "Stipend / Prize (Highest)":
    filtered_opps.sort(key=lambda x: stipend_value(x.get("stipend_or_prize")), reverse=True)
elif sort_by == "Alphabetical (A-Z)":
    filtered_opps.sort(key=lambda x: x["title"].lower())

st.caption(f"Showing **{len(filtered_opps)}** matching opportunities based on current criteria.")

# ----------------- MAIN LAYOUT: SPLIT VIEW -----------------
# Left Column: Opportunity Feed / List
# Right Column: Deep-Dive Opportunity Agent Inspector

left_col, right_col = st.columns([1.5, 1.3], gap="medium")

# Session state to track selected opportunity for agent analysis
if "selected_opp_id" not in st.session_state:
    if filtered_opps:
        st.session_state.selected_opp_id = filtered_opps[0]["id"]
    else:
        st.session_state.selected_opp_id = None

# Keep the inspector in sync with the feed: if the selected item was filtered out, select the first visible one
_visible_ids = [o["id"] for o in filtered_opps]
if st.session_state.selected_opp_id not in _visible_ids:
    st.session_state.selected_opp_id = _visible_ids[0] if _visible_ids else None

# Opportunity Cards on Left Column
with left_col:
    st.subheader("📋 Ranked Opportunity Feed")
    
    if not filtered_opps:
        st.info("No opportunities match your filter criteria. Try adjusting the filters or resetting search.")
    else:
        for opp in filtered_opps:
            opp_id = opp["id"]
            is_selected = (st.session_state.selected_opp_id == opp_id)
            
            with st.container():
                # Header row inside card
                c_head1, c_head2 = st.columns([3, 1])
                with c_head1:
                    st.markdown(f"**{opp['title']}**")
                    st.caption(f"🏢 **{opp['organization']}** • 📍 {opp['mode']} ({opp['location']})")
                with c_head2:
                    score_val = opp['match_score']
                    score_color = "#16a34a" if score_val >= 75 else ("#ca8a04" if score_val >= 55 else "#dc2626")
                    st.markdown(f"<div style='text-align: right;'><span style='font-size: 1.4rem; font-weight: 800; color: {score_color};'>{score_val}%</span><br/><span style='font-size: 0.75rem; color: #64748b;'>Match Score</span></div>", unsafe_allow_html=True)

                # Badges row
                b_col1, b_col2, b_col3 = st.columns([1.2, 1.2, 1.6])
                with b_col1:
                    if opp["is_eligible"]:
                        st.markdown('<span class="badge-eligible">✅ Eligible</span>', unsafe_allow_html=True)
                    else:
                        st.markdown('<span class="badge-ineligible">❌ Ineligible</span>', unsafe_allow_html=True)
                with b_col2:
                    st.markdown(f'<span class="badge-type">{esc(str(opp["type"]))}</span>', unsafe_allow_html=True)
                with b_col3:
                    d_info = opp["deadline_info"]
                    if d_info["status"] == "Closing Soon":
                        st.markdown(f'<span class="badge-urgent">{d_info["urgency_label"]}</span>', unsafe_allow_html=True)
                    elif d_info["status"] == "Expired":
                        st.markdown(f'<span class="badge-ineligible">{d_info["urgency_label"]}</span>', unsafe_allow_html=True)
                    else:
                        st.markdown(f'<span style="font-size: 0.8rem; color: #475569;">📅 {d_info["urgency_label"]}</span>', unsafe_allow_html=True)

                # Perks / Stipend
                st.markdown(f"💰 **Perks/Prize:** `{opp['stipend_or_prize']}`")

                # Skills match row
                matched_str = " ".join([f"<span class='skill-tag'>✓ {esc(str(s))}</span>" for s in opp["matched_skills"][:4]])
                missing_str = " ".join([f"<span class='missing-tag'>+ {esc(str(s))}</span>" for s in opp["missing_required"][:3]])
                st.markdown(f"<div style='margin-top: 6px;'>{matched_str}{missing_str}</div>", unsafe_allow_html=True)

                # Action button to select for agent deep-dive
                btn_label = "👉 Inspect with Agent" if not is_selected else "🔍 Currently Inspecting"
                if st.button(btn_label, key=f"inspect_{opp_id}", use_container_width=True):
                    st.session_state.selected_opp_id = opp_id
                    st.rerun()

                st.markdown("---")

# Right Column: Deep-Dive Agent Inspector
with right_col:
    st.subheader("🤖 Opportunity Agent Deep-Dive")

    # Active opportunity (already evaluated, always one of the visible feed items)
    evaluated_selected = next((o for o in filtered_opps if o["id"] == st.session_state.selected_opp_id), None)

    if not evaluated_selected:
        st.info("Select an opportunity from the feed to view agent insights.")
    else:

        # Header Info Box
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a8a, #3b82f6); color: white; padding: 16px; border-radius: 10px; margin-bottom: 12px;">
            <div style="font-size: 1.25rem; font-weight: 700;">{esc(str(evaluated_selected['title']))}</div>
            <div style="font-size: 0.9rem; opacity: 0.9;">{esc(str(evaluated_selected['organization']))} • {esc(str(evaluated_selected['type']))}</div>
            <div style="margin-top: 8px; font-size: 0.85rem;">
                <b>Deadline:</b> {esc(str(evaluated_selected['deadline_info']['formatted_date']))} ({esc(str(evaluated_selected['deadline_info']['urgency_label']))})
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab_agent, tab_eligibility, tab_skills, tab_details = st.tabs([
            "🧠 Agent Advice & Actions",
            "🛡️ Eligibility Breakdown",
            "📊 Skills Matrix",
            "📖 Description & Process"
        ])

        # TAB 1: AGENT ADVICE & RECOMMENDED NEXT ACTIONS
        with tab_agent:
            # Generate insights
            with st.spinner("Agent synthesizing profile alignment and action roadmap..."):
                agent_output = cached_agent_insight(
                    student_profile, evaluated_selected, bool(api_key_input), api_key_input
                )

            st.caption(f"⚡ Mode: **{agent_output.get('engine_mode', 'Unknown')}**")

            # Match Score Breakdown Progress & Transparent Explainability
            st.markdown("##### 🎯 Transparent Scoring & Explainability")
            expl = evaluated_selected.get("explanation", {})
            skill_pct = evaluated_selected.get("match_percentage", 0.0)
            rel_score = evaluated_selected.get("relevance_score", evaluated_selected.get("match_score", 0)) or 0

            m_c1, m_c2 = st.columns(2)
            with m_c1:
                st.metric("Skill Match %", f"{skill_pct}%", help="Pure percentage of required skills possessed by student")
            with m_c2:
                st.metric("Relevance Score", f"{rel_score} / 100", delta="Eligible" if evaluated_selected["is_eligible"] else "Ineligible", delta_color="normal" if evaluated_selected["is_eligible"] else "inverse")

            st.progress(max(0.0, min(1.0, rel_score / 100.0)), text=f"Overall Relevance: {rel_score}/100")

            with st.expander("🔍 Transparent Calculation Breakdown (No Black Box)", expanded=True):
                st.markdown(f"**Formula:** `{expl.get('formula', '')}`")
                for step in expl.get("calculation_steps", []):
                    st.markdown(f"- {step}")
                st.caption(f"**Verdict:** {expl.get('summary', '')}")

            st.markdown("##### 💡 1. Why This Opportunity Is Recommended")
            if evaluated_selected["is_eligible"]:
                st.info(agent_output.get("why_recommended", "Unknown"))
            else:
                st.warning(agent_output.get("why_recommended", "Unknown"))

            st.markdown("##### 🎯 2. Skill Alignment Explanation")
            st.markdown(agent_output.get("skill_alignment", "Unknown"))

            st.markdown("##### 🛡️ 3. Eligibility Explanation (Deterministic Verification)")
            st.markdown(agent_output.get("eligibility_explanation", "Unknown"))

            st.markdown("##### ⚡ 4. Missing Skills & Gap Analysis")
            st.markdown(agent_output.get("missing_skills", "Unknown"))

            st.markdown("##### 🚀 5. Recommended Next Actions")
            actions_list = agent_output.get("recommended_next_actions", [])
            if isinstance(actions_list, list) and actions_list:
                for act in actions_list:
                    if isinstance(act, dict):
                        phase_label = act.get("phase", "Action Step")
                        task_label = act.get("task", "Action")
                        detail_label = act.get("detail", "")
                        with st.expander(f"📌 {phase_label}: {task_label}", expanded=True):
                            st.markdown(f"**Action Steps:** {detail_label}")
                    else:
                        st.markdown(f"- {str(act)}")
            else:
                st.markdown("No pending actions recommended.")

            apply_url = str(evaluated_selected.get("apply_url") or "")
            if apply_url.lower().startswith(("https://", "http://")):
                st.link_button(f"🔗 Go to Official Application Portal ({evaluated_selected['organization']})", apply_url, use_container_width=True)
            else:
                st.caption("No official application link is available for this opportunity.")

        # TAB 2: ELIGIBILITY CHECKLIST
        with tab_eligibility:
            st.markdown("##### 🛡️ Hard Eligibility Verification")
            st.caption("The agent verifies college requirements against official guidelines before you invest preparation time.")

            elig_data = evaluated_selected["eligibility"]
            checks = elig_data["checks"]

            for criterion, result in checks.items():
                icon = "✅" if result["passed"] else "❌"
                status_title = criterion.upper()
                st.markdown(f"**{icon} {status_title}:** {result['detail']}")

            if elig_data["is_eligible"]:
                st.success("🎉 You meet all mandatory eligibility criteria for this opportunity!")
            else:
                st.error("⚠️ You do not meet one or more hard eligibility requirements.")
                for r in elig_data["failure_reasons"]:
                    st.markdown(f"- ❗ {r}")

        # TAB 3: SKILLS MATRIX
        with tab_skills:
            st.markdown("##### 🔍 Required Skills vs. Your Profile")
            matched_list = evaluated_selected.get("matched_skills", [])
            missing_list = evaluated_selected.get("missing_skills", [])
            total_skills_count = len(matched_list) + len(missing_list)
            skill_pct = evaluated_selected.get("match_percentage", 0.0)

            st.caption(f"**Skill Match Coverage:** `{len(matched_list)} / {total_skills_count} skills matched ({skill_pct}%)`")

            s_col1, s_col2 = st.columns(2)
            with s_col1:
                st.markdown(f"**✅ Matched Skills ({len(matched_list)}):**")
                if matched_list:
                    for s in matched_list:
                        st.markdown(f"- <span style='color: #16a34a; font-weight: 600;'>✓ {esc(str(s))}</span> *(You possess this)*", unsafe_allow_html=True)
                else:
                    st.caption("No matching skills found in your profile.")

            with s_col2:
                st.markdown(f"**⚠️ Missing Skills to Learn ({len(missing_list)}):**")
                if missing_list:
                    for s in missing_list:
                        st.markdown(f"- <span style='color: #ea580c; font-weight: 600;'>+ {esc(str(s))}</span> *(Action item: learn or showcase)*", unsafe_allow_html=True)
                else:
                    st.success("🎉 You meet 100% of the required technical skills!")

        # TAB 4: DESCRIPTION & PROCESS
        with tab_details:
            st.markdown("##### 📄 Opportunity Overview")
            st.write(evaluated_selected.get("description", ""))

            st.markdown("##### 🏆 Selection & Evaluation Process")
            st.info(evaluated_selected.get("selection_process", "Standard Application Review"))

            st.markdown("##### 🏷️ Domain & Categorization")
            for tag in evaluated_selected.get("domain_tags", []):
                st.markdown(f"`#{tag}` ", help="Domain tag")

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; font-size: 0.85rem;">
    Student Opportunity Agent MVP • Built with Streamlit & Agentic AI Principles • Designed for Undergraduate CSE/IT Students
</div>
""", unsafe_allow_html=True)
