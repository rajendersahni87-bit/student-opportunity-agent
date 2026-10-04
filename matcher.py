"""
Deterministic & Explainable Opportunity Matching Engine.
Provides transparent skill comparison, eligibility checks, explainable scoring,
and relevance-based ranking without using LLMs for numerical computation.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Tuple, Optional

CLOSING_SOON_DAYS = 5   # single source of truth (UI metric uses the same status)


# ---------------------------------------------------------
# NORMALIZATION & SYNONYM DICTIONARIES
# ---------------------------------------------------------

SKILL_ALIASES = {
    "dsa": "data structures",
    "ds": "data structures",
    "data structure": "data structures",
    "data structures": "data structures",
    "algo": "algorithms",
    "algorithm": "algorithms",
    "algorithms": "algorithms",
    "cp": "competitive programming",
    "competitive coding": "competitive programming",
    "competitive programming": "competitive programming",
    "ml": "machine learning",
    "ai": "machine learning",
    "artificial intelligence": "machine learning",
    "machine learning": "machine learning",
    "dl": "deep learning",
    "deep learning": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "node": "node.js",
    "nodejs": "node.js",
    "node.js": "node.js",
    "vue": "vue.js",
    "vuejs": "vue.js",
    "next": "next.js",
    "nextjs": "next.js",
    "cpp": "c++",
    "c++": "c++",
    "c#": "c-sharp",
    "c-sharp": "c-sharp",
    "golang": "go",
    "go": "go",
    "fullstack": "full stack development",
    "full stack": "full stack development",
    "full stack development": "full stack development",
    "web dev": "web development",
    "web development": "web development",
    "frontend": "frontend development",
    "backend": "backend development",
    "cloud": "cloud computing",
    "cloud computing": "cloud computing",
    "aws": "cloud computing",
    "gcp": "google cloud",
    "google cloud": "google cloud",
    "azure": "azure",
    "git": "git",
    "github": "github",
    "rest": "rest apis",
    "api": "rest apis",
    "apis": "rest apis",
    "rest apis": "rest apis",
    "dbms": "database management",
    "database": "database management",
    "databases": "database management",
    "sql": "sql"
}

BRANCH_ALIASES = {
    "cse": "computer science",
    "cs": "computer science",
    "computer engineering": "computer science",
    "computer science and engineering": "computer science",
    "computer science": "computer science",
    "it": "information technology",
    "information technology": "information technology",
    "information science": "information technology",
    "ise": "information technology",
    "ece": "electronics & communication",
    "etc": "electronics & communication",
    "electronics and communication": "electronics & communication",
    "electronics & communication": "electronics & communication",
    "electronics and telecommunication": "electronics & communication",
    "eee": "electrical engineering",
    "ee": "electrical engineering",
    "electrical engineering": "electrical engineering",
    "electrical and electronics": "electrical engineering",
    "mech": "mechanical engineering",
    "me": "mechanical engineering",
    "mechanical engineering": "mechanical engineering",
    "civil": "civil engineering",
    "civil engineering": "civil engineering",
    "computer science & engineering": "computer science",
    "computer science engineering": "computer science",
    "electronics & communication engineering": "electronics & communication",
    "electronics and communication engineering": "electronics & communication"
}

YEAR_ALIASES = {
    "1": "1st year",
    "1st": "1st year",
    "1st year": "1st year",
    "first": "1st year",
    "first year": "1st year",
    "2": "2nd year",
    "2nd": "2nd year",
    "2nd year": "2nd year",
    "second": "2nd year",
    "second year": "2nd year",
    "3": "3rd year",
    "3rd": "3rd year",
    "3rd year": "3rd year",
    "third": "3rd year",
    "third year": "3rd year",
    "4": "4th year",
    "4th": "4th year",
    "4th year": "4th year",
    "fourth": "4th year",
    "fourth year": "4th year",
    "final": "4th year",
    "final year": "4th year"
}


# ---------------------------------------------------------
# NORMALIZATION HELPERS
# ---------------------------------------------------------

def _to_float(value: Any) -> Optional[float]:
    """Safe float parse. Returns None for None / blank / non-numeric input."""
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def infer_mode(opportunity: Dict[str, Any]) -> str:
    """Single place that derives Remote / Hybrid / In-Person from an opportunity."""
    mode = str(opportunity.get("mode") or "").strip()
    if mode:
        return mode
    loc = str(opportunity.get("location") or "").lower()
    if "remote" in loc or "online" in loc or ("pan-india" in loc and "in-person" not in loc):
        return "Remote"
    if "hybrid" in loc:
        return "Hybrid"
    return "In-Person"


def _skill_match(norm_req: str, norm_student: set) -> bool:
    """Exact (alias-normalised) match, or multi-word phrase contained in the other.
    Plain substring matching is NOT used: it made Java match JavaScript, Git match GitHub, etc."""
    if norm_req in norm_student:
        return True
    req_tokens = set(norm_req.split())
    for s in norm_student:
        s_tokens = set(s.split())
        shorter, longer = (s_tokens, req_tokens) if len(s_tokens) <= len(req_tokens) else (req_tokens, s_tokens)
        if len(shorter) >= 2 and shorter <= longer:
            return True
    return False


def normalize_skill(skill: str) -> str:
    """Normalize skill string for case-insensitive matching and synonyms."""
    s = str(skill).strip().lower()
    return SKILL_ALIASES.get(s, s)


def normalize_branch(branch: str) -> str:
    """Normalize branch string for flexible matching."""
    b = str(branch).strip().lower()
    return BRANCH_ALIASES.get(b, b)


def normalize_year(year: str) -> str:
    """Normalize academic year string."""
    y = str(year).strip().lower()
    return YEAR_ALIASES.get(y, y)


# ---------------------------------------------------------
# REQ 1, 2, 6, 7: SKILL COMPARISON & TRANSPARENT MATCH %
# ---------------------------------------------------------

def compare_skills(student_skills: List[str], required_skills: List[str]) -> Dict[str, Any]:
    """
    Compares student skills against opportunity required skills.
    
    Returns:
        {
            "matched_skills": List[str],      # Skills the student possesses
            "missing_skills": List[str],      # Skills the student lacks
            "match_percentage": float,        # Transparent percentage (0.0 - 100.0)
            "explanation": str                # Human-readable calculation explanation
        }
    """
    if not required_skills:
        return {
            "matched_skills": [],
            "missing_skills": [],
            "match_percentage": 100.0,
            "explanation": "No specific required skills specified; 100% skill match by default."
        }

    norm_student = {normalize_skill(s) for s in (student_skills or []) if s and str(s).strip()}
    
    matched = []
    missing = []

    for req in required_skills:
        req_clean = str(req).strip()
        norm_req = normalize_skill(req_clean)
        
        if _skill_match(norm_req, norm_student):
            matched.append(req_clean)
        else:
            missing.append(req_clean)

    total_req = len(required_skills)
    matched_count = len(matched)
    
    # Transparent formula: (Matched / Total Required) * 100
    match_pct = round((matched_count / total_req) * 100.0, 1) if total_req > 0 else 100.0

    return {
        "matched_skills": matched,
        "missing_skills": missing,
        "match_percentage": match_pct,
        "explanation": f"Matched {matched_count} of {total_req} required skills ({match_pct}%)."
    }


# ---------------------------------------------------------
# REQ 3: YEAR ELIGIBILITY CHECK
# ---------------------------------------------------------

def check_year_eligibility(student_year: str, eligible_years: List[str]) -> Tuple[bool, str]:
    """
    Validates whether the student's academic year matches the opportunity criteria.
    """
    if not eligible_years:
        return True, "Open to all academic years."

    norm_eligible = [normalize_year(y) for y in eligible_years]
    
    # Check for wildcards
    if any(k in norm_eligible for k in ["all", "all years", "open to all", "any"]):
        return True, "Open to all academic years."

    student_norm = normalize_year(student_year)
    if student_norm in norm_eligible:
        return True, f"Eligible: Student is in '{student_year}' (Allowed: {', '.join(eligible_years)})."
    else:
        return False, f"Ineligible: Opportunity restricts to {', '.join(eligible_years)}, but student is in '{student_year}'."


# ---------------------------------------------------------
# REQ 4: BRANCH ELIGIBILITY CHECK
# ---------------------------------------------------------

def check_branch_eligibility(student_branch: str, eligible_branches: List[str]) -> Tuple[bool, str]:
    """
    Validates whether the student's branch/major satisfies the criteria.
    """
    if not eligible_branches:
        return True, "Open to all academic branches."

    norm_eligible = [normalize_branch(b) for b in eligible_branches]
    norm_student = normalize_branch(student_branch)

    # Check for wildcards
    wildcards = ["all", "all engineering", "all engineering branches", "any", "all branches"]
    if any(w in norm_eligible for w in wildcards):
        return True, f"Eligible: Open to all engineering branches (Student: '{student_branch}')."

    if not str(student_branch or "").strip():
        return False, f"Ineligible: Branch not provided, but opportunity requires [{', '.join(eligible_branches)}]."

    # Exact (alias-normalised) comparison only; substring matching let blank/short branches pass everything
    for eb, raw_eb in zip(norm_eligible, eligible_branches):
        if eb == norm_student:
            return True, f"Eligible: Branch '{student_branch}' satisfies requirement '{raw_eb}'."

    return False, f"Ineligible: Eligible branches are [{', '.join(eligible_branches)}], but student is in '{student_branch}'."


# ---------------------------------------------------------
# REQ 5: CGPA ELIGIBILITY CHECK (IF PROVIDED)
# ---------------------------------------------------------

def check_cgpa_eligibility(student_cgpa: Optional[Any], min_cgpa: float) -> Tuple[bool, str]:
    """
    Validates student CGPA against minimum requirement.
    Gracefully handles optional / omitted student CGPA.
    """
    min_cutoff = _to_float(min_cgpa) or 0.0
    parsed = _to_float(student_cgpa)

    # If opportunity has no cutoff
    if min_cutoff <= 0.0:
        if parsed is not None:
            return True, f"Eligible: No minimum CGPA cutoff required (Student CGPA: {parsed:.2f})."
        return True, "Eligible: No minimum CGPA cutoff required."

    # If student did not provide CGPA
    if student_cgpa is None or str(student_cgpa).strip() == "":
        return False, f"Ineligible: Requires minimum CGPA of {min_cutoff:.2f}, but no CGPA was provided by student."

    val = parsed
    if val is None:
        return False, f"Ineligible: Invalid student CGPA value '{student_cgpa}'."

    if val >= min_cutoff:
        return True, f"Eligible: Student CGPA {val:.2f} satisfies minimum requirement of {min_cutoff:.2f}."
    else:
        return False, f"Ineligible: Student CGPA {val:.2f} is below the required cutoff of {min_cutoff:.2f}."


# ---------------------------------------------------------
# COMBINED ELIGIBILITY EVALUATOR
# ---------------------------------------------------------

def check_eligibility(student: Dict[str, Any], opportunity: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates year, branch, and CGPA constraints.
    Returns:
        {
            "is_eligible": bool,
            "checks": {
                "year": {"passed": bool, "detail": str},
                "branch": {"passed": bool, "detail": str},
                "cgpa": {"passed": bool, "detail": str}
            },
            "failure_reasons": List[str]
        }
    """
    elig_dict = opportunity.get("eligibility", {}) if isinstance(opportunity.get("eligibility"), dict) else {}
    
    # Extract criteria supporting both flat schema and nested dict
    allowed_years = opportunity.get("eligible_years", elig_dict.get("allowed_years", []))
    allowed_branches = opportunity.get("eligible_branches", elig_dict.get("allowed_branches", []))
    min_cgpa = _to_float(opportunity.get("min_cgpa", elig_dict.get("min_cgpa", 0.0))) or 0.0

    student_year = student.get("year", "")
    student_branch = student.get("branch", "")
    student_cgpa = student.get("cgpa", None)

    # Run individual checks
    year_ok, year_reason = check_year_eligibility(student_year, allowed_years)
    branch_ok, branch_reason = check_branch_eligibility(student_branch, allowed_branches)
    cgpa_ok, cgpa_reason = check_cgpa_eligibility(student_cgpa, min_cgpa)

    checks = {
        "year": {"passed": year_ok, "detail": year_reason},
        "branch": {"passed": branch_ok, "detail": branch_reason},
        "cgpa": {"passed": cgpa_ok, "detail": cgpa_reason}
    }

    failure_reasons = []
    if not year_ok:
        failure_reasons.append(year_reason)
    if not branch_ok:
        failure_reasons.append(branch_reason)
    if not cgpa_ok:
        failure_reasons.append(cgpa_reason)

    is_eligible = (year_ok and branch_ok and cgpa_ok)

    return {
        "is_eligible": is_eligible,
        "checks": checks,
        "failure_reasons": failure_reasons
    }


