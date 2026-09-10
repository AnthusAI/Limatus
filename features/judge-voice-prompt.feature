@backend @editorial
Feature: Judge voice prompt
  As a copy-editing agent
  I want the OpenAI judge to receive the full configured voice
  So judge findings align with house style without humans restating voice rules

  Scenario: Judge user prompt includes configured voice fields
    Given a style profile for judge voice prompt fixtures
    When I build the OpenAI judge user prompt for a short draft
    Then the judge user prompt includes the sentence style marker
    And the judge user prompt includes the structure marker
    And the judge user prompt includes the voice patterns marker

  Scenario: Reference samples are truncated excerpts
    Given a style profile for judge voice prompt fixtures
    When I build the OpenAI judge user prompt for a short draft
    Then the judge user prompt includes the short reference sample body
    And the judge user prompt omits the long reference sample tail marker

  Scenario: Judge system prompt forbids rewriting
    When I read the judge system prompt
    Then the judge system prompt forbids rewriting the draft
