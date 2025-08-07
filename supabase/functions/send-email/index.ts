// supabase/functions/send-email/index.ts
// Solution 2: Using updated SMTP library that's compatible with current Deno
import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type'
};
// SMTP sending function using native Deno APIs
async function sendEmailViaSMTP(emailData) {
  const GMAIL_USER = "your-email@gmail.com";
  const GMAIL_APP_PASSWORD = Deno.env.get('GMAIL_APP_PASSWORD');
  const FROM_EMAIL = GMAIL_USER;
  if (!GMAIL_USER || !GMAIL_APP_PASSWORD) {
    throw new Error('Gmail credentials not configured. Please set GMAIL_USER and GMAIL_APP_PASSWORD');
  }
  const subject = `Thank you for your interest!`;
  const textContent = `
Welcome to Our Platform!

Hi ${emailData.name},

Thank you for reaching out and expressing interest in connecting with me!

I hope the PersonaGPT gave you a clear and helpful introduction to my background, skills, and the kind of work I’m passionate about.

If you have any follow-up questions, want to explore opportunities to collaborate, or simply want to continue the conversation, feel free to reply to this email.

I’d love to hear from you!

Best regards,
your name
`;
  // Create simple text email
  const emailBody = [
    `From: your name ${FROM_EMAIL}`,
    `To: ${emailData.email}`,
    `Subject: ${subject}`,
    `MIME-Version: 1.0`,
    `Content-Type: text/plain; charset=UTF-8`,
    `Content-Transfer-Encoding: 7bit`,
    ``,
    textContent
  ].join('\r\n');
  // Connect directly to Gmail SMTP with TLS (port 465)
  console.log('Connecting to Gmail SMTP with TLS...');
  const conn = await Deno.connectTls({
    hostname: "smtp.gmail.com",
    port: 465
  });
  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  // Helper function to read SMTP response with timeout
  async function readResponse() {
    const buffer = new Uint8Array(4096);
    // Add timeout to prevent hanging
    const timeoutPromise = new Promise((_, reject)=>setTimeout(()=>reject(new Error('SMTP read timeout')), 10000));
    const readPromise = conn.read(buffer);
    const n = await Promise.race([
      readPromise,
      timeoutPromise
    ]);
    if (n === null) throw new Error('Connection closed');
    const response = decoder.decode(buffer.subarray(0, n));
    console.log('SMTP Response:', response.trim());
    return response;
  }
  // Helper function to send SMTP command
  async function sendCommand(command) {
    const logCommand = command.includes('AUTH PLAIN') ? 'AUTH PLAIN ***' : command;
    console.log('SMTP Command:', logCommand);
    await conn.write(encoder.encode(command + '\r\n'));
    return await readResponse();
  }
  try {
    // Read initial greeting
    await readResponse();
    // SMTP conversation
    await sendCommand('EHLO localhost');
    // Use AUTH PLAIN for simpler authentication
    const authString = btoa(`\0${GMAIL_USER}\0${GMAIL_APP_PASSWORD}`);
    await sendCommand(`AUTH PLAIN ${authString}`);
    await sendCommand(`MAIL FROM:<${FROM_EMAIL}>`);
    await sendCommand(`RCPT TO:<${emailData.email}>`);
    await sendCommand('DATA');
    // Send email content
    console.log('Sending email content...');
    await conn.write(encoder.encode(emailBody + '\r\n.\r\n'));
    await readResponse(); // Read the response after sending data
    await sendCommand('QUIT');
    console.log('Email sent successfully via native SMTP');
  } catch (error) {
    console.error('SMTP Error:', error);
    throw error;
  } finally{
    try {
      conn.close();
    } catch (closeError) {
      console.error('Error closing connection:', closeError);
    }
  }
}
serve(async (req)=>{
  console.log('Function called with method:', req.method);
  // Handle CORS preflight requests
  if (req.method === 'OPTIONS') {
    return new Response('ok', {
      headers: corsHeaders
    });
  }
  // Declare variables outside try block for proper scoping
  let queueId = null;
  let supabaseClient = null;
  try {
    // Get request body
    let body;
    try {
      const rawBody = await req.text();
      console.log('Raw request body:', rawBody);
      body = JSON.parse(rawBody);
    } catch (parseError) {
      console.error('Failed to parse request body:', parseError);
      return new Response(JSON.stringify({
        error: 'Invalid JSON in request body'
      }), {
        status: 400,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        }
      });
    }
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL');
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
    if (supabaseUrl && supabaseServiceKey) {
      supabaseClient = createClient(supabaseUrl, supabaseServiceKey);
    }
    let emailData;
    // Handle webhook payload structure
    if (body.type === 'INSERT' && body.table === 'user_email_queue' && body.record) {
      console.log('Processing webhook payload');
      const record = body.record;
      queueId = record.id;
      emailData = {
        name: record.name,
        email: record.email,
        id: record.user_id
      };
    } else if (body.record) {
      console.log('Processing direct API call with record');
      emailData = body.record;
    } else {
      console.log('Processing direct API call');
      emailData = body;
    }
    if (!emailData || !emailData.name || !emailData.email) {
      return new Response(JSON.stringify({
        error: 'Missing required fields: name and email',
        received: emailData
      }), {
        status: 400,
        headers: {
          ...corsHeaders,
          'Content-Type': 'application/json'
        }
      });
    }
    // Send email via native SMTP
    console.log('Sending email via native SMTP...');
    await sendEmailViaSMTP(emailData);
    // Update queue status if this was from a queue
    if (queueId && supabaseClient) {
      try {
        const { error } = await supabaseClient.rpc('mark_email_sent', {
          queue_id: queueId,
          success: true
        });
        if (error) {
          console.error('Error updating queue status:', error);
        }
      } catch (rpcError) {
        console.error('RPC call failed:', rpcError);
      }
    }
    return new Response(JSON.stringify({
      success: true,
      message: `Email sent to ${emailData.email}`,
      queueId: queueId,
      timestamp: new Date().toISOString()
    }), {
      status: 200,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      }
    });
  } catch (error) {
    console.error('Function error:', error);
    // Update queue status if this was from a queue
    if (queueId && supabaseClient) {
      try {
        await supabaseClient.rpc('mark_email_sent', {
          queue_id: queueId,
          success: false,
          error_message: error.message
        });
      } catch (dbError) {
        console.error('Failed to update queue status:', dbError);
      }
    }
    return new Response(JSON.stringify({
      error: 'Failed to send email',
      details: error.message,
      timestamp: new Date().toISOString()
    }), {
      status: 500,
      headers: {
        ...corsHeaders,
        'Content-Type': 'application/json'
      }
    });
  }
});
