const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

interface HealthResponse {
  status: string
  timestamp: string
  version: string
  environment: string
}

class ApiClient {
  baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  async health(): Promise<HealthResponse> {
    const response = await fetch(`${this.baseURL}/api/v1/health`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`)
    }

    return response.json()
  }
}

export const apiClient = new ApiClient(API_BASE_URL)