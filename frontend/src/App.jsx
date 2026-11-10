import { useEffect, useState } from 'react'
import { api, getToken, setToken } from './api.js'
import Acceso from './componentes/Acceso.jsx'
import Pedir from './componentes/Pedir.jsx'
import Ticket from './componentes/Ticket.jsx'
import { Estado } from './componentes/Ui.jsx'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(Boolean(getToken()))
  const [listo, setListo] = useState(null) // pedido recién confirmado

  async function cargarUsuario() {
    setCargando(true)
    try { setUsuario(await api('/auth/yo/')) } catch { setUsuario(null) } finally { setCargando(false) }
  }

  useEffect(() => { if (getToken()) cargarUsuario() }, [])
  useEffect(() => {
    const salir = () => setUsuario(null)
    window.addEventListener('sesion-expirada', salir)
    return () => window.removeEventListener('sesion-expirada', salir)
  }, [])

  async function cerrarSesion() {
    try { await api('/auth/logout/', { method: 'POST' }) } catch { /* ya expiró */ }
    setToken(null); setUsuario(null); setListo(null)
  }

  return (
    <div className="app">
      <header>
        <h1>☕ Cafetería como dice el dicho</h1>
        {usuario && (
          <div className="sesion">
            <span>{usuario.username}</span>
            <button className="btn" onClick={cerrarSesion}>Salir</button>
          </div>
        )}
      </header>
      <main>
        {cargando ? <Estado cargando /> : !usuario ? <Acceso onEntrar={cargarUsuario} /> : (
          listo ? (
            <section className="tarjeta confirmado">
              <h2>¡Pedido realizado con éxito!</h2>
              <Ticket pedido={listo.pedido} restantes={listo.restantes} />
              <button className="btn primario" onClick={() => setListo(null)}>Hacer otro pedido</button>
            </section>
          ) : <Pedir usuario={usuario} onTerminar={setListo} />
        )}
      </main>
    </div>
  )
}
