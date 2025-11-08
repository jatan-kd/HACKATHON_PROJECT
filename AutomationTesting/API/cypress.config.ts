import { defineConfig } from 'cypress'

export default defineConfig({
  viewportWidth: 1360,
  viewportHeight: 790,
  reporter: 'cypress-multi-reporters',
  reporterOptions: {
    reporterEnabled: 'mochawesome, mocha-junit-reporter',
    mochawesomeReporterOptions: {
      reportDir: 'cypress/reports/mocha',
      quite: true,
      overwrite: false,
      html: false,
      json: true,
    },
    mochaJunitReporterReporterOptions: {
      mochaFile: 'cypress/reports/junit/test-results.[hash].xml',
      testsuitesTitle: false,
    },
  },
  chromeWebSecurity: false,
  modifyObstructiveCode: false,
  env: {
    client: '<inject_variable_3>',
    env: '<inject_variable_4>',
  },
  responseTimeout: 300000,
  screenshotOnRunFailure: false,
  video: false,
  e2e: {
    // We've imported your old cypress plugins here.
    // You may want to clean this up later by importing these.
    setupNodeEvents(on, config) {
      return require('./cypress/plugins/index.js')(on, config)
    },
    specPattern: ['**/*.feature']
  },
})
