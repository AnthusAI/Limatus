@backend @editorial
Feature: Composable editorial suggestions
  Scenario: Request an optional rewrite suggestion
    Given a draft, portable style profile, and diagnostic annotations
    When a caller invokes the suggestion tool
    Then Limatus returns reviewable candidates with rationale and a diff
    And the source draft remains unchanged

  Scenario: Focus without prescribing a process
    Given a draft and optional finding guidance
    When a caller invokes the suggestion tool
    Then the guidance informs the candidates without requiring a decision record
    And the caller may use the candidate with or without other Limatus tools
