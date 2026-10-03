@backend @editorial
Feature: Opening screen
  As a publication operator
  I want the opening paragraph checked for vocabulary the reader hasn't been given, and optionally for a concrete number
  So the first screen reads for a general reader before any product or trade term arrives

  Scenario: An undefined insider term in the opening paragraph is flagged
    Given a draft whose opening paragraph uses "decision model" without defining it
    When I diagnose it with the opening-screen profile
    Then diagnosis reports an opening-screen finding for "decision model"

  Scenario: A term defined in the same sentence is not flagged
    Given a draft whose opening paragraph defines "decision model" where it first appears
    When I diagnose it with the opening-screen profile
    Then diagnosis reports no opening-screen finding for "decision model"

  Scenario: Overlapping terms report one finding
    Given a draft whose opening paragraph uses "hosted decision model" without defining it
    When I diagnose it with the opening-screen profile
    Then diagnosis reports exactly one opening-screen finding

  Scenario: The same term later in the body is not flagged
    Given a draft that first uses "decision model" in its second paragraph
    When I diagnose it with the opening-screen profile
    Then diagnosis reports no opening-screen finding for "decision model"

  Scenario: Imports, figures, and headings before the first paragraph are skipped
    Given an MDX draft with an import, a figure, and a heading before an opening paragraph that uses "scorecard"
    When I diagnose it with the opening-screen profile
    Then diagnosis reports an opening-screen finding for "scorecard"

  Scenario: An opening with no number is flagged when the profile requires one
    Given a draft whose first number arrives in its second paragraph
    When I diagnose it with the opening-screen profile
    Then diagnosis reports an opening-screen finding about a missing number

  Scenario: A digit inside a link address is not a number in the prose
    Given a draft whose only later digit is inside a link address
    When I diagnose it with the opening-screen profile
    Then diagnosis reports no opening-screen finding about a missing number

  Scenario: A digit inside a component attribute is not a number in the prose
    Given a draft whose only later digit is inside a citation component attribute
    When I diagnose it with the opening-screen profile
    Then diagnosis reports no opening-screen finding about a missing number

  Scenario: A comma that starts a new clause does not define the term
    Given a draft whose opening paragraph follows "decision model" with a comma and "and"
    When I diagnose it with the opening-screen profile
    Then diagnosis reports an opening-screen finding for "decision model"

  Scenario: A profile without opening rules reports nothing
    Given a draft whose opening paragraph uses "decision model" without defining it
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no opening-screen finding for "decision model"
