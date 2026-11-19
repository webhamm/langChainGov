This new feature is to create a way to maximize the amount of tokens being processed for a model in order to stretch the ability to process the tokens and evaluate the drift in responses to the tests.

Parts of the feature we need
* A consistent max generation of characters for tokens input maxing for context windows.
* A method of sending out the request that is consitent and captures the return result.
* Evaluation for historical comparisions over time to determine differnces and any drift in return potentially.
