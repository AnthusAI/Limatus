@backend @editorial
Feature: Standfirst checks
  As a publication operator, I want the checkable parts of a good standfirst
  enforced automatically -- length, whether it names somebody the reader
  hasn't met, whether it leans on inside vocabulary, whether it just repeats
  the description -- so a copywriting agent can iterate on a candidate
  sentence before it ever reaches the file.

  Scenario: A well-formed standfirst passes clean
    Given a standfirst that fits the shape rules and names no strangers
    When I check the standfirst against the surface-rules profile
    Then no standfirst findings are reported

  Scenario: A standfirst that runs too long is flagged
    Given a standfirst with three sentences
    When I check the standfirst against the surface-rules profile
    Then a standfirst finding mentions the sentence cap

  Scenario: A standfirst naming an unintroduced person is flagged
    Given a standfirst naming a person absent from the article body
    When I check the standfirst against the surface-rules profile
    Then a standfirst finding mentions a name the reader has not met

  Scenario: A standfirst using insider vocabulary is flagged
    Given a standfirst that uses an insider term
    When I check the standfirst against the surface-rules profile
    Then a standfirst finding mentions insider vocabulary

  Scenario: A standfirst that only repeats the description is flagged
    Given a standfirst that closely repeats its description
    When I check the standfirst against the surface-rules profile
    Then a standfirst finding mentions the description overlap
