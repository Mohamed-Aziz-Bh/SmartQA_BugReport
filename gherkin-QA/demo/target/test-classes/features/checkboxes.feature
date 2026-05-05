Feature: Checkboxes Management

  Background:
    Given the user is on the checkboxes page

  @Success
  Scenario: Toggle checkboxes successfully
    When the user clicks on checkbox 1
    Then checkbox 1 should be "selected"
    When the user clicks on checkbox 2
    Then checkbox 2 should be "unselected"

  @Failure
  Scenario Outline: Incorrect initial state verification
    Then checkbox <number> should be "<expected_state>"

    Examples:
      | number | expected_state |
      | 1      | unselected     |
      | 2      | selected       |