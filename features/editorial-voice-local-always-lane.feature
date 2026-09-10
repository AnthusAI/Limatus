@backend @editorial
Feature: Voice-local always lane
  As a publication operator
  I want scan to honor this publication's profile
  So Anth.us and another voice do not share one generic slop list

  Scenario: Two profiles
    Given one draft and two loadable style profiles with different banned phrases
    When I run limatus scan with each profile and no judge
    Then the finding sets differ
    And each banned-phrase hit matches the profile that was loaded
