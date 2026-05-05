package pages;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

public class CheckboxesPage {
    private WebDriver driver;

    private By cb1 = By.xpath("//form[@id='checkboxes']/input[1]");
    private By cb2 = By.xpath("//form[@id='checkboxes']/input[2]");

    public CheckboxesPage(WebDriver driver) {
        this.driver = driver;
    }

    public void open() {
        driver.get("https://the-internet.herokuapp.com/checkboxes");
    }

    public void toggle(int id) {
        if (id == 1) driver.findElement(cb1).click();
        else driver.findElement(cb2).click();
    }

    public boolean isChecked(int id) {
        return (id == 1) ? driver.findElement(cb1).isSelected() : driver.findElement(cb2).isSelected();
    }
}