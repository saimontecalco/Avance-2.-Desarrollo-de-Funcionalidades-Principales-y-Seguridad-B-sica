import { useState } from 'react'
import { api, leerError, listarTodos } from '../api.js'
import { useCarga } from '../hooks.js'
import { Aviso, Campo, Estado, dinero } from './Ui.jsx'

export const LECHES = [
  { valor: 'ninguna', etiqueta: 'Sin leche' },
  { valor: 'deslactosada', etiqueta: 'Deslactosada' },
  { valor: 'entera', etiqueta: 'Entera' },
  { valor: 'semidescremada', etiqueta: 'Semidescremada' },
  { valor: 'almendras', etiqueta: 'De almendras' },
]
export const etiquetaLeche = (v) => LECHES.find((l) => l.valor === v)?.etiqueta ?? v

const PASOS = ['Elige tus cafés', 'Leche y azúcar', 'Confirmar']

function Pasos({ paso }) {
  return (
    <ol className="pasos" aria-label="Progreso del pedido">
      {PASOS.map((t, i) => (
        <li key={t} className={i + 1 === paso ? 'actual' : i + 1 < paso ? 'hecho' : ''}
            aria-current={i + 1 === paso ? 'step' : undefined}>
          <span>{i + 1}</span> {t}
        </li>
      ))}
    </ol>
  )
}

// Paso 1: tarjetas de café con selector de cantidad; se pueden combinar varios tipos.
function PasoCafes({ cafes, cantidades, setCantidad }) {
  return (
    <div className="menu">
      {cafes.map((c) => {
        const n = cantidades[c.id] || 0
        const max = c.disponible
        const quedan = max - n  // lo que queda después de lo que ya elegiste
        return (
          <div key={c.id} className={`cafe-tarjeta${n > 0 ? ' elegido' : ''}${max === 0 ? ' agotado-tarjeta' : ''}`}>
            <div>
              <h3>{c.nombre}</h3>
              <p className="precio">{dinero(c.precio)}</p>
              <p className="nota">{max === 0 ? <span className="agotado">Agotado</span>
                : quedan === 0 ? <span className="agotado">Quedan 0</span>
                : `Quedan ${quedan}`}</p>
            </div>
            <div className="cantidad" role="group" aria-label={`Cantidad de ${c.nombre}`}>
              <button type="button" className="btn" aria-label={`Quitar un ${c.nombre}`}
                      disabled={n === 0} onClick={() => setCantidad(c.id, n - 1)}>−</button>
              <output aria-live="polite">{n}</output>
              <button type="button" className="btn" aria-label={`Agregar un ${c.nombre}`}
                      disabled={n >= max} onClick={() => setCantidad(c.id, n + 1)}>+</button>
            </div>
          </div>
        )
      })}
    </div>
  )
}

// Paso 2: leche (una opción) y azúcar (sí / no).
function PasoExtras({ leche, setLeche, azucar, setAzucar }) {
  return (
    <div className="extras">
      <fieldset className="opciones">
        <legend>¿Quieres leche?</legend>
        {LECHES.map((l) => (
          <label key={l.valor} className={`opcion${leche === l.valor ? ' elegida' : ''}`}>
            <input type="radio" name="leche" value={l.valor} checked={leche === l.valor}
                   onChange={() => setLeche(l.valor)} />
            {l.etiqueta}
          </label>
        ))}
      </fieldset>
      <fieldset className="opciones">
        <legend>¿Con azúcar?</legend>
        {[[true, 'Con azúcar'], [false, 'Sin azúcar']].map(([v, t]) => (
          <label key={t} className={`opcion${azucar === v ? ' elegida' : ''}`}>
            <input type="radio" name="azucar" checked={azucar === v} onChange={() => setAzucar(v)} />
            {t}
          </label>
        ))}
      </fieldset>
    </div>
  )
}

