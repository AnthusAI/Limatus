@backend @editorial
Feature: Scan and decide via CLI
  As a copy-editing agent
  I want to scan and record steering decisions from the CLI
  So the loop stays offline until options generation

  Scenario: Scan to file then append decisions without touching the draft
    Given a CLI scan fixture draft and style profile
    When I run python -m limatus scan with output diagnosis.json
    And I run python -m limatus decide for rewrite on one finding
    And I run python -m limatus decide for skip on another finding when available
    Then the diagnosis JSON has no steering decision fields
    And the decisions file validates
    And the draft file is unchanged
