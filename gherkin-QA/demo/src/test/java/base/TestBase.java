package base;

import java.io.File;
import java.text.SimpleDateFormat;
import java.time.Duration;
import java.util.Date;
import org.apache.commons.io.FileUtils;
import org.openqa.selenium.JavascriptExecutor;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.support.ui.WebDriverWait;

public class TestBase {

    protected static WebDriver driver;
    protected static WebDriverWait wait;

    /**
     * Synchronise le driver initialisé dans Hooks avec TestBase
     */
    public static void setDriver(WebDriver newDriver) {
        driver = newDriver;
        if (driver != null) {
            wait = new WebDriverWait(driver, Duration.ofSeconds(10));
        }
    }

    public static WebDriver getDriver() {
        return driver;
    }

    /**
     * Envoie des logs de suivi à l'extension (Succès, Début, Fin)
     * Pour les ERREURS, on utilise le signal réseau CDP dans Hooks.java
     */
    public static void notifyExtension(String type, String message) {
        if (driver == null) return;
        try {
            JavascriptExecutor js = (JavascriptExecutor) driver;

            // Nettoyage minimal pour éviter les erreurs de syntaxe JS
            String cleanMessage = message.replace("'", "\\'").replace("\n", " ");

            String script = String.format(
                    "window.dispatchEvent(new CustomEvent('SMART_QA_SIGNAL', { " +
                            "detail: { type: '%s', text: '%s', timestamp: '%d' } " +
                            "}));",
                    type, cleanMessage, System.currentTimeMillis()
            );

            js.executeScript(script);
        } catch (Exception e) {
            System.err.println("⚠️ Log extension non envoyé : " + e.getMessage());
        }
    }

    /**
     * Capture une image en cas d'échec pour le rapport Extent
     */
    public static String captureScreenshot(String scenarioName) {
        if (driver == null) return "";
        try {
            String cleanName = scenarioName.replaceAll("[^a-zA-Z0-9]", "_");
            File src = ((TakesScreenshot) driver).getScreenshotAs(OutputType.FILE);

            String timestamp = new SimpleDateFormat("yyyyMMdd-HHmmss").format(new Date());
            String imgName = cleanName + "_" + timestamp + ".png";

            String folderPath = System.getProperty("user.dir") + "/target/screenshots/";
            File dest = new File(folderPath + imgName);
            FileUtils.copyFile(src, dest);

            return "../screenshots/" + imgName;
        } catch (Exception e) {
            return "";
        }
    }

    /**
     * Fermeture propre du navigateur
     */
    public static void tearDown() {
        if (driver != null) {
            driver.quit();
            driver = null;
        }
    }
}