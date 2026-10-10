"""Selenium step definitions for the provided Product Catalog administration UI."""

import logging
from behave import when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as ec

ID_PREFIX = 'product_'


def field_id(name):
    """Map a human-readable field name onto its HTML identifier."""
    return ID_PREFIX + name.lower().replace(' ', '_')


@when('I visit the "Home Page"')
def visit_home(context):
    """Open the storefront administration form."""
    context.driver.get(context.base_url)


@then('I should see "{message}" in the title')
def check_title(context, message):
    """Check the browser's document title."""
    assert message in context.driver.title


@then('I should not see "{text_string}"')
def check_body_missing(context, text_string):
    """Check that a message does not appear in page content."""
    body = context.driver.find_element(By.TAG_NAME, 'body')
    assert text_string not in body.text


@when('I set the "{element_name}" to "{text_string}"')
def set_field(context, element_name, text_string):
    """Fill in a form field."""
    element = context.driver.find_element(By.ID, field_id(element_name))
    element.clear()
    element.send_keys(text_string)


@when('I change "{element_name}" to "{text_string}"')
def change_field(context, element_name, text_string):
    """Change a form field before updating the saved product."""
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        ec.presence_of_element_located((By.ID, field_id(element_name)))
    )
    element.clear()
    element.send_keys(text_string)


@when('I select "{text}" in the "{element_name}" dropdown')
def select_dropdown(context, text, element_name):
    """Choose a visible drop-down option."""
    menu = Select(context.driver.find_element(By.ID, field_id(element_name)))
    menu.select_by_visible_text(text)


@then('I should see "{text}" in the "{element_name}" dropdown')
def check_dropdown(context, text, element_name):
    """Assert the selected option."""
    menu = Select(context.driver.find_element(By.ID, field_id(element_name)))
    assert menu.first_selected_option.text == text


@then('the "{element_name}" field should be empty')
def check_field_empty(context, element_name):
    """Assert an input has been cleared."""
    field = context.driver.find_element(By.ID, field_id(element_name))
    assert field.get_attribute('value') == ''


@when('I copy the "{element_name}" field')
def copy_field(context, element_name):
    """Remember an ID so it can be pasted after clearing the form."""
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        ec.presence_of_element_located((By.ID, field_id(element_name)))
    )
    context.clipboard = element.get_attribute('value')
    logging.info('Copied field value: %s', context.clipboard)


@when('I paste the "{element_name}" field')
def paste_field(context, element_name):
    """Restore the copied ID into the form."""
    element = context.driver.find_element(By.ID, field_id(element_name))
    element.clear()
    element.send_keys(context.clipboard)


@when('I press the "{button}" button')
def click_button(context, button):
    """Click a named button using the UI's button-ID convention."""
    button_id = f"{button.lower().replace(' ', '-')}-btn"
    element = WebDriverWait(context.driver, context.wait_seconds).until(
        ec.element_to_be_clickable((By.ID, button_id))
    )
    element.click()


@then('I should see the message "{message}"')
def check_flash_message(context, message):
    """Wait for the Ajax response to update the flash message."""
    assert WebDriverWait(context.driver, context.wait_seconds).until(
        ec.text_to_be_present_in_element((By.ID, 'flash_message'), message)
    )


@then('I should see "{text_string}" in the "{element_name}" field')
def check_field_value(context, text_string, element_name):
    """Wait until the expected value is present in a field."""
    assert WebDriverWait(context.driver, context.wait_seconds).until(
        ec.text_to_be_present_in_element_value((By.ID, field_id(element_name)), text_string)
    )


@then('I should see "{text_string}" in the results')
def check_results_contain(context, text_string):
    """Look for a product in the search-results table."""
    assert WebDriverWait(context.driver, context.wait_seconds).until(
        ec.text_to_be_present_in_element((By.ID, 'search_results'), text_string)
    )


@then('I should not see "{text_string}" in the results')
def check_results_missing(context, text_string):
    """Confirm a search-results table does not contain an item."""
    table = context.driver.find_element(By.ID, 'search_results')
    assert text_string not in table.text
