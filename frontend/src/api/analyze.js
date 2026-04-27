/**
 * Client for the microstructure analysis backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * @param {File} file - Image file (PNG, JPEG, etc.)
 * @returns {Promise<{ original_b64: string, mask_b64: string, pore_count: number, porosity_percent: number }>}
 */
export async function analyzeImage(file) {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    const message = Array.isArray(err.detail) ? err.detail.map((d) => d.msg).join(', ') : (err.detail || res.statusText)
    throw new Error(message)
  }

  return res.json()
}
