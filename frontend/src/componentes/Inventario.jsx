import { useState } from 'react'
import { api, leerError } from '../api.js'
import { useCarga } from '../hooks.js'
import { Aviso, Campo, Estado, Paginador, dinero } from './Ui.jsx'

const VACIO = { nombre: '', precio: '', stock: '', activo: true }

function FormProducto({ inicial, onGuardado, onCancelar }) {
  const [f, setF] = useState(inicial ? { ...inicial } : VACIO)
  const [err, setErr] = useState({ general: '', campos: {} })
  const [enviando, setEnviando] = useState(false)
  const editando = Boolean(inicial?.id)

  async function enviar(e) {
    e.preventDefault()
    setEnviando(true); setErr({ general: '', campos: {} })
    try {
      const body = { nombre: f.nombre, precio: f.precio, stock: f.stock === '' ? '' : Number(f.stock), activo: f.activo }
      await api(editando ? `/inventario/${inicial.id}/` : '/inventario/', { method: editando ? 'PUT' : 'POST', body })
      onGuardado(editando ? 'Producto actualizado' : 'Producto agregado')
    } catch (ex) {
      setErr(leerError(ex))
    } finally {
      setEnviando(false)
    }
  }

  return (
    <form className="tarjeta formulario" onSubmit={enviar} noValidate>
      <h3>{editando ? `Editar «${inicial.nombre}»` : 'Agregar producto'}</h3>
      <Aviso tipo="error">{err.general}</Aviso>
      <div className="fila">
        <Campo etiqueta="Nombre" error={err.campos.nombre}>
          <input value={f.nombre} maxLength={60} onChange={(e) => setF({ ...f, nombre: e.target.value })} required />
        </Campo>
        <Campo etiqueta="Precio ($)" error={err.campos.precio}>
          <input inputMode="decimal" value={f.precio} onChange={(e) => setF({ ...f, precio: e.target.value })} required />
        </Campo>
        <Campo etiqueta="Existencias" error={err.campos.stock}>
          <input inputMode="numeric" value={f.stock} onChange={(e) => setF({ ...f, stock: e.target.value })} required />
        </Campo>
      </div>
      <label className="check">
        <input type="checkbox" checked={f.activo} onChange={(e) => setF({ ...f, activo: e.target.checked })} /> Disponible
      </label>
      <div className="acciones">
        <button className="btn primario" disabled={enviando}>{enviando ? 'Guardando…' : 'Guardar'}</button>
        {onCancelar && <button type="button" className="btn" onClick={onCancelar}>Cancelar</button>}
      </div>
    </form>
  )
}

export default function Inventario({ usuario }) {
  const [buscar, setBuscar] = useState('')
  const [pagina, setPagina] = useState(1)
  const [edicion, setEdicion] = useState(null) // null | 'nuevo' | producto
  const [aviso, setAviso] = useState('')
  const { datos, cargando, error, recargar } = useCarga(
    () => api(`/inventario/?page=${pagina}&search=${encodeURIComponent(buscar)}`), [pagina, buscar])

  const guardado = (msg) => { setEdicion(null); setAviso(msg); recargar() }

  return (
    <section>
      <div className="encabezado-seccion">
        <h2>Inventario</h2>
        {usuario.is_staff && !edicion && (
          <button className="btn primario" onClick={() => { setAviso(''); setEdicion('nuevo') }}>+ Agregar producto</button>
        )}
      </div>
      <Aviso>{aviso}</Aviso>
      {edicion && usuario.is_staff && (
        <FormProducto inicial={edicion === 'nuevo' ? null : edicion} onGuardado={guardado} onCancelar={() => setEdicion(null)} />
      )}
      {!usuario.is_staff && <p className="nota">Solo el personal administrativo puede modificar el inventario.</p>}
      <input className="buscador" type="search" placeholder="Buscar producto…" aria-label="Buscar producto"
             value={buscar} onChange={(e) => { setBuscar(e.target.value); setPagina(1) }} />
      <Estado cargando={cargando} error={error} onReintentar={recargar}
              vacio={datos && datos.results.length === 0} textoVacio="No hay productos que coincidan.">
        {datos && (
          <>
            <div className="tabla-scroll">
              <table>
                <thead><tr><th>Producto</th><th>Precio</th><th>Existencias</th><th>Estado</th>{usuario.is_staff && <th></th>}</tr></thead>
                <tbody>
                  {datos.results.map((p) => (
                    <tr key={p.id}>
                      <td>{p.nombre}</td>
                      <td>{dinero(p.precio)}</td>
                      <td className={p.stock === 0 ? 'agotado' : ''}>{p.stock}</td>
                      <td>{p.activo ? 'Disponible' : 'No disponible'}</td>
                      {usuario.is_staff && <td><button className="btn" onClick={() => { setAviso(''); setEdicion(p) }}>Editar</button></td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Paginador pagina={pagina} setPagina={setPagina} data={datos} />
          </>
        )}
      </Estado>
    </section>
  )
}
