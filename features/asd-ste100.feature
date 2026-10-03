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

  Scenario: An unapproved word with a known alternative is flagged
    Given an ASD-STE100 style profile with default limits
    When I run the diagnose command on the unapproved-word draft
    Then the diagnosis reports an asd_unapproved_word finding naming the approved alternative

  Scenario: Approved words and technical names are not flagged
    Given an ASD-STE100 style profile with default limits
    When I run the diagnose command on the clean technical draft
    Then the diagnosis reports no asd_ findings

  Scenario: A verb-only word used as a noun is flagged
    Given an ASD-STE100 style profile with default limits
    When I run the diagnose command on the multi-meaning draft
    Then the diagnosis reports an asd_multi_meaning finding for the noun usage

  Scenario: Profile-approved words override the packaged dictionary
    Given an ASD-STE100 style profile with dictionary overrides
    When I run the diagnose command on the override-approved draft
    Then the diagnosis reports no asd_ findings

  Scenario: Profile-unapproved words extend the packaged dictionary
    Given an ASD-STE100 style profile with dictionary overrides
    When I run the diagnose command on the override-unapproved draft
    Then the diagnosis reports an asd_unapproved_word finding naming the approved alternative