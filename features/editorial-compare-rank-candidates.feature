@backend @editorial
Feature: Rank rewrite candidates
  As a copy-editing agent
  I want to compare two or three options I generated
  So I can shortlist before asking a human

  Scenario: Three candidates
    Given a style profile and three candidate texts
    When I run limatus compare
    Then the JSON lists all three candidates
    And each has a rank and always-lane deltas versus the baseline
    And no candidate is omitted because it lost
    And none of the candidate files are modified
