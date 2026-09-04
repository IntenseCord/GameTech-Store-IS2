Feature: Modelos de base de datos
  Como desarrollador de GameTech Store
  Quiero que los modelos de base de datos funcionen correctamente
  Para poder gestionar usuarios, juegos y hardware

  Scenario: Crear usuario exitosamente
    Given tengo una base de datos vacía
    When creo un usuario con nombre "testuser" y email "test@example.com"
    And establezco la contraseña "Test1234"
    Then el usuario debería tener un ID asignado
    And el nombre de usuario debería ser "testuser"
    And el email debería ser "test@example.com"
    And la contraseña debería ser válida para "Test1234"
    And la contraseña no debería ser válida para "WrongPassword"

  Scenario: Crear juego exitosamente
    Given tengo una base de datos vacía
    When creo un juego con nombre "Test Game" y precio 49.99
    And establezco el género "Acción"
    And establezco el desarrollador "Test Dev"
    And establezco el stock 10
    Then el juego debería tener un ID asignado
    And el nombre debería ser "Test Game"
    And el precio del juego debería ser 49.99
    And el stock debería ser 10

  Scenario: Crear hardware exitosamente
    Given tengo una base de datos vacía
    When creo un hardware tipo "CPU" con marca "Intel"
    And establezco el modelo "Core i5-10400"
    And establezco el precio 199.99
    And fijo el stock de hardware en 5
    Then el hardware debería tener un ID asignado
    And el tipo debería ser "CPU"
    And la marca debería ser "Intel"
    And el precio del hardware debería ser 199.99

  Scenario: Usuario con rol de administrador
    Given tengo una base de datos vacía
    When creo un usuario administrador con nombre "admin"
    And establezco el rol de administrador
    Then el usuario debería ser administrador

  Scenario: Obtener requisitos de juego
    Given tengo un juego con requisitos mínimos JSON
    When obtengo los requisitos mínimos
    Then debería tener CPU "Intel i3"
    And debería tener RAM "8GB"

  Scenario: Obtener especificaciones de hardware
    Given tengo un hardware con especificaciones JSON
    When obtengo las especificaciones
    Then debería tener 6 cores
    And debería tener 12 threads
