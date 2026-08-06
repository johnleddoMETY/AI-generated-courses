import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.warn(
    "VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY are not set. Copy frontend/.env.example to " +
      "frontend/.env and fill in your Supabase project's values, then restart the dev server."
  );
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "");