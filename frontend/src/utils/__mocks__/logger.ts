// Mock logger for Jest tests
export const createLogger = () => ({
    debug: jest.fn(),
    info: jest.fn(),
    warn: jest.fn(),
    error: jest.fn(),
});

export const withServiceLogging = <T extends any[], R>(
    fn: (...args: T) => Promise<R>,
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    _context: { service: string; operation: string; logArgs?: (args: T) => Record<string, unknown>; logResult?: (result: R) => Record<string, unknown> }
) => fn;

export const withApiLogging = <T extends any[], R>(
    fn: (...args: T) => Promise<R>
) => fn;

export const LogLevel = {
    setLevel: jest.fn(),
    showAll: jest.fn(),
};

