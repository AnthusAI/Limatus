@backend @editorial
Feature: Hard constraints on compare
  As a copy-editing agent
  I want factual/unsupported-claim regressions to lose
  Even if the prose sounds smoother

  Scenario: New unsupported claim
    Given an original draft and a candidate that adds an unsupported claim
    When I run limatus compare
    Then the candidate is not rank 1
    And the report names the unsupported-claim increase
    And detector score is not an input
