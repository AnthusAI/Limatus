@backend @editorial
Feature: Punch-line cadence
  As a copy editor
  I want a very short sentence that lands right after a long one flagged when it closes a paragraph or recurs within one
  So mic-drop rhythm is caught even when the sentence lengths around it vary

  Scenario: Two drops in one paragraph are both flagged
    Given a paragraph where two very short sentences each follow a long sentence
    When I diagnose it with the surface-rules profile
    Then diagnosis reports punch-line cadence findings for "Its confidence got better fast." and "Its accuracy didn't move."

  Scenario: A short closing line after a long sentence is flagged
    Given a paragraph that ends on a very short sentence after a long one
    When I diagnose it with the surface-rules profile
    Then diagnosis reports punch-line cadence findings for "Nobody trained anything."

  Scenario: A terse tag closing a paragraph of shortening sentences is flagged
    Given a paragraph whose sentences shorten until a three-word closing line
    When I diagnose it with the surface-rules profile
    Then diagnosis reports punch-line cadence findings for "Nobody trained anything."

  Scenario: List lead-ins, questions, quotations, link-only calls to action, and code fences are not punch lines
    Given a draft whose short sentences after long ones are a list lead-in, a question, a quotation, a link, and a code fence
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no punch-line cadence finding

  Scenario: A short closing line that states a number is not a punch line
    Given a paragraph that ends on a short sentence with a number in it after a long one
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no punch-line cadence finding

  Scenario: A closing ellipsis is not a punch line
    Given a paragraph that ends on a stand-alone ellipsis after a long sentence
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no punch-line cadence finding

  Scenario: A short closer after a quoted sentence is still flagged
    Given a paragraph where a quoted sentence is followed by a very short closing line
    When I diagnose it with the surface-rules profile
    Then diagnosis reports punch-line cadence findings for "So we did."

  Scenario: One short sentence in the middle of a paragraph is not flagged
    Given a paragraph with a single short sentence between two long ones
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no punch-line cadence finding

  Scenario: Headings, list items, and table rows are not prose paragraphs
    Given a draft whose short lines are headings, list items, and table rows
    When I diagnose it with the surface-rules profile
    Then diagnosis reports no punch-line cadence finding

  Scenario: A profile can turn the check off
    Given a paragraph that ends on a very short sentence after a long one
    When I diagnose it with a profile where punchlineCadence is off
    Then diagnosis reports no punch-line cadence finding
