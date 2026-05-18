package pages;

import java.time.Duration;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class SauceDemoCheckoutPage {

    private WebDriver driver;
    private WebDriverWait wait;
    private JavascriptExecutor js;

    // Step 1 - Information
    private final By firstNameField = By.id("first-name");
    private final By lastNameField = By.id("last-name");
    private final By zipCodeField = By.id("postal-code");
    private final By continueButton = By.id("continue");

    // Step 2 - Overview
    private final By finishButton = By.id("finish");

    // Step 3 - Complete
    private final By completeHeader = By.cssSelector(".complete-header");

    public SauceDemoCheckoutPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(12));
        this.js = (JavascriptExecutor) driver;
    }

    public void fillCheckoutInfo(String firstName, String lastName, String zipCode) {
        try {
            WebElement first = wait.until(ExpectedConditions.visibilityOfElementLocated(firstNameField));
            first.clear();
            first.sendKeys(firstName);

            WebElement last = wait.until(ExpectedConditions.visibilityOfElementLocated(lastNameField));
            last.clear();
            last.sendKeys(lastName);

            WebElement zip = wait.until(ExpectedConditions.visibilityOfElementLocated(zipCodeField));
            zip.clear();
            zip.sendKeys(zipCode);

            // Petite pause pour que le formulaire prenne les valeurs
            Thread.sleep(500);
        } catch (Exception e) {
            throw new RuntimeException("Failed to fill checkout info", e);
        }
    }

    public void clickContinue() {
        WebElement btn = wait.until(ExpectedConditions.elementToBeClickable(continueButton));

        // Scroll + Click classique
        js.executeScript("arguments[0].scrollIntoView(true);", btn);
        btn.click();

        // Attente robuste du changement de page
        wait.until(ExpectedConditions.urlContains("checkout-step-two"));
    }

    public void clickFinish() {
        WebElement btn = wait.until(ExpectedConditions.elementToBeClickable(finishButton));
        js.executeScript("arguments[0].scrollIntoView(true);", btn);
        btn.click();
    }

    public String getConfirmationMessage() {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(completeHeader)).getText();
    }
}