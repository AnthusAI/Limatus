@backend @editorial
Feature: Annotated scan export
  As a copy-editing agent
  I want Markus and XML views of scan findings
  So I can review portable marked-up text

  Scenario: Markup flags
    Given a draft and style profile
    When I run limatus scan with markup-out and xml-out
    Then the Markdown contains editorial-finding directives
    And the XML lists findings with ids and spans
    And the draft file is unchanged
