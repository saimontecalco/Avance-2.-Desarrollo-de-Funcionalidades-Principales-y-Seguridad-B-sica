// Cliente de la API Django. El token se guarda en localStorage y se envía como Bearer.
const KEY = 'cafeteria_token'

export const getToken = () => {
  try { return localStorage.getItem(KEY) } catch { return null }
}
export const setToken = (t) => {
  try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) } catch { /* sin storage */ }
}

export class ApiError extends Error {
  constructor(status, data) {
    super('Error de API')
    this.status = status
    this.data = data
  }
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = { Accept: 'application/json' }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`

  let res
  try {
    res = await fetch('/api' + path, {
      method, headers, body: body !== undefined ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, { detail: 'No se pudo conectar con el servidor. ¿Está corriendo Django?' })
  }
  if (res.status === 204) return null
  const data = await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && token) {
      setToken(null)
      window.dispatchEvent(new Event('sesion-expirada'))
    }
    throw new ApiError(res.status, data)
  }
  return data
}

// Convierte el error de DRF ({campo: [msgs]} o {detail}) en {general, campos}.
export function leerError(err) {
  const d = err?.data
  if (!d || typeof d !== 'object') return { general: 'Ocurrió un error inesperado.', campos: {} }
  const campos = {}
  let general = d.detail || ''
  for (const [k, v] of Object.entries(d)) {
    if (k === 'detail') continue
    const msg = Array.isArray(v) ? v.join(' ') : String(v)
    if (k === 'non_field_errors') general = msg
    else campos[k] = msg
  }
  if (err.status === 429) general = 'Demasiados intentos. Espera un momento.'
  return { general, campos }
}

// Descarga todas las páginas de un listado paginado.
export async function listarTodos(path) {
  let url = path, items = []
  while (url) {
    const data = await api(url)
    items = items.concat(data.results)
    url = data.next ? data.next.replace(/^https?:\/\/[^/]+\/api/, '') : null
  }
  return items
}
