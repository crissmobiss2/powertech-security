// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenClaims {
  sub: string;
  tenant_id: string;
  client_id: string | null;
  role: UserRole;
  permissions: string[];
  exp: number;
}

export type UserRole =
  | "super_admin"
  | "client_admin"
  | "security_director"
  | "soc_analyst"
  | "it_engineer"
  | "field_technician"
  | "site_supervisor"
  | "executive"
  | "auditor";

// ─── Common ───────────────────────────────────────────────────────────────────
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

// ─── Client ───────────────────────────────────────────────────────────────────
export type RiskTier = "critical" | "high" | "medium" | "low";

export interface Client {
  id: string;
  tenant_id: string;
  code: string;
  name: string;
  industry: string | null;
  risk_tier: RiskTier;
  status: "active" | "inactive" | "suspended" | "prospect";
  billing_email: string | null;
  address: Record<string, string> | null;
  sla_config: Record<string, number> | null;
  notes: string | null;
  account_manager_id: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Site ─────────────────────────────────────────────────────────────────────
export interface Site {
  id: string;
  tenant_id: string;
  client_id: string;
  name: string;
  code: string | null;
  address: Record<string, string> | null;
  latitude: number | null;
  longitude: number | null;
  risk_level: RiskTier;
  timezone: string;
  type: string;
  status: string;
  emergency_contacts: Array<{name: string; role: string; phone: string; email: string}> | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Asset ────────────────────────────────────────────────────────────────────
export type AssetStatus = "online" | "offline" | "degraded" | "maintenance" | "decommissioned" | "unknown";
export type AssetType =
  | "camera" | "nvr" | "dvr" | "access_panel" | "door_controller" | "biometric"
  | "server" | "workstation" | "laptop" | "network_switch" | "router" | "firewall"
  | "ups" | "sensor" | "iot_device" | "cloud_resource" | "other";

export interface Asset {
  id: string;
  tenant_id: string;
  client_id: string;
  site_id: string | null;
  name: string;
  code: string | null;
  type: AssetType;
  sub_type: string | null;
  status: AssetStatus;
  ip_address: string | null;
  mac_address: string | null;
  serial_number: string | null;
  manufacturer: string | null;
  model: string | null;
  firmware_version: string | null;
  location_detail: string | null;
  floor: string | null;
  zone: string | null;
  last_seen_at: string | null;
  tags: string[] | null;
  metadata: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

// ─── Incident ─────────────────────────────────────────────────────────────────
export type IncidentSeverity = "critical" | "high" | "medium" | "low" | "info";
export type IncidentStatus =
  | "new" | "acknowledged" | "investigating" | "in_progress"
  | "resolved" | "closed" | "false_positive";
export type IncidentType = "physical" | "cyber" | "combined" | "operational";

export interface Incident {
  id: string;
  tenant_id: string;
  client_id: string;
  site_id: string | null;
  title: string;
  description: string | null;
  severity: IncidentSeverity;
  status: IncidentStatus;
  type: IncidentType;
  source: string;
  assigned_to: string | null;
  escalated_to: string | null;
  sla_due_at: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  resolution_summary: string | null;
  tags: string[] | null;
  metadata: Record<string, unknown> | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentTimelineEntry {
  id: string;
  incident_id: string;
  user_id: string | null;
  event_type: string;
  description: string;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

// ─── Alert ────────────────────────────────────────────────────────────────────
export type AlertChannel = "sms" | "email" | "push" | "in_app" | "whatsapp" | "telegram" | "voice";
export type AlertStatus = "draft" | "sending" | "sent" | "partial_failure" | "failed";

export interface Alert {
  id: string;
  tenant_id: string;
  client_id: string | null;
  incident_id: string | null;
  title: string;
  message: string;
  severity: IncidentSeverity;
  type: string;
  status: AlertStatus;
  channels: AlertChannel[];
  total_recipients: number;
  sent_count: number;
  delivered_count: number;
  acknowledged_count: number;
  failed_count: number;
  scheduled_at: string | null;
  sent_at: string | null;
  created_by: string | null;
  created_at: string;
}

// ─── Ticket ───────────────────────────────────────────────────────────────────
export type TicketStatus = "open" | "assigned" | "in_progress" | "on_hold" | "resolved" | "closed" | "cancelled";
export type TicketPriority = "critical" | "high" | "medium" | "low";

export interface Ticket {
  id: string;
  tenant_id: string;
  client_id: string;
  site_id: string | null;
  incident_id: string | null;
  asset_id: string | null;
  title: string;
  description: string | null;
  type: string;
  status: TicketStatus;
  priority: TicketPriority;
  assigned_to: string | null;
  sla_due_at: string | null;
  checkin_at: string | null;
  checkout_at: string | null;
  resolved_at: string | null;
  closed_at: string | null;
  client_signoff_at: string | null;
  client_signoff_by: string | null;
  labor_hours: number | null;
  cost: number | null;
  resolution_notes: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Playbook ─────────────────────────────────────────────────────────────────
export interface Playbook {
  id: string;
  tenant_id: string;
  name: string;
  description: string | null;
  trigger_type: string;
  trigger_config: Record<string, unknown> | null;
  conditions: Record<string, unknown> | null;
  actions: Array<{type: string; config: Record<string, unknown>}>;
  enabled: boolean;
  run_count: number;
  last_triggered_at: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

// ─── Dashboard stats ──────────────────────────────────────────────────────────
export interface DashboardStats {
  open_incidents: number;
  critical_incidents: number;
  assets_offline: number;
  open_tickets: number;
  alerts_sent_today: number;
  sla_breach_count: number;
}

// ─── AI Vision ───────────────────────────────────────────────────────────────
export type PersonType = "employee" | "contractor" | "visitor" | "vip" | "banned";
export type AccessLevel = "restricted" | "standard" | "elevated" | "full";
export type ThreatType =
  | "weapon_detected" | "aggressive_behavior" | "unauthorized_person"
  | "banned_person" | "intrusion" | "loitering" | "tailgating"
  | "crowd_anomaly" | "perimeter_breach" | "abandoned_object"
  | "vehicle_violation" | "fire_smoke" | "fall_detected"
  | "after_hours_presence";
export type ThreatStatus = "active" | "acknowledged" | "investigating" | "resolved" | "false_positive";

export interface AuthorizedPerson {
  id: string;
  tenant_id: string;
  client_id: string;
  site_ids: string[] | null;
  first_name: string;
  last_name: string;
  person_type: PersonType;
  employee_id: string | null;
  department: string | null;
  access_level: AccessLevel;
  status: string;
  photo_url: string | null;
  access_schedule: Record<string, unknown> | null;
  face_encoding_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface CameraFeed {
  id: string;
  tenant_id: string;
  client_id: string;
  site_id: string | null;
  asset_id: string | null;
  name: string;
  stream_url: string;
  stream_type: "rtsp" | "http" | "hls";
  location_description: string | null;
  floor: string | null;
  zone: string | null;
  ai_enabled: boolean;
  face_recognition_enabled: boolean;
  threat_detection_enabled: boolean;
  person_tracking_enabled: boolean;
  processing_fps: number;
  detection_confidence_threshold: number;
  roi_zones: Array<Record<string, unknown>> | null;
  status: string;
  last_frame_at: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface FaceDetection {
  id: string;
  camera_id: string;
  person_id: string | null;
  match_confidence: number | null;
  is_recognized: boolean;
  is_authorized: boolean;
  person_type_detected: string | null;
  person_name: string | null;
  bbox_x: number | null;
  bbox_y: number | null;
  bbox_w: number | null;
  bbox_h: number | null;
  estimated_age: number | null;
  age_range: string | null;
  gender: string | null;
  primary_emotion: string | null;
  mood_category: string | null;
  emotion_scores: Record<string, number> | null;
  body_language: {
    posture: string;
    stance: string;
    hand_position: string;
    movement_type: string;
    indicators: string[];
    confidence: number;
  } | null;
  appearance: {
    dominant_colors: Array<{ color: string; percentage: number }>;
    has_bag: boolean;
    has_hat: boolean;
    has_mask: boolean;
    has_glasses: boolean;
    clothing_description: string;
  } | null;
  threat_score: number | null;
  threat_level: string | null;
  threat_factors: string[] | null;
  snapshot_path: string | null;
  frame_timestamp: string;
  created_at: string;
}

export interface ThreatDetection {
  id: string;
  tenant_id: string;
  client_id: string;
  site_id: string | null;
  camera_id: string;
  incident_id: string | null;
  threat_type: ThreatType;
  severity: IncidentSeverity;
  confidence: number;
  status: ThreatStatus;
  description: string;
  snapshot_path: string | null;
  video_clip_path: string | null;
  detected_objects: Array<Record<string, unknown>> | null;
  zone: string | null;
  frame_timestamp: string;
  auto_response_triggered: boolean;
  response_actions: Array<Record<string, unknown>> | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  created_at: string;
}

export interface PersonTrack {
  id: string;
  site_id: string | null;
  person_id: string | null;
  track_id: string;
  is_identified: boolean;
  person_label: string | null;
  first_seen_at: string;
  last_seen_at: string;
  first_camera_id: string;
  last_camera_id: string;
  dwell_time_seconds: number;
  movement_path: Array<Record<string, unknown>> | null;
  threat_level: string;
  flags: string[] | null;
  snapshot_path: string | null;
  created_at: string;
}

export interface VisionDashboardStats {
  active_cameras: number;
  total_cameras: number;
  authorized_persons: number;
  faces_detected_today: number;
  unknown_faces_today: number;
  active_threats: number;
  threats_today: number;
  active_tracks: number;
  cameras_with_errors: number;
}
