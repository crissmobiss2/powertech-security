import axios, { AxiosError, AxiosInstance } from "axios";
import Cookies from "js-cookie";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const apiClient: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

// Attach access token from cookie on every request
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Auto-refresh on 401
apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean };
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;
      const refresh = Cookies.get("refresh_token");
      if (refresh) {
        try {
          const { data } = await axios.post(`${BASE_URL}/api/v1/auth/refresh`, {
            refresh_token: refresh,
          });
          Cookies.set("access_token", data.access_token, { secure: true, sameSite: "strict" });
          if (original.headers) {
            original.headers.Authorization = `Bearer ${data.access_token}`;
          }
          return apiClient(original);
        } catch {
          Cookies.remove("access_token");
          Cookies.remove("refresh_token");
          window.location.href = "/login";
        }
      } else {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

// ─── Resource helpers ─────────────────────────────────────────────────────────
export const api = {
  auth: {
    login: (email: string, password: string) =>
      apiClient.post("/auth/login", { email, password }).then((r) => r.data),
    logout: (refresh_token: string) =>
      apiClient.post("/auth/logout", { refresh_token }),
    me: () => apiClient.get("/auth/me").then((r) => r.data),
  },

  clients: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/clients", { params }).then((r) => r.data),
    get: (id: string) => apiClient.get(`/clients/${id}`).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/clients", data).then((r) => r.data),
    update: (id: string, data: unknown) =>
      apiClient.put(`/clients/${id}`, data).then((r) => r.data),
    delete: (id: string) => apiClient.delete(`/clients/${id}`),
  },

  sites: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/sites", { params }).then((r) => r.data),
    get: (id: string) => apiClient.get(`/sites/${id}`).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/sites", data).then((r) => r.data),
    update: (id: string, data: unknown) =>
      apiClient.put(`/sites/${id}`, data).then((r) => r.data),
  },

  assets: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/assets", { params }).then((r) => r.data),
    get: (id: string) => apiClient.get(`/assets/${id}`).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/assets", data).then((r) => r.data),
    update: (id: string, data: unknown) =>
      apiClient.put(`/assets/${id}`, data).then((r) => r.data),
    updateStatus: (id: string, status: string) =>
      apiClient.patch(`/assets/${id}/status`, { status }).then((r) => r.data),
  },

  incidents: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/incidents", { params }).then((r) => r.data),
    get: (id: string) => apiClient.get(`/incidents/${id}`).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/incidents", data).then((r) => r.data),
    update: (id: string, data: unknown) =>
      apiClient.put(`/incidents/${id}`, data).then((r) => r.data),
    acknowledge: (id: string) =>
      apiClient.post(`/incidents/${id}/acknowledge`).then((r) => r.data),
    close: (id: string, data: unknown) =>
      apiClient.post(`/incidents/${id}/close`, data).then((r) => r.data),
    timeline: (id: string) =>
      apiClient.get(`/incidents/${id}/timeline`).then((r) => r.data),
    addComment: (id: string, data: unknown) =>
      apiClient.post(`/incidents/${id}/comments`, data).then((r) => r.data),
  },

  alerts: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/alerts", { params }).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/alerts", data).then((r) => r.data),
  },

  tickets: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/tickets", { params }).then((r) => r.data),
    get: (id: string) => apiClient.get(`/tickets/${id}`).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/tickets", data).then((r) => r.data),
    update: (id: string, data: unknown) =>
      apiClient.put(`/tickets/${id}`, data).then((r) => r.data),
    checkin: (id: string, notes?: string) =>
      apiClient.post(`/tickets/${id}/checkin`, { notes }).then((r) => r.data),
    checkout: (id: string, data: unknown) =>
      apiClient.post(`/tickets/${id}/checkout`, data).then((r) => r.data),
    signoff: (id: string, signed_by: string) =>
      apiClient.post(`/tickets/${id}/signoff`, { signed_by }).then((r) => r.data),
  },

  playbooks: {
    list: (params?: Record<string, string | number>) =>
      apiClient.get("/playbooks", { params }).then((r) => r.data),
    create: (data: unknown) => apiClient.post("/playbooks", data).then((r) => r.data),
    execute: (id: string, data?: unknown) =>
      apiClient.post(`/playbooks/${id}/execute`, data ?? {}).then((r) => r.data),
  },

  events: {
    ingest: (data: unknown) => apiClient.post("/events/ingest", data).then((r) => r.data),
  },

  vision: {
    stats: () => apiClient.get("/vision/stats").then((r) => r.data),

    persons: {
      list: (params?: Record<string, string | number>) =>
        apiClient.get("/vision/persons", { params }).then((r) => r.data),
      get: (id: string) => apiClient.get(`/vision/persons/${id}`).then((r) => r.data),
      create: (data: unknown) => apiClient.post("/vision/persons", data).then((r) => r.data),
      update: (id: string, data: unknown) =>
        apiClient.patch(`/vision/persons/${id}`, data).then((r) => r.data),
      delete: (id: string) => apiClient.delete(`/vision/persons/${id}`),
      enroll: (id: string, data: { image_base64: string; is_primary?: boolean }) =>
        apiClient.post(`/vision/persons/${id}/enroll`, data).then((r) => r.data),
    },

    cameras: {
      list: (params?: Record<string, string | number>) =>
        apiClient.get("/vision/cameras", { params }).then((r) => r.data),
      get: (id: string) => apiClient.get(`/vision/cameras/${id}`).then((r) => r.data),
      create: (data: unknown) => apiClient.post("/vision/cameras", data).then((r) => r.data),
      update: (id: string, data: unknown) =>
        apiClient.patch(`/vision/cameras/${id}`, data).then((r) => r.data),
      delete: (id: string) => apiClient.delete(`/vision/cameras/${id}`),
    },

    detections: {
      faces: (params?: Record<string, string | number>) =>
        apiClient.get("/vision/detections/faces", { params }).then((r) => r.data),
    },

    threats: {
      list: (params?: Record<string, string | number>) =>
        apiClient.get("/vision/threats", { params }).then((r) => r.data),
      acknowledge: (id: string, data: { status: string; notes?: string }) =>
        apiClient.patch(`/vision/threats/${id}`, data).then((r) => r.data),
    },

    tracks: {
      list: (params?: Record<string, string | number>) =>
        apiClient.get("/vision/tracks", { params }).then((r) => r.data),
    },
  },

  threatResponse: {
    respond: (data: { action: string; threat_id: string; notes?: string; zone?: string }) =>
      apiClient.post("/threat-response/respond", data).then((r) => r.data),
    bulk: (data: { threat_ids: string[]; action: string; notes?: string }) =>
      apiClient.post("/threat-response/bulk", data).then((r) => r.data),
    protocols: () =>
      apiClient.get("/threat-response/protocols").then((r) => r.data),
  },

  aiStream: {
    livekit: {
      cameraToken: (camera_id: string) =>
        apiClient.post("/ai-stream/livekit/camera-token", { camera_id }).then((r) => r.data),
      enrollmentToken: () =>
        apiClient.post("/ai-stream/livekit/enrollment-token").then((r) => r.data),
      operatorToken: () =>
        apiClient.post("/ai-stream/livekit/operator-token").then((r) => r.data),
      cameraIngress: (camera_id: string, rtsp_url: string) =>
        apiClient.post("/ai-stream/livekit/camera-ingress", { camera_id, rtsp_url }).then((r) => r.data),
    },
    soar: {
      analyze: (data: { threat_id: string; threat: object; camera: object }) =>
        apiClient.post("/ai-stream/soar/analyze", data).then((r) => r.data),
      crewAnalyze: (data: { threat_id: string; threat: object; camera: object }) =>
        apiClient.post("/ai-stream/soar/crew-analyze", data).then((r) => r.data),
    },
    videoAction: {
      analyze: (frames: string[], camera_id?: string) =>
        apiClient.post("/ai-stream/video-action/analyze", { frames, camera_id: camera_id ?? "browser" }).then((r) => r.data),
    },
    diarization: {
      analyze: (audio_base64: string, sample_rate = 16000, format = "wav") =>
        apiClient.post("/ai-stream/diarization/analyze", { audio_base64, sample_rate, format }).then((r) => r.data),
    },
    violence: {
      detect: (frames: string[], camera_id = "browser") =>
        apiClient.post("/ai-stream/violence/detect", { frames, camera_id }).then((r) => r.data),
    },
    scene: {
      understand: (image_base64: string, task = "caption", query?: string) =>
        apiClient.post("/ai-stream/scene/understand", { image_base64, task, query }).then((r) => r.data),
      caption: (image_base64: string) =>
        apiClient.post("/ai-stream/scene/understand", { image_base64, task: "caption" }).then((r) => r.data),
      detectObjects: (image_base64: string, query: string) =>
        apiClient.post("/ai-stream/scene/understand", { image_base64, task: "detect", query }).then((r) => r.data),
      ask: (image_base64: string, question: string) =>
        apiClient.post("/ai-stream/scene/understand", { image_base64, task: "vqa", query: question }).then((r) => r.data),
    },
    ocr: {
      read: (image_base64: string, target = "general") =>
        apiClient.post("/ai-stream/ocr/read", { image_base64, target }).then((r) => r.data),
      readPlate: (image_base64: string) =>
        apiClient.post("/ai-stream/ocr/read", { image_base64, target: "license_plate" }).then((r) => r.data),
    },
    semantic: {
      search: (query: string, limit = 10, index_incidents?: unknown[]) =>
        apiClient.post("/ai-stream/semantic/search", { query, limit, index_incidents }).then((r) => r.data),
    },
    speaker: {
      enroll: (audio_base64: string, speaker_id: string, display_name: string, sample_rate = 16000) =>
        apiClient.post("/ai-stream/speaker/enroll", { audio_base64, speaker_id, display_name, sample_rate }).then((r) => r.data),
      verify: (audio_base64: string, speaker_id: string, sample_rate = 16000) =>
        apiClient.post("/ai-stream/speaker/verify", { audio_base64, speaker_id, sample_rate }).then((r) => r.data),
      gallery: () => apiClient.get("/ai-stream/speaker/gallery").then((r) => r.data),
    },
    reid: {
      gallery: () => apiClient.get("/ai-stream/reid/gallery").then((r) => r.data),
      footprint: (reidId: string) => apiClient.get(`/ai-stream/reid/${reidId}/footprint`).then((r) => r.data),
    },
  },

  biometrics: {
    webauthn: {
      registrationOptions: (data?: { user_id?: string; person_id?: string }) =>
        apiClient.post("/biometrics/webauthn/register/options", data || {}).then((r) => r.data),
      register: (data: {
        credential_id: string;
        public_key: string;
        sign_count?: number;
        device_type?: string;
        backed_up?: boolean;
        transports?: string[];
        friendly_name?: string;
        person_id?: string;
      }) => apiClient.post("/biometrics/webauthn/register", data).then((r) => r.data),
      authenticate: (data: {
        credential_id: string;
        signature: string;
        authenticator_data: string;
        client_data_json: string;
      }) => apiClient.post("/biometrics/webauthn/authenticate", data).then((r) => r.data),
      credentials: () =>
        apiClient.get("/biometrics/webauthn/credentials").then((r) => r.data),
      deleteCredential: (id: string) =>
        apiClient.delete(`/biometrics/webauthn/credentials/${id}`).then((r) => r.data),
    },
    accessLog: {
      list: (params?: Record<string, string | number | boolean>) =>
        apiClient.get("/biometrics/access-log", { params }).then((r) => r.data),
      stats: () =>
        apiClient.get("/biometrics/access-log/stats").then((r) => r.data),
    },
  },
};
