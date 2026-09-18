Feature: Consulta del catálogo por GraphQL
  Como cliente de la API de GameTech Store
  Quiero pedir solo los datos del catálogo que necesito
  Para no descargar información de más y consultarlo todo en una sola petición

  Background:
    Given existe un catálogo con juegos y hardware

  Scenario: Pedir solo algunos campos de los juegos
    When consulto los juegos pidiendo los campos "nombre precio"
    Then cada juego devuelto tiene solo los campos "nombre precio"

  Scenario: Consultar juegos y hardware en una sola petición
    When consulto juegos y hardware en una sola petición
    Then recibo ambas colecciones en la misma respuesta

  Scenario: Un campo que no existe da un error claro
    When consulto el campo "inexistente" de los juegos
    Then recibo un error que menciona el campo "inexistente"

  Scenario: La API es de solo lectura y no expone datos sensibles
    When consulto los tipos que expone el esquema
    Then no aparecen usuarios, órdenes, facturas ni pagos
    And no se puede modificar nada con una mutación

  Scenario: Un cambio del administrador se ve enseguida en la consulta
    Given un administrador con la sesión iniciada
    When el administrador cambia el stock del primer componente a 9
    Then la consulta GraphQL muestra ese componente con stock 9
