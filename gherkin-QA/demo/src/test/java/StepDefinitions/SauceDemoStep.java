package StepDefinitions;

import base.TestBase;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import pages.*;
import com.aventstack.extentreports.Status;

public class SauceDemoStep {

    private SauceDemoLoginPage loginPage;
    private SauceDemoInventoryPage inventoryPage;
    private SauceDemoCartPage cartPage;
    private SauceDemoCheckoutPage checkoutPage;

    public SauceDemoStep() {
        this.loginPage = new SauceDemoLoginPage(TestBase.getDriver());
        this.inventoryPage = new SauceDemoInventoryPage(TestBase.getDriver());
        this.cartPage = new SauceDemoCartPage(TestBase.getDriver());
        this.checkoutPage = new SauceDemoCheckoutPage(TestBase.getDriver());
    }

    @Given("the user is on the SauceDemo login page")
    public void userIsOnLoginPage() {
        TestBase.notifyExtension("STEP_START", "Ouverture SauceDemo");
        loginPage.openLoginPage();
        Hooks._scenario.log(Status.PASS, "Opened SauceDemo login page");
    }

    @When("the user enters username as {string} on SauceDemo")
    public void enterUsername(String username) {
        loginPage.enterUsername(username);
        Hooks._scenario.log(Status.PASS, "Entered username: " + username);
    }

    @When("the user enters password as {string} on SauceDemo")
    public void enterPassword(String password) {
        loginPage.enterPassword(password);
        Hooks._scenario.log(Status.PASS, "Entered password");
    }

    @When("clicks on the SauceDemo login button")
    public void clickLoginButton() {
        loginPage.clickLoginButton();
        Hooks._scenario.log(Status.PASS, "Clicked login button");
    }

    @Then("the user should be logged in successfully")
    public void verifySuccessfulLogin() {
        String title = loginPage.getInventoryTitle();
        Assertions.assertEquals("Products", title);
        Hooks._scenario.log(Status.PASS, "Login successful - Title: " + title);
    }

    @Then("the user should see a login error message")
    public void verifyLoginError() {
        String error = loginPage.getErrorMessage();
        Assertions.assertTrue(error.contains("Epic sadface"));
        Hooks._scenario.log(Status.PASS, "Login error verified: " + error);
    }

    @When("the user adds the first product to the cart")
    public void addFirstProduct() {
        inventoryPage.addFirstProductToCart();
        Hooks._scenario.log(Status.PASS, "Added first product to cart");
    }

    @When("the user adds {string} to the cart")
    public void addSpecificProduct(String product) {
        inventoryPage.addProductToCart(product);
        Hooks._scenario.log(Status.PASS, "Added product: " + product);
    }

    @When("the user goes to the cart")
    public void goToCart() {
        inventoryPage.goToCart();
        Hooks._scenario.log(Status.PASS, "Navigated to cart");
    }

    @When("the user sorts products by {string}")
    public void sortProducts(String option) {
        inventoryPage.sortBy(option);
        Hooks._scenario.log(Status.PASS, "Sorted by: " + option);
    }

    @Then("the cart badge should show {int} item")
    public void verifyCartBadge(int count) {
        int actual = inventoryPage.getCartCount();
        Assertions.assertEquals(count, actual,
                "Cart badge should show " + count + " but was " + actual);
        Hooks._scenario.log(Status.PASS, "Cart badge correctly shows " + count + " item");
    }

    @Then("the cart should contain {int} item")
    public void verifyCartItems(int count) {
        Assertions.assertEquals(count, cartPage.getItemCount());
    }
    @Given("the cart is empty")
    public void ensureCartEmpty() {
        inventoryPage.ensureCartIsEmpty();
        Hooks._scenario.log(Status.PASS, "Cart has been emptied");
    }

    @When("the user clicks on checkout")
    public void clickCheckout() {
        cartPage.clickCheckout();
        Hooks._scenario.log(Status.PASS, "Clicked checkout");
    }

    @When("the user fills checkout information with {string} {string} {string}")
    public void fillCheckoutInfo(String first, String last, String zip) {
        try {
            checkoutPage.fillCheckoutInfo(first, last, zip);
            Hooks._scenario.log(Status.PASS, "Filled checkout information: " + first + " " + last);
        } catch (Exception e) {
            Hooks._scenario.log(Status.FAIL, "Failed to fill checkout info: " + e.getMessage());
            throw e;
        }
    }

    @When("the user clicks continue")
    public void clickContinue() {
        try {
            checkoutPage.clickContinue();
            Hooks._scenario.log(Status.PASS, "Clicked continue - moved to overview");
        } catch (Exception e) {
            Hooks._scenario.log(Status.FAIL, "Failed to click continue: " + e.getMessage());
            throw e;
        }
    }

    @When("the user clicks finish")
    public void clickFinish() {
        try {
            checkoutPage.clickFinish();
            Hooks._scenario.log(Status.PASS, "Clicked finish button");
        } catch (Exception e) {
            Hooks._scenario.log(Status.FAIL, "Failed to click finish button: " + e.getMessage());
            throw e;
        }
    }

    @Then("the user should see order confirmation message")
    public void verifyOrderConfirmation() {
        String msg = checkoutPage.getConfirmationMessage();
        Assertions.assertTrue(msg.contains("Thank you for your order"));
        Hooks._scenario.log(Status.PASS, "Order completed successfully");
    }

    @When("the user clicks on the menu")
    public void openMenu() {
        inventoryPage.openMenu();
        Hooks._scenario.log(Status.PASS, "Menu opened");
    }

    @When("the user clicks logout")
    public void logout() {
        try {
            inventoryPage.logout();
            Hooks._scenario.log(Status.PASS, "Logout performed");
        } catch (Exception e) {
            Hooks._scenario.log(Status.FAIL, "Logout failed: " + e.getMessage());
            throw e;
        }
    }

    @Then("the user should be redirected to the login page")
    public void verifyLogout() {
        String currentUrl = TestBase.getDriver().getCurrentUrl();
        Assertions.assertTrue(currentUrl.contains("saucedemo.com"));
        Hooks._scenario.log(Status.PASS, "Successfully redirected to login page");
    }
}