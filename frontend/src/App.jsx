import React, { useState, useRef, useEffect } from "react"
import { uploadFile, askQuestion } from "./api"

function ChatBubble({ text, from }) {
  const cls = `bubble ${from}`
  return <div className={cls} dangerouslySetInnerHTML={{ __html: text }} />
}

function SourceSnippet({ snippet, index }) {
  return (
    <div className="source">
      <div className="source-header">Source {index + 1}</div>
      <div className="source-body">{snippet}</div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([
    { id: 1, from: "bot", text: "Welcome! Upload a document to get started." },
  ])
  const [file, setFile] = useState(null)
  const [dragActive, setDragActive] = useState(false)
  const [previewText, setPreviewText] = useState("")
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState("")
  const [question, setQuestion] = useState("")
  const [isUploading, setIsUploading] = useState(false)
  const [isAsking, setIsAsking] = useState(false)
  const [error, setError] = useState("")
  const messagesRef = useRef(null)

  function pushMessage(from, text) {
    setMessages((m) => [...m, { id: Date.now() + Math.random(), from, text }])
    setTimeout(() => {
      messagesRef.current?.scrollTo({ top: messagesRef.current.scrollHeight, behavior: "smooth" })
    }, 50)
  }

  async function handleUpload(e) {
    e.preventDefault()
    if (!file) return
    setError("")
    setIsUploading(true)
    setStatus("Uploading...")
    setProgress(6)
    // simulated progress while uploading
    const progInterval = setInterval(() => {
      setProgress((p) => Math.min(90, p + Math.floor(Math.random() * 10)))
    }, 400)
    pushMessage("user", `Uploading <strong>${file.name}</strong>...`)
    try {
      const res = await uploadFile(file)
      // ensure progress reaches 100 for brief moment
      setProgress(100)
      await new Promise((r) => setTimeout(r, 300))
      setProgress(0)
      clearInterval(progInterval)
      setStatus("Uploaded")
      pushMessage("bot", `Upload result: ${res.message || "OK"}`)
    } catch (err) {
      clearInterval(progInterval)
      const msg = err?.response?.data?.detail || err.message
      setError(msg)
      setStatus("Upload failed")
      pushMessage("bot", `Upload error: ${msg}`)
    } finally {
      setIsUploading(false)
    }
  }

  // handle drag-and-drop
  function onDragOver(e) {
    e.preventDefault()
    setDragActive(true)
  }
  function onDragLeave(e) {
    e.preventDefault()
    setDragActive(false)
  }
  function onDrop(e) {
    e.preventDefault()
    setDragActive(false)
    const f = e.dataTransfer.files?.[0]
    if (f) {
      setFile(f)
    }
  }

  // preview small text files
  useEffect(() => {
    setPreviewText("")
    if (!file) return
    const name = file.name.toLowerCase()
    if (name.endsWith(".txt") || name.endsWith(".md")) {
      const reader = new FileReader()
      reader.onload = (ev) => {
        const txt = String(ev.target.result || "").slice(0, 1000)
        setPreviewText(txt)
      }
      reader.readAsText(file)
    }
  }, [file])

  async function handleAsk(e) {
    e.preventDefault()
    if (!question) return
    setError("")
    setIsAsking(true)
    pushMessage("user", question)
    setQuestion("")
    try {
      const res = await askQuestion(question)
      const ans = res.answer || "(no answer)"
      pushMessage("bot", ans.replace(/\n/g, "<br/>"))
      if (Array.isArray(res.source_documents) && res.source_documents.length) {
        res.source_documents.forEach((s) => {
          pushMessage("source", s)
        })
      }
    } catch (err) {
      const msg = err?.response?.data?.detail || err.message
      setError(msg)
      pushMessage("bot", `Error: ${msg}`)
    } finally {
      setIsAsking(false)
    }
  }

  return (
    <div className="page">
      <div className="uploader-center">
        <div className="uploader-card">
          <h3>Upload Document</h3>
          <div
            className={`dropzone ${dragActive ? "active" : ""}`}
            onDragOver={onDragOver}
            onDragEnter={onDragOver}
            onDragLeave={onDragLeave}
            onDrop={onDrop}
          >
            <input
              className="file-input"
              type="file"
              accept=".pdf,.txt,.md"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              disabled={isUploading || isAsking}
            />
            <div className="drop-content">
              <div className="drop-title">Drag & drop a file here</div>
              <div className="drop-sub">or click to browse — PDF, TXT, MD</div>
              {file && <div className="file-info">Selected: {file.name} — {(file.size/1024).toFixed(1)} KB</div>}
            </div>
          </div>

          <div style={{ marginTop: 8 }}>
            <button className="primary" onClick={handleUpload} disabled={!file || isUploading || isAsking}>
              {isUploading ? "Uploading..." : "Upload"}
            </button>
          </div>

          {progress > 0 && (
            <div className="progress-wrap" aria-hidden>
              <div className="progress-bar" style={{ width: `${progress}%` }} />
            </div>
          )}

          {previewText && (
            <div className="preview">
              <div className="preview-title">Preview</div>
              <pre className="preview-body">{previewText}</pre>
            </div>
          )}

          <div className="status">{status}</div>
        </div>
      </div>

      <div className="chat-widget">
        <div className="chat-header">Chatbot</div>
        <div className="chat-messages" ref={messagesRef}>
          {messages.map((m) => (
            <ChatBubble key={m.id} from={m.from} text={m.text} />
          ))}
        </div>
        <form className="chat-input" onSubmit={handleAsk}>
          <input
            placeholder="Ask a question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={isAsking || isUploading}
          />
          <button type="submit" disabled={isAsking || isUploading}>
            {isAsking ? "Thinking..." : "Ask"}
          </button>
        </form>
        {error && <div className="error">{error}</div>}
      </div>
    </div>
  )
}
