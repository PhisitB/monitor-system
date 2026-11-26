// Public Supabase settings for viewing metrics from other devices.
// The publishable (anon) key is safe to publish: Row Level Security limits reads
// to emails in allowed_viewers. NEVER put the secret / service_role key here.
// Leave empty to disable cloud mode (local agent only).
window.MONITOR_CONFIG = {
  supabaseUrl: "",
  supabaseKey: "",
};
