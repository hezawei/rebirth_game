// src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

// 从环境变量中读取 Supabase 配置
const supabaseUrl = import.meta.env.VITE_PUBLIC_SUPABASE_URL as string;
const supabaseAnonKey = import.meta.env.VITE_PUBLIC_SUPABASE_ANON_KEY as string;

// 【调试日志】打印环境变量，以便在线上环境中排查问题
console.log("Supabase URL from env:", supabaseUrl);
console.log("Supabase Anon Key from env:", supabaseAnonKey ? 'Key Loaded (first 5 chars): ' + supabaseAnonKey.substring(0, 5) : 'Key Not Loaded');

export const supabase = createClient(supabaseUrl, supabaseAnonKey)
