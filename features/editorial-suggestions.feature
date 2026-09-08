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

  Scenario: Preserve approved colloquial source language
    Given a source draft that uses an ordinary colloquial term such as `ngl`
    When Limatus validates a suggestion that preserves the term without instructing evasion
    Then the suggestion is accepted for review

  Scenario: Reject an evasion instruction
    Given a suggestion that recommends adding slang or fake experience to evade detection
    When Limatus validates it
    Then it rejects the suggestion with a safety error
