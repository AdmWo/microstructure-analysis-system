/**
 * Client for the microstructure analysis backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * @param {File} file - Image file (PNG, JPEG, etc.)
 * @param {Object} params - Workflow parameters for all scientific stages.
 * @returns {Promise<{ original_b64: string, roi_b64: string, mask_b64: string, pore_count: number, aa_percent: number, vv_percent: number }>}
 */
export async function analyzeImage(file, params) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('params', JSON.stringify(params))

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
