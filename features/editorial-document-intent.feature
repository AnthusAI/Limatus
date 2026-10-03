@backend @editorial
Feature: Document intent
  As a copy editor
  I want the document intent taken from the first prose sentence
  So an MDX import line or front matter never stands in for what the draft is about

  Scenario: An MDX draft's intent is its first prose sentence
    Given an MDX draft with an import, a figure, and a heading before an opening paragraph that uses "scorecard"
    When I diagnose it with the surface-rules profile
    Then the document intent is "Every month the client gets a scorecard with 4 rows on it."

  Scenario: A plain draft's intent is its first sentence
    Given a paragraph that ends on a very short sentence after a long one
    When I diagnose it with the surface-rules profile
    Then the document intent is "The reviewers kept disagreeing with the same kind of verdict."

  Scenario: An opening paragraph that starts with inline markup is still the opener
    Given a draft whose opening paragraph starts with an inline emphasis tag
    When I diagnose it with the surface-rules profile
    Then the document intent is "<em>Plexus</em> is the platform we run the whole loop on."
