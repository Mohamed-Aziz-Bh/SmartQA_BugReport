@SauceDemo
Feature: SauceDemo E-commerce Full Flow

  Background:
    Given the user is on the SauceDemo login page
    When the user enters username as "standard_user" on SauceDemo
    And the user enters password as "secret_sauce" on SauceDemo
    And clicks on the SauceDemo login button
    Then the user should be logged in successfully
    And the cart is empty

  @AddToCart
  Scenario: Add product to cart
    When the user adds the first product to the cart
    Then the cart badge should show 1 item

  @AddSpecificProduct
  Scenario Outline: Add specific product
    When the user adds "<product>" to the cart
    Then the cart badge should show 1 item

    Examples:
      | product               |
      | Sauce Labs Backpack   |
      | Sauce Labs Bolt T-Shirt |

  @FullCheckout
  Scenario: Complete purchase
    When the user adds the first product to the cart
    And the user goes to the cart
    And the user clicks on checkout
    And the user fills checkout information with "John" "Doe" "12345"
    And the user clicks continue
    And the user clicks finish
    Then the user should see order confirmation message

  @Logout
  Scenario: Successful logout
    When the user clicks on the menu
    And the user clicks logout
    Then the user should be redirected to the login page