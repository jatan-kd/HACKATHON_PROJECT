import { defineStep } from "cypress-cucumber-preprocessor/steps";

defineStep("do something", doSomething);
function doSomething()
{
  console.log("do something")
}