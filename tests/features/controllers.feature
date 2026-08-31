Feature: Controladores de la aplicación
  Como usuario de GameTech Store
  Quiero que los controladores respondan correctamente
  Para poder navegar por la aplicación

  Scenario: Ver página principal
    When voy a la página principal
    Then la respuesta debería ser exitosa

  Scenario: Ver página de tienda
    When voy a la página de tienda
    Then la respuesta debería ser exitosa

  Scenario: Ver página de registro
    When voy a la página de registro
    Then la respuesta debería ser exitosa

  Scenario: Ver página de login
    When voy a la página de login
    Then la respuesta debería ser exitosa

  Scenario: Buscar sin query
    When voy a la página de búsqueda sin query
    Then la respuesta debería ser exitosa

  Scenario: Buscar con query
    Given existe un juego con nombre "Test Game"
    When voy a la página de búsqueda con query "Test"
    Then la respuesta debería ser exitosa

  Scenario: Ver detalle de juego
    Given existe un juego con ID 1
    When voy al detalle del juego con ID 1
    Then la respuesta debería ser exitosa

  Scenario: Ver detalle de hardware
    Given existe un hardware con ID 1
    When voy al detalle del hardware con ID 1
    Then la respuesta debería ser exitosa

  Scenario: Carrito requiere login
    When voy a la página del carrito sin estar logueado
    Then debería ser redirigido al login

  Scenario: Admin requiere login
    When voy a la página de admin sin estar logueado
    Then debería ser redirigido al login

  Scenario: Admin requiere rol de administrador
    Given estoy logueado como usuario normal
    When voy a la página de admin
    Then debería ser redirigido a la página principal
