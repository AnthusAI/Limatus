@backend @editorial
Feature: OpenAI judge configuration
  As a copy-editing agent
  I want Terra as the default judge model
  So scan stays cheap enough to run often

  Scenario: Default model
    Given a profile that enables the OpenAI judge without naming a model
    When I inspect the scan configuration
    Then the judge model is the documented Terra default

  Scenario: Fake judge in acceptance tests
    Given a draft and a fake judge resolver that emits one clarity finding
    When I run limatus scan
    Then the output includes that judge finding
    And production code has no LIMATUS_TEST environment hook
