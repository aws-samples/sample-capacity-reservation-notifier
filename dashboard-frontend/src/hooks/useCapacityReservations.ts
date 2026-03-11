/**
 * Custom React Hook for fetching Capacity Reservations
 *
 * Uses React Query for data fetching, caching, and automatic refetching
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export const useCapacityReservations = () => {
  return useQuery({
    queryKey: ['capacity-reservations'],
    queryFn: () => api.getAllReservations(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 5 * 60 * 1000, // Auto-refetch every 5 minutes
    retry: 2
  });
};

export const useReservationInstances = (reservationId: string, region: string, enabled: boolean = true) => {
  return useQuery({
    queryKey: ['reservation-instances', reservationId, region],
    queryFn: () => api.getReservationInstances(reservationId, region),
    enabled,
    staleTime: 2 * 60 * 1000, // 2 minutes
    retry: 1
  });
};
