<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>WhatsApp Web — Clone (Flask)</title>
  <style>
    /* Minimal styling to mimic WhatsApp Web layout. You can extend with Tailwind if you prefer. */
    :root{--bg:#f0f2f5;--side:#ffffff;--chat:#e9edef;--accent:#128C7E}
    body{margin:0;font-family:Inter, system-ui, Arial;background:var(--bg);height:100vh;display:flex}
    .sidebar{width:340px;background:var(--side);border-right:1px solid #e6e6e6;display:flex;flex-direction:column}
    .search{padding:12px;border-bottom:1px solid #eee}
    .search input{width:100%;padding:8px;border-radius:20px;border:1px solid #ddd}
    .conversations{overflow:auto;flex:1}
    .conv{padding:12px;border-bottom:1px solid #f2f2f2;cursor:pointer;display:flex;gap:12px;align-items:center}
    .conv .avatar{width:48px;height:48px;border-radius:50%;background:#cfd8dc;display:flex;align-items:center;justify-content:center;font-weight:700;color:#fff}
    .conv .meta{flex:1}
    .chat-area{flex:1;display:flex;flex-direction:column}
    .chat-header{height:64px;background:#fff;border-bottom:1px solid #eee;display:flex;align-items:center;padding:0 16px;gap:12px}
    .messages{flex:1;overflow:auto;padding:16px;background:linear-gradient(180deg,#e9edef 0%, #fff 100%)}
    .bubble{max-width:70%;padding:10px 12px;border-radius:8px;margin-bottom:8px;display:inline-block}
    .bubble.in{background:#fff;border:1px solid #dedede;align-self:flex-start}
    .bubble.out{background:var(--accent);color:white;align-self:flex-end}
    .composer{height:68px;background:#fff;border-top:1px solid #eee;display:flex;align-items:center;padding:8px 12px;gap:8px}
    .composer input{flex:1;padding:10px;border-radius:20px;border:1px solid #ddd}
    .send-btn{background:var(--accent);color:white;padding:10px 14px;border-radius:18px;border:none}
    .container{display:flex;flex:1}
    @media (max-width: 700px){
      .sidebar{width:100%;height:240px}
      .chat-area{flex:1}
      body{flex-direction:column}
    }
  </style>
</head>
<body>
  <div class="sidebar">
    <div style="padding:12px;display:flex;align-items:center;gap:12px">
      <div style="width:40px;height:40px;border-radius:50%;background:#128C7E;color:white;display:flex;align-items:center;justify-content:center;font-weight:700">U</div>
      <div>
        <div style="font-weight:700">Your Business</div>
        <div style="font-size:12px;color:#666">Online</div>
      </div>
    </div>
    <div class="search"><input id="search" placeholder="Search or start new chat" /></div>
    <div class="conversations" id="conversations"></div>
  </div>

  <div class="chat-area">
    <div class="chat-header" id="chat-header">
      <div style="font-weight:700">Select a chat</div>
    </div>

    <div class="messages" id="messages" style="display:flex;flex-direction:column"></div>

    <div class="composer">
      <input id="message-input" placeholder="Type a message" />
      <button class="send-btn" id="send-btn">Send</button>
    </div>
  </div>

  <script src="/static/app.js"></script>
</body>
</html>
