import { useCallback, useEffect, useState } from 'react'
import { leerError } from './api.js'

// Carga datos y expone los tres estados que la interfaz debe contemplar.
export function useCarga(fn, deps = []) {
  const [estado, setEstado] = useState({ datos: null, cargando: true, error: null })
  const cargar = useCallback(async () => {
    setEstado((s) => ({ ...s, cargando: true, error: null }))
    try {
      setEstado({ datos: await fn(), cargando: false, error: null })
    } catch (e) {
      setEstado({ datos: null, cargando: false, error: leerError(e).general })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { cargar() }, [cargar])
  return { ...estado, recargar: cargar }
}
