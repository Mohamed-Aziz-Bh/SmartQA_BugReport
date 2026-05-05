package pages;
import org.openqa.selenium.*;
import org.openqa.selenium.support.ui.*;
import java.time.Duration;

public class DynamicPage {
    private WebDriver driver;
    private WebDriverWait wait;

    public DynamicPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public void open() { driver.get("https://the-internet.herokuapp.com/dynamic_loading/1"); }
    public void start() { driver.findElement(By.cssSelector("#start button")).click(); }

    public String getFinishText() {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(By.id("finish"))).getText();
    }

    public boolean isFinishVisible() {
        try { return driver.findElement(By.id("finish")).isDisplayed(); }
        catch (Exception e) { return false; }
    }
}