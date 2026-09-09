@backend @editorial
Feature: Overused crutch words
  As a publication operator or agent
  I want a draft flagged when it leans on the same hedge or crutch word
  repeatedly, even though no single use of that word is itself banned
  So a tell of AI-generated prose gets caught even when it isn't on anyone's banned-word list

  Scenario: A crutch word repeated well past ordinary use is flagged
    Given a draft that uses "actually" far more than ordinary prose would
    When I diagnose it with the surface-rules profile
    Then diagnosis reports an overused-word finding for "actually"

  Scenario: A crutch word used once or twice is not flagged
    Given a draft that uses "really" only twice
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no overused-word finding
