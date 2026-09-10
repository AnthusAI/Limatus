@backend @editorial
Feature: Regression compare
  As a copy-editing agent
  I want to compare the original to a tweaked working copy
  So I know whether my edit got worse

  Scenario: Working copy
    Given an original draft and a working copy after a trial edit
    When I run limatus compare
    Then the report includes always-lane deltas
    And optional rubric deltas if a judge is configured
    And both files are unchanged
