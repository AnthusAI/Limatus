@backend @editorial
Feature: Style profile store for a publication voice
  As a publication operator
  I want an editable style profile and approved reference samples
  So later editorial passes can match house voice instead of generic Internet prose

  Scenario: Load a stored style profile
    Given a publication has an editable style profile on disk
    And the profile names voice, audience, tone, sentence style, structure, prefer and avoid lexicon, and evidence rules
    And five to ten approved reference samples are linked for voice match
    When an editorial pass loads the profile
    Then the loader returns the profile and the linked samples
    And the profile does not contain detector scores

  Scenario: Reject a profile that includes detector scores
    Given a style profile that includes a detector score
    When an editorial pass tries to load the profile
    Then loading fails with a validation error

  Scenario: Load a portable JSON profile with relative samples
    Given a publication has a portable JSON style profile on disk
    When an editorial pass loads the profile
    Then the loader returns the profile and the linked samples
    And all linked samples resolve relative to the profile

  Scenario: Reject malformed profile configuration with an actionable error
    Given a malformed style profile configuration
    When an editorial pass tries to load the profile
    Then loading fails with a validation error
    And the validation error identifies the profile configuration

  Scenario Outline: Reject invalid profile controls
    Given a style profile with an invalid <control>
    When an editorial pass tries to load the profile
    Then loading fails with a validation error

    Examples:
      | control          |
      | check name       |
      | density threshold|
      | rule name        |
