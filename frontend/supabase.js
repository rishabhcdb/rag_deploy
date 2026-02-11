const SUPABASE_URL = "https://uvdgcajudjqizmkupzmr.supabase.co";
const SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV2ZGdjYWp1ZGpxaXpta3Vwem1yIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjY5NDg5MDgsImV4cCI6MjA4MjUyNDkwOH0.ox3-T-GGQGt5FCNPckpjb8cJZtqQtpPJq9K1sRrmosM";

export const supabaseClient = window.supabase.createClient(
  SUPABASE_URL,
  SUPABASE_ANON_KEY
);
