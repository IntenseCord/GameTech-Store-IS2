Feature: Autenticación de usuarios
  Como usuario de GameTech Store
  Quiero poder registrarme, iniciar sesión y cerrar sesión
  Para poder comprar juegos y hardware

  Scenario: Registro exitoso de usuario
    Given estoy en la página de registro
    When ingreso un nombre de usuario válido "newuser"
    And ingreso un email válido "newuser@example.com"
    And ingreso una contraseña válida "Test1234"
    And confirmo la contraseña "Test1234"
    And envío el formulario de registro
    Then el usuario debería ser creado en la base de datos
    And debería ser redirigido a la página de login

  Scenario: Registro con contraseñas que no coinciden
    Given estoy en la página de registro
    When ingreso un nombre de usuario válido "newuser"
    And ingreso un email válido "newuser@example.com"
    And ingreso una contraseña válida "Test1234"
    And confirmo la contraseña "Test12345"
    And envío el formulario de registro
    Then el usuario no debería ser creado
    And debería ver un mensaje de error

  Scenario: Registro con contraseña inválida
    Given estoy en la página de registro
    When ingreso un nombre de usuario válido "newuser"
    And ingreso un email válido "newuser@example.com"
    And ingreso una contraseña sin mayúscula "test1234"
    And confirmo la contraseña "test1234"
    And envío el formulario de registro
    Then el usuario no debería ser creado
    And debería ver un mensaje de error

  Scenario: Login exitoso
    Given existe un usuario con nombre "testuser" y contraseña "Test1234"
    When voy a la página de login
    And ingreso el nombre de usuario "testuser"
    And ingreso la contraseña "Test1234"
    And envío el formulario de login
    Then debería ser redirigido a la página principal

  Scenario: Login fallido con contraseña incorrecta
    Given existe un usuario con nombre "testuser" y contraseña "Test1234"
    When voy a la página de login
    And ingreso el nombre de usuario "testuser"
    And ingreso la contraseña incorrecta "WrongPassword"
    And envío el formulario de login
    Then debería permanecer en la página de login
    And debería ver un mensaje de error

  Scenario: Logout exitoso
    Given estoy logueado como usuario "testuser"
    When voy a la página de logout
    Then debería ser redirigido a la página principal
    And no debería estar logueado
