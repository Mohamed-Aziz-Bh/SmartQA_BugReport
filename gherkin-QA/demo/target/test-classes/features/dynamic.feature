Feature: Dynamic Loading Wait

  @Success
  Scenario: Wait for hidden element
    Given the user is on the dynamic loading page
    When the user clicks the start button
    Then the loading finish text should be "Hello World!"
