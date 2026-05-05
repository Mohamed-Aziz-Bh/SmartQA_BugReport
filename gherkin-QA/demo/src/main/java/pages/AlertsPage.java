package pages;
import org.openqa.selenium.*;

public class AlertsPage {
    private WebDriver driver;
    public AlertsPage(WebDriver driver) { this.driver = driver; }

    public void open() { driver.get("https://the-internet.herokuapp.com/javascript_alerts"); }
    public void trigger(String type) {
        driver.findElement(By.xpath("//button[text()='Click for JS " + type + "']")).click();
    }
    public String getResult() { return driver.findElement(By.id("result")).getText(); }
}