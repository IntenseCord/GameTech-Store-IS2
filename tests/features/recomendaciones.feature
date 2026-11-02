Feature: Recomendaciones de mejora del analizador
  Como cliente de GameTech Store
  Quiero que el analizador me diga qué piezas concretas del catálogo mejoran mi equipo
  Para comprar la mejora con mejor relación precio/rendimiento sin equivocarme de compatibilidad

  Scenario: Un equipo equilibrado no recibe recomendaciones
    Given el catálogo de hardware y juegos está cargado
    And tengo la CPU "Core i7-13700K", la GPU "RTX 4070" y la RAM "Vengeance 32GB DDR5"
    When analizo mi equipo
    Then no recibo recomendaciones

  Scenario: Una GPU limitante recibe opciones ordenadas por precio y rendimiento
    Given el catálogo de hardware y juegos está cargado
    And tengo la CPU "Ryzen 5 5600", la GPU "GTX 1650" y la RAM "Vengeance LPX 16GB DDR4"
    When analizo mi equipo
    Then recibo recomendaciones para "GPU"
    And la primera opción es "RX 7600"
    And las opciones se ordenan de mayor a menor puntaje por dólar
    And ninguna opción es "RTX 4070"

  Scenario: Una CPU de otro socket avisa que hay que cambiar la placa base
    Given el catálogo de hardware y juegos está cargado
    And tengo la CPU "Ryzen 5 5600", la GPU "RTX 4070" y la RAM "Vengeance LPX 16GB DDR4"
    When analizo mi equipo
    Then recibo recomendaciones para "CPU"
    And la primera opción es "Core i7-13700K"
    And la primera opción avisa de "placa base"

  Scenario: Un juego limitado por la VRAM recomienda una GPU con más VRAM
    Given el catálogo de hardware y juegos está cargado
    And tengo la CPU "Core i5-12400F", la GPU "RTX 4060" y la RAM "Vengeance LPX 16GB DDR4"
    When analizo mi equipo
    Then recibo recomendaciones para "GPU"
    And la primera opción es "RTX 4070"
    And el motivo menciona "VRAM"

  Scenario: Una pieza sin stock no se recomienda
    Given el catálogo de hardware y juegos está cargado
    And la pieza "RX 7600" no tiene stock
    And tengo la CPU "Ryzen 5 5600", la GPU "GTX 1650" y la RAM "Vengeance LPX 16GB DDR4"
    When analizo mi equipo
    Then recibo recomendaciones para "GPU"
    And la primera opción es "RTX 4060"
    And ninguna opción es "RX 7600"