# ---------------------------------------------------------
# TRANSPARENT & EXPLAINABLE MATCH SCORING
# ---------------------------------------------------------

def calculate_match_score(
    student: Dict[str, Any],
    opportunity: Dict[str, Any],
    skill_comparison: Dict[str, Any],
    eligibility_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculates a fully explainable, deterministic relevance score (0-100).
    
    EXPLAINABLE FORMULA:
    --------------------
    1. Skill Match Weight (50 points):
       Points = (Skill Match Percentage / 100.0) * 50.0
    
    2. Eligibility Clearance (30 points):
       Points = 30.0 if all hard criteria (Year, Branch, CGPA) are met, else 0.0
    
    3. Preference Alignment (20 points):
       - Category Match (10 pts): Opportunity type is in student's preferred types
       - Work Mode Match (5 pts): In-Person/Hybrid/Remote matches preferred mode
       - Domain / Interest Match (5 pts): Tech interests overlap with opportunity tags/skills
    
    Total Relevance Score = round(Skill Points + Eligibility Points + Preference Points)
    """
    skill_pct = float(skill_comparison.get("match_percentage", 0.0))
    is_eligible = bool(eligibility_result.get("is_eligible", False))

    # 1. Skill Points (Max 50)
    skill_points = round((skill_pct / 100.0) * 50.0, 1)

    # 2. Eligibility Points (Max 30)
    elig_points = 30.0 if is_eligible else 0.0

    # 3. Preference Points (Max 20)
    # A. Type Match (10 pts)
    pref_types = [t.lower().rstrip("s") for t in (student.get("preferred_types") or [])]
    opp_type = str(opportunity.get("type") or "").lower().rstrip("s")
    if not pref_types or any(pt in opp_type or opp_type in pt for pt in pref_types):
        type_points = 10.0
    else:
        type_points = 3.0

    # B. Mode Match (5 pts)
    student_mode = str(student.get("preferred_mode") or "Any").lower()
    opp_mode = infer_mode(opportunity).lower()

    if student_mode == "any" or student_mode in opp_mode or opp_mode in student_mode:
        mode_points = 5.0
    else:
        mode_points = 1.0

    # C. Domain / Interest Match (5 pts)
    student_interests = [i.strip().lower() for i in (student.get("interests") or [])]
    opp_skills = [s.strip().lower() for s in (opportunity.get("skills") or opportunity.get("required_skills") or [])]
    opp_domains = [d.strip().lower() for d in (opportunity.get("domain_tags") or [])] + opp_skills

    if student_interests and opp_domains:
        overlap = sum(1 for i in student_interests if any(i in d or d in i for d in opp_domains))
        interest_ratio = min(1.0, overlap / max(1, len(student_interests)))
        interest_points = round(interest_ratio * 5.0, 1)
    else:
        interest_points = 2.5

    preference_points = round(type_points + mode_points + interest_points, 1)

    # Compute Total Score
    total_relevance = int(round(skill_points + elig_points + preference_points))
    # Ineligible clamp: if ineligible, cap at 58% so eligible items rank higher
    if not is_eligible:
        total_relevance = min(total_relevance, 58)
    total_relevance = max(5, min(100, total_relevance))

    # Detailed Explainability Data
    explanation = {
        "formula": "Relevance Score (0-100) = Skill Points (50%) + Eligibility Clearance (30%) + Preference Alignment (20%)",
        "calculation_steps": [
            f"1. Skill Points: {skill_pct}% match * 0.50 = {skill_points}/50 pts",
            f"2. Eligibility: {'PASSED (All criteria met) = 30/30 pts' if is_eligible else 'FAILED (Hard criteria not satisfied) = 0/30 pts'}",
            f"3. Preferences: Category ({type_points}/10) + Mode ({mode_points}/5) + Interests ({interest_points}/5) = {preference_points}/20 pts"
        ],
        "summary": f"Skill match is {skill_pct}%. Candidate is {'eligible' if is_eligible else 'ineligible'}. Total relevance: {total_relevance}/100."
    }

    return {
        "score": total_relevance,
        "match_percentage": skill_pct,
        "breakdown": {
            "skills": skill_points,
            "eligibility": elig_points,
            "preference": preference_points,
            "interests": interest_points
        },
        "explanation": explanation
    }


# ---------------------------------------------------------
# DEADLINE URGENCY COMPUTATION
# ---------------------------------------------------------

def compute_deadline_info(deadline_str: str, reference_date: date = None) -> Dict[str, Any]:
    """
    Computes days remaining and urgency status badges.
    """
    if reference_date is None:
        reference_date = date.today()

    try:
        deadline_dt = datetime.strptime(str(deadline_str).strip(), "%Y-%m-%d").date()
        days_left = (deadline_dt - reference_date).days
        formatted = deadline_dt.strftime("%d %b %Y")
    except Exception:
        return {
            "days_left": None,
            "is_expired": False,
            "status": "Unknown",
            "badge_color": "gray",
            "urgency_label": "Ongoing / Open",
            "formatted_date": str(deadline_str) or "Ongoing / Open"
        }

    if days_left < 0:
        status = "Expired"
        badge_color = "red"
        urgency_label = f"Expired ({abs(days_left)} days ago)"
    elif days_left <= CLOSING_SOON_DAYS:
        status = "Closing Soon"
        badge_color = "red"
        urgency_label = f"🔥 {days_left} day{'s' if days_left != 1 else ''} left!"
    elif days_left <= 15:
        status = "Approaching Deadline"
        badge_color = "orange"
        urgency_label = f"⚡ {days_left} days left"
    else:
        status = "Active"
        badge_color = "green"
        urgency_label = f"⏳ {days_left} days left"

    return {
        "days_left": days_left,
        "is_expired": status == "Expired",
        "status": status,
        "badge_color": badge_color,
        "urgency_label": urgency_label,
        "formatted_date": formatted
    }


# ---------------------------------------------------------
# REQ 8: RELEVANCE RANKING & EVALUATION ENGINE
# ---------------------------------------------------------

def evaluate_opportunities(
    student: Dict[str, Any],
    opportunities: List[Dict[str, Any]],
    reference_date: date = None
) -> List[Dict[str, Any]]:
    """
    Evaluates, scores, and ranks all opportunities by relevance.
    
    Ranking Order:
    0. Not expired (expired items sink to the bottom)
    1. Eligibility (Eligible candidates rank first)
    2. Overall Relevance Score (Highest first)
    3. Skill Match Percentage (Highest first)
    4. Deadline Urgency (Active, upcoming deadlines before expired ones)
    """
    evaluated = []

    for opp in opportunities:
        # 1. Compare skills (Req 1, 2, 6, 7)
        req_skills = opp.get("skills") or opp.get("required_skills") or []
        student_skills = student.get("skills") or []
        skill_comp = compare_skills(student_skills, req_skills)

        # 2. Check eligibility (Req 3, 4, 5)
        eligibility = check_eligibility(student, opp)

        # 3. Calculate transparent match score & explainability
        score_info = calculate_match_score(student, opp, skill_comp, eligibility)

        # 4. Compute deadline urgency
        deadline_info = compute_deadline_info(opp.get("deadline", ""), reference_date)

        # Derive mode & URL
        mode = infer_mode(opp)

        apply_url = opp.get("application_url", opp.get("apply_url", "#"))

        evaluated.append({
            **opp,
            "mode": mode,
            "apply_url": apply_url,
            "application_url": apply_url,
            "is_eligible": eligibility["is_eligible"],
            "is_expired": deadline_info["is_expired"],
            "eligibility": eligibility,
            "matched_skills": skill_comp["matched_skills"],
            "missing_skills": skill_comp["missing_skills"],
            "matched_required": skill_comp["matched_skills"],
            "missing_required": skill_comp["missing_skills"],
            "match_percentage": skill_comp["match_percentage"],
            "match_score": score_info["score"],
            "relevance_score": score_info["score"],
            "match_breakdown": score_info["breakdown"],
            "explanation": score_info["explanation"],
            "deadline_info": deadline_info
        })

    # Rank by relevance (Req 8)
    evaluated.sort(
        key=lambda x: (
            0 if x["is_expired"] else 1,   # open opportunities always outrank expired ones
            1 if x["is_eligible"] else 0,
            x["relevance_score"],
            x["match_percentage"],
            -x["deadline_info"]["days_left"] if x["deadline_info"]["days_left"] is not None and x["deadline_info"]["days_left"] >= 0 else -9999
        ),
        reverse=True
    )

    return evaluated
