import { useState } from 'react'
import { api } from '../api.js'
import { useCarga } from '../hooks.js'
import { Aviso, Estado, Paginador, dinero } from './Ui.jsx'
import Pedir, { etiquetaLeche } from './Pedir.jsx'

// Historial de pedidos; "Editar" reabre el flujo por pasos con los datos del pedido.
export default function Pedidos({ usuario, avisoInicial = '', irAPedir }) {
  const [pagina, setPagina] = useState(1)
  const [edicion, setEdicion] = useState(null)
  const [aviso, setAviso] = useState(avisoInicial)
  const lista = useCarga(() => api(`/pedidos/?page=${pagina}`), [pagina])

  if (edicion) {
    return <Pedir usuario={usuario} inicial={edicion} onCancelar={() => setEdicion(null)}
                  onTerminar={(msg) => { setEdicion(null); setAviso(msg); lista.recargar() }} />
  }

  return (
    <section>
      <div className="encabezado-seccion">
        <h2>Mis pedidos</h2>
        <button className="btn primario" onClick={irAPedir}>+ Nuevo pedido</button>
      </div>
      <Aviso>{aviso}</Aviso>
      <Estado cargando={lista.cargando} error={lista.error} onReintentar={lista.recargar}
              vacio={lista.datos && lista.datos.results.length === 0} textoVacio="Todavía no hay pedidos.">
        {lista.datos && (
          <>
            <div className="tabla-scroll">
              <table>
                <thead><tr><th>#</th><th>Cliente</th><th>Cafés</th><th>Leche</th><th>Azúcar</th><th>Total</th><th>Tipo</th><th></th></tr></thead>
                <tbody>
                  {lista.datos.results.map((p) => (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>{p.nombre_cliente}</td>
                      <td>{p.lineas.map((l) => `${l.cantidad} × ${l.cafe_nombre}`).join(', ')}</td>
                      <td>{etiquetaLeche(p.leche)}</td>
                      <td>{p.azucar ? 'Sí' : 'No'}</td>
                      <td>{dinero(p.total)}</td>
                      <td>{p.es_mayorista ? 'Mayorista' : 'Regular'}</td>
                      <td><button className="btn" onClick={() => { setAviso(''); setEdicion(p) }}>Editar</button></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginador pagina={pagina} setPagina={setPagina} data={lista.datos} />
          </>
        )}
      </Estado>
    </section>
  )
}
