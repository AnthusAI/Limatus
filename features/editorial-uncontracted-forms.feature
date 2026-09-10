@backend @editorial
Feature: Uncontracted forms
  As a publication operator whose style profile says to use contractions
  I want formal, uncontracted phrasing flagged even though it's grammatically fine
  So a stated voice rule ("use contractions") is actually checked, not just written down

  Scenario: A formal construction with a common contraction is flagged
    Given a draft that says "That is the same family, and it does not change."
    When I diagnose it with the surface-rules profile
    Then diagnosis reports uncontracted-form findings for "That is" and "does not"

  Scenario: The clarifying "that is," is not flagged
    Given a draft that uses the clarifying phrase "the model, that is, the finetuned version"
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no uncontracted-form finding

  Scenario: A profile can turn the check off for a formal or impersonal register
    Given a draft that says "That is the same family, and it does not change."
    When I diagnose it with a profile where uncontractedForms is off
    Then diagnosis reports no uncontracted-form finding
