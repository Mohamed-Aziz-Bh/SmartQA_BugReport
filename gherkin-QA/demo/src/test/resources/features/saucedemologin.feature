@SauceDemoLogin
Feature: saucedemo login
  Scenario: SauceDemo Login
    Given the user is on the SauceDemo login page
    When the user enters username as "standard_user" on SauceDemo
    And the user enters password as "secret_sauce" on SauceDemo
    And clicks on the SauceDemo login button
    Then the user should be logged in successfully