const NODE_PALETTE = ['#38bdf8', '#818cf8', '#34d399', '#fb7185', '#fbbf24', '#c084fc'];

let ws = null;
let clusterNodes = [];
let vnodeRing = [];

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = window.location.host || '127.0.0.1:8000';
  ws = new WebSocket(`${protocol}//${host}/ws`);

  ws.onopen = () => {
    document.getElementById('connectionDot').className = 'w-2 h-2 rounded-full bg-emerald-400 ring-4 ring-emerald-500/20 shrink-0';
    document.getElementById('connectionBadge').className = 'text-xs px-2.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono font-medium shrink-0';
    document.getElementById('connectionBadge').textContent = 'Cluster Connected';
    log('WebSocket connected to Python FastAPI backend.', 'info');
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === 'state') {
      clusterNodes = msg.nodes;
      vnodeRing = msg.vnodes;
      renderNodes();
      drawRing();
      updateStats();
      updateConsistencyOptions();
    } else if (msg.type === 'op_result') {
      handleOpResult(msg);
    } else if (msg.type === 'log') {
      log(msg.message, 'info');
    }
  };

  ws.onclose = () => {
    document.getElementById('connectionDot').className = 'w-2 h-2 rounded-full bg-red-400 ring-4 ring-red-500/20 shrink-0';
    document.getElementById('connectionBadge').className = 'text-xs px-2.5 py-0.5 rounded-md bg-red-500/10 text-red-400 border border-red-500/20 font-mono font-medium shrink-0';
    document.getElementById('connectionBadge').textContent = 'Disconnected (Retrying...)';
    log('WebSocket connection closed. Retrying in 2s...', 'err');
    setTimeout(connectWebSocket, 2000);
  };
}

function drawRing() {
  const canvas = document.getElementById('ringCanvas');
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  const cx = w / 2;
  const cy = h / 2;
  const radius = 125;

  ctx.clearRect(0, 0, w, h);

  // Clean, muted titanium ring track
  ctx.beginPath();
  ctx.arc(cx, cy, radius, 0, Math.PI * 2);
  ctx.strokeStyle = '#27272a';
  ctx.lineWidth = 8;
  ctx.stroke();

  // Sample virtual node markers to keep the ring clean and avoid dot clutter (~28 dots)
  const targetDots = 28;
  const step = Math.max(1, Math.round(vnodeRing.length / targetDots));
  const dotsToDraw = vnodeRing.filter((_, idx) => idx % step === 0);

  dotsToDraw.forEach(vn => {
    const angle = vn.hash * Math.PI * 2 - Math.PI / 2;
    const x = cx + Math.cos(angle) * radius;
    const y = cy + Math.sin(angle) * radius;

    const nodeIdx = clusterNodes.findIndex(n => n.id === vn.nodeId);
    const node = clusterNodes.find(n => n.id === vn.nodeId);
    const isOnline = node ? node.online : true;
    const color = isOnline 
      ? (nodeIdx >= 0 ? NODE_PALETTE[nodeIdx % NODE_PALETTE.length] : '#94a3b8') 
      : '#3f3f46';

    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.restore();
  });
}

