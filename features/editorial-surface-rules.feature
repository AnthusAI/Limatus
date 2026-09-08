@backend @editorial
Feature: Surface-aware rules and a no-emoji ban
  As a publication operator with more than one kind of copy -- editorial
  prose, marketing pages, legal pages -- I want one style profile to apply
  a looser or disabled contrast cap to specific surfaces, and to ban emoji
  outright, without maintaining a separate profile per surface.

  Scenario: A draft with an emoji is flagged when noEmojis is enabled
    Given a draft containing an emoji character
    When I diagnose it with the surface-rules profile
    Then diagnosis reports a finding about the emoji

  Scenario: The default contrast cap applies with no surface given
    Given a draft with two "X, not Y" contrast constructions
    When I diagnose it with the surface-rules profile
    Then diagnosis reports a contrast cap finding

  Scenario: A surface override loosens the contrast cap
    Given a draft with two "X, not Y" contrast constructions
    When I diagnose it with the surface-rules profile for the "marketing" surface
    Then diagnosis reports no contrast cap finding

  Scenario: A surface override can disable the contrast cap entirely
    Given a draft with two "X, not Y" contrast constructions
    When I diagnose it with the surface-rules profile for the "legal" surface
    Then diagnosis reports no contrast cap finding
