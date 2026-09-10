@backend @editorial
Feature: Agent shortlist before human
  As a copy-editing agent
  I want 2-3 patch options ranked by compare
  So a human sees a shortlist instead of raw patches

  Scenario: Ranked options
    Given rewrite decisions and generated options
    When I run limatus compare on those option texts
    Then I obtain a ranking of all options
    And I do not apply a winner automatically
    And the working draft is unchanged until a human apply is recorded