/** Flujo para pedir: 1) cafés (varios a la vez) → 2) leche y azúcar → 3) confirmar. */
export default function Pedir({ usuario, onTerminar }) {
  const menu = useCarga(() => listarTodos('/inventario/?activo=true'), [])
  const [paso, setPaso] = useState(1)
  const [cantidades, setCantidades] = useState({})
  const [leche, setLeche] = useState('ninguna')
  const [azucar, setAzucar] = useState(false)
  const [nombre, setNombre] = useState(usuario?.username ?? '')
  const [err, setErr] = useState({ general: '', campos: {} })
  const [enviando, setEnviando] = useState(false)

  const cafes = (menu.datos ?? []).map((c) => ({ ...c, disponible: c.stock }))

  const elegidos = cafes.filter((c) => cantidades[c.id] > 0)
  const totalCafes = elegidos.reduce((s, c) => s + cantidades[c.id], 0)
  const subtotal = elegidos.reduce((s, c) => s + Number(c.precio) * cantidades[c.id], 0)

  const setCantidad = (id, n) => setCantidades((q) => ({ ...q, [id]: Math.max(0, n) }))

  async function confirmar() {
    setEnviando(true); setErr({ general: '', campos: {} })
    try {
      const body = {
        nombre_cliente: nombre, leche, azucar,
        lineas: elegidos.map((c) => ({ cafe: c.id, cantidad: cantidades[c.id] })),
      }
      const pedido = await api('/pedidos/', { method: 'POST', body })
      let restantes = {}
      try {  // existencias que quedan después de este pedido
        restantes = Object.fromEntries((await listarTodos('/inventario/?activo=true')).map((c) => [c.id, c.stock]))
      } catch { /* el ticket se muestra igual sin esta sección */ }
      onTerminar({ pedido, restantes })
    } catch (ex) {
      setErr(leerError(ex))
    } finally {
      setEnviando(false)
    }
  }

  const errorCampos = Object.entries(err.campos).filter(([k]) => k !== 'nombre_cliente').map(([, v]) => v).join(' ')

  return (
    <section className="tarjeta asistente">
      <div className="encabezado-seccion">
        <h2>Haz tu pedido</h2>
      </div>
      <Pasos paso={paso} />

      <Estado cargando={menu.cargando} error={menu.error} onReintentar={menu.recargar}
              vacio={cafes.length === 0} textoVacio="Por ahora no hay cafés disponibles.">
        {paso === 1 && <PasoCafes cafes={cafes} cantidades={cantidades} setCantidad={setCantidad} />}
        {paso === 2 && <PasoExtras leche={leche} setLeche={setLeche} azucar={azucar} setAzucar={setAzucar} />}
        {paso === 3 && (
          <div className="confirmacion">
            <Aviso tipo="error">{err.general || errorCampos}</Aviso>
            <ul className="resumen">
              {elegidos.map((c) => (
                <li key={c.id}><span>{cantidades[c.id]} × {c.nombre}</span><span>{dinero(Number(c.precio) * cantidades[c.id])}</span></li>
              ))}
              <li><span>Leche</span><span>{etiquetaLeche(leche)}</span></li>
              <li><span>Azúcar</span><span>{azucar ? 'Con azúcar' : 'Sin azúcar'}</span></li>
            </ul>
            <Campo etiqueta="Nombre para el pedido" error={err.campos.nombre_cliente}>
              <input value={nombre} maxLength={100} onChange={(e) => setNombre(e.target.value)} required />
            </Campo>
          </div>
        )}

        <div className="pie-asistente">
          <p className="nota" aria-live="polite">
            {totalCafes === 0 ? 'Aún no has elegido ningún café.'
              : `${totalCafes} ${totalCafes === 1 ? 'café' : 'cafés'} · subtotal ${dinero(subtotal)} (+16 % impuesto, −10 % descuento)`}
            {totalCafes > 5 && ' · pedido mayorista'}
          </p>
          <div className="acciones">
            {paso > 1 && <button className="btn" onClick={() => setPaso(paso - 1)} disabled={enviando}>← Atrás</button>}
            {paso < 3
              ? <button className="btn primario" onClick={() => setPaso(paso + 1)} disabled={totalCafes === 0}>Siguiente →</button>
              : <button className="btn primario" onClick={confirmar} disabled={enviando || totalCafes === 0}>
                  {enviando ? 'Enviando…' : 'Confirmar pedido'}
                </button>}
          </div>
        </div>
      </Estado>
    </section>
  )
}
