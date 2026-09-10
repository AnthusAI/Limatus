@backend @editorial
Feature: Loop provenance record
  As a copy-editing agent
  I want an inspectable record of scan, decisions, options, and compare
  So audit trails retain model and prompt versions

  Scenario: Compose a loop record without persistence
    Given a completed agent shortlist pass
    When I compose a loop provenance record
    Then the record includes scan decisions options and compare ranking
    And the record does not include rewritten prose
