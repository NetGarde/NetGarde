export type TwinAlert = {
  id: number;
  timestamp: string;
  device_id: string;
  event_id?: string | null;
  event_type?: string | null;
  alert_type: string;
  severity: string;
  message?: string | null;
  detail?: string | null;
  created_at?: string | null;
};

export type TwinAlertListResponse = {
  items: TwinAlert[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type TwinAlertListParams = {
  page?: number;
  page_size?: number;
  severity?: string;
  alert_type?: string;
  device_id?: string;
};
