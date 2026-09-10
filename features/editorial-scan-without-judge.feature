@backend @editorial
Feature: Scan without a judge
  As a copy-editing agent
  I want scan to work from a style profile alone
  So I get pertinent findings offline

  Scenario: Always-lane findings only
    Given a draft file and a loadable style profile
    And no judge is configured
    When I run limatus scan
    Then the JSON includes findings with source profile
    And the JSON does not include judge findings
    And the draft file is unchanged
    And the result does not include revised_text
