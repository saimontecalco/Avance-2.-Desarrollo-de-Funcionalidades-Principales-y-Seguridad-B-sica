import { useEffect, useState } from 'react'
import { api, getToken, setToken } from './api.js'
import Acceso from './componentes/Acceso.jsx'
import Inventario from './componentes/Inventario.jsx'
import Pedidos from './componentes/Pedidos.jsx'
import { Estado } from './componentes/Ui.jsx'

export default function App() {
  const [usuario, setUsuario] = useState(null)
  const [cargando, setCargando] = useState(Boolean(getToken()))
  const [vista, setVista] = useState('pedidos')

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
    setToken(null); setUsuario(null)
  }

  return (
    <div className="app">
      <header>
        <h1>☕ Cafetería como dice el dicho</h1>
        {usuario && (
          <div className="sesion">
            <span>{usuario.username}{usuario.is_staff ? ' · admin' : ''}</span>
            <button className="btn" onClick={cerrarSesion}>Salir</button>
          </div>
        )}
      </header>
      <main>
        {cargando ? <Estado cargando /> : !usuario ? <Acceso onEntrar={cargarUsuario} /> : (
          <>
            <nav aria-label="Secciones">
              <button className={vista === 'pedidos' ? 'activa' : ''} onClick={() => setVista('pedidos')}>Pedidos</button>
              <button className={vista === 'inventario' ? 'activa' : ''} onClick={() => setVista('inventario')}>Inventario</button>
            </nav>
            {vista === 'pedidos' ? <Pedidos /> : <Inventario usuario={usuario} />}
          </>
        )}
      </main>
    </div>
  )
}
