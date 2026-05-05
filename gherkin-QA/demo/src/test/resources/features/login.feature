@LoginSuccess
Feature: User Login

  @ValidCredentials
  Scenario Outline: Successful login
    Given the user is on the login page
    When the user enters a username as "<username>"
    And the user enters a password as "<password>"
    And clicks on the login button
    Then the user should see a successful login message

    Examples:
      | username  | password               |
      | smith  | SuperSecretPassword!   |

  @InvalidCredentials
  Scenario Outline: Failed login
    Given the user is on the login page
    When the user enters a username as "<username>"
    And the user enters a password as "<password>"
    And clicks on the login button
    Then the user should see a login failure message

    Examples:
      | username  | password              |
      | invalidUser | SuperSecretPassword! |
      | tomsmith   | WrongPassword!        |
