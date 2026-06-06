declare module "@mathieuc/tradingview" {
  interface ClientOptions {
    token?: string;
    signature?: string;
  }

  interface ChartOptions {
    timeframe?: string;
    range?: number;
  }

  interface Period {
    time: number;
    open: number;
    close: number;
    max: number;
    min: number;
    volume: number;
    [key: string]: unknown;
  }

  interface Chart {
    setMarket(symbol: string, options?: ChartOptions): void;
    onUpdate(callback: () => void): void;
    periods: Period[];
    delete(): void;
    Study: new (name: string) => Study;
  }

  interface Study {
    onUpdate(callback: () => void): void;
    periods: Array<Record<string, unknown>>;
  }

  interface Session {
    Chart: new () => Chart;
  }

  class Client {
    constructor(options?: ClientOptions);
    Session: Session;
    end(): void;
  }

  function getScreener(screener: string): Promise<unknown>;
  function searchMarket(query: string, type?: string): Promise<unknown[]>;

  const _default: {
    Client: typeof Client;
    getScreener: typeof getScreener;
    searchMarket: typeof searchMarket;
  };

  export default _default;
}
