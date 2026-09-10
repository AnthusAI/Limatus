@backend @editorial
Feature: Finding provenance
  As a later compare or options step
  I want to know which lane produced each finding
  So I can treat profile hits as hard and judge hits as stochastic

  Scenario: Source field is required
    Given a completed scan JSON
    Then every finding has source equal to profile or judge
    And judge findings have model and promptVersion
    And profile findings do not require a model field
