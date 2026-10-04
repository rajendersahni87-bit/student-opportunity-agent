# Student Opportunity Agent 🎯
### Hackathon MVP - Track: Agentic AI

An intelligent agent that solves information fragmentation and manual verification for college students (CSE/IT focus) searching for internships, hackathons, scholarships, and coding contests.

## Architecture & Project Structure
- `app.py`: Streamlit frontend dashboard, interactive student profile input, filters, opportunity cards, detail view, and agent action planner.
- `data/opportunities.json`: Structured opportunity repository (eligibility rules, skills, deadlines, perks, domains).
- `engine/matcher.py`: Eligibility evaluation engine and multi-factor weighted match scoring algorithm.
- `engine/agent.py`: Agentic AI engine for contextual fit explanations, skill gap analysis, and tailored step-by-step action roadmaps (supports both Gemini API and fallback rule-based reasoning).
- `engine/sources/`: Modular source layer (`base.py`, `json_source.py`, `live_source.py`, `repository.py`): live feeds with automatic local-JSON fallback.
- `validate_data.py`: Dataset schema/sanity checker (`python validate_data.py`).
- `test_*.py`: Unit and regression tests (`python -m unittest -v`).
- `requirements.txt`: Dependencies (`google-genai` is optional, only for the Gemini agent).

## Run
```bash
pip install -r requirements.txt
streamlit run app.py
python -m unittest -v        # run tests from the project root
python validate_data.py      # validate the dataset
```
Optional env vars: `GEMINI_API_KEY` (live LLM agent), `OPPORTUNITY_API_URL` (live JSON feed; falls back to local data on failure).
