Feature: Follow activity
    In order to keep an eye on activities interesting.
    As a fellow member,
    I want to follow some activities
    Scenario: Follow activity 4fe0239a831529747c000000
        Given I am logged in as leafduo with password 123456
        When I follow activity 4fe0239a831529747c000000
        Then system shows operation completed successfully
