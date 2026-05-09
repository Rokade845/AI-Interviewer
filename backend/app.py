from urllib import response
from flask import Flask, request, Response, stream_with_context, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent
# langchain / langgraph imports are optional for local testing. Provide
# lightweight fallbacks if they're not installed so the app can still run.
try:
    from langchain.chat_models import init_chat_model
    from langgraph.checkpoint.memory import InMemorySaver
    from langchain.agents import create_agent
    _HAS_LANGCHAIN = True
except Exception:
    _HAS_LANGCHAIN = False

    def init_chat_model(name, api_key=None):
        # minimal placeholder model object
        class _DummyModel:
            def __init__(self, name, api_key):
                self.name = name
                self.api_key = api_key

        return _DummyModel(name, api_key)

    class InMemorySaver:
        def __init__(self):
            self.store = []

    class _DummyAgent:
        def __init__(self, model, tools=None, checkpointer=None):
            self.model = model
            self.tools = tools or []
            self.checkpointer = checkpointer

        def invoke(self, payload, config=None):
            # Create a simple deterministic response that mimics the expected
            # shape: {'messages': [{'content': '...'}]}
            messages = payload.get("messages", []) if isinstance(payload, dict) else []
            # try to infer subject from the user prompt
            subject = None
            for m in messages:
                if isinstance(m, dict):
                    content = m.get("content", "")
                    if "about" in content:
                        try:
                            subject = content.split("about", 1)[1].split(".")[0].strip()
                        except Exception:
                            subject = None
            question = f"Hi — let's begin. (stub) First question about {subject or 'the subject'}: What's one thing you're proud of?"
            return {"messages": [{"content": question}]}

    def create_agent(model, tools=None, checkpointer=None):
        return _DummyAgent(model, tools=tools, checkpointer=checkpointer)
import os
import base64
import requests
import json
import assemblyai as aai
import tempfile


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MURF_API_KEY = os.getenv("MURF_API_KEY")
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API_KEY")    

aai.settings.api_key=ASSEMBLYAI_API_KEY

checkpointer = InMemorySaver()

model = init_chat_model(
    "google_genai:gemini-2.5-flash",
    api_key=GOOGLE_API_KEY
)

agent = create_agent(
    model=model,
    tools=[],
    checkpointer=checkpointer
)

question_count = 0
current_subject = ""
thread_id = "interview_session"

INTERVIEW_PROMPT = """You are Natalie, a friendly and conversational interviewer conducting a natural {subject} interview.

IMPORTANT GUIDELINES:
1. Ask exactly 5 questions total throughout the interview
2. Keep questions SHORT and CRISP (1-2 sentences maximum)
3. ALWAYS reference what the candidate ACTUALLY said in their previous answer - do NOT make up or assume their answers
4. Show genuine interest with brief acknowledgments based on their REAL responses
5. Adapt questions based on their ACTUAL responses - go deeper if they're strong, adjust if uncertain
6. Be warm and conversational but CONCISE
7. No lengthy explanations - just ask clear, direct questions

CRITICAL: Read the conversation history carefully. Only acknowledge what the candidate truly said, not what you think they might have said.

Keep it short, conversational, and adaptive!"""

FEEDBACK_PROMPT = """Based on our complete interview conversation, provide detailed feedback.
IMPORTANT: You MUST respond with ONLY a valid JSON object. No other text before or after.
Address the candidate directly using "you" and "your" (e.g., "You explained..." not "The candidate explained...").
Respond with ONLY this JSON structure (no markdown, no code blocks, no extra text):
{{
    "subject": "{subject}",
    "candidate_score": <1-5>,
    "feedback": "<detailed strengths with specific examples from their ACTUAL answers>",
    "areas_of_improvement": "<constructive suggestions based on gaps you noticed>"
}}
Be specific - reference ACTUAL things they said during the interview."""

app = Flask(__name__)
# Configure CORS to allow requests from the frontend dev server.
# Set FRONTEND_ORIGIN in the environment to override if needed.
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": FRONTEND_ORIGIN}}, supports_credentials=True, expose_headers=["X-Question-Number", "X-Interview-Complete"])


@app.after_request
def _add_cors_headers(response):
    # Ensure preflight and regular responses include the CORS headers the browser expects
    response.headers.add("Access-Control-Allow-Origin", FRONTEND_ORIGIN)
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    response.headers.add("Access-Control-Expose-Headers", "X-Interview-Complete, X-Question-Number")
    return response


def stream_audio(text):
    BASE_URL = "https://global.api.murf.ai/v1/speech/stream"
    payload = {
        "text": text,
        "voiceId": "en-US-natalie",
        "model": "FALCON",
        "multiNativeLocale": "en-US",
        "sampleRate": 24000,
        "format": "MP3",
    }

    # If MURF_API_KEY is not set, fall back to streaming the plain text
    # (useful for local development/testing).
    if not MURF_API_KEY:
        # stream the question text in small chunks to emulate streaming
        chunk_size = 80
        for i in range(0, len(text), chunk_size):
            yield text[i : i + chunk_size] + "\n"
        return

    headers = {
        "Content-Type": "application/json",
        "api-key": MURF_API_KEY,
    }
    response = requests.post(
        BASE_URL,
        headers=headers,
        data=json.dumps(payload),
        stream=True,
        timeout=15,
    )
    for chunk in response.iter_content(chunk_size=4096):
        if chunk:
            yield base64.b64encode(chunk).decode("utf-8") + "\n"



