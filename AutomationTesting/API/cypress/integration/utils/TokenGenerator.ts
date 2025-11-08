export class TokenGenerator
{
    static GenerateToken(configFile:any)
    {
        return new Cypress.Promise((resolve) =>
        {
            cy.request
            (
                {
                    method: "POST",
                    url: configFile[Cypress.env("client")].APIURL,
                    body:
                    {
                        gaun: configFile[Cypress.env("client")].USERNAME,
                        gapw: configFile[Cypress.env("client")].PASSWORDAPI,
                        bpc: configFile[Cypress.env("client")].BUYERPARTNERCODE,
                        partnerCode: configFile[Cypress.env("client")].PARTNERCODE,
                        smartFlag: false,
                    },
                    headers: {"Postman-Token":"889c138e-1827-4157-8029-7ef8f8e13bf0,d3ef544f-0231-4910-be50-f1bd253ee4e1"},
                }
            ).then((tokenGeneratorResponse) => resolve(tokenGeneratorResponse));
        });
    }
}