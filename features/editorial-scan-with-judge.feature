@backend @editorial
Feature: Scan with configured judge
  As a copy-editing agent
  I want heuristic and judge findings in one list
  So I do not lose profile rules when Terra runs

  Scenario: Union not filter
    Given a draft that triggers a profile banned-phrase finding
    And a judge is configured that would not flag that phrase
    When I run limatus scan
    Then the banned-phrase finding is still present with source profile
    And any judge findings are additional
    And each judge finding records model and promptVersion
