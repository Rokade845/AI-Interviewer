# AI Interview Assistant

An AI-powered interview practice tool that conducts mock technical interviews with real-time feedback.

## Features

- **5-Question Interviews**: Conducts structured interviews with 5 targeted questions
- **Real-time Audio**: Text-to-speech for questions, speech-to-text for answers
- **AI-Powered**: Uses Google Generative AI (Gemini) for intelligent questions and feedback
- **Multiple Subjects**: Practice on Python, Generative AI, Self Introduction, English, HTML, CSS
- **Detailed Feedback**: Get scores and improvement suggestions after each interview

## Tech Stack

- **Frontend**: HTML5, JavaScript, Tailwind CSS
- **Backend**: Python, Flask, Flask-CORS
- **AI Models**: 
  - Google Generative AI (Gemini 2.5 Flash)
  - AssemblyAI (Speech-to-Text)
  - Murf AI (Text-to-Speech)

## Project Structure

```
.
├── backend/
│   ├── app.py              # Flask backend server
│   ├── venv/               # Python virtual environment
│   ├── .env                # Environment variables (DO NOT COMMIT)
│   └── .env.example        # Template for .env file
├── frontend/
│   ├── index.html          # Main HTML page
│   ├── index.js            # Frontend JavaScript
│   └── (CSS is inline with Tailwind)
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

## Setup Instructions

### 1. Get API Keys

You'll need 3 API keys:

- **Google API Key**: Get from [ai.google.dev](https://ai.google.dev/)
- **Murf AI Key**: Get from [murf.ai](https://murf.ai/)
- **AssemblyAI Key**: Get from [assemblyai.com](https://www.assemblyai.com/)

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment (if not already created)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy the template and add your API keys
cp .env.example .env
# Edit .env and add your actual API keys
nano .env  # Or use your preferred editor
```

### 3. Frontend Setup

No installation needed! Just serve the frontend:

```bash
# From the project root
python3 -m http.server 5500 --directory frontend
```

### 4. Start the Backend

```bash
# From the backend directory (with venv activated)
python app.py
```

The server will start on `http://127.0.0.1:5001`

### 5. Open in Browser

Open `http://127.0.0.1:5500` in your web browser and start practicing!

## Environment Variables

Create a `.env` file in the `backend/` directory with:

```env
GOOGLE_API_KEY="your_key_here"
MURF_API_KEY="your_key_here"
ASSEMBLYAI_API_KEY="your_key_here"
PORT=5001
FRONTEND_ORIGIN="http://127.0.0.1:5500"
```

**⚠️ IMPORTANT**: Never commit `.env` to Git. Use `.env.example` as a template.

## API Endpoints

### `/start-interview` (POST)
Starts a new interview and returns the first question.

**Request:**
```json
{
  "subject": "Python"
}
```

**Response:** Streaming audio/text of the question

### `/submit-answer` (POST)
Submits an answer and gets the next question.

**Request:** Multipart form with audio file

**Response:** Streaming audio/text of the next question + headers:
- `X-Question-Number`: Current question number
- `X-Interview-Complete`: true/false

### `/get-feedback` (POST)
Gets detailed feedback after interview ends.

**Response:**
```json
{
  "success": true,
  "feedback": {
    "subject": "Python",
    "candidate_score": 4,
    "feedback": "Your explanation was clear...",
    "areas_of_improvement": "Consider discussing edge cases..."
  }
}
```

## How It Works

1. **User selects a topic** (Python, AI, etc.)
2. **Backend initializes interview** with LangChain/LangGraph agent
3. **AI generates first question** based on the topic
4. **User records their answer**
5. **Speech-to-text converts** the audio to text
6. **AI generates next question** based on the user's answer
7. **Repeat for 5 questions**
8. **AI generates detailed feedback** including score and improvement areas

## Troubleshooting

### CORS Errors
Make sure the backend is running on `5001` and the frontend origin in `.env` matches your actual frontend URL.

### "API Key not found" Error
Check that your `.env` file has valid API keys and that it's in the `backend/` directory.

### Port Already in Use
Change the `PORT` in `.env` if 5001 is already in use:
```bash
PORT=5002 python app.py
```

### Speech Recognition Not Working
Ensure `ASSEMBLYAI_API_KEY` is set correctly and your audio file format is supported.

## Future Enhancements

- [ ] Support for more subjects
- [ ] Interview history and progress tracking
- [ ] Detailed analytics on performance
- [ ] Video recording option
- [ ] Mock interview with screen sharing
- [ ] Integrate more LLM providers

## License

MIT License - feel free to use and modify!

## Support

For issues or questions, please check the troubleshooting section or open an issue on GitHub.
