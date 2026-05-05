package StepDefinitions;

import base.TestBase;
import io.cucumber.java.en.Given;
import io.cucumber.java.en.When;
import io.cucumber.java.en.Then;
import org.junit.jupiter.api.Assertions;
import pages.loginPage;
import com.aventstack.extentreports.Status;

public class LoginStep {

    private loginPage loginPage;

    public LoginStep() {
        this.loginPage = new loginPage(TestBase.getDriver());
    }

    @Given("the user is on the login page")
    public void userIsOnLoginPage() {
        TestBase.notifyExtension("STEP_START", "Navigation vers la page de login");
        try {
            loginPage.openLoginPage();
            Hooks._scenario.log(Status.PASS, "the user is on the login page");
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Erreur lors de l'ouverture de la page: " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "the user is on the login page");
            Hooks._scenario.log(Status.FAIL, e.getMessage());
        }
    }

    @When("the user enters a username as {string}")
    public void userEntersUsername(String username) {
        TestBase.notifyExtension("STEP_ACTION", "Saisie du login: " + username);
        try {
            loginPage.enterUsername(username);
            Hooks._scenario.log(Status.PASS, "the user enters a username");
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Erreur saisie username: " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "the user enters a username" );
            Hooks._scenario.log(Status.FAIL,e.getMessage());
        }
    }

    @When("the user enters a password as {string}")
    public void userEntersPassword(String password) {
        TestBase.notifyExtension("STEP_ACTION", "Saisie du mot de passe");
        try {
            loginPage.enterPassword(password);
            Hooks._scenario.log(Status.PASS, "the user enters a password");
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Erreur saisie password: " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "the user enters a password" );
            Hooks._scenario.log(Status.FAIL,  e.getMessage());
        }
    }

    @When("clicks on the login button")
    public void userClicksLoginButton() {
        TestBase.notifyExtension("STEP_ACTION", "Clic sur le bouton Login");
        try {
            loginPage.submitLogin();
            Hooks._scenario.log(Status.PASS, "clicks on the login button");
        } catch (Exception e) {
            TestBase.notifyExtension("STEP_ERROR", "Bouton de connexion introuvable: " + e.getMessage());
            Hooks._scenario.log(Status.FAIL, "clicks on the login button");
            Hooks._scenario.log(Status.FAIL,e.getMessage());
        }
    }

    @Then("the user should see a successful login message")
    public void userSeesSuccessfulLoginMessage() {
        TestBase.notifyExtension("STEP_VERIFY", "Vérification du succès de connexion");
        try {
            String successMessage = loginPage.getSuccessMessage();
            Assertions.assertTrue(successMessage.contains("You logged into a secure area!"),
                    "Expected success message not found");

            TestBase.notifyExtension("STEP_RESULT", "Succès détecté: " + successMessage);
            Hooks._scenario.log(Status.PASS, "The user should see a successful login message: " + successMessage);
        } catch (Throwable t) {
            TestBase.notifyExtension("STEP_ERROR", "Échec de l'assertion de succès: " + t.getMessage());
            Hooks._scenario.log(Status.FAIL, "The user should see a successful login message");
            Hooks._scenario.log(Status.FAIL, t.getMessage());
            throw t;
        }
    }

    @Then("the user should see a login failure message")
    public void userSeesLoginFailureMessage() {
        TestBase.notifyExtension("STEP_VERIFY", "Vérification de l'échec de connexion");
        try {
            String failureMessage = loginPage.getErrorMessage();
            Assertions.assertTrue(failureMessage.contains("Your username is invalid!") || failureMessage.contains("Your password is invalid!"),
                    "Expected failure message not found");

            TestBase.notifyExtension("STEP_RESULT", "Échec attendu détecté: " + failureMessage);
            Hooks._scenario.log(Status.PASS, "The user should see a login failure message: " + failureMessage);
        } catch (Throwable t) {
            TestBase.notifyExtension("STEP_ERROR", "Le message d'erreur n'est pas apparu comme prévu: " + t.getMessage());
            Hooks._scenario.log(Status.FAIL, "The user should see a login failure message");
            Hooks._scenario.log(Status.FAIL, t.getMessage());
            throw t;
        }
    }
}