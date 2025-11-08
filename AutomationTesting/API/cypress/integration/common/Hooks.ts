import { TestingContext } from "../utils/TestingContext";
import { TokenGenerator } from "../utils/TokenGenerator";

//TODO define format for test step definitions closer to typescript/oop guidelines
before(() =>
{
  cy.fixture(`config/${ Cypress.env("env").toLowerCase() }.json`).then((configFile) =>
  {
      TestingContext.SetInTestRunContext("baseUrl", configFile[Cypress.env("client")].BaseUrl);
      TestingContext.SetInTestRunContext("ocpSubscriptionKey", configFile[Cypress.env("client")].OcpSubscriptionKey);
      TokenGenerator.GenerateToken(configFile).then((tokenGeneratorResponse:any) => TestingContext.SetInTestRunContext("authBearerToken", tokenGeneratorResponse.body.encryptedToken));
  });
});

beforeEach(() =>
{
  let headers=
  {
    "Authorization" : `Bearer ${TestingContext.GetFromTestRunContext<string>("authBearerToken")}`,
    "Ocp-Apim-Subscription-Key": TestingContext.GetFromTestRunContext<string>("ocpSubscriptionKey"),
    "Content-Type" : "application/json",
    "Access-Control-Allow-Origin" : "*",
    "Accept" : "application/json"
  }
  TestingContext.SetInScenarioContext("headers",headers);
});