/// <reference types="node" />

declare global {
  namespace NodeJS {
    interface Global {
      fetch: typeof fetch
    }
  }
}

export {}
