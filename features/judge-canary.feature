@backend @editorial @canary
Feature: Judge canary
  As an operator
  I want a small fixture canary
  So a prompt or Terra-default change is visible

  Scenario: Versioned canary
    Given the canary fixture drafts
    When the eval runner scans them with the configured judge fake or live
    Then each result records promptVersion and model
    And house-voice canary drafts do not gain density flags on the always-lane
