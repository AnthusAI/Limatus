@backend @editorial @asd-ste100
Feature: ASD-STE100 rule-set plugin registration
  As a technical-publication operator
  I want to enable the ASD-STE100 Simplified Technical English rule set in a style profile
  So that procedure and description text is checked with STE rules instead of only the bot-slop heuristics

  Scenario: A style profile enables the ASD-STE100 rule set
    Given an ASD-STE100 style profile with default limits
    When I run the diagnose command on a procedure draft
    Then the diagnosis includes an asdSte100 summary
    And the asdSte100 summary reports mode auto with 20-word procedure and 25-word description limits
    And the result does not include rewritten prose

  Scenario: STE-only mode gates the bot-slop heuristics off
    Given an ASD-STE100 style profile in STE-only mode
    When I run the diagnose command on a sloppy draft
    Then the diagnosis includes an asdSte100 summary
    And the diagnosis contains no bot-slop kinds

  Scenario: Bot-slop heuristics stay available beside the ASD-STE100 rule set
    Given an ASD-STE100 style profile beside the bot-slop checks
    When I run the diagnose command on a sloppy draft
    Then the diagnosis includes an asdSte100 summary
    And the diagnosis contains at least one bot-slop kind

  Scenario: Unknown asd-ste100 options fail profile validation
    Given an ASD-STE100 style profile with an unknown option
    When I run the diagnose command on a procedure draft
    Then the command fails naming the unknown option

  Scenario: Invalid asd-ste100 limits fail profile validation
    Given an ASD-STE100 style profile with a non-positive word limit
    When I run the diagnose command on a procedure draft
    Then the command fails naming the word limit

  Scenario: Unknown checks keys fail profile validation
    Given an ASD-STE100 style profile with an unknown checks key
    When I run the diagnose command on a procedure draft
    Then the command fails naming the unknown checks key