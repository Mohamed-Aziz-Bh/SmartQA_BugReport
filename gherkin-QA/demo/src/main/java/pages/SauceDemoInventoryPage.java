package pages;

import java.time.Duration;
import org.openqa.selenium.By;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

public class SauceDemoInventoryPage {

    private WebDriver driver;
    private WebDriverWait wait;
    private JavascriptExecutor js;

    private final By title = By.cssSelector(".title");
    private final By addToCartButtons = By.cssSelector("button[id^='add-to-cart']");
    private final By cartBadge = By.cssSelector(".shopping_cart_badge");
    private final By cartLink = By.cssSelector(".shopping_cart_link");
    private final By sortDropdown = By.className("product_sort_container");
    private final By menuButton = By.id("react-burger-menu-btn");
    private final By logoutLink = By.id("logout_sidebar_link");

    public SauceDemoInventoryPage(WebDriver driver) {
        this.driver = driver;
        this.wait = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public String getTitle() {
        return wait.until(ExpectedConditions.visibilityOfElementLocated(title)).getText();
    }

    public void addFirstProductToCart() {
        wait.until(ExpectedConditions.elementToBeClickable(addToCartButtons)).click();
    }

    public void addProductToCart(String productName) {
        String xpath = "//div[text()='" + productName + "']/ancestor::div[contains(@class,'inventory_item')]//button";
        wait.until(ExpectedConditions.elementToBeClickable(By.xpath(xpath))).click();
    }

    public int getCartCount() {
        try {
            return Integer.parseInt(
                    wait.withTimeout(Duration.ofSeconds(5))
                            .until(ExpectedConditions.visibilityOfElementLocated(cartBadge))
                            .getText()
            );
        } catch (Exception e) {
            return 0;
        }
    }
    private void waitForCartBadgeToUpdate(int expectedCount) {
        try {
            wait.withTimeout(Duration.ofSeconds(6))
                    .until(ExpectedConditions.textToBePresentInElementLocated(cartBadge, String.valueOf(expectedCount)));
        } catch (Exception e) {
            // Si le badge n'apparaît pas, on force un refresh visuel
            js.executeScript("window.scrollBy(0, -200);");
        }
    }

    public void goToCart() {
        wait.until(ExpectedConditions.elementToBeClickable(cartLink)).click();
    }

    public void sortBy(String option) {
        WebElement dropdown = wait.until(ExpectedConditions.elementToBeClickable(sortDropdown));
        dropdown.click();
        driver.findElement(By.xpath("//option[text()='" + option + "']")).click();
    }

    public void openMenu() {
        WebElement menuBtn = wait.until(ExpectedConditions.elementToBeClickable(menuButton));
        js.executeScript("arguments[0].scrollIntoView(true);", menuBtn);
        menuBtn.click();

        // Attente explicite que le menu soit ouvert
        wait.until(ExpectedConditions.visibilityOfElementLocated(logoutLink));
    }

    public void logout() {
        openMenu();                    // Ouvre le menu si pas encore ouvert
        WebElement logoutBtn = wait.until(ExpectedConditions.elementToBeClickable(logoutLink));
        logoutBtn.click();
    }

    // ==================== RESET CART ====================
    public void removeAllItemsFromCart() {
        try {
            // Aller dans le panier
            goToCart();

            // Cliquer sur tous les boutons "Remove"
            java.util.List<WebElement> removeButtons = driver.findElements(By.cssSelector("button[id^='remove-']"));
            for (WebElement btn : removeButtons) {
                wait.until(ExpectedConditions.elementToBeClickable(btn)).click();
            }

            // Retour à la page des produits
            driver.navigate().back();
            wait.until(ExpectedConditions.visibilityOfElementLocated(By.cssSelector(".title")));
        } catch (Exception e) {
            // Si déjà vide, on ignore
        }
    }

    public void ensureCartIsEmpty() {
        if (getCartCount() > 0) {
            removeAllItemsFromCart();
        }
    }
}