import axios from "axios"

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000"

const client = axios.create({ baseURL: API_BASE })

export async function uploadFile(file) {
  const form = new FormData()
  form.append("file", file)
  const resp = await client.post(`/upload`, form, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return resp.data
}

export async function askQuestion(question) {
  const resp = await client.post(`/chat`, { question })
  return resp.data
}
