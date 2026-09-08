@backend @editorial
Feature: Human-steered editorial apply and diff
  As an editor
  I want to apply exactly one explicitly selected patch to a working copy
  So the original draft remains preserved and every change is reviewable

  Scenario: Apply one selected option and show an original-versus-working diff
    Given an original draft, a separate working copy, and one options payload
    When I apply the selected option with its exact anchor
    Then only the selected span changes in the working copy
    And the original draft is unchanged
    And a machine-readable change log records the selected option
    And the original-versus-working diff contains the selected replacement

  Scenario: Reject a stale or conflicting anchor without changing the working copy
    Given an original draft, a separate working copy, and one options payload
    When I apply the selected option with a stale anchor
    Then the apply fails safely
    And the working copy is unchanged