function renderNodes() {
  const container = document.getElementById('nodesContainer');
  container.innerHTML = '';

  if (!clusterNodes || clusterNodes.length === 0) {
    container.innerHTML = `
      <div class="col-span-full py-8 px-4 rounded-xl border border-dashed border-zinc-800 text-center text-zinc-500 text-xs font-mono">
        No active nodes. Click "+ Add Node" to spin up a TCP Bloom node.
      </div>
    `;
    return;
  }

  clusterNodes.forEach((node, idx) => {
    const color = NODE_PALETTE[idx % NODE_PALETTE.length];
    const card = document.createElement('div');
    card.className = `p-4 rounded-xl border transition-colors ${
      node.online 
        ? 'bg-zinc-900/80 border-zinc-800 hover:border-zinc-700/80 shadow-sm' 
        : 'bg-zinc-950/40 border-zinc-800/50 opacity-60'
    }`;

    const fillWidth = Math.max(node.fill_pct > 0 ? 1 : 0, Math.min(100, node.fill_pct));
    const keysHtml = node.keys && node.keys.length > 0
      ? node.keys.slice(-4).map(k => `<span class="px-2 py-0.5 text-[11px] rounded bg-zinc-950 text-zinc-300 font-mono border border-zinc-800/90 truncate max-w-[120px] font-medium">${k}</span>`).join('')
      : '<span class="text-zinc-600 italic text-[11px] font-mono">No keys stored</span>';

    card.innerHTML = `
      <div class="flex items-center justify-between gap-2 mb-3">
        <div class="flex items-center gap-2.5 min-w-0">
          <span class="w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-white/10" style="background-color: ${color}"></span>
          <div class="min-w-0">
            <div class="flex items-center gap-2">
              <span class="font-bold text-sm text-zinc-100 truncate">${node.name}</span>
              <span class="text-[10px] font-mono font-medium px-2 py-0.5 rounded ${
                node.online 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-zinc-800 text-zinc-400 border border-zinc-700/60'
              }">
                ${node.online ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            <span class="text-xs font-mono text-zinc-400 block truncate">${node.host}</span>
          </div>
        </div>
        <div class="flex items-center gap-1.5 shrink-0">
          <button onclick="toggleNode('${node.id}')" class="px-2.5 py-1 text-xs rounded-lg font-medium transition-colors border ${
            node.online 
              ? 'bg-zinc-800/80 hover:bg-red-950/40 text-zinc-300 hover:text-red-400 border-zinc-700 hover:border-red-800/60' 
              : 'bg-emerald-950/40 hover:bg-emerald-900/50 text-emerald-400 border-emerald-800/60'
          }">
            ${node.online ? 'Kill' : 'Start'}
          </button>
          <button onclick="removeNode('${node.id}')" title="Remove node from cluster" class="px-2 py-1 text-xs rounded-lg font-medium bg-zinc-800/80 hover:bg-rose-950/50 text-zinc-400 hover:text-rose-300 border border-zinc-700 hover:border-rose-800/60 transition-colors">
            ✕
          </button>
        </div>
      </div>

      <!-- Saturation Progress -->
      <div class="space-y-1.5 mb-3 bg-zinc-950/60 p-2.5 rounded-lg border border-zinc-800/80">
        <div class="flex justify-between text-xs font-mono">
          <span class="text-zinc-400 text-xs font-medium">Bit Saturation</span>
          <span class="text-zinc-200 font-semibold text-xs">${node.set_bits} / ${(node.m || 0).toLocaleString()} bits (${node.fill_pct}%)</span>
        </div>
        <div class="w-full bg-zinc-800/80 rounded-full h-1.5 overflow-hidden">
          <div class="bg-rose-500/90 h-1.5 rounded-full transition-all duration-300" style="width: ${fillWidth}%"></div>
        </div>
      </div>

      <!-- Metrics Grid -->
      <div class="grid grid-cols-3 gap-1.5 text-center text-xs mb-3">
        <div class="bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/80">
          <div class="text-zinc-500 text-[10px] uppercase tracking-wider font-mono font-medium">Memory</div>
          <div class="font-mono text-zinc-200 text-xs font-semibold mt-0.5">${((node.memory_bytes || 0) / 1024).toFixed(1)} KB</div>
        </div>
        <div class="bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/80">
          <div class="text-zinc-500 text-[10px] uppercase tracking-wider font-mono font-medium">Est. FPR</div>
          <div class="font-mono text-amber-400/90 text-xs font-semibold mt-0.5">${node.est_fpr}%</div>
        </div>
        <div class="bg-zinc-950/60 p-2 rounded-lg border border-zinc-800/80">
          <div class="text-zinc-500 text-[10px] uppercase tracking-wider font-mono font-medium">Capacity</div>
          <div class="font-mono text-sky-400/90 text-xs font-semibold mt-0.5">${node.capacity}</div>
        </div>
      </div>

      <!-- Stored Keys -->
      <div class="pt-2 border-t border-zinc-800/80">
        <div class="flex items-center justify-between gap-2 mb-1.5">
          <span class="text-xs font-medium text-zinc-400 uppercase tracking-wider font-mono">Routed Keys (${(node.keys || []).length})</span>
        </div>
        <div class="flex flex-wrap gap-1">
          ${keysHtml}
        </div>
      </div>
    `;
    container.appendChild(card);
  });
}

