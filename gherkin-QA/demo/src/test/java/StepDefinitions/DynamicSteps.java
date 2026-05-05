package StepDefinitions;

import base.TestBase;
import io.cucumber.java.en.*;
import org.junit.jupiter.api.Assertions;
import pages.DynamicPage;
import com.aventstack.extentreports.Status;

public class DynamicSteps {
    private DynamicPage page = new DynamicPage(TestBase.getDriver());

    @Given("the user is on the dynamic loading page")
    public void stepOpen() {
        TestBase.notifyExtension("STEP_START", "Navigation vers la page de chargement dynamique");
        page.open();
    }

    @When("the user clicks the start button")
    public void stepStart() {
        TestBase.notifyExtension("STEP_ACTION", "Clic sur le bouton Start");
        page.start();
    }

    @Then("the loading finish text should be {string}")
    public void stepVerify(String txt) {
        TestBase.notifyExtension("STEP_WAIT", "Attente de l'élément dynamique : " + txt);

        try {
            String actualText = page.getFinishText();
            Assertions.assertEquals(txt, actualText);
            TestBase.notifyExtension("STEP_RESULT", "Élément dynamique apparu avec succès : " + actualText);
            Hooks._scenario.log(Status.PASS, "Text displayed: " + txt);
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Échec du chargement dynamique : " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "Text not found or timeout");
            throw e;
        }
    }
}