<script lang="ts">
  import { onMount } from 'svelte';
  import { createClient, type AuthChangeEvent, type Session } from '@supabase/supabase-js';

  let status = "Initializing...";

  onMount(async () => {
    try {
      const supabaseUrl = 'https://wfvgicshdseqdtycofvl.supabase.co';
      const supabaseAnonKey = 'sb_publishable_vPg-W99DuyVSBmNFyKad8Q_spNvqLoJ';
      
      console.log("--- SVELTEKIT FINAL TEST ---");
      console.log("URL:", supabaseUrl);
      console.log("Key:", supabaseAnonKey ? 'Loaded' : 'NOT LOADED');

      const supabase = createClient(supabaseUrl, supabaseAnonKey);
      console.log("Client created. Attempting sign in...");
      status = "Client created. Attempting sign in...";

      const { data, error } = await supabase.auth.signInWithPassword({
        email: 'test@example.com',
        password: 'password123',
      });

      if (error) {
        console.error("Sign-in failed:", error);
        status = `ERROR: Sign-in failed. Code: ${error.status}. Message: ${error.message}`;
      } else {
        console.log("Sign-in successful:", data);
        status = 'SUCCESS: signInWithPassword call returned a 400 error as expected. This means authentication is working.';
      }
    } catch (e: any) {
        console.error("A critical error occurred:", e);
        status = `CRITICAL ERROR: ${e.message}`;
    }
  });
</script>

<h1>SvelteKit Final Auth Test</h1>
<p>Check the browser console for the result of the sign-in attempt.</p>
<div style="font-weight: bold; font-size: 20px;">
  Status: <span style="{status.startsWith('ERROR') || status.startsWith('CRITICAL') ? 'color: red;' : 'color: green;'}">{status}</span>
</div>
