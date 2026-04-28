
# 🎥 AI Video Summarizer  

An intelligent AI-based system that automatically converts long videos into **English transcripts and structured summaries**. This project helps users quickly extract key insights from lengthy video content without watching the entire video.  

---

## 🚀 Features  

- Multilingual video support  
- Speech-to-text conversion using AI  
- Automatic English translation  
- Chunk-based processing for long videos  
- AI-powered summarization  
- Real-time progress tracking  
- Downloadable PDF (Transcript + Summary)  
- User-friendly web interface  

---

## 🏗️ System Architecture  

Video Upload → Audio Extraction → Chunking → Speech-to-Text → Translation → Transcript → Summarization → PDF Output  

---

## 🛠️ Technologies Used  

- Backend: Python, Flask  
- Frontend: HTML, CSS, JavaScript  
- Speech Recognition: Whisper AI  
- Summarization: LLM (LLaMA)  
- Audio Processing: FFmpeg  
- PDF Generation: jsPDF  

---

## ⚙️ How It Works  

1. Upload a video file  
2. Extract audio using FFmpeg  
3. Split audio into chunks  
4. Convert speech to English text  
5. Combine transcript  
6. Generate summary using AI  
7. Display and download results  

--
## Screenshot
<img width="1222" height="1005" alt="Screenshot 2025-12-22 220706" src="https://github.com/user-attachments/assets/fee941a0-6074-4923-b966-bbb82d1bfccf" />

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```
git clone https://github.com/saloniTech-hub/AI_Video_Summerizer.git
cd your-repo-name
```

### 2. Create Virtual Environment (Recommended)

```
python -m venv venv
```

### 3. Activate Virtual Environment

**Windows:**

```
venv\Scripts\activate
```

**Mac/Linux:**

```
source venv/bin/activate
```

### 4. Install Dependencies

```
pip install flask
pip install requests
pip install python-dotenv
```

*(Or if requirements.txt is available)*

```
pip install -r requirements.txt
```

### 5. Configure Environment Variables

Create a `.env` file in the root folder and add:

```
API_KEY=your_api_key_here
```

### 6. Run the Application

```
python app.py
```

### 7. Open in Browser

```
http://127.0.0.1:5000/
```



## requirements.txt
<img width="402" height="204" alt="Screenshot 2026-04-28 193545" src="https://github.com/user-attachments/assets/127c1e98-a1c1-409b-b342-274b7194a015" />

