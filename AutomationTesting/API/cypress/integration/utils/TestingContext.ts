export class TestingContext {
    //TODO support paralel execution  
    static stepContext = new Map<string, any>();
    static scenarioContext = new Map<string, any>();
    static featureContext = new Map<string, any>();
    static testRunContext = new Map<string, any>();

    static SetInStepContext<T>(key: string, value: T) {
        this.stepContext.set(key, value);
    }

    static GetFromStepContext<T>(key: string): T {
        return this.stepContext.get(key) ??
            this.scenarioContext.get(key) ??
            this.featureContext.get(key) ??
            this.testRunContext.get(key);
    }

    static SetInScenarioContext<T>(key: string, value: T) {
        this.scenarioContext.set(key, value);
    }

    static GetFromScenarioContext<T>(key: string): T {
        return this.scenarioContext.get(key) ??
            this.featureContext.get(key) ??
            this.testRunContext.get(key);
    }

    static SetInFeatureContext<T>(key: string, value: T) {
        this.featureContext.set(key, value);
    }

    static GetFromFeatureContext<T>(key: string): T {
        return this.featureContext.get(key) ??
            this.testRunContext.get(key);
    }

    static SetInTestRunContext<T>(key: string, value: T) {
        this.testRunContext.set(key, value);
    }

    static GetFromTestRunContext<T>(key: string): T {
        return this.testRunContext.get(key);
    }
}

beforeEach(() => {
    TestingContext.stepContext = new Map<string, any>();
    TestingContext.scenarioContext = new Map<string, any>();
});

before(() => {
    TestingContext.featureContext = new Map<string, any>();
});