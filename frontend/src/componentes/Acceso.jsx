import { useState } from 'react'
import { api, leerError, setToken } from '../api.js'
import { Aviso, Campo } from './Ui.jsx'

export default function Acceso({ onEntrar }) {
  const [modo, setModo] = useState('login')
  const [form, setForm] = useState({ username: '', password: '' })
  const [err, setErr] = useState({ general: '', campos: {} })
  const [enviando, setEnviando] = useState(false)

  const cambiar = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true); setErr({ general: '', campos: {} })
    try {
      const r = await api(modo === 'login' ? '/auth/login/' : '/auth/registro/',
        { method: 'POST', body: form })
      setToken(r.token)
      onEntrar()
    } catch (ex) {
      setErr(leerError(ex))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta acceso" onSubmit={enviar} noValidate>
      <h2>{modo === 'login' ? 'Iniciar sesión' : 'Crear cuenta'}</h2>
      <Aviso tipo="error">{err.general}</Aviso>
      <Campo etiqueta="Usuario" error={err.campos.username}>
        <input value={form.username} onChange={cambiar('username')} autoComplete="username" required />
      </Campo>
      <Campo etiqueta="Contraseña" error={err.campos.password}>
        <input type="password" value={form.password} onChange={cambiar('password')}
               autoComplete={modo === 'login' ? 'current-password' : 'new-password'} required />
      </Campo>
      <button className="btn primario" disabled={enviando}>
        {enviando ? 'Enviando…' : modo === 'login' ? 'Entrar' : 'Registrarme'}
      </button>
      <button type="button" className="btn enlace"
              onClick={() => { setModo(modo === 'login' ? 'registro' : 'login'); setErr({ general: '', campos: {} }) }}>
        {modo === 'login' ? '¿No tienes cuenta? Regístrate' : 'Ya tengo cuenta'}
      </button>
    </form>
  )
}
