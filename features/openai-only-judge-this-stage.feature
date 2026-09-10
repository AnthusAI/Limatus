@backend @editorial
Feature: OpenAI-only judge this stage
  As an operator
  I want a clear error if I name Bedrock or Anthropic
  So we do not pretend multi-provider support exists

  Scenario: Unknown provider
    Given a profile that sets judge provider to anthropic
    When I run limatus scan
    Then the command fails with an unsupported-provider error
