@backend @editorial
Feature: Explicit finding decisions
  As a copy-editing agent
  I want to mark findings skip or rewrite myself
  So the scanner is not a silent editor

  Scenario: Scan then decide
    Given scan JSON with profile and optional judge findings
    When I record skip on one finding and rewrite on another
    Then later option generation is eligible only for the rewrite finding
    And the draft is unchanged
