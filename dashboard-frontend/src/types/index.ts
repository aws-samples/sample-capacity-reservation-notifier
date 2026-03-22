// TypeScript type definitions for Capacity Reservation Dashboard

export type ReservationStatus = 'expired' | 'not_fully_launched' | 'expiring_soon' | 'starting_soon' | 'normal';

export interface Tag {
  key: string;
  value: string;
}

export interface DisplayInfo {
  message: string;
  startDateLocal?: string;
  endDateLocal?: string;
}

export interface CapacityReservation {
  CapacityReservationId: string;
  Region: string;
  name: string;
  State: string;
  InstanceType: string;
  AvailabilityZone: string;
  TotalInstanceCount: number;
  AvailableInstanceCount: number;
  StartDate?: string;
  EndDate?: string;
  Tags: Tag[];
  status: ReservationStatus;
  statuses: ReservationStatus[];
  statusTags: { status: ReservationStatus; color: string; message?: string }[];
  statusColor: string;
  displayInfo: DisplayInfo;
}

export interface RegionSummary {
  total: number;
  expired: number;
  not_fully_launched: number;
  expiring_soon: number;
  starting_soon: number;
  normal: number;
}

export interface RegionData {
  regionName: string;
  reservations: CapacityReservation[];
  summary: RegionSummary;
}

export interface GlobalSummary {
  totalRegions: number;
  totalReservations: number;
  byStatus: {
    expired: number;
    not_fully_launched: number;
    expiring_soon: number;
    starting_soon: number;
    normal: number;
  };
}

export interface ReservationsResponse {
  regions: RegionData[];
  summary: GlobalSummary;
  timestamp: string;
  timestampLocal: string;
}

export interface Instance {
  instanceId: string;
  name?: string;
  instanceType: string;
  state: string;
  privateIpAddress?: string;
  publicIpAddress?: string;
  launchTime?: string;
  availabilityZone?: string;
  tags: Tag[];
}

export interface InstancesResponse {
  reservationId: string;
  region: string;
  instances: Instance[];
  summary: {
    total: number;
    running: number;
  };
}

export interface ApiError {
  code: string;
  message: string;
}

export interface StatusCheckSubscription {
  instanceId: string;
  region: string;
  subscribed: boolean;
  alarms: string[];
}
