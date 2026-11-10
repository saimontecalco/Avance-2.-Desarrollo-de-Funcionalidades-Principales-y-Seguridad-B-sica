import { dinero } from './Ui.jsx'
import { etiquetaLeche } from './Pedir.jsx'

// Ticket del pedido recién hecho (mismo formato que el del sitio Django).
export default function Ticket({ pedido, restantes = {} }) {
  const fecha = new Date(pedido.fecha).toLocaleString('es-MX')
  return (
    <div className="ticket" aria-label={`Ticket del pedido ${pedido.id}`}>
      <p className="ticket-titulo">Cafetería</p>
      <p className="ticket-linea ticket-centro ticket-sub">Pedido #{pedido.id}</p>
      <p className="ticket-linea ticket-centro ticket-sub">{fecha}</p>
      <div className="ticket-separador" />
      <p className="ticket-linea"><span>Cliente</span><span>{pedido.nombre_cliente}</span></p>
      {pedido.lineas.map((l) => (
        <p key={l.cafe} className="ticket-linea">
          <span>{l.cantidad} × {l.cafe_nombre} ({dinero(l.precio_unitario)})</span>
          <span>{dinero(Number(l.precio_unitario) * l.cantidad)}</span>
        </p>
      ))}
      <p className="ticket-linea"><span>Leche</span><span>{etiquetaLeche(pedido.leche)}</span></p>
      <p className="ticket-linea"><span>Azúcar</span><span>{pedido.azucar ? 'Sí' : 'No'}</span></p>
      <div className="ticket-separador" />
      <p className="ticket-linea"><span>Subtotal</span><span>{dinero(pedido.subtotal)}</span></p>
      <p className="ticket-linea"><span>Impuesto (16%)</span><span>{dinero(pedido.impuesto_total)}</span></p>
      <p className="ticket-linea"><span>Descuento (10%)</span><span>-{dinero(pedido.descuento_total)}</span></p>
      <div className="ticket-separador" />
      <p className="ticket-linea ticket-total"><span>Total a pagar</span><span>{dinero(pedido.total)}</span></p>
      <p className="ticket-linea ticket-centro ticket-tipo">{pedido.es_mayorista ? 'Pedido mayorista' : 'Pedido regular'}</p>
      {Object.keys(restantes).length > 0 && (
        <>
          <div className="ticket-separador" />
          <p className="ticket-linea ticket-centro ticket-sub">Cafés restantes en existencia</p>
          {pedido.lineas.filter((l) => l.cafe in restantes).map((l) => (
            <p key={l.cafe} className="ticket-linea ticket-sub"><span>{l.cafe_nombre}</span><span>{restantes[l.cafe]}</span></p>
          ))}
        </>
      )}
      <div className="ticket-separador" />
      <p className="ticket-linea ticket-centro ticket-sub">Gracias por tu compra, {pedido.nombre_cliente}</p>
    </div>
  )
}
