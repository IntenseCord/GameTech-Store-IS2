Feature: Pagos con MercadoPago (Incremento 1 y 2)
  Como usuario de GameTech Store
  Quiero pagar mi compra con MercadoPago y que la tienda refleje el resultado real del pago
  Para recibir mis productos, facturar solo lo que realmente pagué, y no perder ni duplicar stock

  Background:
    Given existe un hardware en stock

  Scenario: Checkout crea una orden pendiente, descuenta stock y redirige a MercadoPago
    Given estoy logueado y tengo ese hardware en el carrito
    When voy a pagar el carrito
    Then la orden creada debería quedar en estado "pending"
    And debería ser redirigido a MercadoPago
    And el stock del hardware debería descontarse

  Scenario: Un pago aprobado confirma la orden y permite solicitar factura
    Given tengo una orden "pending" de ese hardware
    When MercadoPago notifica que el pago fue "aprobado"
    Then la orden debería quedar en estado "approved"
    And debería poder solicitar factura de esa orden

  Scenario: Un pago rechazado restaura el stock y bloquea la factura
    Given tengo una orden "pending" de ese hardware
    When MercadoPago notifica que el pago fue "rechazado"
    Then la orden debería quedar en estado "rejected"
    And el stock del hardware debería restaurarse
    And no debería poder solicitar factura de esa orden

  Scenario: Una notificación tardía no puede revertir una orden ya aprobada
    Given tengo una orden "approved" de ese hardware
    When MercadoPago notifica que el pago fue "rechazado"
    Then la orden debería quedar en estado "approved"
    And el stock del hardware no debería restaurarse

  Scenario: Un reintento de pago exitoso tras un rechazo vuelve a descontar el stock
    Given tengo una orden "rejected" de ese hardware
    When MercadoPago notifica que el pago fue "aprobado"
    Then la orden debería quedar en estado "approved"
    And el stock del hardware debería descontarse de nuevo

  Scenario: El panel de administración muestra una orden aprobada como pagada
    Given tengo una orden "approved" de ese hardware
    When un administrador ve el dashboard de órdenes
    Then debería mostrarse la orden como pagada
