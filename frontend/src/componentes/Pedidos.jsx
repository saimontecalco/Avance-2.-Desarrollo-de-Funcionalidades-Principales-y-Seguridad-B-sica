import { useState } from 'react'
import { api, leerError, listarTodos } from '../api.js'
import { useCarga } from '../hooks.js'
import { Aviso, Campo, Estado, Paginador, dinero } from './Ui.jsx'

function FormPedido({ inicial, cafes, onGuardado, onCancelar }) {
  const editando = Boolean(inicial?.id)
  const [f, setF] = useState(inicial
    ? { nombre_cliente: inicial.nombre_cliente, cafe: String(inicial.cafe), cantidad: String(inicial.cantidad) }
    : { nombre_cliente: '', cafe: '', cantidad: '1' })
  const [err, setErr] = useState({ general: '', campos: {} })
  const [enviando, setEnviando] = useState(false)
  const seleccionado = cafes.find((c) => String(c.id) === f.cafe)

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true); setErr({ general: '', campos: {} })
    try {
      const body = { nombre_cliente: f.nombre_cliente, cafe: f.cafe === '' ? null : Number(f.cafe),
                     cantidad: f.cantidad === '' ? null : Number(f.cantidad) }
      await api(editando ? `/pedidos/${inicial.id}/` : '/pedidos/', { method: editando ? 'PUT' : 'POST', body })
      onGuardado(editando ? 'Pedido actualizado' : 'Pedido realizado con éxito')
    } catch (ex) {
      setErr(leerError(ex))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta formulario" onSubmit={enviar} noValidate>
      <h3>{editando ? `Editar pedido #${inicial.id}` : 'Nuevo pedido'}</h3>
      <Aviso tipo="error">{err.general}</Aviso>
      <div className="fila">
        <Campo etiqueta="Nombre del cliente" error={err.campos.nombre_cliente}>
          <input value={f.nombre_cliente} maxLength={100} onChange={(e) => setF({ ...f, nombre_cliente: e.target.value })} required />
        </Campo>
        <Campo etiqueta="Café" error={err.campos.cafe}>
          <select value={f.cafe} onChange={(e) => setF({ ...f, cafe: e.target.value })} required>
            <option value="">Selecciona un café</option>
            {cafes.map((c) => (
              <option key={c.id} value={c.id} disabled={c.stock === 0 && String(c.id) !== f.cafe}>
                {c.nombre} — {dinero(c.precio)} ({c.stock} disp.)
              </option>
            ))}
          </select>
        </Campo>
        <Campo etiqueta="Cantidad" error={err.campos.cantidad}>
          <input inputMode="numeric" value={f.cantidad} onChange={(e) => setF({ ...f, cantidad: e.target.value })} required />
        </Campo>
      </div>
      {seleccionado && Number(f.cantidad) > 0 && (
        <p className="nota">Subtotal estimado: {dinero(seleccionado.precio * Number(f.cantidad))} (+16 % impuesto, −10 % descuento)</p>
      )}
      <div className="acciones">
        <button className="btn primario" disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar'}</button>
        <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>
      </div>
    </form>
  )
}

export default function Pedidos() {
  const [pagina, setPagina] = useState(1)
  const [edicion, setEdicion] = useState(null) // null | 'nuevo' | pedido
  const [aviso, setAviso] = useState('')
  const lista = useCarga(() => api(`/pedidos/?page=${pagina}`), [pagina])
  const cafes = useCarga(() => listarTodos('/inventario/?activo=true'), [])

  const guardado = (msg) => { setEdicion(null); setAviso(msg); lista.recargar(); cafes.recargar() }

  return (
    <section>
      <div className="encabezado-seccion">
        <h2>Pedidos</h2>
        {!edicion && <button className="btn primario" onClick={() => { setAviso(''); setEdicion('nuevo') }}>+ Nuevo pedido</button>}
      </div>
      <Aviso>{aviso}</Aviso>
      {edicion && (
        <Estado cargando={cafes.cargando} error={cafes.error} onReintentar={cafes.recargar}>
          {cafes.datos && (
            <FormPedido inicial={edicion === 'nuevo' ? null : edicion}
                        cafes={edicion === 'nuevo' || cafes.datos.some((c) => c.id === edicion.cafe)
                          ? cafes.datos : [...cafes.datos, { id: edicion.cafe, nombre: edicion.cafe_nombre, precio: edicion.precio_unitario, stock: 0 }]}
                        onGuardado={guardado} onCancelar={() => setEdicion(null)} />
          )}
        </Estado>
      )}
      <Estado cargando={lista.cargando} error={lista.error} onReintentar={lista.recargar}
              vacio={lista.datos && lista.datos.results.length === 0} textoVacio="Todavía no hay pedidos.">
        {lista.datos && (
          <>
            <div className="tabla-scroll">
              <table>
                <thead><tr><th>#</th><th>Cliente</th><th>Café</th><th>Cant.</th><th>Total</th><th>Tipo</th><th></th></tr></thead>
                <tbody>
                  {lista.datos.results.map((p) => (
                    <tr key={p.id}>
                      <td>{p.id}</td>
                      <td>{p.nombre_cliente}</td>
                      <td>{p.cafe_nombre}</td>
                      <td>{p.cantidad}</td>
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