function updateStats() {
  const active = clusterNodes.filter(n => n.online).length;
  const centerStatus = document.getElementById('centerStatus');
  if (centerStatus) {
    centerStatus.textContent = `${active} Active Node${active !== 1 ? 's' : ''}`;
  }
  const centerVnodes = document.getElementById('centerVnodes');
  if (centerVnodes) {
    centerVnodes.textContent = `${vnodeRing.length} Virtual Nodes`;
  }
}

function handleOpResult(msg) {
  const card = document.getElementById('operationResultCard');
  card.classList.remove('hidden');

  const isAdd = msg.action === 'add';
  const targetStr = (msg.targets && msg.targets.length) ? msg.targets.join(', ') : 'None (all nodes offline)';
  const modeStr = msg.mode || '';
  const badge = document.getElementById('resultBadge');
  if (isAdd) {
    badge.textContent = msg.success ? 'ACKNOWLEDGED' : 'FAILED';
    badge.className = msg.success 
      ? 'px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0'
      : 'px-2 py-0.5 rounded text-xs font-mono font-medium bg-red-500/10 text-red-400 border border-red-500/20 shrink-0';
    log(`TCP ADD '${msg.key}' [${modeStr}] -> Targets: [${targetStr}] -> Success: ${msg.success} (${msg.latency_ms}ms)`, msg.success ? 'add' : 'err');
  } else {
    badge.textContent = msg.found ? 'TRUE (EXISTS)' : 'FALSE (NOT FOUND)';
    badge.className = msg.found
      ? 'px-2 py-0.5 rounded text-xs font-mono font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shrink-0'
      : 'px-2 py-0.5 rounded text-xs font-mono font-medium bg-zinc-800 text-zinc-400 border border-zinc-700 shrink-0';
    log(`TCP CONTAINS '${msg.key}' [${modeStr}] -> Targets: [${targetStr}] -> Result: ${msg.found} (${msg.latency_ms}ms)`, 'query');
  }

  document.getElementById('opKey').textContent = msg.key;
  document.getElementById('opMode').textContent = modeStr;
  document.getElementById('opReplicas').textContent = targetStr;
  document.getElementById('resultLatency').textContent = `${msg.latency_ms}ms`;
  document.getElementById('ringKeyInfo').textContent = `Key: ${msg.key}`;
}

function log(msg, type = 'info') {
  const container = document.getElementById('logContainer');
  const placeholder = container.querySelector('.italic');
  if (placeholder) {
    container.innerHTML = '';
  }
  const entry = document.createElement('div');
  const time = new Date().toLocaleTimeString();
  let colorClass = 'text-zinc-400';
  if (type === 'add') colorClass = 'text-rose-400 font-medium';
  if (type === 'query') colorClass = 'text-amber-300/90 font-medium';
  if (type === 'err') colorClass = 'text-red-400 font-medium';

  entry.className = `${colorClass} break-all`;
  entry.innerHTML = `<span class="text-zinc-500">[${time}]</span> ${msg}`;
  container.appendChild(entry);
  container.scrollTop = container.scrollHeight;
}

function setKey(k) {
  document.getElementById('keyInput').value = k;
}

function toggleCustomControls() {
  const isCustom = document.getElementById('repSelect').value === 'custom';
  document.getElementById('customControls').classList.toggle('hidden', !isCustom);
}

function onCustomNChange() {
  const customN = document.getElementById('customN');
  const customW = document.getElementById('customW');
  const m = clusterNodes.length || 1;
  if (!customN || !customW) return;
  let n = parseInt(customN.value, 10) || 1;
  if (n < 1) n = 1;
  if (n > m) n = m;
  customN.value = n;
  customW.max = n;
  if (parseInt(customW.value, 10) > n) {
    customW.value = n;
  }
}

