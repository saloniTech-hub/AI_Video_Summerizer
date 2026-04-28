
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


---

## 📦 Installation  

```bash
git clone https://github.com/yourusername/ai-video-summarizer.git
cd ai-video-summarizer
pip install -r requirements.txt
python app.py
