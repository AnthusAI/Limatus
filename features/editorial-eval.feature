@backend @editorial @eval
Feature: Offline editorial evaluation smoke harness
  As a publication operator
  I want a deterministic local eval over checked-in drafts
  So regressions fail without a network or an LLM

  Scenario: Checked-in corpus passes offline evaluation
    Given the checked-in editorial eval manifest
    When I run the offline eval command
    Then the offline eval exits successfully
    And it reports pass and fail corpus coverage

  Scenario: A missing expected finding is a regression
    Given a temporary eval manifest expecting a missing finding kind
    When I run the offline eval command
    Then the offline eval exits with a regression failure
