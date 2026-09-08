@backend @editorial
Feature: Verify a human-steered revision
  As a publication operator
  I want an advisory verifier for an explicitly applied working draft
  So I can decide whether it improved before human approval

  Scenario: Recommend an improved revision
    Given an original draft and an explicitly applied working draft
    When an operator runs verification with local style rules
    Then Limatus reports quality dimensions and evidence-backed findings
    And it recommends acceptance only when the threshold is met and unsupported claims have not increased
    And neither draft is changed

  Scenario: Reject a riskier revision
    Given a working draft with a new unsupported claim or a factual-change risk
    When an operator runs verification
    Then Limatus advises against acceptance
    And it does not publish or modify either draft
