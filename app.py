import os
import streamlit as st
import trafilatura
from google import genai
from google.genai import types
from pypdf import PdfReader

# ==============================================================================
# 1. PAGE SETUP & INTERFACE STYLING
# ==============================================================================
st.set_page_config(
    page_title="GED Study Coach",
    page_icon="🌟",
    layout="centered"
)

st.title("🌟 Your Personal GED Study Coach")
st.markdown(
    "Welcome! Every step you take here is an investment in yourself. "
    "There are **no grades**, **no ticking clocks**, and **no judgment**—just steady progress."
)

# ==============================================================================
# 2. SECURE API SETUP
# ==============================================================================
api_key = st.secrets.get("GEMINI_API_KEY")
if not api_key:
    st.error("API Key not found. Please add GEMINI_API_KEY to your Streamlit secrets.")
    st.stop()

client = genai.Client(api_key=api_key)

# ==============================================================================
# 3. AUTOMATIC INGESTION OF ROOT PDFS & URLS
# ==============================================================================
@st.cache_resource
def load_all_curriculum_sources():
    combined_text = ""

    # Load all PDFs sitting directly in the main repository folder
    pdf_files = [f for f in os.listdir(".") if f.endswith(".pdf")]
    for pdf in pdf_files:
        try:
            reader = PdfReader(pdf)
            combined_text += f"\n\n=== SOURCE PDF: {pdf} ===\n"
            for idx, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    combined_text += f"[Page {idx+1}] {text}\n"
        except Exception as e:
            st.warning(f"Could not read PDF {pdf}: {e}")

    # Load any websites listed in urls.txt
    if os.path.exists("urls.txt"):
        with open("urls.txt", "r", encoding="utf-8") as f:
            urls = [line.strip() for line in f.readlines() if line.strip().startswith("http")]

        for url in urls:
            try:
                downloaded = trafilatura.fetch_url(url)
                web_text = trafilatura.extract(downloaded)
                if web_text:
                    combined_text += f"\n\n=== SOURCE WEBPAGE: {url} ===\n{web_text}\n"
            except Exception as e:
                st.warning(f"Could not scrape {url}: {e}")

    return combined_text

curriculum_sources = load_all_curriculum_sources()

# ==============================================================================
# 4. TAILORED SYSTEM PROMPT & PEDAGOGY
# ==============================================================================
system_instruction = f"""
You are a warm, reassuring, and highly encouraging GED Study Coach.

STUDENT BACKGROUND & EMPATHY DIRECTIVE:
You are working with an adult learner who did not graduate from high school. They may have had negative, discouraging, or invalidating experiences in the traditional school system, or they may not have seen its value in the past. Now they are here voluntarily to achieve their GED and improve their life. 
- Treat them with unconditional respect, dignity, and warmth.
- Never make them feel embarrassed for not knowing something. Normalize mistakes as a natural part of adult learning.
- Celebrate their effort, reasoning, and courage.

SUBJECT SCOPE (THE FOUR GED TOPICS ONLY):
1. Mathematical Reasoning (Numbers, proportional reasoning, algebraic expressions, linear equations, geometry, graphs)
2. Reasoning Through Language Arts (RLA) (Reading comprehension, identifying main ideas, analyzing arguments, tone, grammar, and sentence structure)
3. Science (Experimental design, independent/dependent variables, reading scientific graphs/tables, life, physical, and earth science concepts)
4. Social Studies (Analyzing historical documents, civics/government, economic concepts, geography and data interpretation)

CONTENT-ONLY RESTRICTION:
- DO NOT ask questions or lecture on test mechanics (e.g., scoring percentages, test length, how the test is delivered, passing cutoffs). Focus 100% on subject content and thinking skills.

PEDAGOGICAL & INTERACTION FLOW:
1. TOPIC SELECTION: If the student hasn't selected a topic yet, warmly introduce the four topics and ask which one they'd like to work on today.
2. EXPLAIN QUESTION LEVELS: Once they pick a topic, explain the levels of questions available for that topic:
   - Level 1: Foundational (Core definitions, basic concepts, single-step operations)
   - Level 2: Intermediate (Applying rules, interpreting a graph or passage, multi-step problem solving)
   - Level 3: Advanced (Synthesizing two passages, evaluating arguments, multi-step algebraic or scientific reasoning)
   Ask the participant what level they would feel most comfortable starting with.
3. INQUIRY & ANTI-GUESSING:
   - Present one clear question or scenario at a time.
   - Encourage them to explain their thinking ("Tell me what stands out to you first" or "Walk me through your thoughts"). We DO NOT want them guessing blindly.
4. WHEN THEY ARE STUCK OR INCORRECT:
   - If they give an incorrect answer, DO NOT just say "incorrect" or blurt out the answer.
   - First, invite them to share how they arrived at that idea: "Tell me what led you to that thought."
   - If they cannot explain or are genuinely stuck, teach the lesson directly and clearly. Break the concept down in plain English, relate it to real-world experience, and show the logic step-by-step.
   - Then, offer a supportive check question on that same concept so they can experience the win of getting it right.
5. VISUAL REPRESENTATIONS:
   - Whenever explaining concepts or if the participant asks, create visual representations!
   - Use Markdown tables, ASCII diagrams, flowcharts, step-by-step vertical layouts, or LaTeX math blocks ($...$ or $$...$$) to make abstract ideas visually concrete.
6. GUIDANCE OVER GIVING ANSWERS:
   - Guide the participant toward finding the solution themselves; never hand over the final answer without them understanding the reasoning.

REFERENCE CURRICULUM (Your uploaded PDFs and URLs):
\"\"\"
{curriculum_sources}
\"\"\"
"""

# ==============================================================================
# 5. CHAT HISTORY INITIALIZATION & SIDEBAR
# ==============================================================================
with st.sidebar:
    st.header("Study Controls")
    if st.button("🔄 Reset / Start New Topic"):
        st.session_state.messages = []
        st.rerun()
    st.markdown("---")
    st.info("💡 **Tip:** If a math formula or science idea feels confusing, type: *'Can you draw a diagram or show me a visual?'*")

if "messages" not in st.session_state:
    st.session_state.messages = []
    # Warm welcome message to start
    welcome_text = (
        "Hello! I am so glad you are here working on your GED. "
        "Which of the four subjects would you like to explore today?\n\n"
        "- **Mathematical Reasoning**\n"
        "- **Reasoning Through Language Arts (RLA)**\n"
        "- **Science**\n"
        "- **Social Studies**\n\n"
        "Let me know which one sounds good to begin with!"
    )
    st.session_state.messages.append({"role": "assistant", "content": welcome_text})

# Render prior chat messages
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ==============================================================================
# 6. USER INPUT & MODEL GENERATION
# ==============================================================================
if user_prompt := st.chat_input("Type your response or thoughts here..."):
    st.chat_message("user").markdown(user_prompt)
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    # Prepare chat history for API context
    contents_payload = []
    for m in st.session_state.messages:
        role = "user" if m["role"] == "user" else "model"
        contents_payload.append(types.Content(role=role, parts=[types.Part.from_text(text=m["content"])]))

with st.chat_message("assistant"):
    with st.spinner("Thinking..."):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents_payload,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                    max_output_tokens=600,  # Caps response size for instant, bite-sized replies
                )
            )
            assistant_text = response.text
            st.markdown(assistant_text)
            st.session_state.messages.append({"role": "assistant", "content": assistant_text})
        except Exception as e:
            st.error(f"Error: {e}")
