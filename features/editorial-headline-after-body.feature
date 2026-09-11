@backend @editorial
Feature: Headline HITL after body edits
  After the article body is edited on a working copy, title and subtitle
  options are generated separately from body scan findings. Frontmatter field
  keys come from the style profile headline block.

  Scenario: Body scan ignores YAML title and subtitle fields
    Given a working copy draft with YAML frontmatter and sloppy body prose
    And a style profile with headline keys for title and standfirst
    When I scan the working copy for body findings
    Then no finding span overlaps the frontmatter block

  Scenario: Title headline options replace only the title scalar
    Given a working copy draft with YAML frontmatter and sloppy body prose
    And a style profile with headline keys for title and standfirst
    When I generate headline options for job title on the working copy
    Then each title option patch replaces only the title value span
    And the working copy file bytes are unchanged

  Scenario: Subtitle headline options see the applied title and body
    Given a working copy draft with YAML frontmatter and sloppy body prose
    And a style profile with headline keys for title and standfirst
    When I generate headline options for job subtitle on the working copy
    Then the subtitle resolver received the current title and article body
    And each subtitle option patch replaces only the standfirst value span
    And the working copy file bytes are unchanged