function updateConsistencyOptions() {
  const select = document.getElementById('repSelect');
  if (!select) return;

  const currentVal = select.value;
  const m = clusterNodes.length || 1;

  const options = [];
  options.push({ value: 'single', label: `1 (Single node: N=1, W=1)` });

  if (m >= 2) {
    options.push({ value: 'primary_plus_one', label: `2 (Primary+1: N=2, W=2)` });
  }

  if (m >= 3) {
    options.push({ value: 'quorum', label: `3 (Quorum: N=3, W=2)` });
  }

  const allIdx = options.length + 1;
  options.push({ value: 'all', label: `${allIdx} (ALL: N=${m}, W=${m})` });
  options.push({ value: 'custom', label: `Custom (N & W)...` });

  const validValues = options.map(o => o.value);
  const nextVal = validValues.includes(currentVal)
    ? currentVal
    : (validValues.includes('quorum') ? 'quorum' : (validValues.includes('primary_plus_one') ? 'primary_plus_one' : 'all'));

  select.innerHTML = options.map(o => 
    `<option value="${o.value}" ${o.value === nextVal ? 'selected' : ''}>${o.label}</option>`
  ).join('');

  const customN = document.getElementById('customN');
  const customW = document.getElementById('customW');
  const customHelper = document.getElementById('customHelper');

  if (customN) {
    customN.max = m;
    if (parseInt(customN.value, 10) > m) customN.value = m;
  }
  if (customW && customN) {
    customW.max = customN.value;
    if (parseInt(customW.value, 10) > parseInt(customN.value, 10)) customW.value = customN.value;
  }
  if (customHelper) {
    customHelper.textContent = `(Cluster size: ${m} nodes. Choose N between 1 and ${m})`;
  }

  toggleCustomControls();
}

function performAdd() {
  const key = document.getElementById('keyInput').value.trim();
  const choice = document.getElementById('repSelect').value;
  if (!key || !ws) return;
  const payload = { action: 'add', key, choice };
  if (choice === 'custom') {
    payload.replicas = parseInt(document.getElementById('customN').value, 10) || 1;
    payload.consistency = parseInt(document.getElementById('customW').value, 10) || 1;
  }
  ws.send(JSON.stringify(payload));
}

function performContains() {
  const key = document.getElementById('keyInput').value.trim();
  const choice = document.getElementById('repSelect').value;
  if (!key || !ws) return;
  const payload = { action: 'contains', key, choice };
  if (choice === 'custom') {
    payload.replicas = parseInt(document.getElementById('customN').value, 10) || 1;
    payload.consistency = parseInt(document.getElementById('customW').value, 10) || 1;
  }
  ws.send(JSON.stringify(payload));
}

function toggleNode(nodeId) {
  if (!ws) return;
  ws.send(JSON.stringify({ action: 'toggle_node', node_id: nodeId }));
}

function addRandomNode() {
  if (!ws) return;
  ws.send(JSON.stringify({ action: 'add_node' }));
}

function removeNode(nodeId) {
  if (!ws) return;
  if (clusterNodes.length <= 1) {
    log('Cannot remove node: cluster requires at least 1 node.', 'err');
    return;
  }
  ws.send(JSON.stringify({ action: 'remove_node', node_id: nodeId }));
}

function removeLastNode() {
  if (!ws) return;
  if (clusterNodes.length <= 1) {
    log('Cannot remove node: cluster requires at least 1 node.', 'err');
    return;
  }
  ws.send(JSON.stringify({ action: 'remove_node' }));
}

function syncAllNodes() {
  if (!ws) return;
  ws.send(JSON.stringify({ action: 'sync' }));
}

function clearLogs() {
  document.getElementById('logContainer').innerHTML = '<div class="text-zinc-600 italic">Logs cleared. Waiting for cluster events...</div>';
}

connectWebSocket();
