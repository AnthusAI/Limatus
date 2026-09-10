@backend @editorial
Feature: Density flags respect profile thresholds
  As a publication operator
  I want density findings only when the draft is long enough and actually fluffy
  So house voice is not punished

  Scenario: House voice
    Given an Anth.us reference excerpt longer than minWords
    And the Anth.us style profile
    When I run limatus scan with no judge
    Then there is no low_lexical_density finding
    And there is no high_compressibility finding

  Scenario: Short draft
    Given a fluffy draft shorter than minWords
    When I run limatus scan with no judge
    Then there is no low_lexical_density finding
    And there is no high_compressibility finding
