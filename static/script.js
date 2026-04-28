const uploadBox = document.getElementById("uploadBox");
const videoInput = document.getElementById("videoInput");
const previewVideo = document.getElementById("previewVideo");
const uploadText = document.getElementById("uploadText");

const summarizeBtn = document.getElementById("summarizeBtn");
const clearBtn = document.getElementById("clearBtn");

const summaryBox = document.getElementById("summaryBox");
const transcriptBox = document.getElementById("transcriptBox");

const loader = document.getElementById("loader");
const progressFill = document.getElementById("progressFill");
const progressText = document.getElementById("progressText");

const downloadSummaryBtn = document.getElementById("downloadSummaryBtn");
const downloadTranscriptBtn = document.getElementById("downloadTranscriptBtn");

let selectedFile = null;
let pollInterval = null;

/* =======================
   UPLOAD & PREVIEW
======================= */
uploadBox.onclick = () => videoInput.click();

videoInput.onchange = (e) => {
  selectedFile = e.target.files[0];
  if (!selectedFile) return;

  previewVideo.src = URL.createObjectURL(selectedFile);
  previewVideo.style.display = "block";
  uploadText.style.display = "none";
};

/* =======================
   PROGRESS
======================= */
function setProgress(percent, text) {
  progressFill.style.width = percent + "%";
  progressText.innerText = text;
}

/* =======================
   START PROCESS
======================= */
summarizeBtn.onclick = async () => {
  if (!selectedFile) {
    alert("Please upload a video first!");
    return;
  }

  loader.style.display = "block";
  setProgress(5, "Uploading video...");

  summaryBox.innerText = "Processing...";
  transcriptBox.innerText = "";

  downloadSummaryBtn.disabled = true;
  downloadTranscriptBtn.disabled = true;

  const formData = new FormData();
  formData.append("video", selectedFile);

  let res;
  try {
    res = await fetch("http://127.0.0.1:5000/process", {
      method: "POST",
      body: formData
    });
  } catch (err) {
    alert("Backend not reachable");
    loader.style.display = "none";
    return;
  }

  const data = await res.json();
  const jobId = data.job_id;

  pollInterval = setInterval(async () => {
    try {
      const r = await fetch(`http://127.0.0.1:5000/status/${jobId}`);
      const d = await r.json();

      if (d.state === "transcribing") {
        setProgress(
          d.progress,
          `Transcribing chunk ${d.chunk}/${d.total_chunks}`
        );
      }

      if (d.state === "summarizing") {
        setProgress(92, "Generating summary...");
      }

      if (d.state === "done") {
        setProgress(100, "Completed ✔");

        summaryBox.innerText = d.summary || "No summary generated";
        transcriptBox.innerText = d.transcript || "No transcript generated";

        loader.style.display = "none";
        downloadSummaryBtn.disabled = false;
        downloadTranscriptBtn.disabled = false;

        clearInterval(pollInterval);
      }

      if (d.state === "error") {
        alert(d.error || "Something went wrong");
        loader.style.display = "none";
        clearInterval(pollInterval);
      }
    } catch (err) {
      alert("Lost connection to server");
      loader.style.display = "none";
      clearInterval(pollInterval);
    }
  }, 1500);
};

/* =======================
   CLEAR
======================= */
clearBtn.onclick = () => {
  selectedFile = null;
  videoInput.value = "";
  previewVideo.style.display = "none";
  uploadText.style.display = "block";

  summaryBox.innerText = "";
  transcriptBox.innerText = "";

  setProgress(0, "Idle");
  loader.style.display = "none";

  downloadSummaryBtn.disabled = true;
  downloadTranscriptBtn.disabled = true;
};

/* =======================
   PDF EXPORT (IMPROVED)
======================= */
function savePDF(filename, reportTitle, contentText) {
  const { jsPDF } = window.jspdf;
  const pdf = new jsPDF("p", "pt", "a4");

  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();

  let y = 40;

  // Title
  pdf.setFont("Times", "Bold");
  pdf.setFontSize(18);
  pdf.text(reportTitle, pageWidth / 2, y, { align: "center" });

  y += 22;

  // Meta
  pdf.setFont("Times", "Normal");
  pdf.setFontSize(10);
  const dateStr = new Date().toLocaleString();
  pdf.text(
    `Created by AI Video Summarizer • ${dateStr}`,
    pageWidth / 2,
    y,
    { align: "center" }
  );

  y += 30;

  // Content
  pdf.setFontSize(10);
  const marginX = 40;
  const maxWidth = pageWidth - marginX * 2;
  const lineHeight = 14;

  const lines = pdf.splitTextToSize(contentText, maxWidth);

  for (let i = 0; i < lines.length; i++) {
    if (y + lineHeight > pageHeight - 40) {
      pdf.addPage();
      y = 40;
    }
    pdf.text(lines[i], marginX, y);
    y += lineHeight;
  }

  pdf.save(filename);
}

/* =======================
   PDF BUTTONS
======================= */
downloadSummaryBtn.onclick = () => {
  savePDF(
    "Video_Summary_Report.pdf",
    "VIDEO SUMMARY REPORT",
    summaryBox.innerText
  );
};

downloadTranscriptBtn.onclick = () => {
  savePDF(
    "Video_Transcript_Report.pdf",
    "VIDEO TRANSCRIPT REPORT",
    transcriptBox.innerText
  );
};
