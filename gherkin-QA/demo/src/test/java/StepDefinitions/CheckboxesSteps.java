package StepDefinitions;

import base.TestBase;
import io.cucumber.java.en.*;
import org.junit.jupiter.api.Assertions;
import pages.CheckboxesPage;
import com.aventstack.extentreports.Status;

public class CheckboxesSteps {
    private CheckboxesPage page = new CheckboxesPage(TestBase.getDriver());

    @Given("the user is on the checkboxes page")
    public void setup() {
        TestBase.notifyExtension("STEP_START", "Navigation vers la page des Checkboxes");
        try {
            page.open();
            Hooks._scenario.log(Status.PASS, "The user is on the checkboxes page");
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Erreur ouverture page checkboxes: " + e.getMessage());
            throw e;
        }
    }

    @When("the user clicks on checkbox {int}")
    public void clickCb(int id) {
        TestBase.notifyExtension("STEP_ACTION", "Clic sur la checkbox ID: " + id);
        try {
            page.toggle(id);
            Hooks._scenario.log(Status.PASS, "Clicked checkbox " + id);
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Échec interaction checkbox " + id + ": " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "Failed to click checkbox " + id);
            throw e;
        }
    }

    @Then("checkbox {int} should be {string}")
    public void verify(int id, String state) {
        TestBase.notifyExtension("STEP_VERIFY", "Vérification de l'état de la checkbox " + id + " attendu: " + state);

        try {
            boolean expectedState = state.equalsIgnoreCase("selected");
            boolean actualState = page.isChecked(id);

            Assertions.assertEquals(expectedState, actualState, "La checkbox " + id + " n'est pas dans l'état : " + state);

            TestBase.notifyExtension("STEP_RESULT", "Checkbox " + id + " est bien " + state);
            Hooks._scenario.log(Status.PASS, "Checkbox " + id + " est bien " + state);

        } catch (AssertionError e) {
            TestBase.notifyExtension("STEP_ERROR", "Échec assertion Checkbox " + id + ". Attendu: " + state);
            Hooks._scenario.log(Status.FAIL, "Échec de vérification : Checkbox " + id + " attendue " + state);
            throw e;
        }
    }
}