@app.route("/start-interview", methods=["POST"])
def start_interview():
    global question_count, current_subject, checkpointer, agent
    data = request.json
    current_subject = data.get("subject", "Python")
    question_count = 1
    checkpointer = InMemorySaver()
    agent = create_agent(
        model=model,
        tools=[],
        checkpointer=checkpointer
    )
    config = {"configurable": {"thread_id": thread_id}}
    formatted_prompt = INTERVIEW_PROMPT.format(subject=current_subject)
    try:
        response = agent.invoke({
            "messages": [
                {"role": "system", "content": formatted_prompt},
                {"role": "user", "content": f"Start the interview with a warm greeting and ask the first question about {current_subject}. Keep it SHORT (1-2 sentences)."}
            ]
        }, config=config)

        # Robust extraction of the question text from different possible response shapes
        question = None
        if isinstance(response, dict):
            msgs = response.get("messages") or response.get("output") or response.get("messages_list")
            if isinstance(msgs, list) and msgs:
                last = msgs[-1]
                if isinstance(last, dict):
                    question = last.get("content") or last.get("text")
                else:
                    question = getattr(last, "content", None) or str(last)
            else:
                question = response.get("text") or response.get("message") or json.dumps(response)
        else:
            question = getattr(response, "content", None) or getattr(response, "text", None) or str(response)

        if not question:
            question = "(no question generated)"

        print(f"\n[Question {question_count}] {question}")

        # Stream the audio as a Flask Response using a generator
        generator = stream_audio(question)
        return Response(stream_with_context(generator), mimetype="text/plain")
    except Exception as e:
        # Return a JSON error with status 500 for easier debugging in the frontend
        return jsonify({"error": "failed to start interview", "details": str(e)}), 500

def speech_to_text(audio_path):
    # Upload audio file to AssemblyAI and get the transcript
    try:
        transcriber = aai.Transcriber()
        config = aai.TranscriptionConfig(speech_models=["universal-2"])
        transcript = transcriber.transcribe(audio_path, config=config)
        return transcript.text if transcript.text else ""
    except Exception as e:
        print(f"Speech-to-text error: {e}")
        return "(Could not transcribe audio)"


@app.route("/submit-answer", methods=["POST"])
def submit_answer():
   global question_count
   try:
       audio_file = request.files["audio"]
       question_count += 1
       temp_path=(
           tempfile.NamedTemporaryFile(
               delete=False, 
               suffix=".webm"
               )).name
       audio_file.save(temp_path)
       answer=speech_to_text(temp_path)
       os.unlink(temp_path)
       if not answer:
           answer = "Empty Text received."
       config = {"configurable": {"thread_id": thread_id}}
       agent.invoke({
           "messages": [{"role": "user", "content": answer}]
       },
       config=config
       )
       prompt=f"""  The candidate just answered question {question_count - 1}.
       
          Look at their ACTUAL answer above. Do NOT assume or make up what they said.
          
          Now ask question {question_count} of 5:
          1. Briefly acknowledge what they ACTUALLY said (1 sentence) - quote their exact words if needed
          2. Ask your next question that builds on their REAL response (1-2 sentences)
          3. If they said "I don't know" or gave a wrong answer, acknowledge that and ask something simpler
          4. Keep the TOTAL response under 3 sentences
          
          Be conversational but CONCISE. Only reference what they truly said."""
       response = agent.invoke({
           "messages": [
               {"role": "user", "content": prompt}
           ]
       }, config=config)     
       question = response["messages"][-1].content 
       is_complete = question_count >= 5
       return (stream_audio(question), {
             "Content-Type": "text/plain",
             "X-Question-Number": str(question_count),
             "X-Interview-Complete": "true" if is_complete else "false"
       })
   except Exception as e:
       print(f"Error in submit_answer: {e}")
       return jsonify({"error": "failed to process answer", "details": str(e)}), 500

@app.route("/get-feedback", methods=["POST"])
def get_feedback():
    config = {"configurable": {"thread_id": thread_id}}
    response = agent.invoke({
        "messages": [
            {"role": "user", "content": f"{FEEDBACK_PROMPT}\n\n Review our complete {current_subject} interview conversation and provide detailed feedback."}
        ]
    }, config=config)
    text = response["messages"][-1].content
    cleaned = text.strip()
    if "```" in cleaned:
        cleaned=cleaned.split("```")[1]
        if cleaned.startswith("json"):
            cleaned=cleaned[4:].strip()
    feedback = json.loads(cleaned)
    return jsonify({"success": True,"feedback": feedback})

if __name__ == "__main__":
    # Warn if using stubbed langchain implementation
    if not _HAS_LANGCHAIN:
        print("WARNING: langchain/langgraph not found — using local stubs for testing")
    PORT = int(os.getenv("PORT", "5001"))
    HOST = os.getenv("HOST", "127.0.0.1")
    print(f"Starting server on {HOST}:{PORT} (FRONTEND_ORIGIN={FRONTEND_ORIGIN})")
    app.run(debug=True, host=HOST, port=PORT)
