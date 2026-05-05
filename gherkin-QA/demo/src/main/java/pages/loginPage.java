package pages;

import java.time.Duration;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class loginPage {
    
    private WebDriver driver;
    private WebDriverWait wait;

    // Constructor to initialize WebDriver and WebDriverWait
    public loginPage(WebDriver driver) {
        if (driver == null) throw new IllegalArgumentException("Driver cannot be null");
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public void openLoginPage() {
        driver.get("https://the-internet.herokuapp.com/login");
    }

    public void enterUsername(String username) {
        WebElement usernameInput = wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("username")));
        usernameInput.sendKeys(username);
    }

    public void enterPassword(String password) {
        WebElement passwordInput = wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("password")));
        passwordInput.sendKeys(password);
    }

    public void submitLogin() {
        WebElement loginBtn = wait.until(ExpectedConditions.elementToBeClickable(By.cssSelector("button[type='submit']")));
        loginBtn.click();
    }

    public String getSuccessMessage() {
        WebElement successMsg = wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".flash.success")));
        return successMsg.getText();
    }
    public String getErrorMessage() {
        WebElement errorMsg = wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".flash.error")));
        return errorMsg.getText();
    }
}
