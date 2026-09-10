@backend @editorial
Feature: Judge optional at runtime
  As a copy-editing agent in CI
  I want scan to succeed without OPENAI_API_KEY
  So always-lane regressions still run

  Scenario: No key
    Given a profile with the OpenAI judge enabled
    And OPENAI_API_KEY is unset
    When I run limatus scan without require-judge
    Then always-lane findings are present
    And judge findings are absent
