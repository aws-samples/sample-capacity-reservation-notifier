/**
 * API Service
 *
 * Handles all API calls to the Capacity Reservation backend
 */

import axios, { AxiosInstance } from 'axios';
import type { ReservationsResponse, InstancesResponse } from '../types';

class CapacityReservationApi {
  private axios: AxiosInstance;

  constructor() {
    const baseURL = process.env.REACT_APP_API_ENDPOINT;
    const apiKey = process.env.REACT_APP_API_KEY;

    if (!baseURL) {
      throw new Error('REACT_APP_API_ENDPOINT is not configured');
    }

    if (!apiKey) {
      throw new Error('REACT_APP_API_KEY is not configured');
    }

    this.axios = axios.create({
      baseURL,
      headers: {
        'x-api-key': apiKey,
        'Content-Type': 'application/json'
      },
      timeout: 30000
    });

    // Response interceptor for error handling
    this.axios.interceptors.response.use(
      response => response,
      error => {
        console.error('API Error:', error);
        if (error.response) {
          // Server responded with error status
          throw new Error(error.response.data?.error?.message || 'API request failed');
        } else if (error.request) {
          // Request made but no response received
          throw new Error('No response from server. Please check your network connection.');
        } else {
          // Something else happened
          throw new Error(error.message || 'An unexpected error occurred');
        }
      }
    );
  }

  /**
   * Get all Capacity Reservations across all regions
   */
  async getAllReservations(): Promise<ReservationsResponse> {
    const response = await this.axios.get('/api/capacity-reservations');
    return response.data;
  }

  /**
   * Get EC2 instances for a specific Capacity Reservation
   */
  async getReservationInstances(reservationId: string, region: string): Promise<InstancesResponse> {
    const response = await this.axios.get(
      `/api/capacity-reservations/${reservationId}/instances`,
      {
        params: { region }
      }
    );
    return response.data;
  }
}

// Export singleton instance
export const api = new CapacityReservationApi();
