// Piezas reutilizables de interfaz.
export function Estado({ cargando, error, vacio, textoVacio, onReintentar, children }) {
  if (cargando) return <p className="estado" role="status">Cargando…</p>
  if (error) {
    return (
      <div className="estado error" role="alert">
        <p>{error}</p>
        {onReintentar && <button className="btn" onClick={onReintentar}>Reintentar</button>}
      </div>
    )
  }
  if (vacio) return <p className="estado">{textoVacio}</p>
  return children
}

export function Campo({ etiqueta, error, children }) {
  return (
    <label className="campo">
      <span>{etiqueta}</span>
      {children}
      {error && <small className="msg-error" role="alert">{error}</small>}
    </label>
  )
}

export function Aviso({ tipo = 'ok', children }) {
  if (!children) return null
  return <p className={`aviso ${tipo}`} role={tipo === 'error' ? 'alert' : 'status'}>{children}</p>
}

export function Paginador({ pagina, setPagina, data }) {
  if (!data || (!data.next && !data.previous)) return null
  return (
    <div className="paginador">
      <button className="btn" disabled={!data.previous} onClick={() => setPagina(pagina - 1)}>← Anterior</button>
      <span>Página {pagina}</span>
      <button className="btn" disabled={!data.next} onClick={() => setPagina(pagina + 1)}>Siguiente →</button>
    </div>
  )
}

export const dinero = (v) => `$${Number(v).toFixed(2)}`
