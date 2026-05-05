package StepDefinitions;

import base.TestBase;
import io.cucumber.java.*;
import com.aventstack.extentreports.*;
import ExtentReport.ExtentManager;
import org.json.JSONArray;
import org.json.JSONObject;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

import java.io.File;
import java.lang.reflect.Field;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.time.Duration;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Collections;
import java.util.List;

public class Hooks {
    private ExtentReports extentReport = ExtentManager.getInstance();
    public static ExtentTest _scenario;
    private WebDriver driver;

    @Before
    public void beforeScenario(Scenario scenario) {
        _scenario = extentReport.createTest(scenario.getName());

        ChromeOptions options = new ChromeOptions();
        System.setProperty("webdriver.chrome.silentOutput", "true");

        String userDataDir = "C:/Users/lenovo/Desktop/PFE 2026/ChromeDebugProfile";
        new File(userDataDir).mkdirs();

        options.addArguments("--user-data-dir=" + userDataDir);
        options.addArguments("--remote-allow-origins=*");
        options.setExperimentalOption("excludeSwitches", Collections.singletonList("enable-automation"));
        options.setExperimentalOption("useAutomationExtension", false);

        driver = new ChromeDriver(options);
        driver.manage().window().maximize();
        TestBase.setDriver(driver);
    }

    @After
    public void afterScenario(Scenario scenario) {
        try {
            String status = scenario.getStatus() != null ? scenario.getStatus().toString() : "FAILED";
            String base64Screenshot = "";

            // 1. Capture d'écran (Uniquement en cas d'échec)
            if (scenario.isFailed() && driver != null) {
                try {
                    byte[] screenshotBytes = ((TakesScreenshot) driver).getScreenshotAs(OutputType.BYTES);
                    base64Screenshot = "data:image/png;base64," + Base64.getEncoder().encodeToString(screenshotBytes);
                } catch (Exception e) {
                    System.err.println("⚠️ Capture échouée : " + e.getMessage());
                }
            }

            // 2. EXTRACTION FILTRÉE DES STATUTS RÉELS
            List<String> realStatuses = new ArrayList<>();
            try {
                Field delegateField = scenario.getClass().getDeclaredField("delegate");
                delegateField.setAccessible(true);
                Object delegate = delegateField.get(scenario);

                // On récupère la liste brute des résultats
                Field stepResultsField = delegate.getClass().getDeclaredField("stepResults");
                stepResultsField.setAccessible(true);
                List<io.cucumber.plugin.event.Result> results = (List<io.cucumber.plugin.event.Result>) stepResultsField.get(delegate);

                // CRITIQUE : Cucumber peut inclure les Hooks dans stepResults.
                // On essaie de récupérer uniquement les "testSteps" pour synchroniser avec le .feature
                for (io.cucumber.plugin.event.Result res : results) {
                    // On ajoute le statut en minuscule (passed, failed, skipped, etc.)
                    realStatuses.add(res.getStatus().toString().toLowerCase());
                }

                System.out.println("📊 Statuts détectés par Cucumber : " + realStatuses);
            } catch (Exception e) {
                System.err.println("⚠️ Réflexion échouée : " + e.getMessage());
            }

            // 3. SYNCHRONISATION PRÉCISE AVEC LE FICHIER .FEATURE
            JSONArray stepsArray = new JSONArray();
            try {
                URI uri = scenario.getUri();
                String pathStr = Paths.get(uri).toString(); // Plus robuste que replace()
                List<String> lines = Files.readAllLines(Paths.get(pathStr));

                String targetName = scenario.getName().split(" -- @")[0].trim();
                boolean scenarioFound = false;
                int currentStepIdx = 0;

                for (String line : lines) {
                    String t = line.trim();

                    // Détection du début du bon scénario
                    if ((t.startsWith("Scenario:") || t.startsWith("Scenario Outline:")) && t.contains(targetName)) {
                        scenarioFound = true;
                        continue;
                    }

                    if (scenarioFound) {
                        // Si on tombe sur un nouveau bloc, on arrête
                        if (t.startsWith("Scenario:") || t.startsWith("Scenario Outline:") || t.startsWith("@") || t.startsWith("Examples:")) {
                            break;
                        }

                        // On ne traite que les lignes commençant par un mot-clé Gherkin
                        if (t.matches("^(Given|When|Then|And|But|\\*)\\s+.*")) {
                            JSONObject stepObj = new JSONObject();
                            stepObj.put("text", t);

                            // SYNCHRONISATION AVEC L'INDEX RÉEL
                            if (currentStepIdx < realStatuses.size()) {
                                String s = realStatuses.get(currentStepIdx);
                                stepObj.put("status", s);
                                System.out.println("🔗 Match : [" + s + "] -> " + t);
                            } else {
                                // Si Cucumber n'a pas encore de résultat pour cette étape (ex: crash prématuré)
                                stepObj.put("status", "skipped");
                            }

                            stepsArray.put(stepObj);
                            currentStepIdx++;
                        }
                    }
                }
            } catch (Exception e) {
                System.err.println("⚠️ Erreur synchronisation Feature : " + e.getMessage());
            }

            // 4. Envoi du Payload
            JSONObject payload = new JSONObject();
            payload.put("scenario_name", scenario.getName());
            payload.put("status", status);
            payload.put("steps", stepsArray);
            payload.put("error_details", scenario.isFailed() ? "Échec détecté dans : " + scenario.getName() : "Succès");
            payload.put("screenshot", base64Screenshot);

            sendDataToFastAPI(payload.toString());

            // 5. Reporting Classique
            if (scenario.isFailed()) {
                _scenario.fail("Test échoué");
            } else {
                _scenario.pass("Test réussi");
            }

        } catch (Exception e) {
            e.printStackTrace();
        } finally {
            extentReport.flush();
            TestBase.tearDown();
        }
    }

    private void sendDataToFastAPI(String json) {
        try {
            HttpClient client = HttpClient.newBuilder()
                    .version(HttpClient.Version.HTTP_1_1)
                    .connectTimeout(Duration.ofSeconds(10))
                    .build();

            HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create("http://127.0.0.1:8000/analyze-error"))
                    .header("Content-Type", "application/json")
                    .POST(HttpRequest.BodyPublishers.ofString(json, StandardCharsets.UTF_8))
                    .build();

            client.sendAsync(request, HttpResponse.BodyHandlers.ofString());
        } catch (Exception e) {
            System.err.println("❌ Connexion Backend impossible.");
        }
    }
}